"""Ensembles à partir des prédictions hors-pli (OOF) : moyenne, moyenne des rangs, sélection gloutonne
de Caruana (hill climbing), poids optimisés (scipy) et stacking.

Les poids et le méta-modèle sont appris uniquement sur l'OOF ; le stacking est lui-même évalué par
une validation croisée externe (mêmes plis que les modèles de base) pour ne pas surestimer son score.
Les lignes sans OOF (premier bloc d'une validation temporelle « forward ») sont ignorées.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.special import logit, softmax
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression, Ridge

from agriml.metrics import Metric

logger = logging.getLogger(__name__)
PROBA_EPS = 1e-6


@dataclass
class EnsembleResult:
    method: str
    oof: np.ndarray
    test: np.ndarray | None
    score: float
    weights: dict[str, float] = field(default_factory=dict)
    meta_model: Any = None
    members: tuple[str, ...] = ()


def valid_mask(preds: Mapping[str, np.ndarray]) -> np.ndarray:
    """Lignes où tous les modèles ont une prédiction OOF."""
    masks = [~np.isnan(p).any(axis=1) if p.ndim == 2 else ~np.isnan(p) for p in preds.values()]
    return np.logical_and.reduce(masks)


def score_masked(metric: Metric, y, pred: np.ndarray, mask: np.ndarray) -> float:
    return metric(np.asarray(y)[mask], pred[mask])


def weighted_average(preds: Mapping[str, np.ndarray], weights: Mapping[str, float]) -> np.ndarray:
    total = sum(weights.values())
    return sum(preds[name] * (w / total) for name, w in weights.items() if w > 0)


def mean_blend(preds: Mapping[str, np.ndarray]) -> np.ndarray:
    return weighted_average(preds, dict.fromkeys(preds, 1.0))


def rank_average(preds: Mapping[str, np.ndarray]) -> np.ndarray:
    """Moyenne des rangs normalisés dans [0, 1] (classement binaire / AUC uniquement)."""
    ranks = []
    for p in preds.values():
        if p.ndim != 1:
            raise ValueError("rank_average : prédictions 1D attendues.")
        r = np.full(len(p), np.nan)
        ok = ~np.isnan(p)
        r[ok] = (rankdata(p[ok]) - 1) / max(ok.sum() - 1, 1)
        ranks.append(r)
    return np.mean(ranks, axis=0)


def hill_climbing(oofs: Mapping[str, np.ndarray], y, metric: Metric, n_iter: int = 50) -> dict[str, float]:
    """Sélection gloutonne avec remise (Caruana et al., 2004), à partir du meilleur modèle seul.

    Un ajout n'est retenu que s'il améliore strictement le score : le résultat est donc au moins
    aussi bon (en OOF) que le meilleur modèle individuel.
    """
    mask = valid_mask(oofs)
    scores = {n: score_masked(metric, y, p, mask) for n, p in oofs.items()}
    best_name = max(scores, key=scores.get) if metric.greater_is_better else min(scores, key=scores.get)
    counts = {best_name: 1}
    current, best_score = oofs[best_name].copy(), scores[best_name]
    for _ in range(n_iter):
        n_members = sum(counts.values())
        trials = {n: (current * n_members + p) / (n_members + 1) for n, p in oofs.items()}
        trial_scores = {n: score_masked(metric, y, p, mask) for n, p in trials.items()}
        cand = max(trial_scores, key=trial_scores.get) if metric.greater_is_better else min(
            trial_scores, key=trial_scores.get)
        if not metric.is_better(trial_scores[cand], best_score):
            break
        counts[cand] = counts.get(cand, 0) + 1
        current, best_score = trials[cand], trial_scores[cand]
    total = sum(counts.values())
    return {n: c / total for n, c in counts.items()}


def optimize_weights(oofs: Mapping[str, np.ndarray], y, metric: Metric, seed: int = 42) -> dict[str, float]:
    """Poids positifs sommant à 1 (paramétrage softmax) optimisés par Nelder-Mead sur l'OOF."""
    names = list(oofs)
    mask = valid_mask(oofs)
    sign = -1.0 if metric.greater_is_better else 1.0

    def loss(theta: np.ndarray) -> float:
        w = softmax(theta)
        return sign * score_masked(metric, y, weighted_average(oofs, dict(zip(names, w, strict=True))), mask)

    x0 = np.random.default_rng(seed).normal(0, 0.01, len(names))
    res = minimize(loss, x0, method="Nelder-Mead", options={"maxiter": 400 * len(names), "xatol": 1e-4})
    return dict(zip(names, softmax(res.x).tolist(), strict=True))


