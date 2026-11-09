"""Fabrique de modèles tabulaires avec une interface commune `fit` / `predict`.

`predict` renvoie toujours : la valeur (régression), P(classe 1) (binaire) ou la matrice n × K (multiclasse).
Arrêt précoce (boosting) :
- « inner » (défaut) : 10 % du pli d'entraînement mis de côté → l'OOF reste honnête ;
- « valid » : utilise la validation du pli (plus rapide, mais OOF optimiste de quelques millièmes) ;
- « none ».
LightGBM, CatBoost, PyTorch (torch_mlp) et Keras (keras_mlp) sont optionnels : `backend_available` permet de
les ignorer proprement.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from agriml._optional import is_available, require
from agriml.models.neural import NEURAL_BACKENDS, make_neural

logger = logging.getLogger(__name__)
INNER_VALID_FRACTION = 0.1
EARLY_STOPPING_ROUNDS = 100
BOOSTING_DEFAULTS = {"n_estimators": 2000, "learning_rate": 0.05}
BOOSTING_BACKENDS = {"xgb": "xgboost", "lgbm": "lightgbm", "catboost": "catboost"}
BACKENDS = {**BOOSTING_BACKENDS, **NEURAL_BACKENDS}
ONE_HOT_KINDS = ("ridge", "logreg", *NEURAL_BACKENDS)  # catégorielles codées puis one-hot dans le pli
NATIVE_CATEGORICAL_KINDS = ("hgb", "lgbm", "catboost")


def backend_available(kind: str) -> bool:
    module = BACKENDS.get(kind)
    return module is None or is_available(module)


def _linear_preprocessor(columns: Sequence[str], categorical: Sequence[str]) -> ColumnTransformer:
    numeric = [c for c in columns if c not in set(categorical)]
    num = make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                        StandardScaler())
    cat = make_pipeline(SimpleImputer(strategy="most_frequent", keep_empty_features=True),
                        OneHotEncoder(handle_unknown="ignore"))
    transformers = [("num", num, numeric)]
    if categorical:
        transformers.append(("cat", cat, list(categorical)))
    return ColumnTransformer(transformers)


def _inner_split(X: pd.DataFrame, y: np.ndarray, task: str, seed: int):
    stratify = y if task != "regression" and np.bincount(y.astype(int)).min() >= 2 else None
    return train_test_split(X, y, test_size=INNER_VALID_FRACTION, random_state=seed, stratify=stratify)


@dataclass
class TabularModel:
    kind: str
    task: str
    params: Mapping[str, Any] = field(default_factory=dict)
    seed: int = 42
    categorical_features: Sequence[str] = ()
    early_stopping: str = "inner"
    n_classes: int | None = None
    estimator_: Any = field(default=None, init=False)
    columns_: list[str] = field(default_factory=list, init=False)

    @property
    def is_classifier(self) -> bool:
        return self.task != "regression"

    # ------------------------------------------------------------------ construction

    def _build(self, columns: Sequence[str]) -> Any:
        p, clf, seed = dict(self.params), self.is_classifier, self.seed
        cats = [c for c in self.categorical_features if c in columns]
        if self.kind in ("ridge", "logreg"):
            est = LogisticRegression(max_iter=2000, **p) if clf else Ridge(**p)
            return Pipeline([("prep", _linear_preprocessor(columns, cats)), ("model", est)])
        if self.kind in NEURAL_BACKENDS:
            est = make_neural(self.kind, self.task, self.n_classes, seed, p)
            return Pipeline([("prep", _linear_preprocessor(columns, cats)), ("model", est)])
        if self.kind == "hgb":
            cls = HistGradientBoostingClassifier if clf else HistGradientBoostingRegressor
            if self.early_stopping != "none":
                p.setdefault("early_stopping", True)
                p.setdefault("validation_fraction", INNER_VALID_FRACTION)
            return cls(random_state=seed, categorical_features=cats or None, **p)
        if self.kind in ("rf", "et"):
            table = {("rf", True): RandomForestClassifier, ("rf", False): RandomForestRegressor,
                     ("et", True): ExtraTreesClassifier, ("et", False): ExtraTreesRegressor}
            p.setdefault("n_estimators", 300)
            est = table[(self.kind, clf)](random_state=seed, n_jobs=-1, **p)
            return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), est)
        return self._build_boosting(p)

    def _build_boosting(self, p: dict) -> Any:
        clf, seed, stop = self.is_classifier, self.seed, self.early_stopping != "none"
        p = {**BOOSTING_DEFAULTS, **p}
        if self.kind == "xgb":
            xgb = require("xgboost", "Le modèle xgb")
            p.setdefault("tree_method", "hist")
            if stop:
                p.setdefault("early_stopping_rounds", EARLY_STOPPING_ROUNDS)
            cls = xgb.XGBClassifier if clf else xgb.XGBRegressor
            return cls(random_state=seed, n_jobs=-1, verbosity=0, **p)
        if self.kind == "lgbm":
            lgb = require("lightgbm", "Le modèle lgbm")
            cls = lgb.LGBMClassifier if clf else lgb.LGBMRegressor
            return cls(random_state=seed, verbose=-1, **p)
        if self.kind == "catboost":
            cb = require("catboost", "Le modèle catboost")
            p["iterations"] = p.pop("n_estimators")
            if stop:
                p.setdefault("od_type", "Iter")
                p.setdefault("od_wait", EARLY_STOPPING_ROUNDS)
            cls = cb.CatBoostClassifier if clf else cb.CatBoostRegressor
            return cls(random_seed=seed, verbose=0, **p)
        raise ValueError(f"Type de modèle inconnu : {self.kind}")

    # ------------------------------------------------------------------ apprentissage

    def fit(self, X: pd.DataFrame, y, X_valid: pd.DataFrame | None = None, y_valid=None) -> TabularModel:
        y = np.asarray(y)
        self.columns_ = list(X.columns)
        self.estimator_ = self._build(self.columns_)
        if self.kind in BOOSTING_BACKENDS and self.early_stopping != "none":
            self._fit_with_eval(X, y, X_valid, y_valid)
        else:
            self.estimator_.fit(X, y)
        return self

    def _fit_with_eval(self, X, y, X_valid, y_valid) -> None:
        if self.early_stopping == "valid" and X_valid is not None:
            X_tr, y_tr, X_ev, y_ev = X, y, X_valid, np.asarray(y_valid)
        else:
            X_tr, X_ev, y_tr, y_ev = _inner_split(X, y, self.task, self.seed)
        if self.kind == "lgbm":
            lgb = require("lightgbm", "Le modèle lgbm")
            self.estimator_.fit(X_tr, y_tr, eval_set=[(X_ev, y_ev)],
                                callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)])
        elif self.kind == "catboost":
            self.estimator_.fit(X_tr, y_tr, eval_set=(X_ev, y_ev), use_best_model=True)
        else:
            self.estimator_.fit(X_tr, y_tr, eval_set=[(X_ev, y_ev)], verbose=False)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.estimator_ is None:
            raise RuntimeError("Modèle non entraîné.")
        X = X[self.columns_]
        if not self.is_classifier:
            return np.asarray(self.estimator_.predict(X), dtype=float).reshape(-1)
        proba = np.asarray(self.estimator_.predict_proba(X), dtype=float)
        classes = np.asarray(getattr(self.estimator_, "classes_", np.arange(proba.shape[1]))).astype(int)
        k = int(self.n_classes or (classes.max() + 1))
        full = np.zeros((len(X), max(k, 2)))
        full[:, classes] = proba
        return full[:, 1] if self.task == "binary" else full

    def best_iteration(self) -> int | None:
        est = self.estimator_[-1] if isinstance(self.estimator_, Pipeline) else self.estimator_
        for attr in ("best_iteration", "best_iteration_", "n_iter_"):
            value = getattr(est, attr, None)
            if isinstance(value, int | np.integer):
                return int(value)
        return None

    def feature_importance(self) -> pd.Series | None:
        est = self.estimator_[-1] if isinstance(self.estimator_, Pipeline) else self.estimator_
        values = getattr(est, "feature_importances_", None)
        if values is None or len(values) != len(self.columns_):
            return None
        return pd.Series(values, index=self.columns_).sort_values(ascending=False)


def build_model(kind: str, task: str, params: Mapping[str, Any] | None = None, seed: int = 42,
                categorical_features: Sequence[str] = (), early_stopping: str = "inner",
                n_classes: int | None = None) -> TabularModel:
    if not backend_available(kind):
        require(BACKENDS[kind], f"Le modèle {kind}")
    return TabularModel(kind=kind, task=task, params=dict(params or {}), seed=seed,
                        categorical_features=tuple(categorical_features), early_stopping=early_stopping,
                        n_classes=n_classes)
