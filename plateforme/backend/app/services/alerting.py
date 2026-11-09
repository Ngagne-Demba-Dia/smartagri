"""Règles d'alerte, anti-rebond et résolution automatique.

| Règle                     | Déclenchement                                                   | Résolution auto |
|---------------------------|-----------------------------------------------------------------|-----------------|
| `soil_sensor_failure`     | dernier point : `soil_sensor_ok = false`                         | oui             |
| `pump_fault`              | dernier point : `pump_fault = true`                              | oui             |
| `dry_soil_persistent`     | ≥ 3 lectures sous le seuil de démarrage couvrant ≥ 75 % de H     | oui             |
| `device_silent`           | aucun point depuis `DEVICE_SILENT_HOURS` (tâche périodique)      | oui (au retour) |
| `disease_suspected`       | N diagnostics consécutifs suspects/malades, confiance ≥ seuil    | non (humain)    |
| `advisor_visit_requested` | demande de visite (assistant)                                   | non             |

Anti-rebond : au plus une alerte non résolue par (kit, règle). Sous PostgreSQL l'index unique partiel
`uq_alerts_device_rule_active` arbitre les courses entre répliques (insertion dans un SAVEPOINT).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import as_utc, iso_utc
from app.db.models import Alert, Device, DeviceThreshold, Diagnosis, Measurement

SOIL_SENSOR_FAILURE = "soil_sensor_failure"
PUMP_FAULT = "pump_fault"
DRY_SOIL = "dry_soil_persistent"
DEVICE_SILENT = "device_silent"
DISEASE_SUSPECTED = "disease_suspected"
ADVISOR_VISIT = "advisor_visit_requested"

DRY_SOIL_MIN_READINGS = 3
DRY_SOIL_MIN_COVERAGE = 0.75
DISEASE_LABELS = frozenset({"suspect", "sick"})


@dataclass(frozen=True)
class AlertDraft:
    rule: str
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def active_alert(session: Session, device_id: Any, rule: str) -> Alert | None:
    return session.scalars(
        select(Alert).where(Alert.device_id == device_id, Alert.rule == rule, Alert.status != "resolved")
    ).first()


def _insert(session: Session, alert: Alert) -> bool:
    if session.get_bind().dialect.name != "postgresql":
        session.add(alert)
        session.flush()
        return True
    try:
        with session.begin_nested():
            session.add(alert)
        return True
    except IntegrityError:
        return False


def raise_alert(session: Session, device: Device, draft: AlertDraft, now: datetime) -> Alert | None:
    """Crée l'alerte sauf si une alerte non résolue existe déjà pour (kit, règle)."""
    if active_alert(session, device.id, draft.rule) is not None:
        return None
    alert = Alert(
        organization_id=device.organization_id,
        device_id=device.id,
        field_id=device.field_id,
        rule=draft.rule,
        severity=draft.severity,
        status="open",
        message=draft.message,
        details=draft.details or None,
        created_at=now,
    )
    return alert if _insert(session, alert) else None


def resolve_alert(session: Session, device_id: Any, rule: str, now: datetime) -> bool:
    alert = active_alert(session, device_id, rule)
    if alert is None:
        return False
    alert.status, alert.resolved_at = "resolved", now
    return True


def acknowledge(alert: Alert, user_id: Any, now: datetime) -> Alert:
    if alert.status == "open":
        alert.status, alert.acknowledged_at, alert.acknowledged_by = "acknowledged", now, user_id
    return alert


# --- Règles fondées sur la télémétrie ---------------------------------------------------------------------

def _latest_measurement(session: Session, device_id: Any) -> Measurement | None:
    return session.scalars(
        select(Measurement).where(Measurement.device_id == device_id).order_by(Measurement.ts.desc()).limit(1)
    ).first()


def _start_threshold(session: Session, device: Device, latest: Measurement) -> int | None:
    if latest.threshold_start_pct is not None:
        return latest.threshold_start_pct
    row = session.get(DeviceThreshold, device.id)
    return row.desired_start_pct if row else None


def _soil_readings(session: Session, device_id: Any, since: datetime, until: datetime) -> Sequence[Measurement]:
    return session.scalars(
        select(Measurement)
        .where(Measurement.device_id == device_id, Measurement.ts >= since, Measurement.ts <= until,
               Measurement.soil_moisture_pct.is_not(None), Measurement.soil_sensor_ok.is_not(False))
        .order_by(Measurement.ts)
    ).all()


def dry_soil_state(readings: Sequence[Measurement], start_pct: int, window: timedelta) -> str:
    """'raise', 'resolve' ou 'keep' pour la règle de sol sec persistant."""
    if not readings:
        return "keep"
    if (readings[-1].soil_moisture_pct or 0.0) >= start_pct:
        return "resolve"
    if len(readings) < DRY_SOIL_MIN_READINGS:
        return "keep"
    if any((r.soil_moisture_pct or 0.0) >= start_pct for r in readings):
        return "keep"
    first, last = as_utc(readings[0].ts), as_utc(readings[-1].ts)
    if first is None or last is None or last - first < window * DRY_SOIL_MIN_COVERAGE:
        return "keep"
    return "raise"


