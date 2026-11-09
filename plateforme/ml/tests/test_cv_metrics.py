"""Validation croisée (absence de fuite) et métriques."""

from __future__ import annotations

import numpy as np
import pytest

from agriml.cv import (
    LeakageError, assert_no_leakage, check_no_leakage, group_splits, kfold_splits, purged_time_splits,
    regression_bins, spatial_block_splits, stratified_group_splits, stratified_splits,
)
from agriml.metrics import (
    apk, get_metric, inverse_log1p, list_metrics, log1p_target, mapk, optimize_f1_threshold,
)


def covers_each_row_once(splits, n):
    seen = np.concatenate([va for _, va in splits])
    return len(seen) == n and len(np.unique(seen)) == n


def test_group_splits_keep_groups_together(rng):
    groups = np.repeat(np.arange(20), 5)
    splits = group_splits(groups, n_splits=5, seed=0)
    assert covers_each_row_once(splits, len(groups))
    for tr, va in splits:
        assert not set(groups[tr]) & set(groups[va])
    assert check_no_leakage(splits, len(groups), groups=groups) == []


def test_stratified_group_splits_balance_and_isolate_groups(rng):
    groups = np.repeat(np.arange(30), 3)
    y = np.repeat(rng.integers(0, 3, 30), 3)
    splits = stratified_group_splits(y, groups, n_splits=3, seed=0)
    assert covers_each_row_once(splits, len(y))
    assert_no_leakage(splits, len(y), groups=groups)
    for _, va in splits:
        assert set(y[va]) == {0, 1, 2}


def test_purged_time_splits_respect_gap_and_embargo():
    times = np.repeat(np.arange(100), 3).astype(float)
    splits = purged_time_splits(times, n_splits=4, gap=5, embargo=3)
    assert check_no_leakage(splits, len(times), times=times, gap=5, embargo=3) == []
    for tr, va in splits:
        lo, hi = times[va].min(), times[va].max()
        before, after = times[tr][times[tr] < lo], times[tr][times[tr] > hi]
        assert before.size == 0 or lo - before.max() > 5
        assert after.size == 0 or after.min() - hi > 3


def test_walk_forward_trains_only_on_the_past():
    times = np.arange(60, dtype=float)
    for tr, va in purged_time_splits(times, n_splits=3, gap=2, forward=True):
        assert times[tr].max() < times[va].min() - 2


def test_leakage_detector_flags_overlap_and_shared_groups():
    groups = np.array([0, 0, 1, 1])
    bad = [(np.array([0, 2]), np.array([1, 3]))]
    issues = check_no_leakage(bad, 4, groups=groups)
    assert issues
    with pytest.raises(LeakageError):
        assert_no_leakage([(np.array([0, 1]), np.array([1, 2]))], 4)


def test_kfold_stratified_bins_and_spatial(rng):
    assert covers_each_row_once(kfold_splits(50, 5, seed=1), 50)
    y = rng.normal(size=200)
    bins = regression_bins(y, n_bins=10)
    assert len(np.unique(bins)) == 10
    assert covers_each_row_once(stratified_splits(bins, 4, seed=1), 200)
    lat, lon = rng.uniform(12, 16, 200), rng.uniform(-17, -12, 200)
    splits = spatial_block_splits(lat, lon, y, n_splits=4, seed=1, block_size_deg=0.5, classification=False)
    assert covers_each_row_once(splits, 200)


# --------------------------------------------------------------------------- métriques


def test_regression_metrics_and_direction():
    y = np.array([1.0, 2.0, 3.0])
    rmse = get_metric("rmse")
    assert rmse(y, y) == 0 and not rmse.greater_is_better
    assert get_metric("mae")(y, y + 1) == pytest.approx(1.0)
    assert get_metric("auc").greater_is_better
    assert {"rmse", "mae", "auc", "logloss", "f1_macro", "accuracy"} <= set(list_metrics())
    with pytest.raises((KeyError, ValueError)):
        get_metric("does_not_exist")


def test_classification_metrics_accept_probability_matrices():
    y = np.array([0, 1, 2, 1])
    proba = np.array([[0.8, 0.1, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8], [0.6, 0.3, 0.1]])
    assert get_metric("accuracy")(y, proba) == pytest.approx(0.75)
    assert 0 < get_metric("f1_macro")(y, proba) < 1
    assert get_metric("logloss")(y, proba) == pytest.approx(-np.mean(np.log([0.8, 0.8, 0.8, 0.3])))


def test_map_at_k_known_values():
    assert apk([1, 2], [1, 3, 2], k=3) == pytest.approx((1 + 2 / 3) / 2)
    assert mapk([[1], [2]], [[1, 2], [3, 4]], k=2) == pytest.approx(0.5)


def test_f1_threshold_beats_default_and_log1p_roundtrip(rng):
    y = (rng.uniform(size=400) < 0.15).astype(int)
    proba = np.clip(0.2 * y + rng.uniform(0, 0.4, 400), 0, 1)
    threshold, f1 = optimize_f1_threshold(y, proba)
    default = get_metric("f1")(y, (proba >= 0.5).astype(int)) if "f1" in list_metrics() else 0.0
    assert 0 < threshold < 1 and f1 >= default
    values = np.array([0.0, 1.5, 30.0])
    assert np.allclose(inverse_log1p(log1p_target(values)), values)
