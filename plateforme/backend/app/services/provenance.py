"""Bloc de provenance du doc 16 § 9.2 (baseline v1) : tout résultat d'IA ou de règle le porte.

Forme produite (clés exactement celles du contrat) :
    {model_name, model_version, source(agriml|octopus|rules), fallback_step 0..2, computed_at,
     data_as_of|null, stale, confidence{kind, value, p10, p90, calibrated}}
Les règles de cohérence du schéma Zod du Frontend sont reprises ici : un bloc invalide est une erreur de
programmation (ValueError), jamais envoyé au client.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.base import as_utc

SOURCES = frozenset({"agriml", "octopus", "rules"})
CONFIDENCE_KINDS = frozenset({"probability", "interval", "class_probability", "none"})
MAX_FALLBACK_STEP = 2

# Source de provenance selon la ligne `model_registry.source` ou le moteur d'inférence.
RULES_ENGINE = "rules"


def confidence(kind: str = "none", *, value: float | None = None, p10: float | None = None,
               p90: float | None = None, calibrated: bool = False) -> dict[str, Any]:
    """Bloc de confiance ; `none` = aucune valeur (règles déterministes)."""
    if kind not in CONFIDENCE_KINDS:
        raise ValueError(f"confidence.kind inconnu : {kind!r}.")
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence.value doit être dans [0, 1].")
    if kind == "none" and (value is not None or p10 is not None or p90 is not None):
        raise ValueError("kind « none » : aucune valeur de confiance.")
    if kind == "interval" and (p10 is None or p90 is None or p10 > p90):
        raise ValueError("kind « interval » : p10 ≤ p90 obligatoires.")
    return {"kind": kind, "value": value, "p10": p10, "p90": p90, "calibrated": calibrated}


def _iso(moment: datetime | None) -> str | None:
    aware = as_utc(moment) if moment is not None else None
    return aware.isoformat() if aware else None


def provenance(*, model_name: str, model_version: str, source: str, computed_at: datetime,
               fallback_step: int = 0, data_as_of: datetime | None = None, stale: bool = False,
               conf: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bloc de provenance complet et validé."""
    if source not in SOURCES:
        raise ValueError(f"provenance.source inconnue : {source!r}.")
    if not 0 <= fallback_step <= MAX_FALLBACK_STEP:
        raise ValueError("provenance.fallback_step doit valoir 0, 1 ou 2.")
    if not model_name or not model_version:
        raise ValueError("model_name et model_version sont obligatoires.")
    return {"model_name": model_name, "model_version": model_version, "source": source,
            "fallback_step": fallback_step, "computed_at": _iso(computed_at), "data_as_of": _iso(data_as_of),
            "stale": stale, "confidence": conf or confidence()}


def rules_provenance(model_name: str, model_version: str, computed_at: datetime, *,
                     data_as_of: datetime | None = None, stale: bool = False) -> dict[str, Any]:
    """Résultat d'un moteur à règles : source `rules`, repli 2 (doc 16 § 5.5), aucune confiance chiffrée."""
    return provenance(model_name=model_name, model_version=model_version, source=RULES_ENGINE,
                      computed_at=computed_at, fallback_step=MAX_FALLBACK_STEP, data_as_of=data_as_of, stale=stale)
