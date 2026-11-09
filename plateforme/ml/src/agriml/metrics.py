"""Registre des métriques d'évaluation et post-traitements spécifiques à chaque métrique.

Chaque métrique déclare son sens d'optimisation et le type de prédiction attendu :
- « value » : valeur continue (régression) ;
- « proba » : probabilité (binaire : vecteur P(classe 1) ; multiclasse : matrice n × K) ;
- « label » : étiquette, dérivée des probabilités par seuil (binaire) ou argmax (multiclasse) ;
- « topk »  : classement des classes (MAP@k calculé à partir des probabilités).

Les modèles produisent toujours des valeurs ou des probabilités ; la conversion vers le type attendu
est faite ici, ce qui permet d'optimiser ensuite le seuil (F1) sans réentraîner.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from sklearn import metrics as skm

EPS_LOGLOSS = 1e-15
REGRESSION = ("regression",)
CLASSIFICATION = ("binary", "multiclass")


@dataclass(frozen=True)
class Metric:
    name: str
    func: Callable[[np.ndarray, np.ndarray], float]
    greater_is_better: bool
    prediction_type: str
    tasks: tuple[str, ...]

    def __call__(self, y_true, y_pred) -> float:
        return float(self.func(np.asarray(y_true), np.asarray(y_pred)))

    @property
    def direction(self) -> str:
        return "maximize" if self.greater_is_better else "minimize"

    @property
    def worst_value(self) -> float:
        return -np.inf if self.greater_is_better else np.inf

    def is_better(self, candidate: float, reference: float) -> bool:
        """Vrai si `candidate` est strictement meilleur que `reference`."""
        if self.greater_is_better:
            return candidate > reference
        return candidate < reference


def to_labels(y_pred, threshold: float = 0.5) -> np.ndarray:
    """Probabilités → étiquettes (seuil en binaire, argmax en multiclasse)."""
    pred = np.asarray(y_pred)
    if pred.ndim == 2:
        return pred.argmax(axis=1)
    if np.issubdtype(pred.dtype, np.integer) or pred.dtype == bool:
        return pred.astype(int)
    return (pred >= threshold).astype(int)


def clip_probabilities(proba, eps: float = 1e-6) -> np.ndarray:
    """Borne les probabilités dans [eps, 1 - eps] (et renormalise en multiclasse) : protège la logloss."""
    p = np.clip(np.asarray(proba, dtype=float), eps, 1 - eps)
    if p.ndim == 2:
        p = p / p.sum(axis=1, keepdims=True)
    return p


def _rmse(y, p):
    return np.sqrt(np.mean((y.astype(float) - p.astype(float)) ** 2))


def _mae(y, p):
    return np.mean(np.abs(y.astype(float) - p.astype(float)))


def _rmsle(y, p):
    return np.sqrt(np.mean((np.log1p(np.clip(p.astype(float), 0, None)) - np.log1p(y.astype(float))) ** 2))


def _r2(y, p):
    return skm.r2_score(y, p)


def _mape(y, p):
    return skm.mean_absolute_percentage_error(y, p)


def _accuracy(y, p):
    return skm.accuracy_score(y.astype(int), to_labels(p))


def _f1_macro(y, p):
    return skm.f1_score(y.astype(int), to_labels(p), average="macro")


def _logloss(y, p):
    p = np.asarray(p, dtype=float)
    if p.ndim == 1:
        p = np.clip(p, EPS_LOGLOSS, 1 - EPS_LOGLOSS)
        return skm.log_loss(y.astype(int), np.column_stack([1 - p, p]), labels=[0, 1])
    return skm.log_loss(y.astype(int), clip_probabilities(p, EPS_LOGLOSS), labels=np.arange(p.shape[1]))


def _auc(y, p):
    p = np.asarray(p, dtype=float)
    if p.ndim == 1:
        return skm.roc_auc_score(y.astype(int), p)
    p = p / p.sum(axis=1, keepdims=True)
    return skm.roc_auc_score(y.astype(int), p, multi_class="ovr", average="macro", labels=np.arange(p.shape[1]))


def apk(actual: Sequence, predicted: Sequence, k: int) -> float:
    """Average precision at k (formulation Kaggle classique)."""
    predicted = list(predicted)[:k]
    if not actual:
        return 0.0
    hits, score, seen = 0, 0.0, set()
    for i, item in enumerate(predicted):
        if item in actual and item not in seen:
            hits += 1
            score += hits / (i + 1.0)
            seen.add(item)
    return score / min(len(actual), k)


def mapk(actual: Sequence[Sequence], predicted: Sequence[Sequence], k: int) -> float:
    return float(np.mean([apk(a, p, k) for a, p in zip(actual, predicted, strict=True)]))


def map_at_k_from_proba(y_true, proba, k: int) -> float:
    """MAP@k avec une seule bonne classe par ligne : 1/(rang) si la classe est dans le top-k."""
    proba = np.asarray(proba, dtype=float)
    top = np.argsort(-proba, axis=1)[:, :k]
    hits = top == np.asarray(y_true).astype(int)[:, None]
    ranks = np.argmax(hits, axis=1)
    return float(np.mean(np.where(hits.any(axis=1), 1.0 / (ranks + 1.0), 0.0)))


REGISTRY: dict[str, Metric] = {
    "rmse": Metric("rmse", _rmse, False, "value", REGRESSION),
    "mae": Metric("mae", _mae, False, "value", REGRESSION),
    "rmsle": Metric("rmsle", _rmsle, False, "value", REGRESSION),
    "r2": Metric("r2", _r2, True, "value", REGRESSION),
    "mape": Metric("mape", _mape, False, "value", REGRESSION),
    "accuracy": Metric("accuracy", _accuracy, True, "label", CLASSIFICATION),
    "f1_macro": Metric("f1_macro", _f1_macro, True, "label", CLASSIFICATION),
    "logloss": Metric("logloss", _logloss, False, "proba", CLASSIFICATION),
    "auc": Metric("auc", _auc, True, "proba", CLASSIFICATION),
}


def get_metric(name: str) -> Metric:
    """Renvoie la métrique `name` (accepte aussi « map@k », ex. « map@3 »)."""
    key = name.lower().strip()
    match = re.fullmatch(r"map@(\d+)", key)
    if match:
        k = int(match.group(1))
        return Metric(key, lambda y, p, k=k: map_at_k_from_proba(y, p, k), True, "topk", ("multiclass",))
    if key not in REGISTRY:
        raise KeyError(f"Métrique inconnue « {name} ». Disponibles : {', '.join(list_metrics())}.")
    return REGISTRY[key]


def list_metrics() -> list[str]:
    return [*REGISTRY, "map@k"]


# --------------------------------------------------------------------------- post-traitements


def log1p_target(y) -> np.ndarray:
    """Pour la RMSLE : apprendre sur log1p(y) avec une perte RMSE, puis revenir par expm1."""
    y = np.asarray(y, dtype=float)
    if (y < 0).any():
        raise ValueError("log1p impossible : la cible contient des valeurs négatives.")
    return np.log1p(y)


def inverse_log1p(pred) -> np.ndarray:
    return np.clip(np.expm1(np.asarray(pred, dtype=float)), 0, None)


def optimize_f1_threshold(y_true, proba, average: str = "binary", n_grid: int = 99) -> tuple[float, float]:
    """Cherche le seuil qui maximise le F1 sur les prédictions OOF (jamais sur le test)."""
    y_true = np.asarray(y_true).astype(int)
    proba = np.asarray(proba, dtype=float)
    grid = np.unique(np.quantile(proba, np.linspace(0.01, 0.99, n_grid)))
    best_thr, best_score = 0.5, -1.0
    for thr in grid:
        score = skm.f1_score(y_true, (proba >= thr).astype(int), average=average, zero_division=0)
        if score > best_score:
            best_thr, best_score = float(thr), float(score)
    return best_thr, best_score
