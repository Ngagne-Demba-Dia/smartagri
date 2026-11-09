"""Validation adversariale : un classifieur tente de distinguer le train du test.

- AUC ≈ 0,5 : distributions proches, la CV a des chances de suivre le classement ;
- AUC 0,6–0,75 : décalage modéré, choisir une CV qui imite le test (groupes, temps, espace) ;
- AUC > 0,75 : décalage fort — inspecter les variables les plus discriminantes (identifiants, dates,
  variables dérivant dans le temps), les retirer ou les rendre relatives, et repondérer le train par
  `train_test_likeness` (probabilité « ressemble au test »).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline

CLOSE_AUC, MODERATE_AUC = 0.6, 0.75


@dataclass(frozen=True)
class AdversarialReport:
    auc: float
    top_features: tuple[tuple[str, float], ...]
    ks_by_feature: dict[str, float]
    train_test_likeness: np.ndarray

    @property
    def verdict(self) -> str:
        if self.auc < CLOSE_AUC:
            return "proche"
        return "modéré" if self.auc < MODERATE_AUC else "fort"

    def summary(self) -> str:
        top = ", ".join(f"{n} ({v:.3f})" for n, v in self.top_features[:5])
        return f"AUC adversariale {self.auc:.3f} → décalage {self.verdict}. Variables discriminantes : {top}"

    def to_dict(self) -> dict:
        return {"auc": self.auc, "verdict": self.verdict, "top_features": [list(t) for t in self.top_features],
                "ks_by_feature": self.ks_by_feature}


def ks_by_feature(train: pd.DataFrame, test: pd.DataFrame, columns: Sequence[str]) -> dict[str, float]:
    """Statistique de Kolmogorov-Smirnov par variable numérique (0 = identique, 1 = disjoint)."""
    out = {}
    for c in columns:
        a, b = train[c].dropna().to_numpy(float), test[c].dropna().to_numpy(float)
        out[c] = float(ks_2samp(a, b).statistic) if len(a) and len(b) else float("nan")
    return dict(sorted(out.items(), key=lambda kv: -np.nan_to_num(kv[1])))


def adversarial_validation(train: pd.DataFrame, test: pd.DataFrame, columns: Sequence[str], n_splits: int = 5,
                           seed: int = 42, top_k: int = 15) -> AdversarialReport:
    """AUC hors-pli d'un classifieur train-vs-test, importances et KS par variable."""
    cols = list(columns)
    X = pd.concat([train[cols], test[cols]], axis=0, ignore_index=True).astype(float)
    y = np.r_[np.zeros(len(train), dtype=int), np.ones(len(test), dtype=int)]
    oof = np.zeros(len(X))
    importances = np.zeros(len(cols))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for tr, va in skf.split(X, y):
        model = make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            RandomForestClassifier(n_estimators=200, min_samples_leaf=5, n_jobs=-1, random_state=seed),
        )
        model.fit(X.iloc[tr], y[tr])
        oof[va] = model.predict_proba(X.iloc[va])[:, 1]
        importances += model[-1].feature_importances_ / n_splits
    order = np.argsort(-importances)[:top_k]
    return AdversarialReport(
        auc=float(roc_auc_score(y, oof)),
        top_features=tuple((cols[i], float(importances[i])) for i in order),
        ks_by_feature=ks_by_feature(train, test, cols),
        train_test_likeness=oof[: len(train)],
    )
