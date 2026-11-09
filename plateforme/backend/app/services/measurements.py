"""Séries de mesures : brutes ou agrégées (`1h`, `1d`, `1w`, `1mo`).

Deux chemins produisent les mêmes colonnes :
- PostgreSQL/TimescaleDB : agrégats continus `measurements_1h` et `measurements_1d` (001_init.sql) ;
  `1w` et `1mo` regroupent `measurements_1d` avec `time_bucket`, moyennes pondérées par `n_points`
  (approximation : un capteur absent sur une partie de la journée pèse comme s'il était présent) ;
- autres moteurs (SQLite des tests et du développement) : agrégation en Python.

Seaux en UTC ; la semaine commence le lundi, le mois le 1er (comme `time_bucket`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import as_utc
from app.db.models import Measurement

RAW_ROW_CAP = 10_000
RAW_COLUMNS = (
    "soil_moisture_pct", "air_temp_c", "air_humidity_pct", "pressure_hpa", "n_mgkg", "p_mgkg", "k_mgkg",
    "pump_on", "pump_fault", "soil_sensor_ok", "bme_ok", "npk_ok", "alert_fertilizer", "alert_plant",
    "threshold_start_pct", "threshold_stop_pct",
)
AGG_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("soil_moisture_pct", ("avg", "min", "max")),
    ("air_temp_c", ("avg", "min", "max")),
    ("air_humidity_pct", ("avg",)),
    ("pressure_hpa", ("avg",)),
    ("n_mgkg", ("avg",)),
    ("p_mgkg", ("avg",)),
    ("k_mgkg", ("avg",)),
)


@dataclass(frozen=True)
class BucketSpec:
    max_span: timedelta
    default_span: timedelta


BUCKETS: dict[str, BucketSpec] = {
    "raw": BucketSpec(timedelta(days=7), timedelta(days=1)),
    "1h": BucketSpec(timedelta(days=92), timedelta(days=7)),
    "1d": BucketSpec(timedelta(days=1100), timedelta(days=90)),
    "1w": BucketSpec(timedelta(days=1830), timedelta(days=365)),
    "1mo": BucketSpec(timedelta(days=1830), timedelta(days=730)),
}


@dataclass(frozen=True)
class SeriesResult:
    bucket: str
    start: datetime
    end: datetime
    rows: list[dict[str, Any]]
    truncated: bool = False


def resolve_range(bucket: str, start: datetime | None, end: datetime | None,
                  now: datetime) -> tuple[datetime, datetime]:
    """Bornes [start, end[ en UTC ; plage par défaut selon le seau, plage maximale imposée."""
    spec = BUCKETS.get(bucket)
    if spec is None:
        raise AppError("INVALID_BUCKET", f"bucket doit valoir : {', '.join(BUCKETS)}.", 400)
    end_utc = as_utc(end) or now
    start_utc = as_utc(start) or end_utc - spec.default_span
    if start_utc >= end_utc:
        raise AppError("INVALID_RANGE", "`from` doit précéder `to`.", 400)
    if end_utc - start_utc > spec.max_span:
        raise AppError("RANGE_TOO_LARGE", f"Plage maximale pour {bucket} : {spec.max_span.days} jours.", 400)
    return start_utc, end_utc


def bucket_start(ts: datetime, bucket: str) -> datetime:
    ts = ts.astimezone(UTC)
    if bucket == "1h":
        return ts.replace(minute=0, second=0, microsecond=0)
    day = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == "1d":
        return day
    if bucket == "1w":
        return day - timedelta(days=day.weekday())
    if bucket == "1mo":
        return day.replace(day=1)
    raise ValueError(f"Seau inconnu : {bucket}")


def _metric_aggregates(values: list[float], funcs: tuple[str, ...]) -> dict[str, float | None]:
    if not values:
        return dict.fromkeys(funcs)
    computed = {"avg": sum(values) / len(values), "min": min(values), "max": max(values)}
    return {func: round(computed[func], 3) for func in funcs}


def aggregate_rows(rows: Sequence[Measurement], bucket: str) -> list[dict[str, Any]]:
    """Agrégation Python ; mêmes colonnes que les vues TimescaleDB."""
    groups: dict[datetime, list[Measurement]] = defaultdict(list)
    for row in rows:
        ts = as_utc(row.ts)
        if ts is not None:
            groups[bucket_start(ts, bucket)].append(row)
    result = []
    for start in sorted(groups):
        members = groups[start]
        item: dict[str, Any] = {"ts": start.isoformat(), "n_points": len(members)}
        for metric, funcs in AGG_SPECS:
            values = [float(v) for v in (getattr(m, metric) for m in members) if v is not None]
            aggregates = _metric_aggregates(values, funcs)
            item.update({f"{metric}_{func}": aggregates[func] for func in funcs})
        pump = [m.pump_on for m in members if m.pump_on is not None]
        item["pump_on_ratio"] = round(sum(pump) / len(pump), 3) if pump else None
        result.append(item)
    return result


def _raw_rows(session: Session, device_id: UUID, start: datetime, end: datetime) -> tuple[list[dict[str, Any]], bool]:
    rows = session.scalars(
        select(Measurement)
        .where(Measurement.device_id == device_id, Measurement.ts >= start, Measurement.ts < end)
        .order_by(Measurement.ts).limit(RAW_ROW_CAP + 1)
    ).all()
    return [measurement_view(row) for row in rows[:RAW_ROW_CAP]], len(rows) > RAW_ROW_CAP


def _python_buckets(session: Session, device_id: UUID, start: datetime, end: datetime,
                    bucket: str) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(Measurement)
        .where(Measurement.device_id == device_id, Measurement.ts >= start, Measurement.ts < end)
        .order_by(Measurement.ts)
    ).all()
    return aggregate_rows(rows, bucket)


# --- Chemin TimescaleDB -----------------------------------------------------------------------------------

_CAGG_VIEWS = {"1h": "measurements_1h", "1d": "measurements_1d"}
_ROLLUP_WIDTH = {"1w": "1 week", "1mo": "1 month"}


def _agg_columns() -> list[str]:
    return [f"{metric}_{func}" for metric, funcs in AGG_SPECS for func in funcs]


def _rollup_expr(column: str) -> str:
    """Re-agrégation d'une colonne de measurements_1d (noms internes, jamais saisis)."""
    if column.endswith("_min"):
        return f"min({column})"
    if column.endswith("_max"):
        return f"max({column})"
    return (f"sum({column} * n_points) / nullif(sum(n_points) FILTER (WHERE {column} IS NOT NULL), 0)")


def _pg_sql(bucket: str) -> str:
    columns = [*_agg_columns(), "pump_on_ratio"]
    if bucket in _CAGG_VIEWS:
        selected = ", ".join(columns)
        return (f"SELECT bucket AS ts, n_points, {selected} FROM {_CAGG_VIEWS[bucket]} "
                "WHERE device_id = :device_id AND bucket >= :start AND bucket < :end ORDER BY bucket")
    rollups = ", ".join(f"{_rollup_expr(column)} AS {column}" for column in columns)
    width = _ROLLUP_WIDTH[bucket]
    return (f"SELECT time_bucket(INTERVAL '{width}', bucket) AS ts, sum(n_points)::int AS n_points, {rollups} "
            "FROM measurements_1d WHERE device_id = :device_id AND bucket >= :start AND bucket < :end "
            "GROUP BY 1 ORDER BY 1")


def _pg_buckets(session: Session, device_id: UUID, start: datetime, end: datetime,
                bucket: str) -> list[dict[str, Any]]:
    result = session.execute(text(_pg_sql(bucket)), {"device_id": device_id, "start": start, "end": end})
    items = []
    for row in result.mappings():
        item = {key: (round(float(value), 3) if isinstance(value, float) else value) for key, value in row.items()}
        item["ts"] = as_utc(row["ts"]).isoformat()
        items.append(item)
    return items


def query_series(session: Session, device_id: UUID, bucket: str, start: datetime | None,
                 end: datetime | None, now: datetime) -> SeriesResult:
    start_utc, end_utc = resolve_range(bucket, start, end, now)
    if bucket == "raw":
        rows, truncated = _raw_rows(session, device_id, start_utc, end_utc)
        return SeriesResult(bucket, start_utc, end_utc, rows, truncated)
    if session.get_bind().dialect.name == "postgresql":
        rows = _pg_buckets(session, device_id, start_utc, end_utc, bucket)
    else:
        rows = _python_buckets(session, device_id, start_utc, end_utc, bucket)
    return SeriesResult(bucket, start_utc, end_utc, rows)


def latest_measurement(session: Session, device_id: UUID) -> Measurement | None:
    return session.scalars(
        select(Measurement).where(Measurement.device_id == device_id).order_by(Measurement.ts.desc()).limit(1)
    ).first()


def measurement_view(row: Measurement) -> dict[str, Any]:
    ts = as_utc(row.ts)
    item: dict[str, Any] = {"ts": ts.isoformat() if ts else None, "source": row.source, "fw": row.fw}
    item.update({column: getattr(row, column) for column in RAW_COLUMNS})
    return item
