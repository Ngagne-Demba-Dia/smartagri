"""Outils de l'assistant : schémas stricts et exécution avec contrôle d'accès systématique.

Un identifiant proposé par le modèle de langage est traité comme une saisie client : chaque outil repasse
par `app.services.access` (404 si la ressource n'appartient pas aux organisations de l'utilisateur).
Les schémas stricts n'acceptent pas minimum/maximum/minLength/maxLength : les bornes sont exprimées par des
énumérations ou revérifiées ici côté serveur.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import Alert, Device
from app.services import access, agronomy, alerting, farms, measurements, weather
from app.services.assistant.knowledge import default_index
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

PERIODS = {"24h": ("1h", timedelta(hours=24)), "7d": ("1d", timedelta(days=7)), "30d": ("1d", timedelta(days=30))}
FORECAST_DAYS = list(range(1, 8))
URGENCIES = ("normale", "urgente")
MAX_QUERY_CHARS = 300
MAX_REASON_CHARS = 500
OPEN_ALERTS_CAP = 20
VISIT_DEBOUNCE = timedelta(hours=24)
HISTORY_KEYS = ("ts", "n_points", "soil_moisture_pct_avg", "soil_moisture_pct_min", "air_temp_c_max",
                "air_temp_c_min", "air_humidity_pct_avg", "pump_on_ratio")


@dataclass(frozen=True)
class ToolContext:
    session: Session
    settings: Settings
    principal: access.Principal
    now: datetime
    weather_provider: weather.WeatherProvider


@dataclass(frozen=True)
class ToolOutcome:
    content: str
    is_error: bool = False


def _schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


_DEVICE = {"type": "string", "description": "Numéro de série (SA92-000123) ou identifiant UUID du kit."}
_FIELD = {"type": "string", "description": "Identifiant UUID de la parcelle."}

TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"name": "get_latest_measurements", "strict": True,
     "description": "Dernière mesure reçue d'un kit de l'utilisateur (humidité du sol, météo locale, NPK, pompe).",
     "input_schema": _schema({"device_id": _DEVICE})},
    {"name": "get_measurement_history", "strict": True,
     "description": "Historique agrégé d'un kit : heures sur 24 h, jours sur 7 ou 30 jours.",
     "input_schema": _schema({"device_id": _DEVICE, "period": {"type": "string", "enum": list(PERIODS)}})},
    {"name": "get_weather_forecast", "strict": True,
     "description": "Prévision météo quotidienne (températures, pluie, ET0) au droit d'une parcelle, 1 à 7 jours.",
     "input_schema": _schema({"field_id": _FIELD, "days": {"type": "integer", "enum": FORECAST_DAYS}})},
    {"name": "get_crop_profile", "strict": True,
     "description": "Profil FAO-56 d'une culture : coefficients Kc et durée des stades.",
     "input_schema": _schema({"crop": {"type": "string", "enum": sorted(agronomy.CROP_PROFILES)}})},
    {"name": "search_agronomic_knowledge", "strict": True,
     "description": "Recherche dans les fiches agronomiques validées (irrigation, protection, sols, kit). "
                    "Renvoie au plus 3 passages avec leur référence à citer.",
     "input_schema": _schema({"query": {"type": "string", "description": "Question en quelques mots."}})},
    {"name": "get_open_alerts", "strict": True,
     "description": "Alertes non résolues des kits et parcelles de l'utilisateur.",
     "input_schema": _schema({})},
    {"name": "request_advisor_visit", "strict": True,
     "description": "Crée une demande de visite d'un conseiller agricole pour une parcelle (alerte visible "
                    "par la coopérative). À utiliser après accord de l'utilisateur.",
     "input_schema": _schema({"field_id": _FIELD, "reason": {"type": "string"},
                              "urgency": {"type": "string", "enum": list(URGENCIES)}})},
)


def tool_definitions() -> list[dict[str, Any]]:
    """Copie des définitions ; point de cache sur le dernier outil (outils + système forment le préfixe)."""
    tools = [dict(tool) for tool in TOOL_DEFINITIONS]
    tools[-1]["cache_control"] = {"type": "ephemeral"}
    return tools


def _text(args: Mapping[str, Any], key: str, max_chars: int = 100) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AppError("TOOL_INPUT_INVALID", f"Paramètre « {key} » manquant ou vide.", 400)
    if len(value) > max_chars:
        raise AppError("TOOL_INPUT_INVALID", f"Paramètre « {key} » trop long ({max_chars} caractères max).", 400)
    return value.strip()


def _choice(args: Mapping[str, Any], key: str, allowed: Any) -> Any:
    value = args.get(key)
    if isinstance(value, bool) or value not in allowed:
        raise AppError("TOOL_INPUT_INVALID", f"Valeur non autorisée pour « {key} ».", 400)
    return value


def latest_measurements(ctx: ToolContext, args: Mapping[str, Any]) -> dict[str, Any]:
    device = access.get_device_for(ctx.session, ctx.principal, _text(args, "device_id"))
    latest = measurements.latest_measurement(ctx.session, device.id)
    return {"device": device.serial, "measurement": measurements.measurement_view(latest) if latest else None}


def measurement_history(ctx: ToolContext, args: Mapping[str, Any]) -> dict[str, Any]:
    device = access.get_device_for(ctx.session, ctx.principal, _text(args, "device_id"))
    bucket, span = PERIODS[_choice(args, "period", PERIODS)]
    series = measurements.query_series(ctx.session, device.id, bucket, ctx.now - span, ctx.now, ctx.now)
    rows = [{key: row.get(key) for key in HISTORY_KEYS} for row in series.rows]
    return {"device": device.serial, "bucket": bucket, "rows": rows}


def weather_forecast(ctx: ToolContext, args: Mapping[str, Any]) -> dict[str, Any]:
    field = access.get_field_for(ctx.session, ctx.principal, _text(args, "field_id"))
    days = _choice(args, "days", FORECAST_DAYS)
    location = farms.field_location(ctx.session, field)
    if location is None:
        raise AppError("LOCATION_REQUIRED", "Parcelle sans contour ni coordonnées : météo impossible.", 400)
    ttl = timedelta(minutes=ctx.settings.weather_cache_minutes)
    forecast = weather.forecast_with_cache(ctx.session, ctx.weather_provider, location.latitude,
                                           location.longitude, days, ctx.now, ttl)
    return {"field": field.name, **forecast.as_dict()}


def crop_profile(_ctx: ToolContext, args: Mapping[str, Any]) -> dict[str, Any]:
    profile = agronomy.crop_profile(_choice(args, "crop", agronomy.CROP_PROFILES))
    return {**asdict(profile), "season_days": profile.season_days}


def knowledge_search(_ctx: ToolContext, args: Mapping[str, Any]) -> dict[str, Any]:
    hits = default_index().search(_text(args, "query", MAX_QUERY_CHARS))
    return {"results": [hit.as_dict() for hit in hits],
            "note": "Fiches en cours de validation par l'ISRA, l'ANCAR et la DPV."}


def open_alerts(ctx: ToolContext, _args: Mapping[str, Any]) -> dict[str, Any]:
    rows = ctx.session.scalars(
        select(Alert).where(Alert.organization_id.in_(ctx.principal.org_ids), Alert.status != "resolved")
        .order_by(Alert.created_at.desc()).limit(OPEN_ALERTS_CAP)
    ).all()
    return {"alerts": [alerting.alert_view(row) for row in rows]}


def advisor_visit(ctx: ToolContext, args: Mapping[str, Any]) -> dict[str, Any]:
    field = access.get_field_for(ctx.session, ctx.principal, _text(args, "field_id"))
    reason = _text(args, "reason", MAX_REASON_CHARS)
    urgency = _choice(args, "urgency", URGENCIES)
    existing = ctx.session.scalars(
        select(Alert).where(Alert.field_id == field.id, Alert.rule == alerting.ADVISOR_VISIT,
                            Alert.status != "resolved", Alert.created_at >= ctx.now - VISIT_DEBOUNCE)
    ).first()
    if existing is not None:
        return {"created": False, "alert_id": str(existing.id), "message": "Une demande est déjà en cours."}
    device_id = ctx.session.scalars(select(Device.id).where(Device.field_id == field.id).limit(1)).first()
    alert = Alert(organization_id=field.organization_id, field_id=field.id, device_id=device_id,
                  rule=alerting.ADVISOR_VISIT, severity="warning" if urgency == "urgente" else "info",
                  status="open", message=f"Demande de visite conseiller ({urgency}) : {reason}",
                  details={"urgency": urgency, "requested_by": str(ctx.principal.user_id), "via": "assistant"},
                  created_at=ctx.now)
    ctx.session.add(alert)
    ctx.session.flush()
    record_audit(ctx.session, "assistant.advisor_visit", actor_user_id=ctx.principal.user_id,
                 organization_id=field.organization_id, target_type="alert", target_id=alert.id)
    return {"created": True, "alert_id": str(alert.id), "message": "Demande transmise à la coopérative."}


HANDLERS: dict[str, Callable[[ToolContext, Mapping[str, Any]], dict[str, Any]]] = {
    "get_latest_measurements": latest_measurements,
    "get_measurement_history": measurement_history,
    "get_weather_forecast": weather_forecast,
    "get_crop_profile": crop_profile,
    "search_agronomic_knowledge": knowledge_search,
    "get_open_alerts": open_alerts,
    "request_advisor_visit": advisor_visit,
}


def execute_tool(ctx: ToolContext, name: str, args: Any) -> ToolOutcome:
    """Exécute un outil ; toute erreur devient un résultat `is_error` lisible par le modèle (jamais de trace)."""
    handler = HANDLERS.get(name)
    if handler is None:
        return ToolOutcome(f"Outil inconnu : {name}.", is_error=True)
    if not isinstance(args, Mapping):
        return ToolOutcome("Paramètres d'outil invalides.", is_error=True)
    try:
        result = handler(ctx, args)
    except AppError as exc:
        return ToolOutcome(exc.message, is_error=True)
    except ValueError as exc:
        return ToolOutcome(str(exc), is_error=True)
    except Exception:
        logger.exception("Échec de l'outil %s", name)
        return ToolOutcome("Erreur interne de l'outil.", is_error=True)
    return ToolOutcome(json.dumps(result, ensure_ascii=False, default=str))
