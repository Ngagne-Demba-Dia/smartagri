"""Chaîne de repli de l'inférence (doc 16 § 5.5, R12) — version minimale de D0.

    étape 0 : paquet local vérifié        (backend « local »)
    étape 1 : lot OctOpus                 (backend « octopus »)
    étape 2 : règles agronomiques         (fonction `rules` fournie par l'appelant)
    étape 3 : MODEL_UNAVAILABLE (503)     (rien n'a répondu)

Un backend qui échoue (InferenceError) fait passer à l'étape suivante ; le détail reste dans les journaux.
Le résultat dit quelle étape a répondu, pour alimenter le bloc de provenance (`fallback_step`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.services.inference.base import FeatureRow, InferenceError, ModelBackend, Prediction, model_unavailable
from app.services.provenance import MAX_FALLBACK_STEP, RULES_ENGINE

logger = logging.getLogger(__name__)

# Rang de l'étape d'un moteur d'inférence dans la chaîne.
BACKEND_STEPS = {"local": 0, "octopus": 1}

RulesFallback = Callable[[Sequence[FeatureRow]], list[Prediction]]


@dataclass(frozen=True)
class FallbackResult:
    predictions: list[Prediction]
    step: int  # 0 paquet local, 1 OctOpus, 2 règles
    engine: str  # nom du moteur qui a répondu, ou « rules »

    @property
    def used_fallback(self) -> bool:
        return self.step > 0


def predict_with_fallback(backends: Sequence[ModelBackend | None], model_name: str,
                          rows: Sequence[FeatureRow], rules: RulesFallback | None = None) -> FallbackResult:
    """Essaie chaque moteur dans l'ordre, puis les règles ; lève 503 MODEL_UNAVAILABLE si rien ne répond."""
    for backend in backends:
        if backend is None:
            continue
        try:
            predictions = backend.predict(model_name, rows)
        except InferenceError as exc:
            logger.warning("Inférence %s via %s impossible : %s", model_name, backend.name, exc)
            continue
        return FallbackResult(predictions, BACKEND_STEPS.get(backend.name, 0), backend.name)
    if rules is not None:
        try:
            return FallbackResult(rules(rows), MAX_FALLBACK_STEP, RULES_ENGINE)
        except InferenceError as exc:
            logger.warning("Repli par règles pour %s impossible : %s", model_name, exc)
    raise model_unavailable()
