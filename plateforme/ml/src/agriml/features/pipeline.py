"""Assemblage des variables : étape sans état (train + test) puis transformation ajustée pli par pli.

1. `build_stateless_features` : agronomie, télédétection, retards/fenêtres, encodage cyclique.
   Aucune statistique de la cible → appliqué une fois sur train + test concaténés (les retards du test
   peuvent ainsi utiliser l'historique connu du train, comme en production).
2. `FoldTransformer` : codes catégoriels + encodage de cible, ajustés sur le seul pli d'entraînement.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from agriml.features.agronomy import add_agronomy_features
from agriml.features.encoding import CategoricalCoder, OOFTargetEncoder
from agriml.features.remote_sensing import add_series_features
from agriml.features.temporal import (
    add_cyclical_features,
    add_diff_features,
    add_lag_features,
    add_rolling_features,
)

if TYPE_CHECKING:
    from agriml.config import ExperimentConfig

logger = logging.getLogger(__name__)
MAX_NATIVE_CATEGORIES = 255  # limite des catégories natives de HistGradientBoosting


def _temporal_block(df: pd.DataFrame, spec: Mapping, cfg: ExperimentConfig) -> pd.DataFrame:
    time = spec.get("time") or cfg.columns.time
    group = spec.get("group", cfg.columns.group)
    if not time:
        raise ValueError("features.temporal : colonne temps requise (columns.time ou temporal.time).")
    cols = list(spec["columns"])
    out = df
    if spec.get("lags"):
        out = add_lag_features(out, cols, spec["lags"], time, group)
    if spec.get("windows"):
        out = add_rolling_features(out, cols, spec["windows"], time, group, tuple(spec.get("stats", ("mean",))),
                                   bool(spec.get("include_current", False)))
    if spec.get("diff", False):
        out = add_diff_features(out, cols, time, group)
    return out


def build_stateless_features(df: pd.DataFrame, cfg: ExperimentConfig) -> pd.DataFrame:
    """Applique les blocs sans état configurés ; renvoie une nouvelle table (index remis à zéro)."""
    blocks = cfg.features.blocks
    out = df.reset_index(drop=True)
    if "agronomy" in blocks:
        out = add_agronomy_features(out, cfg.features.agronomy)
    if "remote_sensing" in blocks:
        for prefix in cfg.features.remote_sensing.get("series", ()):
            out = add_series_features(out, prefix)
    if "temporal" in blocks:
        out = _temporal_block(out, cfg.features.temporal, cfg)
    if "date_cyclical" in blocks:
        for spec in cfg.features.date_cyclical:
            out = add_cyclical_features(out, spec["column"], spec.get("kind", "raw"), spec.get("period"))
    return out


def target_encoding_columns(cfg: ExperimentConfig) -> tuple[str, ...]:
    if "target_encoding" not in cfg.features.blocks:
        return ()
    return tuple(cfg.features.target_encoding.get("columns", ()))


def select_feature_columns(df: pd.DataFrame, cfg: ExperimentConfig) -> tuple[list[str], list[str]]:
    """Renvoie (colonnes numériques, colonnes catégorielles) utilisables par les modèles."""
    cols = cfg.columns
    excluded = {cols.id, cols.target, *cols.drop}
    if not cfg.features.include_time and cols.time:
        excluded.add(cols.time)
    if cols.group:
        excluded.add(cols.group)  # identité brute : apprise via l'encodage de cible si demandé
    te_cols = set(target_encoding_columns(cfg))
    categorical = [c for c in cols.categorical if c in df and c not in excluded]
    numeric, dropped = [], []
    for c in df.columns:
        if c in excluded or c in categorical:
            continue
        if pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
            numeric.append(c)
        elif c not in te_cols:
            dropped.append(c)
    if dropped:
        logger.info("Colonnes non numériques ignorées (déclarer dans columns.categorical) : %s", dropped)
    return numeric, categorical


@dataclass
class FoldTransformer:
    """Transformation ajustée sur un pli : numériques + codes catégoriels + encodage de cible hors-pli."""

    numeric: Sequence[str]
    categorical: Sequence[str]
    te_columns: Sequence[str] = ()
    te_smoothing: float = 20.0
    te_splits: int = 5
    task: str = "regression"
    n_classes: int | None = None
    seed: int = 42
    coder_: CategoricalCoder | None = field(default=None, init=False)
    encoder_: OOFTargetEncoder | None = field(default=None, init=False)

    @classmethod
    def from_config(cls, cfg: ExperimentConfig, numeric: Sequence[str], categorical: Sequence[str],
                    n_classes: int | None, seed: int) -> FoldTransformer:
        te = cfg.features.target_encoding
        te_cols = target_encoding_columns(cfg)
        if cfg.columns.group in te_cols and cfg.cv.scheme in ("group", "stratified_group"):
            logger.warning("Encodage de cible sur la colonne de groupe « %s » avec validation groupée : "
                           "inutile en validation (a priori seul) — à retirer.", cfg.columns.group)
        return cls(numeric=list(numeric), categorical=list(categorical), te_columns=te_cols,
                   te_smoothing=float(te.get("smoothing", 20.0)), te_splits=int(te.get("n_splits", 5)),
                   task=cfg.task, n_classes=n_classes, seed=seed)

    def _base(self, X: pd.DataFrame) -> pd.DataFrame:
        parts = [X[list(self.numeric)].astype(float)]
        if self.categorical:
            parts.append(self.coder_.transform(X).add_prefix("cat_"))
        return pd.concat(parts, axis=1)

    def fit_transform(self, X: pd.DataFrame, y) -> pd.DataFrame:
        self.coder_ = CategoricalCoder(self.categorical).fit(X) if self.categorical else None
        out = self._base(X)
        if self.te_columns:
            self.encoder_ = OOFTargetEncoder(self.te_columns, self.te_smoothing, self.te_splits, self.seed,
                                             self.task, self.n_classes)
            out = pd.concat([out, self.encoder_.fit_transform(X, y)], axis=1)
        return out

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = self._base(X)
        if self.encoder_ is not None:
            out = pd.concat([out, self.encoder_.transform(X)], axis=1)
        return out

    @property
    def native_categorical(self) -> list[str]:
        """Colonnes codées assez petites pour un traitement catégoriel natif par les arbres."""
        if self.coder_ is None:
            return []
        return [f"cat_{c}" for c in self.categorical if self.coder_.cardinality(c) <= MAX_NATIVE_CATEGORIES]

    @property
    def coded_categorical(self) -> list[str]:
        return [f"cat_{c}" for c in self.categorical]
