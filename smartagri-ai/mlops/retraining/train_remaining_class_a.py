"""Entraînement local complet des modèles Classe A manquants (A2, A4, A6, A7, A8).

Utilise exclusivement les datasets Parquet réels de `smartagri-ai/datasets/` (via fastparquet)
et les hyperparamètres / features de référence de `champions_summary.json` et `features_by_model.json`.
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
PYDEPS = ROOT / ".pydeps"
if PYDEPS.exists() and str(PYDEPS) not in sys.path:
    sys.path.append(str(PYDEPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import OneClassSVM

from runtime.rain_intelligence_service import RainIntelligenceService

RAW_DIR = ROOT / "datasets" / "raw"
CURATED_DIR = ROOT / "datasets" / "curated" / "soil_nowcast_proxy_national" / "v=20261114-natl01"
MODELS_DIR = ROOT / "models"


def train_a2_et0() -> Dict[str, Any]:
    t0 = time.perf_counter()
    print("\n=== [A2] Entraînement ET0 Forecast (CatBoostRegressor) ===")
    et0 = pd.read_parquet(RAW_DIR / "et0" / "fao56_et0_national_daily.parquet", engine="fastparquet")
    nasa = pd.read_parquet(RAW_DIR / "meteo" / "nasa_power_national_daily.parquet", engine="fastparquet")
    df = nasa.merge(
        et0[["power_cell_id", "date", "et0_pm_mm", "ra_mj_m2", "et0_hargreaves_mm"]],
        on=["power_cell_id", "date"],
        how="inner",
    ).dropna(subset=["et0_pm_mm"]).copy()

    df["date"] = pd.to_datetime(df["date"])
    df["doy"] = df["date"].dt.dayofyear
    df["month"] = df["date"].dt.month
    df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365.0)
    df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365.0)
    df["t_range_c"] = df["t_max_c"] - df["t_min_c"]

    features = [
        "t_min_c", "t_max_c", "t_mean_c", "rh_mean_pct", "wind_2m_ms",
        "solar_rad_mj_m2", "pressure_hpa", "rain_mm", "ra_mj_m2",
        "et0_hargreaves_mm", "doy_sin", "doy_cos", "month", "t_range_c", "lat", "lon",
    ]
    X = df[features].to_numpy(dtype=np.float64)
    y = df["et0_pm_mm"].to_numpy(dtype=np.float64)
    groups = df["power_cell_id"].to_numpy()

    gkf = GroupKFold(n_splits=5)
    oof = np.zeros_like(y)
    for fold, (tr, va) in enumerate(gkf.split(X, y, groups)):
        m = cb.CatBoostRegressor(
            iterations=1000, learning_rate=0.05, depth=8,
            subsample=0.8, l2_leaf_reg=3.0, random_seed=42, verbose=0, early_stopping_rounds=50,
        )
        m.fit(X[tr], y[tr], eval_set=(X[va], y[va]))
        oof[va] = m.predict(X[va])
        print(f"  fold {fold}: RMSE={root_mean_squared_error(y[va], oof[va]):.4f} R2={r2_score(y[va], oof[va]):.4f}")

    # Entraînement final sur 100% des données
    final_model = cb.CatBoostRegressor(
        iterations=1000, learning_rate=0.05, depth=8,
        subsample=0.8, l2_leaf_reg=3.0, random_seed=42, verbose=0,
    )
    final_model.fit(X, y)
    out_dir = MODELS_DIR / "et0"
    out_dir.mkdir(parents=True, exist_ok=True)
    cbm_path = out_dir / "a2_et0_champion.cbm"
    final_model.save_model(str(cbm_path))

    metrics = {
        "champion": "CatBoost",
        "r2": round(float(r2_score(y, oof)), 4),
        "rmse": round(float(root_mean_squared_error(y, oof)), 4),
        "mae": round(float(mean_absolute_error(y, oof)), 4),
        "rows": int(len(df)),
        "features": features,
        "artifact": str(cbm_path.relative_to(ROOT)).replace("\\", "/"),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    (out_dir / "a2_et0_metadata.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"  [OK] A2 sauvegardé -> {cbm_path.name} | R2={metrics['r2']} RMSE={metrics['rmse']}")
    return metrics


def train_a4_rain() -> Dict[str, Any]:
    t0 = time.perf_counter()
    print("\n=== [A4] Entraînement Rain Intelligence (CatBoostClassifier x3 horizons) ===")
    df = pd.read_parquet(CURATED_DIR / "train.parquet", engine="fastparquet")
    df = df.sort_values(["power_cell_id", "ts"]).reset_index(drop=True)

    features = list(RainIntelligenceService.FEATURES)
    # Cibles binaires pluie >= 1.0 mm à J+1, J+2, J+3 (sans fuite entre mailles)
    grp = df.groupby("power_cell_id")
    for h, tname in [(1, "rain_1d"), (2, "rain_2d"), (3, "rain_3d")]:
        fut_chirps = grp["rain_chirps_mm"].shift(-h)
        fut_nasa = grp["rain_mm"].shift(-h)
        df[tname] = ((fut_chirps >= 1.0) | (fut_nasa >= 1.0)).astype(float)
        df.loc[fut_chirps.isna() & fut_nasa.isna(), tname] = np.nan

    df_clean = df.dropna(subset=features + ["rain_1d", "rain_2d", "rain_3d"]).reset_index(drop=True)
    X = df_clean[features].to_numpy(dtype=np.float64)
    groups = df_clean["power_cell_id"].to_numpy()
    gkf = GroupKFold(n_splits=5)

    out_dir = MODELS_DIR / "rain_intelligence"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Any] = {"champion": "CatBoost", "targets": {}, "features": features}

    for tname in ("rain_1d", "rain_2d", "rain_3d"):
        y = df_clean[tname].to_numpy(dtype=np.int32)
        oof_prob = np.zeros(len(y), dtype=np.float64)
        for fold, (tr, va) in enumerate(gkf.split(X, y, groups)):
            clf = cb.CatBoostClassifier(
                iterations=600, learning_rate=0.06, depth=6, l2_leaf_reg=3.0,
                eval_metric="AUC", random_seed=42, verbose=0, early_stopping_rounds=40,
            )
            clf.fit(X[tr], y[tr], eval_set=(X[va], y[va]))
            oof_prob[va] = clf.predict_proba(X[va])[:, 1]

        auc = float(roc_auc_score(y, oof_prob))
        brier = float(brier_score_loss(y, oof_prob))
        thr = RainIntelligenceService.THRESHOLDS[tname]
        f1 = float(f1_score(y, (oof_prob >= thr).astype(int)))
        print(f"  {tname}: AUC={auc:.4f} F1={f1:.4f} Brier={brier:.4f}")

        final_clf = cb.CatBoostClassifier(
            iterations=600, learning_rate=0.06, depth=6, l2_leaf_reg=3.0,
            random_seed=42, verbose=0,
        )
        final_clf.fit(X, y)
        cbm_path = out_dir / f"{tname}_champion.cbm"
        final_clf.save_model(str(cbm_path))
        summary["targets"][tname] = {
            "auc": round(auc, 4), "f1": round(f1, 4), "brier": round(brier, 4),
            "artifact": str(cbm_path.relative_to(ROOT)).replace("\\", "/"),
        }

    summary["elapsed_s"] = round(time.perf_counter() - t0, 2)
    (out_dir / "a4_rain_metadata.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  [OK] A4 sauvegardé (3 .cbm) en {summary['elapsed_s']}s")
    return summary


def train_a6_crop_calendar() -> Dict[str, Any]:
    t0 = time.perf_counter()
    print("\n=== [A6] Entraînement Crop Calendar (CatBoostClassifier) ===")
    kc = pd.read_parquet(RAW_DIR / "crops_senegal" / "fao56_crop_coefficients_daily.parquet", engine="fastparquet")
    le_stage = LabelEncoder()
    le_crop = LabelEncoder()
    kc["stage_enc"] = le_stage.fit_transform(kc["growth_stage"])
    kc["crop_enc"] = le_crop.fit_transform(kc["crop_code"])

    features = ["crop_enc", "day_after_planting", "season_days", "kc", "kc_ini", "kc_mid", "kc_end"]
    X = kc[features].to_numpy(dtype=np.float64)
    y = kc["stage_enc"].to_numpy(dtype=np.int32)

    oof = np.zeros_like(y)
    for tr, va in KFold(5, shuffle=True, random_state=42).split(X):
        m = cb.CatBoostClassifier(
            iterations=500, learning_rate=0.05, depth=6, bootstrap_type="Bernoulli",
            subsample=0.8, l2_leaf_reg=3.0, random_seed=42, verbose=0, early_stopping_rounds=30,
        )
        m.fit(X[tr], y[tr], eval_set=(X[va], y[va]))
        oof[va] = m.predict(X[va]).ravel()

    final_m = cb.CatBoostClassifier(
        iterations=500, learning_rate=0.05, depth=6, bootstrap_type="Bernoulli",
        subsample=0.8, l2_leaf_reg=3.0, random_seed=42, verbose=0,
    )
    final_m.fit(X, y)
    out_dir = MODELS_DIR / "clustering"
    out_dir.mkdir(parents=True, exist_ok=True)
    cbm_path = out_dir / "a6_crop_calendar_champion.cbm"
    final_m.save_model(str(cbm_path))

    metrics = {
        "champion": "CatBoost",
        "accuracy": round(float(accuracy_score(y, oof)), 4),
        "f1_macro": round(float(f1_score(y, oof, average="macro", zero_division=0)), 4),
        "stages": le_stage.classes_.tolist(),
        "crops": le_crop.classes_.tolist(),
        "features": features,
        "artifact": str(cbm_path.relative_to(ROOT)).replace("\\", "/"),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    (out_dir / "a6_crop_calendar_metadata.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"  [OK] A6 sauvegardé -> {cbm_path.name} | F1={metrics['f1_macro']} Acc={metrics['accuracy']}")
    return metrics


def train_a7_ndvi_anomaly() -> Dict[str, Any]:
    t0 = time.perf_counter()
    print("\n=== [A7] Entraînement NDVI Anomaly (LightGBMClassifier) ===")
    ndvi = pd.read_parquet(RAW_DIR / "sentinel2_ndvi" / "s2_ndvi_national_grid_monthly_2025.parquet", engine="fastparquet")
    wc = pd.read_parquet(RAW_DIR / "crops_senegal" / "esa_worldcover_national_grid_0p05.parquet", engine="fastparquet")
    df = ndvi.dropna(subset=["ndvi_mean"]).copy()
    df["month_num"] = pd.to_datetime(df["month"]).dt.month
    df["is_anomaly"] = 0
    for mo in df["month_num"].unique():
        mask = df["month_num"] == mo
        vals = df.loc[mask, "ndvi_mean"]
        df.loc[mask & ((df["ndvi_mean"] < vals.quantile(0.10)) | (df["ndvi_mean"] > vals.quantile(0.98))), "is_anomaly"] = 1

    share_cols = [c for c in wc.columns if c.startswith("share_")]
    df = df.merge(wc[["cell_id"] + share_cols].drop_duplicates(subset=["cell_id"]), on="cell_id", how="left")
    features = ["cell_id", "month_num", "ndvi_mean", "ndvi_std", "n_valid_px", "valid_fraction"] + share_cols
    features = [f for f in features if f in df.columns]
    df = df.dropna(subset=features).reset_index(drop=True)

    X = df[features].to_numpy(dtype=np.float64)
    y = df["is_anomaly"].to_numpy(dtype=np.int32)
    oof = np.zeros_like(y)
    for tr, va in StratifiedKFold(5, shuffle=True, random_state=42).split(X, y):
        m = lgb.LGBMClassifier(
            n_estimators=500, learning_rate=0.05, max_depth=6, num_leaves=31,
            subsample=0.8, colsample_bytree=0.8, min_child_samples=5, random_state=42, verbosity=-1, n_jobs=2,
            callbacks=[lgb.early_stopping(30, verbose=False)],
        )
        m.fit(X[tr], y[tr], eval_set=[(X[va], y[va])])
        oof[va] = m.predict(X[va])

    final_m = lgb.LGBMClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=6, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=5, random_state=42, verbosity=-1, n_jobs=2,
    )
    final_m.fit(X, y)
    out_dir = MODELS_DIR / "clustering"
    txt_path = out_dir / "a7_ndvi_anomaly_champion.txt"
    final_m.booster_.save_model(str(txt_path))

    metrics = {
        "champion": "LightGBM",
        "accuracy": round(float(accuracy_score(y, oof)), 4),
        "f1_macro": round(float(f1_score(y, oof, average="macro", zero_division=0)), 4),
        "rows": int(len(df)),
        "features": features,
        "artifact": str(txt_path.relative_to(ROOT)).replace("\\", "/"),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    (out_dir / "a7_ndvi_anomaly_metadata.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"  [OK] A7 sauvegardé -> {txt_path.name} | F1={metrics['f1_macro']} Acc={metrics['accuracy']}")
    return metrics


def train_a8_anomaly() -> Dict[str, Any]:
    t0 = time.perf_counter()
    print("\n=== [A8] Entraînement Anomaly Intelligence (IsoForest + OCSVM + AutoEncoder) ===")
    df = pd.read_parquet(CURATED_DIR / "train.parquet", engine="fastparquet")
    anomaly_features = [
        "t_min_c", "t_max_c", "t_mean_c", "rh_mean_pct", "wind_2m_ms",
        "solar_rad_mj_m2", "pressure_hpa", "rain_mm", "rain_chirps_mm", "et0_pm_mm",
        "soil_wetness_root_pct",
    ]
    df_clean = df[anomaly_features].dropna()
    # Échantillon représentatif stratifié de 40 000 lignes pour entraînement rapide et reproductible
    sample_df = df_clean.sample(n=min(40000, len(df_clean)), random_state=42)
    X = sample_df.to_numpy(dtype=np.float64)

    out_dir = MODELS_DIR / "anomaly"
    out_dir.mkdir(parents=True, exist_ok=True)

    iso_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("iso", IsolationForest(n_estimators=200, contamination=0.05, random_state=42, n_jobs=2)),
    ])
    iso_pipe.fit(X)
    with (out_dir / "isolation_forest_champion.pkl").open("wb") as fh:
        pickle.dump(iso_pipe, fh)

    ocsvm_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("ocsvm", OneClassSVM(kernel="rbf", nu=0.05, gamma="scale")),
    ])
    ocsvm_pipe.fit(X[:15000])
    with (out_dir / "ocsvm_champion.pkl").open("wb") as fh:
        pickle.dump(ocsvm_pipe, fh)

    # AutoEncoder MLP dans l'espace brut (compatible avec AnomalyService: mean((vec - ae.predict(vec))**2))
    ae_model = Pipeline([
        ("scaler", StandardScaler()),
        ("mlp", MLPRegressor(hidden_layer_sizes=(8, 4, 8), max_iter=150, random_state=42, early_stopping=True)),
    ])
    # Entraîné à reconstruire X en sortie brute
    ae_model.fit(X, X)
    with (out_dir / "autoencoder_champion.pkl").open("wb") as fh:
        pickle.dump(ae_model, fh)

    recon_mse = float(np.mean((X - ae_model.predict(X)) ** 2))
    iso_scores = iso_pipe.decision_function(X)
    metrics = {
        "champion": "IsolationForest + OneClassSVM + AutoEncoder",
        "features": anomaly_features,
        "train_samples": int(len(X)),
        "iso_anomaly_rate_pct": round(100.0 * float((iso_scores < -0.15).mean()), 2),
        "ae_mean_reconstruction_mse": round(recon_mse, 4),
        "artifacts": [
            "models/anomaly/isolation_forest_champion.pkl",
            "models/anomaly/ocsvm_champion.pkl",
            "models/anomaly/autoencoder_champion.pkl",
        ],
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    (out_dir / "a8_anomaly_metadata.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"  [OK] A8 sauvegardé (IsoForest + OCSVM + AutoEncoder) en {metrics['elapsed_s']}s")
    return metrics


def main() -> int:
    report = {
        "A2_ET0_Forecast": train_a2_et0(),
        "A4_Rain_Intelligence": train_a4_rain(),
        "A6_Crop_Calendar": train_a6_crop_calendar(),
        "A7_NDVI_Anomaly": train_a7_ndvi_anomaly(),
        "A8_Anomaly_Intelligence": train_a8_anomaly(),
    }
    out = ROOT / "manifests" / "local_training_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n=== RECONSTRUCTION MODÈLES CLASSE A TERMINÉE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
