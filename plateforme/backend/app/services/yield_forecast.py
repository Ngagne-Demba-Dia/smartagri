"""Prévision de rendement (t/ha) du cycle cultural actif d'une parcelle.

Les variables envoyées au modèle sont agronomiques et agrégées (culture, jours depuis le semis, surface,
type de sol et d'irrigation, saison, moyennes des capteurs sur 30 jours) ; aucun identifiant ni donnée
personnelle. Seules les variables déclarées par le modèle (`model_registry.features`) sont transmises.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import iso_utc
from app.db.models import Campaign, CropCycle, Device, Field, Measurement, YieldForecast
from app.services import kpis
from app.services.campaigns import actual_t_ha
from app.services.inference.base import InferenceError, ModelBackend, Prediction, model_unavailable
from app.services.inference.factory import predict_or_503
from app.services.inference.registry import serving_entry

MODEL_NAME = "yield_t_ha"
FEATURE_WINDOW = timedelta(days=30)
RAINY_MONTHS = frozenset(range(6, 11))  # hivernage au Sénégal : juin à octobre
POINT_KEYS = ("p50", "prediction", "yield_t_ha")
CAVEAT = ("Prévision indicative issue d'un modèle statistique : à confronter à l'observation de la parcelle "
          "et à l'avis du conseiller agricole.")
_SENSOR_COLUMNS = ("soil_moisture_pct", "air_temp_c", "air_humidity_pct", "n_mgkg", "p_mgkg", "k_mgkg")


def active_cycle(session: Session, field: Field) -> CropCycle:
    cycle = session.scalars(
        select(CropCycle).where(CropCycle.field_id == field.id, CropCycle.status == "active")
        .order_by(CropCycle.planted_on.desc(), CropCycle.created_at.desc()).limit(1)
    ).first()
    if cycle is None:
        raise AppError("NO_ACTIVE_CYCLE", "Aucun cycle cultural actif sur cette parcelle.", 404)
    return cycle


def _sensor_means(session: Session, device_ids: tuple[Any, ...], start: datetime, end: datetime) -> dict[str, Any]:
    if not device_ids:
        return {f"{column}_mean_30d": None for column in _SENSOR_COLUMNS}
    columns = [func.avg(getattr(Measurement, column)) for column in _SENSOR_COLUMNS]
    values = session.execute(
        select(*columns).where(Measurement.device_id.in_(device_ids), Measurement.ts >= start, Measurement.ts < end)
    ).one()
    return {f"{column}_mean_30d": round(float(value), 2) if value is not None else None
            for column, value in zip(_SENSOR_COLUMNS, values, strict=True)}


def feature_row(session: Session, field: Field, cycle: CropCycle, now: datetime) -> dict[str, Any]:
    """Ligne de variables candidates (sur-ensemble) ; le modèle n'en reçoit que les colonnes déclarées."""
    campaign = session.get(Campaign, cycle.campaign_id) if cycle.campaign_id else None
    planted = cycle.planted_on
    device_ids = tuple(session.scalars(select(Device.id).where(Device.field_id == field.id)).all())
    start = now - FEATURE_WINDOW
    stats = kpis.activity_by_device(session, device_ids, start, now)
    return {
        "crop": cycle.crop,
        "variety": cycle.variety,
        "days_since_planting": (now.date() - planted).days if planted else None,
        "planting_month": planted.month if planted else None,
        "season": campaign.season if campaign else ("rainy" if now.month in RAINY_MONTHS else "dry"),
        "area_ha": field.area_ha,
        "soil_type": field.soil_type,
        "irrigation_type": field.irrigation_type,
        "pump_hours_30d": round(sum(item.pump_hours for item in stats.values()), 2),
        "irrigation_events_30d": sum(item.irrigation_events for item in stats.values()),
        **_sensor_means(session, device_ids, start, now),
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def parse_prediction(value: Prediction) -> tuple[float, float | None, float | None]:
    """(médiane, p10, p90) bornés pour respecter les contraintes : 0 ≤ p10 ≤ médiane ≤ p90."""
    if isinstance(value, dict):
        point = next((_number(value[key]) for key in POINT_KEYS if _number(value.get(key)) is not None), None)
        p10, p90 = _number(value.get("p10")), _number(value.get("p90"))
    else:
        point, p10, p90 = _number(value), None, None
    if point is None:
        raise InferenceError("Prédiction de rendement sans valeur centrale exploitable.")
    point = max(0.0, point)
    p10 = min(max(0.0, p10), point) if p10 is not None else None
    p90 = max(p90, point) if p90 is not None else None
    return round(point, 3), (round(p10, 3) if p10 is not None else None), (round(p90, 3) if p90 is not None else None)


def forecast_view(row: YieldForecast) -> dict[str, Any]:
    return {"id": str(row.id), "model_name": row.model_name, "model_version": row.model_version,
            "predicted_t_ha": row.predicted_t_ha, "p10": row.p10, "p90": row.p90,
            "created_at": iso_utc(row.created_at)}


def latest_forecast(session: Session, cycle: CropCycle) -> YieldForecast | None:
    return session.scalars(
        select(YieldForecast).where(YieldForecast.crop_cycle_id == cycle.id)
        .order_by(YieldForecast.created_at.desc()).limit(1)
    ).first()


def refresh_forecast(session: Session, backend: ModelBackend | None, field: Field, cycle: CropCycle,
                     now: datetime) -> YieldForecast:
    """Calcule une nouvelle prévision via le moteur configuré (503 MODEL_UNAVAILABLE en cas d'échec)."""
    if backend is None:
        raise model_unavailable()
    try:
        entry = serving_entry(session, MODEL_NAME, backend.sources)
        prediction = predict_or_503(backend, MODEL_NAME, [feature_row(session, field, cycle, now)])[0]
        point, p10, p90 = parse_prediction(prediction)
    except InferenceError as exc:
        raise model_unavailable() from exc
    row = YieldForecast(organization_id=cycle.organization_id, crop_cycle_id=cycle.id, model_name=entry.name,
                        model_version=entry.version, predicted_t_ha=point, p10=p10, p90=p90, created_at=now)
    session.add(row)
    session.flush()
    return row


def field_forecast(session: Session, backend: ModelBackend | None, field: Field, now: datetime,
                   refresh: bool) -> dict[str, Any]:
    cycle = active_cycle(session, field)
    row = refresh_forecast(session, backend, field, cycle, now) if refresh else latest_forecast(session, cycle)
    return {"field_id": str(field.id),
            "crop_cycle": {"id": str(cycle.id), "crop": cycle.crop, "status": cycle.status,
                           "planted_on": cycle.planted_on.isoformat() if cycle.planted_on else None},
            "forecast": forecast_view(row) if row else None,
            "actual_t_ha": actual_t_ha(cycle, field.area_ha),
            "caveat": CAVEAT}
