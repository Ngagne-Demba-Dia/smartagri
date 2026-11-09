"""Sélection de variables « grandmaster » : importance nulle, permutation hors-pli, élagage adversarial.

- `null_importance` : on réentraîne le modèle sur une cible permutée ; une variable dont l'importance réelle
  ne dépasse pas la distribution nulle n'apporte que du bruit (ou une fuite par cardinalité).
- `permutation_importance_cv` : perte de score quand on permute une variable dans le pli de validation ;
  calculée sur les mêmes plis que la CV (jamais sur le train), donc sans fuite.
- `adversarial_prune` : retire tour à tour la variable la plus discriminante train/test tant que l'AUC
  adversariale reste au-dessus du seuil, sans dépasser un nombre maximal de retraits.

Les estimateurs sont des objets scikit-learn (clonés à chaque ajustement) ; les DataFrames d'entrée ne sont
jamais modifiés. Coût : (1 + n_null) ajustements pour l'importance nulle, n_plis × (1 + n_variables ×
n_repeats) prédictions pour la permutation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone

from agriml.adversarial import adversarial_validation
from agriml.metrics import Metric

NULL_QUANTILE = 0.75
DEFAULT_MAX_P_VALUE = 0.10


@dataclass(frozen=True)
class FeatureScore:
    name: str
    importance: float   # importance réelle (null) ou perte moyenne de score (permutation)
    reference: float    # quantile nul (null) ou écart-type de la perte (permutation)
    p_value: float      # part des tirages nuls ≥ réel (null) ; part des plis sans perte (permutation)

    @property
    def useful(self) -> bool:
        return self.importance > self.reference and self.p_value <= DEFAULT_MAX_P_VALUE


@dataclass(frozen=True)
class AdversarialPruning:
    kept: tuple[str, ...]
    dropped: tuple[str, ...]
    auc_history: tuple[float, ...]   # AUC avant chaque retrait, puis AUC finale


def _importances(model) -> np.ndarray:
    final = model[-1] if hasattr(model, "steps") else model
    if hasattr(final, "feature_importances_"):
        return np.asarray(final.feature_importances_, dtype=float)
    if hasattr(final, "coef_"):
        return np.abs(np.atleast_2d(np.asarray(final.coef_, dtype=float))).mean(axis=0)  # multiclasse : moyenne
    raise TypeError(f"{type(final).__name__} n'expose ni feature_importances_ ni coef_")


def _predict(model, X: pd.DataFrame, metric: Metric) -> np.ndarray:
    if metric.prediction_type in ("proba", "topk"):
        proba = model.predict_proba(X)
        return proba[:, 1] if proba.shape[1] == 2 else proba
    return model.predict(X)


def null_importance(estimator, X: pd.DataFrame, y, n_null: int = 20, seed: int = 42) -> list[FeatureScore]:
    """Importance réelle vs distribution obtenue sur `n_null` cibles permutées ; trié du plus utile au moins."""
    y = np.asarray(y)
    rng = np.random.default_rng(seed)
    actual = _importances(clone(estimator).fit(X, y))
    null = np.vstack([_importances(clone(estimator).fit(X, rng.permutation(y))) for _ in range(n_null)])
    scores = [
        FeatureScore(name=col, importance=float(actual[j]), reference=float(np.quantile(null[:, j], NULL_QUANTILE)),
                     p_value=float((1 + np.sum(null[:, j] >= actual[j])) / (1 + n_null)))
        for j, col in enumerate(X.columns)
    ]
    return sorted(scores, key=lambda s: (s.p_value, -s.importance))


def _fold_drops(model, X_va: pd.DataFrame, y_va, metric: Metric, n_repeats: int,
                rng: np.random.Generator) -> np.ndarray:
    """Perte de score (orientée « positive = utile ») par variable sur un pli de validation."""
    base = metric(y_va, _predict(model, X_va, metric))
    sign = 1.0 if metric.greater_is_better else -1.0
    drops = np.zeros(X_va.shape[1])
    for j, col in enumerate(X_va.columns):
        for _ in range(n_repeats):
            shuffled = X_va.assign(**{col: rng.permutation(X_va[col].to_numpy())})
            drops[j] += sign * (base - metric(y_va, _predict(model, shuffled, metric))) / n_repeats
    return drops


def permutation_importance_cv(estimator, X: pd.DataFrame, y, splits: Sequence[tuple[np.ndarray, np.ndarray]],
                              metric: Metric, n_repeats: int = 3, seed: int = 42) -> list[FeatureScore]:
    """Permutation calculée pli par pli sur la validation ; agrège moyenne, écart-type et part de plis neutres."""
    y = np.asarray(y)
    rng = np.random.default_rng(seed)
    per_fold = np.vstack([
        _fold_drops(clone(estimator).fit(X.iloc[tr], y[tr]), X.iloc[va], y[va], metric, n_repeats, rng)
        for tr, va in splits
    ])
    scores = [
        FeatureScore(name=col, importance=float(per_fold[:, j].mean()), reference=float(per_fold[:, j].std()),
                     p_value=float(np.mean(per_fold[:, j] <= 0.0)))
        for j, col in enumerate(X.columns)
    ]
    return sorted(scores, key=lambda s: -s.importance)


def adversarial_prune(train: pd.DataFrame, test: pd.DataFrame, columns: Sequence[str], max_auc: float = 0.6,
                      max_drops: int = 5, n_splits: int = 5, seed: int = 42) -> AdversarialPruning:
    """Retire la variable la plus discriminante tant que AUC > `max_auc` (au plus `max_drops` retraits).

    À réserver aux variables sans valeur métier stable (identifiants, compteurs, dates absolues) : une
    variable agronomique utile qui dérive se rend relative (anomalie, rang) plutôt que de disparaître.
    """
    kept, dropped, history = list(columns), [], []
    while True:
        report = adversarial_validation(train, test, kept, n_splits=n_splits, seed=seed)
        history.append(report.auc)
        if report.auc <= max_auc or len(dropped) >= max_drops or len(kept) <= 1:
            break
        worst = report.top_features[0][0]
        kept.remove(worst)
        dropped.append(worst)
    return AdversarialPruning(kept=tuple(kept), dropped=tuple(dropped), auc_history=tuple(history))
