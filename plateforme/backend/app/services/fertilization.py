"""Recommandation de fumure par parcelle (doc 16 § 9.3, service 6 `fertilization`, modèle `fert_reco`).

Tant que les barèmes agronomiques officiels ISRA par culture, stade et zone ne sont pas chargés et validés
(`reference` non fourni), le service reste strictement en classes NPK indicatives (`n_kg_ha = None`,
`p_kg_ha = None`, `k_kg_ha = None`, `indicative = True`) conformément à `agronomy.FERTILITY_CAVEAT` et
au catalogue `ml/catalog/models.yaml` (`npk_calibration` / `fert_reco`).
Lorsqu'un barème validé est injecté (`app.state.fertilization_reference`), les doses indicatives sont
calculées par culture et modulées par la classe NPK.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.base import as_utc
from app.db.models import Field
from app.services import agronomy, recommendations
from app.services.provenance import rules_provenance

ENGINE_VERSION = "regles-npk-v1"
CLASS_FACTOR: Mapping[str, float] = {"bas": 1.2, "moyen": 1.0, "eleve": 0.8}


def _overall_npk_class(statuses: list[agronomy.NutrientStatus]) -> str | None:
    levels = [s.level for s in statuses if s.level is not None]
    if not levels:
        return None
    if "bas" in levels:
        return "bas"
    if all(level == "eleve" for level in levels):
        return "eleve"
    return "moyen"


def field_fertilization(
    session: Session,
    field: Field,
    now: datetime,
    reference: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, Any]:
    """Construit la réponse `FertilizationSchema` pour une parcelle."""
    ctx = recommendations.load_context(session, field)
    crop_info = recommendations.crop_state(ctx.cycle, now)
    crop_code = crop_info["crop"] if crop_info else (ctx.cycle.crop if ctx.cycle else None)
    stage = crop_info["stage"] if crop_info else None

    latest = ctx.latest
    usable = latest is not None and latest.npk_ok is not False
    statuses = agronomy.fertility_status(
        latest.n_mgkg if usable and latest else None,
        latest.p_mgkg if usable and latest else None,
        latest.k_mgkg if usable and latest else None,
    )
    npk_class = _overall_npk_class(statuses)
    measured_at = as_utc(latest.ts) if latest else None

    n_kg_ha: float | None = None
    p_kg_ha: float | None = None
    k_kg_ha: float | None = None
    if reference and crop_code and crop_code in reference:
        base = reference[crop_code]
        factor = CLASS_FACTOR.get(npk_class or "moyen", 1.0)
        n_kg_ha = round(base["n"] * factor) if "n" in base else None
        p_kg_ha = round(base["p"] * factor) if "p" in base else None
        k_kg_ha = round(base["k"] * factor) if "k" in base else None

    return {
        "field_id": str(field.id),
        "crop": crop_code,
        "stage": stage,
        "n_kg_ha": n_kg_ha,
        "p_kg_ha": p_kg_ha,
        "k_kg_ha": k_kg_ha,
        "npk_class": npk_class,
        "indicative": True,
        "caveat": agronomy.FERTILITY_CAVEAT,
        "provenance": rules_provenance(
            "fert_reco",
            ENGINE_VERSION,
            now,
            data_as_of=measured_at,
        ),
    }
