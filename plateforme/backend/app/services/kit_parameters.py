"""Jeux de paramètres poussés aux kits (doc 16 § 6.1 et § 9.3, service 7 `kit_parameters`).

Quatre blocs :
- `seuils` : seuils conseillés `start`/`stop` (`irr_water_balance`, pédotransfert par type de sol) ;
  conformément au doc 16 § 6.1, ils ne remplacent jamais les seuils choisis par l'agriculteur ;
- `npk` : seuils d'alerte N, P, K (mg/kg) indicatifs (`fert_reco`) ;
- `etalonnage` : lectures ADC sec / eau de la sonde d'humidité (`sm_calibration`, `null` sans étalonnage) ;
- `agro` : culture, stade, date de semis et Kc FAO-56 du jour (`phenology_stage`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.base import as_utc, iso_utc
from app.db.models import CropCycle, Device, DeviceParameterSet, DeviceThreshold, Field
from app.services import agronomy
from app.services.measurements import latest_measurement
from app.services.provenance import rules_provenance

ENGINE_VERSION = "regles-v1"
NPK_DEFAULT_ALERTS = {"n": 20, "p": 10, "k": 80}
FACTORY_CALIBRATION = {"adc_sec": 3200, "adc_eau": 1350}
ADVISED_BY_SOIL: tuple[tuple[str, int, int], ...] = (
    ("sableux", 28, 55),
    ("dior", 28, 55),
    ("loamy_sand", 28, 55),
    ("deck", 32, 62),
    ("argileux", 38, 70),
    ("hollald", 38, 70),
)
DEFAULT_ADVISED = (30, 60)


def advised_thresholds(soil_type: str | None) -> dict[str, int]:
    """Seuils conseillés par texture du sol (doc 14 § 4.2.1)."""
    lower = (soil_type or "").lower()
    for token, start, stop in ADVISED_BY_SOIL:
        if token in lower:
            return {"start": start, "stop": stop}
    return {"start": DEFAULT_ADVISED[0], "stop": DEFAULT_ADVISED[1]}


def _agro_block(session: Session, field: Field | None, now: datetime) -> dict[str, Any]:
    if field is None:
        return {"culture": None, "stade": None, "date_semis": None, "kc": None}
    cycle = session.scalars(
        select(CropCycle).where(CropCycle.field_id == field.id, CropCycle.status == "active")
        .order_by(CropCycle.planted_on.desc()).limit(1)
    ).first()
    if cycle is None:
        return {"culture": None, "stade": None, "date_semis": None, "kc": None}
    planted = cycle.planted_on
    stade: str | None = None
    kc: float | None = None
    if planted is not None and cycle.crop in agronomy.CROP_PROFILES:
        profile = agronomy.crop_profile(cycle.crop)
        day = max(0, (now.date() - planted).days)
        stade = agronomy.growth_stage(profile, day)
        kc = round(agronomy.kc_for_day(profile, day), 2)
    return {
        "culture": cycle.crop,
        "stade": stade,
        "date_semis": planted.isoformat() if planted else None,
        "kc": kc,
    }


def _effective_thresholds(session: Session, device: Device) -> tuple[int, int] | None:
    latest = latest_measurement(session, device.id)
    if latest is not None and latest.threshold_start_pct is not None and latest.threshold_stop_pct is not None:
        return latest.threshold_start_pct, latest.threshold_stop_pct
    row = session.get(DeviceThreshold, device.id)
    if row is not None:
        if row.reported_start_pct is not None and row.reported_stop_pct is not None:
            return row.reported_start_pct, row.reported_stop_pct
        return row.desired_start_pct, row.desired_stop_pct
    return None


def latest_parameter_set(session: Session, device_id: Any) -> DeviceParameterSet | None:
    return session.scalars(
        select(DeviceParameterSet)
        .where(DeviceParameterSet.device_id == device_id)
        .order_by(DeviceParameterSet.version.desc())
        .limit(1)
    ).first()


def ensure_parameter_set(session: Session, device: Device, now: datetime) -> DeviceParameterSet:
    """Renvoie le dernier jeu publié pour le kit ou en construit la version initiale."""
    existing = latest_parameter_set(session, device.id)
    field = session.get(Field, device.field_id) if device.field_id else None
    seuils = advised_thresholds(field.soil_type if field else None)
    agro = _agro_block(session, field, now)
    effective = _effective_thresholds(session, device)
    auto_applied = effective == (seuils["start"], seuils["stop"])
    if existing is not None:
        if auto_applied and not existing.applied:
            existing.applied = True
            existing.applied_at = now
            session.flush()
        return existing

    payload: dict[str, Any] = {
        "seuils": seuils,
        "npk": dict(NPK_DEFAULT_ALERTS),
        "etalonnage": dict(FACTORY_CALIBRATION),  # repli courbe usine (ml/catalog/models.yaml sm_calibration)
        "agro": agro,
    }
    row = DeviceParameterSet(
        organization_id=device.organization_id,
        device_id=device.id,
        version=1,
        issued_at=now,
        payload=payload,
        applied=auto_applied,
        applied_at=now if auto_applied else None,
    )
    session.add(row)
    session.flush()
    return row


def acknowledge_parameters(
    session: Session, device: Device, version: int | None, applied: bool, now: datetime
) -> DeviceParameterSet:
    """Acquitte le jeu de paramètres (version explicite ou dernière version publiée)."""
    if version is not None:
        row = session.scalars(
            select(DeviceParameterSet).where(
                DeviceParameterSet.device_id == device.id,
                DeviceParameterSet.version == version,
            )
        ).first()
        if row is None:
            raise not_found("Jeu de paramètres")
    else:
        row = ensure_parameter_set(session, device, now)
    row.applied = applied
    row.applied_at = now if applied else None
    session.flush()
    return row


def parameter_set_view(row: DeviceParameterSet, now: datetime) -> dict[str, Any]:
    issued = as_utc(row.issued_at) or now
    payload = dict(row.payload or {})
    seuils = payload.get("seuils") or {"start": DEFAULT_ADVISED[0], "stop": DEFAULT_ADVISED[1]}
    npk = payload.get("npk") or dict(NPK_DEFAULT_ALERTS)
    etalonnage = payload.get("etalonnage") or dict(FACTORY_CALIBRATION)
    agro = payload.get("agro") or {"culture": None, "stade": None, "date_semis": None, "kc": None}
    return {
        "device_id": str(row.device_id),
        "version": row.version,
        "emis_a": iso_utc(issued),
        "seuils": seuils,
        "npk": npk,
        "etalonnage": etalonnage,
        "agro": agro,
        "applied": bool(row.applied),
        "provenance": {
            "seuils": rules_provenance("irr_water_balance", ENGINE_VERSION, now, data_as_of=issued),
            "npk": rules_provenance("fert_reco", ENGINE_VERSION, now, data_as_of=issued),
            "etalonnage": rules_provenance("sm_calibration", ENGINE_VERSION, now, data_as_of=issued),
            "agro": rules_provenance("phenology_stage", ENGINE_VERSION, now, data_as_of=issued),
        },
    }
