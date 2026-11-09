"""Encodages catégoriels ajustés pli par pli (aucune statistique ne voit la validation ni le test).

`OOFTargetEncoder` : encodage par la moyenne de la cible avec lissage bayésien.
- `fit_transform(X_train, y_train)` : chaque ligne d'entraînement est encodée par un K-fold interne ;
  la moyenne a priori est elle-même calculée sur la partie interne d'entraînement, donc la ligne
  ne voit jamais sa propre cible (sinon le modèle apprend un encodage « trop beau » → sur-apprentissage) ;
- `transform(X)` : validation / test encodés avec la table apprise sur tout le pli d'entraînement.

Attention : encoder la colonne de groupe d'une validation groupée est inutile (toutes les lignes de
validation reçoivent l'a priori) et crée un écart train/validation — à éviter.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

MISSING_KEY = "__nan__"


def _keys(series: pd.Series) -> pd.Series:
    return series.astype(object).where(series.notna(), MISSING_KEY).astype(str)


def _target_matrix(y, task: str, n_classes: int | None) -> np.ndarray:
    """Cible → matrice (n, m) : 1 colonne (régression / binaire) ou one-hot (multiclasse)."""
    y = np.asarray(y)
    if task == "multiclass":
        k = int(n_classes or (y.max() + 1))
        return np.eye(k)[y.astype(int)]
    return y.astype(float).reshape(-1, 1)


def _fit_table(keys: pd.Series, target: np.ndarray, prior: np.ndarray, smoothing: float) -> pd.DataFrame:
    frame = pd.DataFrame(target, index=keys.index)
    grouped = frame.groupby(keys.to_numpy())
    sums, counts = grouped.sum(), grouped.size().to_numpy()[:, None]
    return (sums + prior * smoothing) / (counts + smoothing)


def _apply_table(keys: pd.Series, table: pd.DataFrame, prior: np.ndarray) -> np.ndarray:
    values = table.reindex(keys.to_numpy()).to_numpy(dtype=float)
    return np.where(np.isnan(values), prior, values)


@dataclass
class OOFTargetEncoder:
    columns: Sequence[str]
    smoothing: float = 20.0
    n_splits: int = 5
    seed: int = 42
    task: str = "regression"
    n_classes: int | None = None
    tables_: dict = field(default_factory=dict, init=False)
    prior_: np.ndarray | None = field(default=None, init=False)

    def output_names(self, column: str) -> list[str]:
        if self.task == "multiclass":
            return [f"te_{column}_c{k}" for k in range(int(self.n_classes))]
        return [f"te_{column}"]

    def fit(self, X: pd.DataFrame, y) -> OOFTargetEncoder:
        target = _target_matrix(y, self.task, self.n_classes)
        if self.task == "multiclass":
            self.n_classes = target.shape[1]
        self.prior_ = target.mean(axis=0)
        self.tables_ = {c: _fit_table(_keys(X[c]), target, self.prior_, self.smoothing) for c in self.columns}
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if self.prior_ is None:
            raise RuntimeError("OOFTargetEncoder non ajusté : appeler fit ou fit_transform.")
        parts = {}
        for c in self.columns:
            values = _apply_table(_keys(X[c]), self.tables_[c], self.prior_)
            for j, name in enumerate(self.output_names(c)):
                parts[name] = values[:, j]
        return pd.DataFrame(parts, index=X.index)

    def fit_transform(self, X: pd.DataFrame, y) -> pd.DataFrame:
        """Encodage hors-pli des lignes d'entraînement, puis ajustement final sur tout X."""
        target = _target_matrix(y, self.task, self.n_classes)
        if self.task == "multiclass":
            self.n_classes = target.shape[1]
        n = len(X)
        n_splits = max(2, min(self.n_splits, n))
        out = {name: np.empty(n) for c in self.columns for name in self.output_names(c)}
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=self.seed)
        for tr, va in kf.split(np.zeros(n)):
            prior = target[tr].mean(axis=0)
            for c in self.columns:
                keys = _keys(X[c])
                table = _fit_table(keys.iloc[tr], target[tr], prior, self.smoothing)
                values = _apply_table(keys.iloc[va], table, prior)
                for j, name in enumerate(self.output_names(c)):
                    out[name][va] = values[:, j]
        self.fit(X, y)
        return pd.DataFrame(out, index=X.index)


@dataclass
class CategoricalCoder:
    """Codes entiers 0..n−1 appris sur le pli d'entraînement ; NaN pour les modalités inconnues."""

    columns: Sequence[str]
    mappings_: dict = field(default_factory=dict, init=False)

    def fit(self, X: pd.DataFrame) -> CategoricalCoder:
        self.mappings_ = {}
        for c in self.columns:
            cats = sorted(_keys(X[c]).unique())
            self.mappings_[c] = {cat: float(i) for i, cat in enumerate(cats)}
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {c: _keys(X[c]).map(self.mappings_[c]).astype(float) for c in self.columns}, index=X.index
        )

    def cardinality(self, column: str) -> int:
        return len(self.mappings_[column])
