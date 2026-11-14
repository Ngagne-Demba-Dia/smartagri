"""Besoin en eau net des prochaines 24 h d'une parcelle (doc 16 § 9.1, service 3 `irrigation_need`).

Moteur à règles FAO-56, pas un modèle : ETc = Kc × ET0 ; besoin net = max(0, ETc − pluie annoncée) ; arrosage
reporté si une pluie significative (≥ `RAIN_SKIP_MM`) est annoncée alors qu'il reste un besoin. Volume net
(m³) = mm × ha × 10. Source `rules`, repli 2, sans confiance chiffrée (rien n'est calibré).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.base import as_utc
from app.services import agronomy
from app.services.field_weather import today_row
from app.services.provenance import rules_provenance
from app.services.recommendations import ENGINE_VERSION, FieldContext, crop_state, estimate_et0
from app.services.weather import DailyWeather, Forecast

WINDOW_HOURS = 24
MODEL_NAME = "irrigation_fao56"
NOT_COMPUTABLE = "Besoin non calculable : %s."


def _missing_inputs(crop: dict[str, Any] | None, et0: float | None) -> str | None:
    if crop is None:
        return "aucun cycle cultural actif avec un coefficient cultural"
    if et0 is None:
        return "évapotranspiration indisponible (kit sans assez de relevés et pas de prévision météo)"
    return None


def _et0(session: Session, ctx: FieldContext, forecast_day: DailyWeather | None, now: datetime) -> float | None:
    """ET0 du jour : Hargreaves du kit (24 h), sinon ET0 fournisseur, sinon Hargreaves de la prévision."""
    latitude = ctx.farm.latitude if ctx.farm else None
    if ctx.device is not None:
        measured = estimate_et0(session, ctx.device.id, latitude, now)
        if measured is not None:
            return measured
    if forecast_day is None:
        return None
    return forecast_day.et0_mm if forecast_day.et0_mm is not None else forecast_day.et0_hargreaves_mm


def irrigation_need(session: Session, ctx: FieldContext, forecast: Forecast | None, now: datetime) -> dict[str, Any]:
    """Charge utile de `GET /fields/{id}/irrigation-need` (forme de `IrrigationNeedSchema` du Frontend)."""
    crop = crop_state(ctx.cycle, now)
    day = today_row(forecast, now)
    rain = day.precipitation_mm if day else None
    et0 = _et0(session, ctx, day, now)
    missing = _missing_inputs(crop, et0)

    need_mm, volume_m3, defer, reason = 0.0, None, False, None
    if missing is not None:
        reason = NOT_COMPUTABLE % missing
    else:
        etc = float(crop["kc"]) * float(et0)  # type: ignore[index, arg-type]
        need_mm = round(max(0.0, etc - (rain or 0.0)), 2)
        if ctx.field.area_ha:
            volume_m3 = round(need_mm * ctx.field.area_ha * agronomy.M3_PER_MM_HA, 1)
        if need_mm > 0 and rain is not None and rain >= agronomy.RAIN_SKIP_MM:
            defer = True
            reason = f"Pluie annoncée ({rain:.0f} mm sous 24 h) : arrosage reporté."

    return {"field_id": str(ctx.field.id), "window_hours": WINDOW_HOURS, "need_mm": need_mm,
            "volume_m3": volume_m3, "defer": defer, "defer_reason": reason, "rain_expected_mm": rain,
            "provenance": _provenance(ctx, forecast, now)}


def _provenance(ctx: FieldContext, forecast: Forecast | None, now: datetime) -> dict[str, Any]:
    """`data_as_of` : la donnée la plus récente utilisée (prévision, sinon dernier relevé du kit)."""
    if forecast is not None:
        return rules_provenance(MODEL_NAME, ENGINE_VERSION, now, data_as_of=forecast.fetched_at,
                                stale=forecast.source == "stale_cache")
    measured = as_utc(ctx.latest.ts) if ctx.latest else None
    return rules_provenance(MODEL_NAME, ENGINE_VERSION, now, data_as_of=measured)