def stack_features(preds: Mapping[str, np.ndarray], task: str) -> np.ndarray:
    """Matrice du méta-modèle : logits (binaire), log-probas (multiclasse) ou valeurs (régression)."""
    cols = []
    for p in preds.values():
        if task == "binary":
            cols.append(logit(np.clip(p, PROBA_EPS, 1 - PROBA_EPS))[:, None])
        elif task == "multiclass":
            cols.append(np.log(np.clip(p, PROBA_EPS, 1.0)))
        else:
            cols.append(p[:, None])
    return np.hstack(cols)


def _meta_model(task: str, seed: int):
    if task == "regression":
        return Ridge(alpha=1.0, positive=True)
    return LogisticRegression(C=1.0, max_iter=2000, random_state=seed)


def meta_predict(model, X: np.ndarray, task: str) -> np.ndarray:
    if task == "regression":
        return model.predict(X)
    proba = model.predict_proba(X)
    return proba[:, 1] if task == "binary" else proba


def stacking(oofs, tests, y, task: str, splits: Sequence[tuple[np.ndarray, np.ndarray]], seed: int = 42):
    """Stacking : OOF du méta-modèle par les plis externes, puis méta-modèle final sur tout l'OOF."""
    y = np.asarray(y)
    mask = valid_mask(oofs)
    X = stack_features(oofs, task)
    meta_oof = np.full((len(y), X.shape[1] // len(oofs)) if task == "multiclass" else len(y), np.nan)
    for tr, va in splits:
        tr, va = tr[mask[tr]], va[mask[va]]
        if len(va) == 0 or len(np.unique(y[tr])) < (1 if task == "regression" else 2):
            continue
        model = _meta_model(task, seed).fit(X[tr], y[tr])
        meta_oof[va] = meta_predict(model, X[va], task)
    final = _meta_model(task, seed).fit(X[mask], y[mask])
    test_pred = meta_predict(final, stack_features(tests, task), task) if tests else None
    return meta_oof, test_pred, final


def _result(method, oofs, tests, y, metric, weights) -> EnsembleResult:
    oof = weighted_average(oofs, weights)
    test = weighted_average(tests, weights) if tests else None
    score = score_masked(metric, y, oof, valid_mask(oofs))
    return EnsembleResult(method, oof, test, score, weights=dict(weights), members=tuple(oofs))


def run_ensemble(method: str, oofs, tests, y, metric: Metric, task: str, splits, n_iter: int = 50,
                 seed: int = 42) -> EnsembleResult:
    if method == "mean":
        return _result(method, oofs, tests, y, metric, dict.fromkeys(oofs, 1.0))
    if method == "hill_climbing":
        return _result(method, oofs, tests, y, metric, hill_climbing(oofs, y, metric, n_iter))
    if method == "weights_opt":
        return _result(method, oofs, tests, y, metric, optimize_weights(oofs, y, metric, seed))
    if method == "rank_average":
        oof = rank_average(oofs)
        test = rank_average(tests) if tests else None
        score = score_masked(metric, y, oof, valid_mask(oofs))
        return EnsembleResult(method, oof, test, score, weights=dict.fromkeys(oofs, 1 / len(oofs)),
                              members=tuple(oofs))
    if method == "stacking":
        meta_oof, test, model = stacking(oofs, tests, y, task, splits, seed)
        ok = valid_mask({"meta": meta_oof})
        score = score_masked(metric, y, meta_oof, ok)
        return EnsembleResult(method, meta_oof, test, score, meta_model=model, members=tuple(oofs))
    raise ValueError(f"Méthode d'ensemble inconnue : {method}")


def applicable_methods(task: str, metric: Metric) -> list[str]:
    methods = ["mean", "hill_climbing", "weights_opt", "stacking"]
    if task == "binary" and metric.name == "auc":
        methods.insert(1, "rank_average")
    return methods


def run_all_ensembles(oofs, tests, y, metric: Metric, task: str, splits, selected: str, n_iter: int = 50,
                      seed: int = 42) -> tuple[EnsembleResult | None, dict[str, float]]:
    """Évalue toutes les méthodes applicables ; renvoie la méthode configurée et le tableau des scores."""
    if len(oofs) < 2 or selected == "none":
        return None, {}
    report: dict[str, float] = {}
    chosen = None
    for method in applicable_methods(task, metric):
        try:
            result = run_ensemble(method, oofs, tests, y, metric, task, splits, n_iter, seed)
        except (ValueError, np.linalg.LinAlgError) as exc:
            logger.warning("Ensemble %s ignoré : %s", method, exc)
            continue
        report[method] = result.score
        if method == selected:
            chosen = result
    if chosen is None:
        logger.warning("Méthode d'ensemble « %s » non applicable : aucun ensemble retenu.", selected)
    return chosen, report