def _evaluate_dry_soil(session: Session, settings: Settings, device: Device, latest: Measurement,
                       now: datetime) -> None:
    start_pct = _start_threshold(session, device, latest)
    latest_ts = as_utc(latest.ts)
    if start_pct is None or latest_ts is None:
        return
    window = timedelta(hours=settings.dry_soil_hours)
    readings = _soil_readings(session, device.id, latest_ts - window, latest_ts)
    state = dry_soil_state(readings, start_pct, window)
    if state == "resolve":
        resolve_alert(session, device.id, DRY_SOIL, now)
    elif state == "raise":
        message = (f"Sol sec depuis plus de {settings.dry_soil_hours:g} h malgré le seuil de démarrage "
                   f"({start_pct} %) : vérifier l'arrivée d'eau et la pompe.")
        details = {"start_pct": start_pct, "readings": len(readings),
                   "last_moisture_pct": readings[-1].soil_moisture_pct}
        raise_alert(session, device, AlertDraft(DRY_SOIL, "warning", message, details), now)


def _evaluate_flag(session: Session, device: Device, flag: bool | None, draft: AlertDraft, now: datetime) -> None:
    """Alerte binaire : `flag` vrai = défaut présent, faux = résolu, None = inconnu (rien)."""
    if flag is True:
        raise_alert(session, device, draft, now)
    elif flag is False:
        resolve_alert(session, device.id, draft.rule, now)


def evaluate_measurements(session: Session, settings: Settings, device: Device, now: datetime) -> None:
    """Réévalue les règles après une ingestion (le kit a donné signe de vie)."""
    latest = _latest_measurement(session, device.id)
    if latest is None:
        return
    resolve_alert(session, device.id, DEVICE_SILENT, now)
    sensor_down = None if latest.soil_sensor_ok is None else not latest.soil_sensor_ok
    _evaluate_flag(session, device, sensor_down, AlertDraft(
        SOIL_SENSOR_FAILURE, "critical", "Capteur d'humidité du sol en défaut : l'irrigation automatique est "
        "suspendue par le kit. Vérifier le câblage de la sonde."), now)
    _evaluate_flag(session, device, latest.pump_fault, AlertDraft(
        PUMP_FAULT, "critical", "Défaut de pompe signalé par le kit (marche à sec ou blocage) : "
        "vérifier la réserve d'eau et la pompe."), now)
    _evaluate_dry_soil(session, settings, device, latest, now)


# --- Diagnostics (vision) ---------------------------------------------------------------------------------

def disease_draft(diagnoses: Sequence[Diagnosis], settings: Settings) -> AlertDraft | None:
    """N derniers diagnostics (du plus récent au plus ancien) tous suspects/malades et assez confiants."""
    needed = settings.disease_consecutive
    if len(diagnoses) < needed:
        return None
    newest = as_utc(diagnoses[0].captured_at)
    oldest = as_utc(diagnoses[needed - 1].captured_at)
    if newest is None or oldest is None or newest - oldest > timedelta(hours=settings.disease_window_hours):
        return None
    recent = diagnoses[:needed]
    if any(d.label not in DISEASE_LABELS or d.confidence < settings.disease_min_confidence for d in recent):
        return None
    severity = "critical" if all(d.label == "sick" for d in recent) else "warning"
    codes = sorted({d.disease_code for d in recent if d.disease_code})
    message = (f"Maladie suspectée sur {needed} diagnostics consécutifs (verdict indicatif du modèle de vision) : "
               "faire confirmer par un agent agricole avant tout traitement.")
    return AlertDraft(DISEASE_SUSPECTED, severity, message, {"disease_codes": codes, "count": needed})


def evaluate_diagnoses(session: Session, settings: Settings, device: Device, now: datetime) -> Alert | None:
    """Jamais résolue automatiquement : un humain confirme ou infirme."""
    diagnoses = session.scalars(
        select(Diagnosis).where(Diagnosis.device_id == device.id)
        .order_by(Diagnosis.captured_at.desc()).limit(settings.disease_consecutive)
    ).all()
    draft = disease_draft(diagnoses, settings)
    return raise_alert(session, device, draft, now) if draft else None


# --- Tâche périodique -------------------------------------------------------------------------------------

def sweep_silent_devices(session: Session, settings: Settings, now: datetime) -> int:
    """Alerte `device_silent` pour les kits actifs muets depuis `device_silent_hours`."""
    cutoff = now - timedelta(hours=settings.device_silent_hours)
    devices = session.scalars(
        select(Device).where(Device.status == "active", Device.last_seen_at.is_not(None),
                             Device.last_seen_at < cutoff)
    ).all()
    raised = 0
    for device in devices:
        message = (f"Aucune donnée reçue depuis plus de {settings.device_silent_hours:g} h : vérifier "
                   "l'alimentation du kit et la synchronisation avec le téléphone relais.")
        last_seen = as_utc(device.last_seen_at)
        details = {"last_seen_at": last_seen.isoformat() if last_seen else None}
        if raise_alert(session, device, AlertDraft(DEVICE_SILENT, "warning", message, details), now):
            raised += 1
    return raised


def alert_view(alert: Alert) -> dict[str, Any]:
    return {
        "id": str(alert.id),
        "organization_id": str(alert.organization_id),
        "device_id": str(alert.device_id) if alert.device_id else None,
        "field_id": str(alert.field_id) if alert.field_id else None,
        "rule": alert.rule,
        "severity": alert.severity,
        "status": alert.status,
        "message": alert.message,
        "details": alert.details,
        "created_at": iso_utc(alert.created_at),
        "acknowledged_at": iso_utc(alert.acknowledged_at),
        "resolved_at": iso_utc(alert.resolved_at),
    }
