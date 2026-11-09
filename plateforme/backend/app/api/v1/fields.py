"""Parcelle : recommandations, météo, prévision de rendement et cycles culturaux."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    get_model_backend,
    get_now,
    get_principal,
    get_request_meta,
    get_session,
    get_settings,
    get_weather_provider,
)
from app.core.config import Settings
from app.core.constants import CROP_CYCLE_WRITERS
from app.core.envelope import ok
from app.core.errors import AppError
from app.schemas.planning import CropCycleIn, CropCyclePatch
from app.services import access, crop_cycles, farms, recommendations, weather, yield_forecast
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit
from app.services.inference.base import ModelBackend

router = APIRouter(tags=["fields"])


@router.get("/fields/{field_id}")
def get_field(field_id: str, principal: Principal = Depends(get_principal),
              session: Session = Depends(get_session)) -> dict[str, Any]:
    """Détail d'une parcelle avec son cycle cultural actif (404 hors de l'organisation)."""
    field = access.get_field_for(session, principal, field_id)
    cycle = farms.active_cycles(session, [field.id]).get(field.id)
    return ok({**farms.field_view(field), "active_cycle": crop_cycles.cycle_view(cycle) if cycle else None})


@router.get("/fields/{field_id}/recommendations")
def field_recommendations(field_id: str, principal: Principal = Depends(get_principal),
                          session: Session = Depends(get_session),
                          now: datetime = Depends(get_now)) -> dict[str, Any]:
    field = access.get_field_for(session, principal, field_id)
    items = recommendations.field_recommendations(session, field, now)
    session.commit()
    return ok(items)


@router.get("/fields/{field_id}/weather")
def field_weather(field_id: str, days: int = Query(7), principal: Principal = Depends(get_principal),
                  session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
                  provider: weather.WeatherProvider = Depends(get_weather_provider),
                  now: datetime = Depends(get_now)) -> dict[str, Any]:
    field = access.get_field_for(session, principal, field_id)
    location = farms.field_location(session, field)
    if location is None:
        raise AppError("LOCATION_REQUIRED", "Parcelle sans contour ni coordonnées d'exploitation.", 400)
    ttl = timedelta(minutes=settings.weather_cache_minutes)
    forecast = weather.forecast_with_cache(session, provider, location.latitude, location.longitude, days, now, ttl)
    session.commit()
    return ok({"field_id": str(field.id), "location_source": location.source, **forecast.as_dict()})


@router.get("/fields/{field_id}/yield-forecast")
def field_yield_forecast(field_id: str, refresh: bool = Query(False), principal: Principal = Depends(get_principal),
                         session: Session = Depends(get_session),
                         backend: ModelBackend | None = Depends(get_model_backend),
                         now: datetime = Depends(get_now)) -> dict[str, Any]:
    field = access.get_field_for(session, principal, field_id)
    result = yield_forecast.field_forecast(session, backend, field, now, refresh)
    if refresh:
        session.commit()
    return ok(result)


@router.get("/fields/{field_id}/crop-cycles")
def list_crop_cycles(field_id: str, principal: Principal = Depends(get_principal),
                     session: Session = Depends(get_session)) -> dict[str, Any]:
    field = access.get_field_for(session, principal, field_id)
    return ok([crop_cycles.cycle_view(cycle) for cycle in crop_cycles.list_cycles(session, field)])


@router.post("/fields/{field_id}/crop-cycles", status_code=201)
def create_crop_cycle(field_id: str, body: CropCycleIn, principal: Principal = Depends(get_principal),
                      session: Session = Depends(get_session),
                      meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    field = access.get_field_for(session, principal, field_id)
    access.require_role(principal, field.organization_id, CROP_CYCLE_WRITERS)
    cycle = crop_cycles.create_cycle(session, principal, field, body.values())
    record_audit(session, "crop_cycle.create", actor_user_id=principal.user_id,
                 organization_id=cycle.organization_id, target_type="crop_cycle", target_id=cycle.id, meta=meta)
    session.commit()
    return ok(crop_cycles.cycle_view(cycle))


@router.patch("/crop-cycles/{cycle_id}")
def update_crop_cycle(cycle_id: str, body: CropCyclePatch, principal: Principal = Depends(get_principal),
                      session: Session = Depends(get_session),
                      meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    cycle = crop_cycles.get_cycle_for(session, principal, cycle_id)
    access.require_role(principal, cycle.organization_id, CROP_CYCLE_WRITERS)
    changes = body.changes()
    crop_cycles.update_cycle(session, principal, cycle, changes)
    record_audit(session, "crop_cycle.update", actor_user_id=principal.user_id,
                 organization_id=cycle.organization_id, target_type="crop_cycle", target_id=cycle.id, meta=meta,
                 details={"fields": sorted(changes)})
    session.commit()
    return ok(crop_cycles.cycle_view(cycle))
