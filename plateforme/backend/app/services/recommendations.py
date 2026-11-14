"""Recommandations par parcelle : irrigation (FAO-56) et état de fertilité (indicatif, sans dose).

Moteur à règles explicables (`regles-fao56-v1`). Entrées : cycle cultural actif (Kc du jour), dernier
point du kit de la parcelle, ET0 de Hargreaves estimée avec les températures min/max du kit sur 24 h et
la latitude de l'exploitation. Une recommandation de même nature datant de moins de 30 min est réutilisée.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import as_utc
from app.db.models import CropCycle, Device, DeviceThreshold, Farm, Field, Measurement, Recommendation
from app.services import agronomy
from app.services.field_weather import today_row
from app.services.measurements import latest_measurement
from app.services.provenance import rules_provenance
from app.services.weather import Forecast

ENGINE_VERSION = "regles-fao56-v1"
REUSE_WINDOW = timedelta(minutes=30)
ET0_WINDOW = timedelta(hours=24)
ET0_MIN_READINGS = 6
DEFAULT_THRESHOLDS = (30, 60)


@dataclass(frozen=True)
class FieldContext:
    field: Field
    farm: Farm | None
    cycle: CropCycle | None
    device: Device | None
    latest: Measurement | None


def load_context(session: Session, field: Field) -> FieldContext:
    farm = session.get(Farm, field.farm_id)
    cycle = session.scalars(
        select(CropCycle).where(CropCycle.field_id == field.id, CropCycle.status == "active")
        .order_by(CropCycle.planted_on.desc()).limit(1)
    ).first()
    device = session.scalars(
        select(Device).where(Device.field_id == field.id, Device.status == "active")
        .order_by(Device.created_at).limit(1)
    ).first()
    latest = latest_measurement(session, device.id) if device else None
    return FieldContext(field, farm, cycle, device, latest)


def crop_state(cycle: CropCycle | None, now: datetime) -> dict[str, Any] | None:
    """Culture, jour depuis le semis/repiquage, stade et Kc FAO-56 du jour."""
    if cycle is None or cycle.planted_on is None or cycle.crop not in agronomy.CROP_PROFILES:
        return None
    profile = agronomy.crop_profile(cycle.crop)
    day = max(0, (now.date() - cycle.planted_on).days)
    return {"crop": profile.code, "crop_name": profile.name_fr, "day": day,
            "stage": agronomy.growth_stage(profile, day), "kc": round(agronomy.kc_for_day(profile, day), 3),
            "kc_source": profile.stage_source}


def estimate_et0(session: Session, device_id: Any, latitude: float | None, now: datetime) -> float | None:
    """ET0 Hargreaves (FAO-56 éq. 52) à partir des températures du kit sur les dernières 24 h."""
    if latitude is None:
        return None
    temps = session.scalars(
        select(Measurement.air_temp_c).where(Measurement.device_id == device_id, Measurement.ts >= now - ET0_WINDOW,
                                             Measurement.air_temp_c.is_not(None))
    ).all()
    if len(temps) < ET0_MIN_READINGS or max(temps) <= min(temps):
        return None
    ra = agronomy.extraterrestrial_radiation(latitude, now.timetuple().tm_yday)
    return round(agronomy.hargreaves_et0(max(temps), min(temps), ra), 2)


def thresholds_for(session: Session, device: Device | None, latest: Measurement | None) -> tuple[int, int, str]:
    """Seuils rapportés par le kit, sinon désirés côté plateforme, sinon valeurs par défaut."""
    if latest is not None and latest.threshold_start_pct is not None and latest.threshold_stop_pct is not None:
        return latest.threshold_start_pct, latest.threshold_stop_pct, "kit"
    row = session.get(DeviceThreshold, device.id) if device else None
    if row is not None:
        return row.desired_start_pct, row.desired_stop_pct, "plateforme"
    return DEFAULT_THRESHOLDS[0], DEFAULT_THRESHOLDS[1], "defaut"


def irrigation_payload(session: Session, ctx: FieldContext, now: datetime,
                       forecast: Forecast | None = None) -> dict[str, Any]:
    crop = crop_state(ctx.cycle, now)
    start, stop, source = thresholds_for(session, ctx.device, ctx.latest)
    latitude = ctx.farm.latitude if ctx.farm else None
    et0 = estimate_et0(session, ctx.device.id, latitude, now) if ctx.device else None
    latest = ctx.latest
    today = today_row(forecast, now)
    if et0 is None and today is not None:
        et0 = today.et0_hargreaves_mm if today.et0_hargreaves_mm is not None else today.et0_mm
    rain = today.precipitation_mm if today else None  # E2 : pluie annoncée sous 24 h (None si météo absente)
    advice = agronomy.recommend_irrigation(agronomy.IrrigationInput(
        soil_moisture_pct=latest.soil_moisture_pct if latest else None,
        soil_sensor_ok=bool(latest and latest.soil_sensor_ok is not False),
        threshold_start_pct=start,
        threshold_stop_pct=stop,
        et0_mm=et0,
        kc=crop["kc"] if crop else None,
        rain_forecast_mm=rain,
        irrigation_type=ctx.field.irrigation_type,
        area_ha=ctx.field.area_ha,
    ))
    measured_at = as_utc(latest.ts) if latest else None
    # `crop` est le code de la culture (chaîne, contrat doc 16 / Frontend) ; le détail est dans `crop_state`.
    return {"advice": asdict(advice), "crop": crop["crop"] if crop else None, "crop_state": crop,
            "et0_mm": et0, "et0_method": "hargreaves" if et0 else None,
            "rain_expected_mm": rain,
            "thresholds": {"start_pct": start, "stop_pct": stop, "source": source},
            "measured_at": measured_at.isoformat() if measured_at else None,
            "device_serial": ctx.device.serial if ctx.device else None}


def fertilization_payload(ctx: FieldContext) -> dict[str, Any]:
    latest = ctx.latest
    usable = latest is not None and latest.npk_ok is not False
    statuses = agronomy.fertility_status(
        latest.n_mgkg if usable and latest else None,
        latest.p_mgkg if usable and latest else None,
        latest.k_mgkg if usable and latest else None,
    )
    return {"nutrients": [asdict(status) for status in statuses], "sensor_ok": usable,
            "caveat": agronomy.FERTILITY_CAVEAT}


def _recent(session: Session, field_id: Any, kind: str, now: datetime) -> Recommendation | None:
    return session.scalars(
        select(Recommendation).where(Recommendation.field_id == field_id, Recommendation.kind == kind,
                                     Recommendation.created_at >= now - REUSE_WINDOW)
        .order_by(Recommendation.created_at.desc()).limit(1)
    ).first()


def _normalized_payload(row: Recommendation) -> dict[str, Any]:
    """Payload sans mutation de la ligne ; répare les lignes d'avant E1 où `crop` était un objet."""
    payload = dict(row.payload)
    crop = payload.get("crop")
    if isinstance(crop, dict):
        payload["crop_state"] = crop
        payload["crop"] = crop.get("crop")
    return payload


