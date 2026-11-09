"""Tests de bout en bout sur données synthétiques minuscules (générées dans un dossier temporaire).

Couvre : entraînement CV → artefacts → prédiction (parité) → évaluation → paquet signé (et refus si altéré),
prévision d'humidité du sol (sans fuite du futur) et correction MOS de la prévision météo.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from agriml.config import ConfigError, parse_config
from agriml.evaluate import evaluate_run
from agriml.export import MANIFEST, BundleIntegrityError, export_bundle, verify_bundle
from agriml.forecast.soil_moisture import (
    SoilForecastConfig,
    cross_validate,
    feature_columns,
    make_supervised,
    resample_hourly,
)
from agriml.forecast.weather_mos import MosConfig, evaluate_mos
from agriml.predict import load_run, predict_frame
from agriml.train import run_experiment

ML_ROOT = Path(__file__).resolve().parents[1]
SEED = 123


def _load_generator():
    spec = importlib.util.spec_from_file_location("make_synthetic", ML_ROOT / "scripts" / "make_synthetic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def synthetic_root(tmp_path_factory) -> Path:
    gen, out = _load_generator(), tmp_path_factory.mktemp("synthetic")
    rng = np.random.default_rng(SEED)
    gen.make_yield(rng, out, n_fields=40)
    gen.make_telemetry(rng, out, n_devices=2, days=20)
    gen.make_weather_mos(rng, out, n_stations=2, days=40)
    return out


def _yield_raw(root: Path) -> dict:
    folder = root / "yield"
    return {
        "name": "yield_e2e", "task": "regression", "metric": "rmse", "seeds": [42],
        "data": {"train": str(folder / "yield_train.csv"), "test": str(folder / "yield_test.csv"),
                 "sample_submission": str(folder / "yield_sample_submission.csv"),
                 "test_labels": str(folder / "yield_test_labels.csv")},
        "columns": {"id": "row_id", "target": "yield_t_ha", "group": "field_id", "time": "year",
                    "categorical": ["region", "crop", "soil_type"]},
        "cv": {"scheme": "group", "n_splits": 3},
        "features": {"blocks": ["agronomy"], "agronomy": {
            "tmin": "tmin_mean", "tmax": "tmax_mean", "rh": "rh_mean", "rain": "rain_mm",
            "irrigation": "irrigation_mm", "lat": "lat", "doy": "mid_season_doy", "crop": "crop",
            "season_days": "season_days", "heat_days": "heat_days_35"}},
        "models": [{"name": "hgb", "kind": "hgb", "params": {"max_iter": 60, "learning_rate": 0.1}},
                   {"name": "ridge", "kind": "ridge", "params": {"alpha": 3.0}}],
        "ensemble": {"method": "hill_climbing", "n_iter": 10},
        "output_dir": str(root / "artifacts"),
    }


@pytest.fixture(scope="module")
def yield_run(synthetic_root):
    cfg = parse_config(_yield_raw(synthetic_root), root_dir=synthetic_root)
    scores = run_experiment(cfg, use_tuning=False)
    return cfg, scores


def test_run_experiment_writes_scores_and_beats_constant_baseline(yield_run):
    # Arrange
    cfg, scores = yield_run

    # Act
    on_disk = json.loads((cfg.run_dir / "cv_scores.json").read_text(encoding="utf-8"))

    # Assert
    assert set(scores["models"]) == {"hgb", "ridge"}
    assert scores["final"]["cv"] < scores["baseline_constant"]
    assert on_disk["final"]["name"] == scores["final"]["name"]
    assert scores["holdout"], "le holdout figé doit être noté (rapport uniquement)"


def test_predict_frame_matches_training_submission(yield_run, synthetic_root):
    # Arrange
    cfg, _ = yield_run
    folder = synthetic_root / "yield"
    train, test = pd.read_csv(folder / "yield_train.csv"), pd.read_csv(folder / "yield_test.csv")
    submission = pd.read_csv(cfg.run_dir / cfg.submission.file_name)

    # Act
    pred = predict_frame(load_run(cfg.run_dir), test, history=train)

    # Assert
    merged = submission.merge(pred, on="row_id")
    assert len(merged) == len(test)
    np.testing.assert_allclose(merged["yield_t_ha"], merged["prediction"], rtol=1e-6, atol=1e-6)


def test_evaluate_run_reports_slices_and_residuals(yield_run):
    cfg, _ = yield_run
    report = evaluate_run(cfg.run_dir)
    assert report["metric"] == "rmse" and report["n_rows"] > 0
    assert "residuals" in report and "region" in report["slices"]
    assert (cfg.run_dir / "evaluation.json").exists()


def test_export_bundle_verifies_then_refuses_tampering(yield_run, tmp_path):
    # Arrange
    cfg, _ = yield_run
    bundle = export_bundle(cfg.run_dir, tmp_path / "bundle")
    manifest = json.loads((bundle / MANIFEST).read_text(encoding="utf-8"))

    # Act
    digest = verify_bundle(bundle)
    victim = bundle / sorted(manifest["files"])[0]
    victim.write_bytes(victim.read_bytes() + b"x")

    # Assert
    assert len(digest) == 64
    with pytest.raises(BundleIntegrityError):
        verify_bundle(bundle)


@pytest.mark.parametrize("patch, message", [
    ({"cv": {"scheme": "inconnu"}}, "cv.scheme"),
    ({"models": []}, "models"),
    ({"cv": {"scheme": "purged_time"}, "columns": {"id": "row_id", "target": "yield_t_ha"}}, "columns.time"),
])
def test_invalid_config_raises_config_error(synthetic_root, patch, message):
    raw = {**_yield_raw(synthetic_root), **patch}
    with pytest.raises(ConfigError, match=message):
        parse_config(raw, root_dir=synthetic_root)


def _soil_cfg(root: Path) -> SoilForecastConfig:
    return SoilForecastConfig(data=str(root / "telemetry" / "telemetry.csv"), n_splits=3,
                              params={"max_iter": 60, "learning_rate": 0.1, "max_leaf_nodes": 15})


def test_soil_features_ignore_future_values(synthetic_root):
    # Arrange
    cfg = _soil_cfg(synthetic_root)
    hourly = resample_hourly(pd.read_csv(cfg.data), cfg)
    cutoff = hourly[cfg.time].quantile(0.5)
    altered = hourly.copy()
    future = altered[cfg.time] > cutoff
    altered.loc[future, cfg.target] = altered.loc[future, cfg.target] + 25.0

    # Act
    base, moved = make_supervised(hourly, cfg), make_supervised(altered, cfg)

    # Assert : les variables connues à t ≤ cutoff ne voient pas le futur modifié
    feats = feature_columns(base, cfg)
    past_base = base[base[cfg.time] <= cutoff].reset_index(drop=True)
    past_moved = moved[moved[cfg.time] <= cutoff].reset_index(drop=True)
    pd.testing.assert_frame_equal(past_base[feats], past_moved[feats])
    assert not past_base["delta_h24"].equals(past_moved["delta_h24"])


def test_soil_cross_validate_beats_persistence(synthetic_root):
    cfg = _soil_cfg(synthetic_root)
    sup = make_supervised(resample_hourly(pd.read_csv(cfg.data), cfg), cfg)
    scores, oof = cross_validate(sup, cfg)
    assert set(scores) == {"h24", "h48", "h72"}
    assert scores["h24"]["n"] > 0 and oof.notna().any().all()
    assert scores["h24"]["rmse"] < scores["h24"]["persistence_rmse"]


def test_soil_config_requires_gap_at_least_max_horizon():
    with pytest.raises(ValueError, match="gap_hours"):
        SoilForecastConfig(gap_hours=24)


def test_weather_mos_reduces_raw_error(synthetic_root):
    df = pd.read_csv(synthetic_root / "weather_mos" / "weather_mos.csv")
    cfg = MosConfig(n_splits=3, params={"max_iter": 60, "learning_rate": 0.1, "max_leaf_nodes": 15})
    report = evaluate_mos(df, cfg)
    assert report["n_validated"] > 0
    assert report["mos_rmse"] < report["raw_rmse"]
    assert all({"raw_rmse", "mos_rmse"} <= set(v) for v in report["per_lead"].values())
