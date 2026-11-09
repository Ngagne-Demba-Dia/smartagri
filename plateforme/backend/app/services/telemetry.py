"""Ingestion telemetry.v1 : correspondance des clés du kit, plausibilité, idempotence.

Utilisée par l'API (`POST /v1/telemetry/batch`) et par le worker MQTT. Une valeur hors plage est
stockée à `null` et comptée ; un point en double `(device_id, ts)` est ignoré et compté.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.metrics import count_telemetry
from app.db.base import as_utc
from app.db.models import Device, Measurement
from app.schemas.telemetry import TelemetryPoint
from app.services import alerting
from app.services.devices import apply_reported_thresholds

# Clés du firmware v1.1 (`/data`) → clés plateforme (CONVENTIONS §3).
KIT_KEY_MAP: Mapping[str, str] = {
    "sol": "soil_moisture_pct",
    "temp": "air_temp_c",
    "hum": "air_humidity_pct",
    "pres": "pressure_hpa",
    "n": "n_mgkg",
    "p": "p_mgkg",
    "k": "k_mgkg",
    "pompe": "pump_on",
    "defautPompe": "pump_fault",
    "capteurSolOk": "soil_sensor_ok",
    "bmeOk": "bme_ok",
    "npkOk": "npk_ok",
    "alerteEngrais": "alert_fertilizer",
    "alertePlante": "alert_plant",
    "seuilStart": "threshold_start_pct",
    "seuilStop": "threshold_stop_pct",
}
FLOAT_RANGES: Mapping[str, tuple[float, float]] = {
    "soil_moisture_pct": (0.0, 100.0),
    "air_temp_c": (-10.0, 60.0),
    "air_humidity_pct": (0.0, 100.0),
    "pressure_hpa": (800.0, 1100.0),
}
INT_RANGES: Mapping[str, tuple[int, int]] = {
    "n_mgkg": (0, 1999),
    "p_mgkg": (0, 1999),
    "k_mgkg": (0, 1999),
    "threshold_start_pct": (0, 95),
    "threshold_stop_pct": (5, 100),
}
BOOL_KEYS = ("pump_on", "pump_fault", "soil_sensor_ok", "bme_ok", "npk_ok", "alert_fertilizer", "alert_plant")
METRIC_KEYS = (*FLOAT_RANGES, *INT_RANGES, *BOOL_KEYS)
MIN_TS = datetime(2024, 1, 1, tzinfo=UTC)
MAX_FUTURE = timedelta(minutes=10)


@dataclass(frozen=True)
class CleanedMetrics:
    values: Mapping[str, Any]
    rejected: tuple[str, ...]


@dataclass(frozen=True)
class IngestResult:
    accepted: int = 0
    duplicates: int = 0
    rejected_points: int = 0
    rejected_values: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"accepted": self.accepted, "duplicates": self.duplicates,
                "rejected_points": self.rejected_points, "rejected_values": self.rejected_values}


def map_kit_payload(kit: Mapping[str, Any]) -> dict[str, Any]:
    """Renomme les clés du firmware ; une clé inconnue est conservée telle quelle (puis rejetée au nettoyage)."""
    return {KIT_KEY_MAP.get(key, key): value for key, value in kit.items()}


def _clean_float(value: Any, bounds: tuple[float, float]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if math.isnan(number) or not bounds[0] <= number <= bounds[1]:
        return None
    return number


def _clean_int(value: Any, bounds: tuple[int, int]) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if not isinstance(value, int) or not bounds[0] <= value <= bounds[1]:
        return None
    return value


def _clean_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return None


def _clean_value(key: str, value: Any) -> Any:
    if key in FLOAT_RANGES:
        return _clean_float(value, FLOAT_RANGES[key])
    if key in INT_RANGES:
        return _clean_int(value, INT_RANGES[key])
    return _clean_bool(value)


def clean_metrics(raw: Mapping[str, Any]) -> CleanedMetrics:
    """Plausibilité : valeur absente/null = null sans rejet ; hors plage, NaN, mauvais type ou clé inconnue = rejet."""
    values: dict[str, Any] = {}
    rejected: list[str] = []
    for key, value in raw.items():
        if key not in METRIC_KEYS:
            rejected.append(key)
            continue
        if value is None:
            values[key] = None
            continue
        cleaned = _clean_value(key, value)
        if cleaned is None:
            rejected.append(key)
        values[key] = cleaned
    return CleanedMetrics(values=values, rejected=tuple(rejected))


def normalize_ts(ts: datetime) -> datetime:
    """Horodatage sans fuseau = UTC (contrat telemetry.v1)."""
    return ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)


def ts_plausible(ts: datetime, now: datetime) -> bool:
    return MIN_TS <= ts <= now + MAX_FUTURE


def build_row(point: TelemetryPoint, device_id: UUID, now: datetime) -> tuple[dict[str, Any], int]:
    """Ligne `measurements` prête à insérer et nombre de valeurs rejetées."""
    raw = point.m if point.m is not None else map_kit_payload(point.kit or {})
    cleaned = clean_metrics(raw)
    row: dict[str, Any] = {key: None for key in METRIC_KEYS}
    row.update(cleaned.values)
    row.update(device_id=device_id, ts=normalize_ts(point.ts), received_at=now, source=point.source,
               seq=point.seq, fw=point.fw)
    return row, len(cleaned.rejected)


def _existing_keys(session: Session, rows: Sequence[Mapping[str, Any]]) -> set[tuple[UUID, datetime]]:
    keys: set[tuple[UUID, datetime]] = set()
    for device_id in {row["device_id"] for row in rows}:
        stamps = [row["ts"] for row in rows if row["device_id"] == device_id]
        found = session.execute(
            select(Measurement.ts).where(Measurement.device_id == device_id,
                                         Measurement.ts >= min(stamps), Measurement.ts <= max(stamps))
        ).scalars()
        keys.update((device_id, as_utc(ts)) for ts in found if ts is not None)
    return keys


def insert_ignoring_duplicates(session: Session, rows: Sequence[Mapping[str, Any]]) -> None:
    """INSERT … ON CONFLICT DO NOTHING (PostgreSQL, SQLite) : protège des courses entre répliques."""
    if not rows:
        return
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        session.execute(insert(Measurement), list(rows))
        return
    stmt = dialect_insert(Measurement).on_conflict_do_nothing(index_elements=["device_id", "ts"])
    session.execute(stmt, list(rows))


def _prepare_rows(points: Sequence[TelemetryPoint], devices: Mapping[str, Device],
                  now: datetime) -> tuple[list[dict[str, Any]], IngestResult]:
    rows: dict[tuple[UUID, datetime], dict[str, Any]] = {}
    rejected_points = rejected_values = duplicates = 0
    for point in points:
        ts = normalize_ts(point.ts)
        if not ts_plausible(ts, now):
            rejected_points += 1
            continue
        row, rejected = build_row(point, devices[point.device_id].id, now)
        rejected_values += rejected
        key = (row["device_id"], row["ts"])
        if key in rows:
            duplicates += 1
            continue
        rows[key] = row
    return list(rows.values()), IngestResult(0, duplicates, rejected_points, rejected_values)


def _update_device_state(session: Session, device: Device, rows: Sequence[Mapping[str, Any]],
                         now: datetime) -> None:
    latest = max(rows, key=lambda row: row["ts"])
    last_seen = as_utc(device.last_seen_at)
    if last_seen is None or latest["ts"] > last_seen:
        device.last_seen_at = latest["ts"]
        if latest["fw"]:
            device.firmware_version = latest["fw"]
        apply_reported_thresholds(session, device, latest["threshold_start_pct"], latest["threshold_stop_pct"], now)


def ingest_points(session: Session, settings: Settings, points: Sequence[TelemetryPoint],
                  devices: Mapping[str, Device], now: datetime) -> IngestResult:
    """Insère un lot déjà autorisé ; `devices` associe chaque numéro de série du lot à son kit.

    L'appelant valide la transaction. Les alertes des kits concernés sont réévaluées.
    """
    rows, partial = _prepare_rows(points, devices, now)
    existing = _existing_keys(session, rows) if rows else set()
    fresh = [row for row in rows if (row["device_id"], row["ts"]) not in existing]
    insert_ignoring_duplicates(session, fresh)
    for device in {devices[p.device_id].id: devices[p.device_id] for p in points}.values():
        device_rows = [row for row in fresh if row["device_id"] == device.id]
        if device_rows:
            _update_device_state(session, device, device_rows, now)
            session.flush()
            alerting.evaluate_measurements(session, settings, device, now)
    result = IngestResult(len(fresh), partial.duplicates + len(rows) - len(fresh),
                          partial.rejected_points, partial.rejected_values)
    _count(result)
    return result


def _count(result: IngestResult) -> None:
    count_telemetry("accepted", result.accepted)
    count_telemetry("duplicate", result.duplicates)
    count_telemetry("rejected_point", result.rejected_points)
    count_telemetry("rejected_value", result.rejected_values)