def _parse_instant(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def recommendation_provenance(row: Recommendation, payload: dict[str, Any]) -> dict[str, Any]:
    """Provenance doc 16 § 9.2 : moteur à règles (`rules`, repli 2), sans confiance chiffrée."""
    model_name = "irrigation_fao56" if row.kind == "irrigation" else "fertility_rules"
    return rules_provenance(model_name, row.engine_version, row.created_at,
                            data_as_of=_parse_instant(payload.get("measured_at")))


def recommendation_view(row: Recommendation) -> dict[str, Any]:
    created = as_utc(row.created_at)
    payload = _normalized_payload(row)
    return {"id": str(row.id), "kind": row.kind, "engine_version": row.engine_version,
            "created_at": created.isoformat() if created else None, "payload": payload,
            "provenance": recommendation_provenance(row, payload)}


def field_recommendations(session: Session, field: Field, now: datetime,
                          forecast_source: Callable[[], Forecast | None] | None = None) -> list[dict[str, Any]]:
    """Calcule (ou réutilise) les recommandations de la parcelle ; l'appelant valide la transaction.

    `forecast_source` fournit la prévision météo (appelée seulement si l'irrigation doit être recalculée) ;
    sans elle, la pluie annoncée est inconnue et ne retient pas l'arrosage.
    """
    ctx: FieldContext | None = None
    views = []
    for kind in ("irrigation", "fertilization"):
        row = _recent(session, field.id, kind, now)
        if row is None:
            ctx = ctx or load_context(session, field)
            if kind == "irrigation":
                payload = irrigation_payload(session, ctx, now, forecast_source() if forecast_source else None)
            else:
                payload = fertilization_payload(ctx)
            row = Recommendation(organization_id=field.organization_id, field_id=field.id, kind=kind,
                                 payload=payload, engine_version=ENGINE_VERSION, created_at=now)
            session.add(row)
            session.flush()
        views.append(recommendation_view(row))
    return views
