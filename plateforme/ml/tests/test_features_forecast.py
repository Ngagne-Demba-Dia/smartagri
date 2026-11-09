"""Features (pas de fuite du futur, entrée intacte), agronomie, encodage de cible, irrigation, dérive."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agriml.features.agronomy import (
    extraterrestrial_radiation_mj, growing_degree_days, hargreaves_et0_mm, vapour_pressure_deficit_kpa,
)
from agriml.features.encoding import CategoricalCoder, OOFTargetEncoder
from agriml.features.remote_sensing import add_series_features, ndvi
from agriml.features.temporal import add_cyclical_features, add_lag_features, add_rolling_features
from agriml.forecast.irrigation import (
    ACTION_DEFER, ACTION_NONE, ACTION_NOW, ACTION_SOON, crop_water_need_mm, irrigation_depth_mm, pump_minutes,
    recommend_irrigation, validate_thresholds,
)
from agriml.monitoring.drift import (
    RetrainPolicy, drift_report, psi_band, psi_categorical, psi_numeric, relative_decay, should_retrain,
)


@pytest.fixture
def series_frame(rng) -> pd.DataFrame:
    return pd.DataFrame({"g": np.repeat(["a", "b"], 10), "t": np.tile(np.arange(10), 2),
                         "x": rng.normal(size=20)}).sample(frac=1, random_state=0)


def test_lags_are_per_group_and_ignore_the_future(series_frame):
    before = series_frame.copy()
    out = add_lag_features(series_frame, ["x"], [1, 2], time="t", group="g")
    pd.testing.assert_frame_equal(series_frame, before)
    a = out[out.g == "a"].sort_values("t")
    assert np.isnan(a["x_lag1"].iloc[0]) and a["x_lag1"].iloc[3] == pytest.approx(a["x"].iloc[2])
    future = series_frame.assign(x=np.where(series_frame.t >= 5, 999.0, series_frame.x))
    out2 = add_lag_features(future, ["x"], [1], time="t", group="g")
    early = out.t <= 5
    assert np.allclose(out.loc[early, "x_lag1"].fillna(0), out2.loc[early, "x_lag1"].fillna(0))


def test_rolling_excludes_current_value_by_default(series_frame):
    out = add_rolling_features(series_frame, ["x"], [3], time="t", group="g")
    new_cols = [c for c in out.columns if c not in series_frame.columns]
    assert new_cols
    bumped = series_frame.assign(x=np.where(series_frame.t == 4, 1e6, series_frame.x))
    out2 = add_rolling_features(bumped, ["x"], [3], time="t", group="g")
    at_t4 = out.t == 4
    assert np.allclose(out.loc[at_t4, new_cols].fillna(0), out2.loc[at_t4, new_cols].fillna(0))


def test_cyclical_encoding_is_on_unit_circle():
    out = add_cyclical_features(pd.DataFrame({"doy": [1, 91, 182, 274]}), "doy", kind="doy")
    sin_col, cos_col = [c for c in out.columns if c != "doy"]
    assert np.allclose(out[sin_col] ** 2 + out[cos_col] ** 2, 1.0)


def test_agronomy_formulas_are_physical():
    assert growing_degree_days(np.array([15.0]), np.array([35.0]), base=10.0, upper=30.0)[0] == pytest.approx(12.5)
    assert (vapour_pressure_deficit_kpa(np.array([20.0]), np.array([35.0]), np.array([40.0])) > 0).all()
    ra = extraterrestrial_radiation_mj(np.array([14.7]), np.array([172]))
    et0 = hargreaves_et0_mm(np.array([24.0]), np.array([36.0]), ra)
    assert 30 < ra[0] < 45 and 4 < et0[0] < 9  # Dakar, juin : ordres de grandeur FAO-56


def test_remote_sensing_series_features():
    assert ndvi(np.array([0.5]), np.array([0.1]))[0] == pytest.approx(0.4 / 0.6)
    df = pd.DataFrame({"ndvi_1": [0.2, 0.3], "ndvi_2": [0.6, 0.4], "ndvi_3": [0.4, 0.5]})
    out = add_series_features(df, "ndvi_")
    assert out.shape[1] > df.shape[1] and df.shape[1] == 3


def test_target_encoder_is_out_of_fold_and_smoothed(rng):
    X = pd.DataFrame({"c": rng.choice(list("abcde"), 300)})
    y = (X.c == "a").astype(float).to_numpy() + rng.normal(0, 0.1, 300)
    enc = OOFTargetEncoder(columns=["c"], smoothing=5.0, n_splits=5, seed=0)
    train_enc = enc.fit_transform(X, y)
    test_enc = enc.transform(pd.DataFrame({"c": ["a", "b", "zzz"]}))
    col = enc.output_names("c")[0]
    assert train_enc[col].nunique() > 5  # valeurs hors-pli : pas une simple table
    assert test_enc[col].iloc[0] > 0.8 and test_enc[col].iloc[1] < 0.2
    assert test_enc[col].iloc[2] == pytest.approx(enc.prior_[0], abs=1e-9)  # catégorie inconnue → a priori


def test_categorical_coder_handles_unknown():
    coder = CategoricalCoder(columns=["c"]).fit(pd.DataFrame({"c": ["x", "y", None]}))
    out = coder.transform(pd.DataFrame({"c": ["y", "new"]}))
    assert out["c"].iloc[0] != out["c"].iloc[1] and coder.cardinality("c") >= 2


# --------------------------------------------------------------------------- irrigation


@pytest.mark.parametrize("start, stop", [(30, 35), (0, 5), (95, 100)])
def test_valid_firmware_thresholds(start, stop):
    assert validate_thresholds(start, stop) == (start, stop)


@pytest.mark.parametrize("start, stop", [(30, 34), (-1, 10), (96, 101), (30.0, 40), (True, 40)])
def test_invalid_firmware_thresholds(start, stop):
    with pytest.raises(ValueError):
        validate_thresholds(start, stop)


def test_water_balance_helpers():
    assert crop_water_need_mm(6.0, 1.15, rain_mm=2.0) == pytest.approx(6.9 - 1.6)
    assert crop_water_need_mm(2.0, 1.0, rain_mm=20.0) == 0.0
    assert irrigation_depth_mm(25, 40, root_depth_mm=300) == pytest.approx(45.0)
    assert pump_minutes(10, 100, 50) == pytest.approx(20.0)
    with pytest.raises(ValueError):
        pump_minutes(10, 100, 0)


def test_recommendations():
    assert recommend_irrigation(25, {24: 24}, 30, 40).action == ACTION_NOW
    assert recommend_irrigation(35, {24: 34, 48: 33}, 30, 40).action == ACTION_NONE
    soon = recommend_irrigation(35, {48: 29, 24: 32}, 30, 40)
    assert soon.action == ACTION_SOON and soon.hours_to_start == 48 and soon.depth_mm > 0
    assert recommend_irrigation(35, {24: 28}, 30, 40, rain_forecast_mm=15).action == ACTION_DEFER


# --------------------------------------------------------------------------- dérive


def test_psi_detects_shift(rng):
    ref = rng.normal(size=5000)
    assert psi_numeric(ref, rng.normal(size=5000)) < 0.1
    assert psi_numeric(ref, rng.normal(1.5, 1, size=5000)) > 0.25
    assert psi_band(0.05) != psi_band(0.5)
    assert psi_categorical(np.array(["a"] * 50 + ["b"] * 50), np.array(["a"] * 90 + ["b"] * 10)) > 0.25


def test_drift_report_and_retrain_decision(rng):
    ref = pd.DataFrame({"a": rng.normal(size=2000), "b": rng.normal(size=2000)})
    cur = ref.assign(a=ref.a + 2)
    report = drift_report(ref, cur, ["a", "b"])
    assert report.share_significant == pytest.approx(0.5) and report.top(1)[0].feature == "a"
    assert should_retrain(report).retrain
    calm = drift_report(ref, ref.copy(), ["a", "b"])
    assert not should_retrain(calm, RetrainPolicy(), model_age_days=10).retrain
    assert should_retrain(calm, model_age_days=120, n_new_labels=500).retrain
    assert not should_retrain(calm, model_age_days=120, n_new_labels=0).retrain  # pas d'étiquettes : inutile
    assert relative_decay(0.80, 0.70, greater_is_better=True) == pytest.approx(0.125)
    assert should_retrain(calm, reference_score=1.0, current_score=1.2, greater_is_better=False).retrain
