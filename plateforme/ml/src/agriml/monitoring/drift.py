"""Surveillance de dérive : PSI (numérique par quantiles de référence, catégoriel par fréquences) et test KS.

Bandes PSI usuelles : < 0,1 stable ; 0,1–0,25 dérive modérée (surveiller) ; > 0,25 dérive forte (agir).
`should_retrain` combine dérive des variables, dérive des prédictions, dégradation mesurée et âge du modèle.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

PSI_EPS = 1e-4
PSI_STABLE = 0.1
PSI_SIGNIFICANT = 0.25
DEFAULT_BINS = 10
KS_ALPHA = 0.01


def psi_band(value: float) -> str:
    if np.isnan(value):
        return "indetermine"
    if value < PSI_STABLE:
        return "stable"
    return "moderee" if value <= PSI_SIGNIFICANT else "forte"


def _psi_from_props(ref: np.ndarray, cur: np.ndarray) -> float:
    ref, cur = np.clip(ref, PSI_EPS, None), np.clip(cur, PSI_EPS, None)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def psi_numeric(reference, current, n_bins: int = DEFAULT_BINS) -> float:
    """PSI sur les quantiles de la référence (bornes extrêmes ouvertes) ; NaN ignorés."""
    ref = pd.Series(reference, dtype=float).dropna().to_numpy()
    cur = pd.Series(current, dtype=float).dropna().to_numpy()
    if len(ref) == 0 or len(cur) == 0:
        return float("nan")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, n_bins + 1)[1:-1]))
    ref_counts = np.bincount(np.searchsorted(edges, ref, side="right"), minlength=len(edges) + 1)
    cur_counts = np.bincount(np.searchsorted(edges, cur, side="right"), minlength=len(edges) + 1)
    return _psi_from_props(ref_counts / len(ref), cur_counts / len(cur))


def psi_categorical(reference, current) -> float:
    """PSI sur les fréquences des modalités (modalités nouvelles comprises, NaN = modalité)."""
    ref = pd.Series(reference).astype("object").fillna("__nan__")
    cur = pd.Series(current).astype("object").fillna("__nan__")
    cats = sorted(set(ref) | set(cur), key=str)
    ref_p = ref.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    cur_p = cur.value_counts(normalize=True).reindex(cats, fill_value=0).to_numpy()
    return _psi_from_props(ref_p, cur_p)


@dataclass(frozen=True)
class FeatureDrift:
    feature: str
    kind: str
    psi: float
    band: str
    ks_stat: float | None = None
    ks_pvalue: float | None = None
    missing_ref: float = 0.0
    missing_cur: float = 0.0


def feature_drift(reference: pd.Series, current: pd.Series, name: str, n_bins: int = DEFAULT_BINS) -> FeatureDrift:
    missing = (float(reference.isna().mean()), float(current.isna().mean()))
    if pd.api.types.is_numeric_dtype(reference) and not pd.api.types.is_bool_dtype(reference):
        psi = psi_numeric(reference, current, n_bins)
        ref, cur = reference.dropna(), current.dropna()
        ks = ks_2samp(ref, cur) if len(ref) and len(cur) else None
        return FeatureDrift(name, "numeric", psi, psi_band(psi), float(ks.statistic) if ks else None,
                            float(ks.pvalue) if ks else None, *missing)
    psi = psi_categorical(reference, current)
    return FeatureDrift(name, "categorical", psi, psi_band(psi), None, None, *missing)


@dataclass(frozen=True)
class DriftReport:
    features: tuple[FeatureDrift, ...]
    prediction_psi: float | None = None

    @property
    def share_significant(self) -> float:
        valid = [f for f in self.features if not np.isnan(f.psi)]
        return sum(f.psi > PSI_SIGNIFICANT for f in valid) / len(valid) if valid else 0.0

    def top(self, k: int = 10) -> list[FeatureDrift]:
        return sorted(self.features, key=lambda f: -np.nan_to_num(f.psi, nan=-1))[:k]

    def to_dict(self) -> dict[str, Any]:
        return {"share_significant": self.share_significant, "prediction_psi": self.prediction_psi,
                "prediction_band": psi_band(self.prediction_psi) if self.prediction_psi is not None else None,
                "features": [asdict(f) for f in self.top(len(self.features))]}


def drift_report(reference: pd.DataFrame, current: pd.DataFrame, columns: Sequence[str] | None = None,
                 reference_pred=None, current_pred=None, n_bins: int = DEFAULT_BINS) -> DriftReport:
    cols = list(columns) if columns is not None else [c for c in reference.columns if c in current.columns]
    feats = tuple(feature_drift(reference[c], current[c], c, n_bins) for c in cols)
    pred_psi = None
    if reference_pred is not None and current_pred is not None:
        pred_psi = psi_numeric(reference_pred, current_pred, n_bins)
    return DriftReport(feats, pred_psi)


@dataclass(frozen=True)
class RetrainPolicy:
    max_share_significant: float = 0.20
    max_prediction_psi: float = 0.20
    max_relative_decay: float = 0.10
    max_age_days: int = 90
    min_new_labels: int = 200


@dataclass(frozen=True)
class RetrainDecision:
    retrain: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def relative_decay(reference_score: float, current_score: float, greater_is_better: bool) -> float:
    """Dégradation relative (> 0 = pire) : sens de la métrique pris en compte."""
    if reference_score == 0:
        return 0.0
    delta = (reference_score - current_score) if greater_is_better else (current_score - reference_score)
    return delta / abs(reference_score)


def should_retrain(report: DriftReport, policy: RetrainPolicy = RetrainPolicy(), model_age_days: int = 0,
                   n_new_labels: int = 0, reference_score: float | None = None, current_score: float | None = None,
                   greater_is_better: bool = False) -> RetrainDecision:
    """Décision de réentraînement (n'importe quel critère suffit) ; la promotion reste soumise à la porte."""
    reasons = []
    if report.share_significant >= policy.max_share_significant:
        reasons.append(f"{report.share_significant:.0%} des variables en dérive forte (PSI > {PSI_SIGNIFICANT})")
    if report.prediction_psi is not None and report.prediction_psi > policy.max_prediction_psi:
        reasons.append(f"PSI des prédictions {report.prediction_psi:.3f} > {policy.max_prediction_psi}")
    if reference_score is not None and current_score is not None:
        decay = relative_decay(reference_score, current_score, greater_is_better)
        if decay > policy.max_relative_decay:
            reasons.append(f"dégradation de la performance {decay:.1%} > {policy.max_relative_decay:.0%}")
    if model_age_days > policy.max_age_days and n_new_labels >= policy.min_new_labels:
        reasons.append(f"modèle âgé de {model_age_days} j avec {n_new_labels} nouvelles étiquettes")
    return RetrainDecision(bool(reasons), tuple(reasons))
