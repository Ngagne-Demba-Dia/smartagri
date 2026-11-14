"""État de santé d'un kit et de ses capteurs (doc 16 § 9.3, service 13 `device_health`).

Agrège :
- le dernier point de télémétrie (`soil_sensor_ok`, `bme_ok`, `npk_ok`, `pump_fault`, `battery_mv`) ;
- les équipements rattachés au kit (débitmètre / pompe) ;
- les alertes ouvertes ou acquittées du kit (`since` de l'anomalie).

Tant que le modèle ML `pump_health` (V2, qui exige débitmètre + mesure de puissance) n'est pas chargé,
`pump_failure_48h` vaut honnêtement `None` et la provenance reflète `anomaly_rules` (`source="rules"`).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import as_utc, iso_utc
from app.db.models import Alert, Device, Equipment
from app.services.measurements import latest_measurement
from app.services.provenance import rules_provenance

ENGINE_VERSION = "anomaly-rules-v1"
LOW_BATTERY_MV = 3500
CRITICAL_BATTERY_MV = 3300


def _active_alerts_by_rule(session: Session, device_id: Any) -> dict[str, Alert]:
    rows = session.scalars(
        select(Alert)
        .where(Alert.device_id == device_id, Alert.status != "resolved")
        .order_by(Alert.created_at.desc())
    ).all()
    by_rule: dict[str, Alert] = {}
    for row in rows:
        by_rule.setdefault(row.rule, row)
    return by_rule


def _has_flow_meter(session: Session, device_id: Any) -> bool:
    rows = session.scalars(select(Equipment).where(Equipment.device_id == device_id)).all()
    return any(r.kind == "pump" and r.flow_m3h is not None for r in rows)


def device_health_view(session: Session, settings: Settings, device: Device, now: datetime) -> dict[str, Any]:
    latest = latest_measurement(session, device.id)
    alerts = _active_alerts_by_rule(session, device.id)
    last_seen = as_utc(device.last_seen_at) or (as_utc(latest.ts) if latest else None)
    checked_at = last_seen or now
    stale = last_seen is None or (now - last_seen) > timedelta(hours=settings.device_silent_hours)
    inactive = device.status != "active" or stale

    def flag_state(ok_flag: bool | None, alert_rule: str | None = None) -> tuple[str, str | None]:
        alert = alerts.get(alert_rule) if alert_rule else None
        since = iso_utc(alert.created_at) if alert else (iso_utc(last_seen) if last_seen else None)
        if ok_flag is False:
            return "fault", since
        if inactive:
            return "degraded", since
        if ok_flag is True:
            return "ok", None
        return ("degraded", since) if latest is None else ("ok", None)

    soil_state, soil_since = flag_state(
        latest.soil_sensor_ok if latest else None, "soil_sensor_failure"
    )
    bme_state, bme_since = flag_state(latest.bme_ok if latest else None)
    npk_state, npk_since = flag_state(latest.npk_ok if latest else None)

    if _has_flow_meter(session, device.id):
        flow_state, flow_since = ("degraded", iso_utc(last_seen)) if inactive else ("ok", None)
    else:
        flow_state, flow_since = ("absent", None)

    pump_alert = alerts.get("pump_fault")
    if latest is not None and latest.pump_fault is True:
        pump_state = "fault"
        pump_since = iso_utc(pump_alert.created_at) if pump_alert else iso_utc(latest.ts)
    elif inactive:
        pump_state = "degraded"
        pump_since = iso_utc(last_seen) if last_seen else None
    else:
        pump_state, pump_since = "ok", None

    battery_mv = getattr(latest, "battery_mv", None) if latest is not None else None
    if battery_mv is not None:
        if battery_mv < CRITICAL_BATTERY_MV:
            bat_state, bat_since = "fault", iso_utc(latest.ts) if latest else None
        elif battery_mv < LOW_BATTERY_MV:
            bat_state, bat_since = "degraded", iso_utc(latest.ts) if latest else None
        else:
            bat_state, bat_since = "ok", None
    else:
        bat_state, bat_since = ("degraded", iso_utc(last_seen)) if inactive else ("ok", None)

    sensors = [
        {"sensor": "soil", "state": soil_state, "since": soil_since},
        {"sensor": "bme", "state": bme_state, "since": bme_since},
        {"sensor": "npk", "state": npk_state, "since": npk_since},
        {"sensor": "flow", "state": flow_state, "since": flow_since},
        {"sensor": "pump", "state": pump_state, "since": pump_since},
        {"sensor": "battery", "state": bat_state, "since": bat_since},
    ]

    return {
        "device_id": str(device.id),
        "checked_at": iso_utc(checked_at),
        "sensors": sensors,
        "pump_failure_48h": None,
        "provenance": rules_provenance(
            "anomaly_rules",
            ENGINE_VERSION,
            now,
            data_as_of=last_seen,
            stale=stale,
        ),
    }
