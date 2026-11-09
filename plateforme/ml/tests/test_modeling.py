"""Modèles, ensembles (OOF uniquement), optimisation, validation adverse, soumission, registre et promotion."""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import pytest

from agriml.adversarial import adversarial_validation
from agriml.cv import kfold_splits
from agriml.ensemble import hill_climbing, mean_blend, rank_average, run_ensemble
from agriml.metrics import get_metric
from agriml.mlops.promotion import decide_promotion, improvement, promote, slice_regressions
from agriml.mlops.registry import LocalRegistry, RegistryError
from agriml.models.factory import backend_available, build_model
from agriml.submission import (
    SubmissionError, align_to_sample, assert_valid_submission, build_submission, validate_submission,
)
from agriml.tuning import tune


@pytest.fixture
def tabular(rng):
    X = pd.DataFrame({"a": rng.normal(size=300), "b": rng.normal(size=300), "c": rng.choice(["x", "y"], 300)})
    y = 3 * X.a - 2 * X.b + (X.c == "x") + rng.normal(0, 0.3, 300)
    return X, y.to_numpy()


@pytest.mark.parametrize("kind, native", [("ridge", True), ("hgb", True), ("rf", False)])
def test_tabular_models_learn_signal(tabular, kind, native):
    X, y = tabular
    if not native:  # en entraînement, FoldTransformer code les catégories pour ces modèles
        X = X.assign(c=(X.c == "x").astype(int))
    cats = ["c"] if native else []
    model = build_model(kind, "regression", seed=0, categorical_features=cats).fit(X.iloc[:240], y[:240])
    rmse = get_metric("rmse")(y[240:], model.predict(X.iloc[240:]))
    assert rmse < 0.6 * y.std()


def test_classifier_returns_probabilities(tabular):
    X, y = tabular
    labels = (y > np.median(y)).astype(int)
    model = build_model("logreg", "binary", seed=0, categorical_features=["c"]).fit(X, labels)
    proba = model.predict(X)
    assert proba.ndim == 1 and 0 <= proba.min() and proba.max() <= 1
    assert get_metric("auc")(labels, proba) > 0.9


def test_missing_backend_is_reported_cleanly():
    for kind in ("lgbm", "catboost"):
        if not backend_available(kind):
            with pytest.raises(ImportError, match="pip install"):
                build_model(kind, "regression")


def test_torch_mlp_trains_and_pickles(tabular, tmp_path):
    pytest.importorskip("torch")
    X, y = tabular
    model = build_model("torch_mlp", "regression", params={"max_epochs": 30, "patience": 5}, seed=0,
                        categorical_features=["c"]).fit(X.iloc[:240], y[:240])
    pred = model.predict(X.iloc[240:])
    assert get_metric("rmse")(y[240:], pred) < y.std()
    joblib.dump(model, tmp_path / "m.joblib")
    assert np.allclose(joblib.load(tmp_path / "m.joblib").predict(X.iloc[240:]), pred)


# --------------------------------------------------------------------------- ensembles et optimisation


def test_blends_and_hill_climbing_use_oof_only(rng):
    y = rng.normal(size=200)
    oofs = {"good": y + rng.normal(0, 0.2, 200), "bad": y + rng.normal(0, 1.0, 200)}
    rmse = get_metric("rmse")
    assert rmse(y, mean_blend(oofs)) < rmse(y, oofs["bad"])
    assert rank_average(oofs).shape == (200,)
    weights = hill_climbing(oofs, y, rmse, n_iter=20)
    assert weights["good"] > weights.get("bad", 0)
    splits = kfold_splits(200, 4, seed=0)
    stacked = run_ensemble("stacking", oofs, None, y, rmse, "regression", splits)
    assert stacked.score <= rmse(y, oofs["bad"]) and stacked.oof.shape == (200,)


