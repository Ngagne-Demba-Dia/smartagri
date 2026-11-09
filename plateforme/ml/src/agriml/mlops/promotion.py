"""Porte champion / challenger : un modèle n'est promu que s'il bat le champion sur le même hold-out récent,
sans dégrader une tranche (région, culture…) au-delà de la tolérance.

Le hold-out doit être postérieur aux données d'entraînement des deux modèles et assez grand ; sinon on refuse
(une promotion sur 50 lignes est du bruit). La promotion elle-même est un changement d'alias (MLflow ou local),
réversible : revenir en arrière = remettre l'alias « champion » sur l'ancienne version.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from agriml._optional import optional_import
from agriml.mlops.registry import LocalRegistry

logger = logging.getLogger(__name__)
CHAMPION = "champion"


@dataclass(frozen=True)
class PromotionPolicy:
    min_relative_improvement: float = 0.01
    min_abs_improvement: float = 0.0
    max_slice_regression: float = 0.02
    min_holdout_rows: int = 200


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    delta: float | None = None
    rel_delta: float | None = None


def improvement(champion: float, challenger: float, greater_is_better: bool) -> tuple[float, float]:
    """(gain absolu, gain relatif) orientés : > 0 = le challenger est meilleur."""
    delta = (challenger - champion) if greater_is_better else (champion - challenger)
    if champion == 0:
        return delta, float("inf") if delta > 0 else 0.0
    return delta, delta / abs(champion)


def slice_regressions(champion: Mapping[str, float], challenger: Mapping[str, float], greater_is_better: bool,
                      tolerance: float) -> list[str]:
    """Tranches communes où le challenger se dégrade de plus de `tolerance` (relatif)."""
    worse = []
    for key in sorted(set(champion) & set(challenger)):
        _, rel = improvement(champion[key], challenger[key], greater_is_better)
        if rel < -tolerance:
            worse.append(f"{key} ({rel:+.1%})")
    return worse


def decide_promotion(champion_score: float | None, challenger_score: float, greater_is_better: bool,
                     n_holdout: int, policy: PromotionPolicy = PromotionPolicy(),
                     champion_slices: Mapping[str, float] | None = None,
                     challenger_slices: Mapping[str, float] | None = None) -> PromotionDecision:
    if n_holdout < policy.min_holdout_rows:
        return PromotionDecision(False, (f"hold-out trop petit ({n_holdout} < {policy.min_holdout_rows})",))
    if champion_score is None:
        return PromotionDecision(True, ("aucun champion : premier modèle promu",))
    delta, rel = improvement(champion_score, challenger_score, greater_is_better)
    reasons = []
    if rel < policy.min_relative_improvement:
        reasons.append(f"gain relatif {rel:+.2%} < {policy.min_relative_improvement:.0%}")
    if delta < policy.min_abs_improvement:
        reasons.append(f"gain absolu {delta:+.5f} < {policy.min_abs_improvement}")
    worse = slice_regressions(champion_slices or {}, challenger_slices or {}, greater_is_better,
                              policy.max_slice_regression)
    if worse:
        reasons.append("tranches dégradées : " + ", ".join(worse))
    if reasons:
        return PromotionDecision(False, tuple(reasons), delta, rel)
    return PromotionDecision(True, (f"gain relatif {rel:+.2%}",), delta, rel)


def promote(model_name: str, version: int | str, alias: str = CHAMPION,
            registry: LocalRegistry | None = None) -> str:
    """Pose l'alias dans MLflow si disponible, sinon dans le registre local ; renvoie le backend utilisé."""
    mlflow = optional_import("mlflow")
    if mlflow is not None and registry is None:
        from mlflow.tracking import MlflowClient

        MlflowClient().set_registered_model_alias(model_name, alias, str(version))
        logger.info("MLflow : %s@%s -> version %s", model_name, alias, version)
        return "mlflow"
    (registry or LocalRegistry()).set_alias(model_name, alias, int(version))
    logger.info("Registre local : %s@%s -> version %s", model_name, alias, version)
    return "local"
