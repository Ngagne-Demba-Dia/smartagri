"""Risques phytosanitaires par parcelle (doc 16 § 9.3, service 9 `pest_risk`, modèle `risk_rules`).

En l'absence du référentiel agronomique validé ISRA / DPV (`phyto.reference` : seuils T, HR, pluie × stade
× culture et plafond <= 3 alertes/mois), le service s'abstient honnêtement (`pests = []`) au lieu d'émettre
des alertes non étalonnées. Lorsqu'un référentiel de règles expertes est injecté (`app.state.pest_reference`),
il évalue les règles météo × culture sans jamais inventer de probabilités ML (`p_outbreak_7d = None`,
`p_outbreak_14d = None`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Field
from app.services import recommendations
from app.services.field_weather import today_row
from app.services.provenance import rules_provenance
from app.services.weather import Forecast

ENGINE_VERSION = "regles-phyto-v1"


@dataclass(frozen=True)
class PestRule:
    pest_code: str
    min_temp_c: float = 20.0
    max_temp_c: float = 36.0
    min_rain_mm: float = 0.0
    stages: tuple[str, ...] = ()


def _evaluate_rule(rule: PestRule, stage: str | None, t_max: float | None, rain_mm: float | None) -> dict[str, Any]:
    factors: list[str] = []
    score = 0
    if stage and (not rule.stages or stage in rule.stages):
        factors.append(f"stade sensible de la culture ({stage})")
        score += 1
    if t_max is not None and rule.min_temp_c <= t_max <= rule.max_temp_c:
        factors.append(f"température maximale favorable ({t_max:.1f} °C)")
        score += 1
    if rain_mm is not None and rain_mm >= rule.min_rain_mm and rule.min_rain_mm > 0:
        factors.append(f"pluie prévue ({rain_mm:.1f} mm)")
        score += 1
    level = "high" if score >= 3 else "medium" if score == 2 else "low"
    if not factors:
        factors.append("surveillance préventive de saison")
    return {
        "pest_code": rule.pest_code,
        "level": level,
        "p_outbreak_7d": None,
        "p_outbreak_14d": None,
        "factors": factors,
    }


def field_pest_risk(
    session: Session,
    field: Field,
    forecast: Forecast | None,
    now: datetime,
    reference: Mapping[str, Sequence[PestRule]] | None = None,
) -> dict[str, Any]:
    """Construit la réponse `PestRiskSchema` pour une parcelle."""
    ctx = recommendations.load_context(session, field)
    crop_info = recommendations.crop_state(ctx.cycle, now)
    crop_code = crop_info["crop"] if crop_info else (ctx.cycle.crop if ctx.cycle else None)
    stage = crop_info["stage"] if crop_info else None
    today = today_row(forecast, now)

    pests: list[dict[str, Any]] = []
    if reference and crop_code and crop_code in reference:
        t_max = today.t_max_c if today else None
        rain = today.precipitation_mm if today else None
        pests = [_evaluate_rule(rule, stage, t_max, rain) for rule in reference[crop_code]]

    data_as_of = forecast.fetched_at if forecast else (ctx.latest.ts if ctx.latest else None)
    stale = bool(forecast and forecast.source == "stale_cache")
    return {
        "field_id": str(field.id),
        "pests": pests,
        "provenance": rules_provenance(
            "risk_rules",
            ENGINE_VERSION,
            now,
            data_as_of=data_as_of,
            stale=stale,
        ),
    }