def test_random_search_fallback_finds_optimum():
    space = {"x": {"type": "float", "low": -3, "high": 3}, "k": {"type": "int", "low": 1, "high": 4},
             "m": {"type": "categorical", "choices": ["a", "b"]}}

    def objective(params, report):
        score = (params["x"] - 1) ** 2 + (params["m"] == "b")
        report(0, score)  # valeur intermédiaire : l'arrêt médian peut élaguer l'essai
        return score

    result = tune(objective, space, n_trials=40, greater_is_better=False, seed=0)
    assert result.n_trials + result.n_pruned == 40 and result.best_score < 0.3 and result.best_params["m"] == "a"
    assert result.backend in ("optuna", "random")


def test_adversarial_validation_detects_shift(rng):
    train = pd.DataFrame({"a": rng.normal(size=400), "b": rng.normal(size=400)})
    same = adversarial_validation(train, pd.DataFrame({"a": rng.normal(size=400), "b": rng.normal(size=400)}),
                                  ["a", "b"], n_splits=3)
    shifted = adversarial_validation(train, train.assign(a=train.a + 3), ["a", "b"], n_splits=3)
    assert same.auc < 0.65 and shifted.auc > 0.9 and shifted.top_features[0][0] == "a"
    assert shifted.verdict != same.verdict


# --------------------------------------------------------------------------- soumission


def test_submission_build_validate_and_align():
    sample = pd.DataFrame({"id": ["3", "1", "2"], "target": 0.0})
    sub = build_submission(np.array(["1", "2", "3"]), np.array([5.0, -1.0, 2.0]), "id", ["target"], clip_min=0.0)
    assert sub["target"].min() == 0.0
    aligned = align_to_sample(sub, sample, "id")
    assert list(aligned["id"].astype(str)) == ["3", "1", "2"] and validate_submission(aligned, sample, "id") == []
    broken = aligned.iloc[:2]
    assert validate_submission(broken, sample, "id")
    with pytest.raises(SubmissionError):
        assert_valid_submission(broken, sample, "id")
    nan_sub = aligned.assign(target=[np.nan, 1.0, 2.0])
    assert validate_submission(nan_sub, sample, "id")


# --------------------------------------------------------------------------- registre et promotion


def test_local_registry_versions_aliases_and_names(tmp_path):
    reg = LocalRegistry(tmp_path)
    assert reg.register("yield", {"score": 1.0}) == 1 and reg.register("yield", {"score": 0.9}) == 2
    reg.set_alias("yield", "champion", 2)
    assert reg.get_by_alias("yield", "champion")["score"] == 0.9 and reg.get("yield", 1)["score"] == 1.0
    assert reg.get_by_alias("yield", "challenger") is None
    with pytest.raises(RegistryError):
        reg.set_alias("yield", "champion", 99)
    with pytest.raises(RegistryError):
        reg.register("../evil", {})


def test_promotion_gate():
    assert improvement(1.0, 0.9, greater_is_better=False) == pytest.approx((0.1, 0.1))
    assert decide_promotion(None, 0.9, False, n_holdout=500).promote
    assert not decide_promotion(1.0, 0.5, False, n_holdout=50).promote  # holdout trop petit
    assert not decide_promotion(1.0, 0.995, False, n_holdout=500).promote  # gain < 1 %
    assert decide_promotion(1.0, 0.95, False, n_holdout=500).promote
    regressed = decide_promotion(1.0, 0.95, False, 500, champion_slices={"riz": 1.0, "mil": 1.0},
                                 challenger_slices={"riz": 1.1, "mil": 0.8})
    assert not regressed.promote and "riz" in regressed.reasons[0]
    assert slice_regressions({"a": 0.8}, {"a": 0.7}, True, 0.02) == ["a (-12.5%)"]


def test_promote_writes_local_alias(tmp_path):
    reg = LocalRegistry(tmp_path)
    version = reg.register("disease", {"auc": 0.93})
    assert promote("disease", version, registry=reg) == "local"
    assert reg.aliases("disease") == {"champion": version}
