"""Sélection de variables : importance nulle, permutation hors-pli, élagage adversarial (données minuscules)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor

from agriml.cv import kfold_splits
from agriml.metrics import get_metric
from agriml.selection import adversarial_prune, null_importance, permutation_importance_cv


@pytest.fixture
def signal_frame(rng) -> tuple[pd.DataFrame, np.ndarray]:
    X = pd.DataFrame({"signal": rng.normal(size=300), "noise_a": rng.normal(size=300), "noise_b": rng.normal(size=300)})
    return X, 3.0 * X["signal"].to_numpy() + rng.normal(scale=0.3, size=300)


def test_null_importance_keeps_signal_and_rejects_noise(signal_frame):
    # Arrange
    X, y = signal_frame
    before = X.copy()
    forest = RandomForestRegressor(n_estimators=30, max_depth=4, random_state=0, n_jobs=1)

    # Act
    scores = null_importance(forest, X, y, n_null=12, seed=0)

    # Assert
    by_name = {s.name: s for s in scores}
    assert scores[0].name == "signal" and by_name["signal"].useful
    assert not by_name["noise_a"].useful and not by_name["noise_b"].useful
    pd.testing.assert_frame_equal(X, before)  # entrée intacte


def test_null_importance_uses_coefficients_and_rejects_opaque_models(signal_frame):
    X, y = signal_frame
    assert null_importance(Ridge(), X, y, n_null=12)[0].name == "signal"
    with pytest.raises(TypeError, match="feature_importances_"):
        null_importance(KNeighborsRegressor(), X, y, n_null=2)


def test_permutation_importance_cv_regression(signal_frame):
    X, y = signal_frame
    scores = permutation_importance_cv(Ridge(), X, y, kfold_splits(len(X), 3, seed=0), get_metric("rmse"))
    by_name = {s.name: s for s in scores}
    assert scores[0].name == "signal" and by_name["signal"].importance > 1.0 and by_name["signal"].p_value == 0.0
    assert abs(by_name["noise_a"].importance) < 0.05 * by_name["signal"].importance


def test_permutation_importance_cv_binary_uses_probabilities(signal_frame):
    X, y = signal_frame
    labels = (y > 0).astype(int)
    scores = permutation_importance_cv(LogisticRegression(), X, labels, kfold_splits(len(X), 3, seed=0),
                                       get_metric("auc"), n_repeats=2)
    assert scores[0].name == "signal" and scores[0].importance > 0.2


def test_adversarial_prune_drops_only_the_shifted_column(rng):
    # Arrange : « compteur » dérive entre train et test, les autres variables sont stables
    train = pd.DataFrame({"compteur": rng.normal(0, 1, 300), "a": rng.normal(size=300), "b": rng.normal(size=300)})
    test = pd.DataFrame({"compteur": rng.normal(3, 1, 300), "a": rng.normal(size=300), "b": rng.normal(size=300)})

    # Act
    result = adversarial_prune(train, test, ["compteur", "a", "b"], max_auc=0.6, max_drops=2, n_splits=3)

    # Assert
    assert result.dropped == ("compteur",) and result.kept == ("a", "b")
    assert result.auc_history[0] > 0.9 and result.auc_history[-1] <= 0.6
