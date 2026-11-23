"""Entraînement Classe A enrichi sur les nouveaux datasets CSV Sénégal (A3 Yield, A5 Price, A9 Clustering)."""

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

import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostRegressor


def kfold_indices(n: int, n_splits: int = 5, seed: int = 42):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    folds = np.array_split(idx, n_splits)
    for i in range(n_splits):
        va = folds[i]
        tr = np.concatenate([folds[j] for j in range(n_splits) if j != i])
        yield tr, va


def calc_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    return {"r2": round(r2, 4), "rmse": round(rmse, 4), "mae": round(mae, 4)}


def kmeans_np(X: np.ndarray, k: int, n_init: int = 30, max_iter: int = 300, seed: int = 42):
    rng = np.random.default_rng(seed)
    best_inertia = np.inf
    best_labels = None
    best_centers = None
    for _ in range(n_init):
        centers = X[rng.choice(len(X), size=k, replace=False)].copy()
        for _ in range(max_iter):
            dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
            labels = np.argmin(dists, axis=1)
            new_centers = np.array([
                X[labels == j].mean(axis=0) if np.any(labels == j) else centers[j]
                for j in range(k)
            ])
            if np.allclose(centers, new_centers):
                break
            centers = new_centers
        inertia = float(np.sum((X - centers[labels]) ** 2))
        if inertia < best_inertia:
            best_inertia, best_labels, best_centers = inertia, labels, centers
    return best_labels, best_centers


def silhouette_np(X: np.ndarray, labels: np.ndarray) -> float:
    dists = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    s_vals = []
    for i in range(len(X)):
        same = labels == labels[i]
        a = float(np.mean(dists[i, same & (np.arange(len(X)) != i)])) if np.sum(same) > 1 else 0.0
        b = min(
            float(np.mean(dists[i, labels == c]))
            for c in np.unique(labels) if c != labels[i]
        )
        s_vals.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(s_vals))

REAL_DIR = ROOT / "datasets" / "real"


def train_a3_yield() -> Dict[str, Any]:
    t0 = time.perf_counter()
    df = pd.read_csv(REAL_DIR / "harveststat_senegal_v1.2.csv")
    df = df.dropna(subset=["yield", "area", "harvest_year", "product", "admin_1"]).copy()
    df = df[(df["yield"] > 0) & (df["area"] > 0)].copy()

    # Encodage déterministe
    crops = sorted(df["product"].unique().tolist())
    regions = sorted(df["admin_1"].unique().tolist())
    depts = sorted(df["admin_2"].fillna("UNKNOWN").unique().tolist())
    seasons = sorted(df["season_name"].fillna("Main").unique().tolist())

    crop_map = {c: i for i, c in enumerate(crops)}
    reg_map = {r: i for i, r in enumerate(regions)}
    dept_map = {d: i for i, d in enumerate(depts)}
    season_map = {s: i for i, s in enumerate(seasons)}

    df["crop_enc"] = df["product"].map(crop_map)
    df["admin1_enc"] = df["admin_1"].map(reg_map)
    df["admin2_enc"] = df["admin_2"].fillna("UNKNOWN").map(dept_map)
    df["season_enc"] = df["season_name"].fillna("Main").map(season_map)
    df["year"] = df["harvest_year"].astype(int)
    df["year_norm"] = (df["year"] - df["year"].min()) / max(1, df["year"].max() - df["year"].min())
    df["decade"] = (df["year"] // 10) * 10
    df["log_area_ha"] = np.log1p(df["area"].astype(float))

    features = ["year", "year_norm", "decade", "log_area_ha", "crop_enc", "admin1_enc", "admin2_enc", "season_enc"]
    X = df[features].to_numpy(dtype=np.float64)
    y = df["yield"].to_numpy(dtype=np.float64)

    results = {}

    for name, builder in [
        ("CatBoost", lambda: CatBoostRegressor(iterations=1200, learning_rate=0.05, depth=6, l2_leaf_reg=5.0, random_seed=42, verbose=0)),
        ("LightGBM", lambda: lgb.LGBMRegressor(n_estimators=1200, learning_rate=0.05, max_depth=6, num_leaves=63, random_state=42, verbose=-1)),
        ("XGBoost", lambda: xgb.XGBRegressor(n_estimators=1200, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=4)),
    ]:
        oof = np.zeros_like(y)
        for tr, va in kfold_indices(len(X), n_splits=5, seed=42):
            m = builder()
            m.fit(X[tr], y[tr])
            oof[va] = m.predict(X[va])
        results[name] = calc_metrics(y, oof)

    best_name = max(results, key=lambda k: results[k]["r2"])
    if best_name == "CatBoost":
        final_model = CatBoostRegressor(iterations=1200, learning_rate=0.05, depth=6, l2_leaf_reg=5.0, random_seed=42, verbose=0)
    elif best_name == "LightGBM":
        final_model = lgb.LGBMRegressor(n_estimators=1200, learning_rate=0.05, max_depth=6, num_leaves=63, random_state=42, verbose=-1)
    else:
        final_model = xgb.XGBRegressor(n_estimators=1200, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=4)
    final_model.fit(X, y)

    out_dir = ROOT / "models" / "yield"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "a3_yield_champion.pkl").open("wb") as fh:
        pickle.dump(final_model, fh)
    (out_dir / "a3_yield_metadata.json").write_text(
        json.dumps({
            "champion": best_name,
            "rows": len(df),
            "features": features,
            "metrics_cv5": results,
            "encoders": {"crop": crop_map, "admin1": reg_map, "admin2": dept_map, "season": season_map},
            "train_seconds": round(time.perf_counter() - t0, 2),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"champion": best_name, "rows": len(df), "metrics": results[best_name], "all": results}


def train_a5_price() -> Dict[str, Any]:
    t0 = time.perf_counter()
    df = pd.read_csv(REAL_DIR / "wfp_food_prices_sen.csv")
    df = df.dropna(subset=["date", "price", "commodity", "market", "admin1", "latitude", "longitude"]).copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[(df["price"] > 0) & (df["price"] < 50000)].copy()

    dt = pd.to_datetime(df["date"], errors="coerce")
    df = df[dt.notna()].copy()
    dt = dt[dt.notna()]
    df["year"] = dt.dt.year
    df["month"] = dt.dt.month
    doy = dt.dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)

    comm_map = {c: i for i, c in enumerate(sorted(df["commodity"].unique()))}
    mkt_map = {m: i for i, m in enumerate(sorted(df["market"].unique()))}
    reg_map = {r: i for i, r in enumerate(sorted(df["admin1"].unique()))}
    cat_map = {c: i for i, c in enumerate(sorted(df["category"].fillna("other").unique()))}

    df["crop_enc"] = df["commodity"].map(comm_map)
    df["market_enc"] = df["market"].map(mkt_map)
    df["region_enc"] = df["admin1"].map(reg_map)
    df["category_enc"] = df["category"].fillna("other").map(cat_map)

    features = ["year", "month", "doy_sin", "doy_cos", "crop_enc", "market_enc", "region_enc", "category_enc", "latitude", "longitude"]
    X = df[features].to_numpy(dtype=np.float64)
    y = df["price"].to_numpy(dtype=np.float64)

    results = {}
    for name, builder in [
        ("XGBoost", lambda: xgb.XGBRegressor(n_estimators=1000, learning_rate=0.05, max_depth=8, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=4)),
        ("LightGBM", lambda: lgb.LGBMRegressor(n_estimators=1000, learning_rate=0.05, max_depth=8, num_leaves=127, random_state=42, verbose=-1)),
        ("CatBoost", lambda: CatBoostRegressor(iterations=1000, learning_rate=0.05, depth=8, random_seed=42, verbose=0)),
    ]:
        oof = np.zeros_like(y)
        for tr, va in kfold_indices(len(X), n_splits=5, seed=42):
            m = builder()
            m.fit(X[tr], y[tr])
            oof[va] = m.predict(X[va])
        results[name] = calc_metrics(y, oof)

    best_name = max(results, key=lambda k: results[k]["r2"])
    if best_name == "XGBoost":
        final_model = xgb.XGBRegressor(n_estimators=1000, learning_rate=0.05, max_depth=8, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=4)
    elif best_name == "LightGBM":
        final_model = lgb.LGBMRegressor(n_estimators=1000, learning_rate=0.05, max_depth=8, num_leaves=127, random_state=42, verbose=-1)
    else:
        final_model = CatBoostRegressor(iterations=1000, learning_rate=0.05, depth=8, random_seed=42, verbose=0)
    final_model.fit(X, y)

    out_dir = ROOT / "models" / "yield"
    with (out_dir / "a5_price_champion.pkl").open("wb") as fh:
        pickle.dump(final_model, fh)
    (out_dir / "a5_price_metadata.json").write_text(
        json.dumps({
            "champion": best_name,
            "rows": len(df),
            "features": features,
            "metrics_cv5": results,
            "encoders": {"commodity": comm_map, "market": mkt_map, "region": reg_map, "category": cat_map},
            "train_seconds": round(time.perf_counter() - t0, 2),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"champion": best_name, "rows": len(df), "metrics": results[best_name], "all": results}


def train_a9_clustering() -> Dict[str, Any]:
    df = pd.read_csv(REAL_DIR / "wfp_food_prices_sen.csv")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0].dropna(subset=["market", "latitude", "longitude", "price"]).copy()

    agg = df.groupby(["market", "admin1"], as_index=False).agg(
        mean_price=("price", "mean"),
        std_price=("price", "std"),
        n_obs=("price", "count"),
        n_commodities=("commodity", "nunique"),
        lat=("latitude", "first"),
        lon=("longitude", "first"),
    ).fillna(0.0)

    feat_cols = ["mean_price", "std_price", "n_obs", "n_commodities", "lat", "lon"]
    raw_X = agg[feat_cols].to_numpy(dtype=np.float64)
    mean = raw_X.mean(axis=0)
    std = np.where(raw_X.std(axis=0) > 0, raw_X.std(axis=0), 1.0)
    X = (raw_X - mean) / std

    scores = {}
    best_k, best_sil, best_labels, best_centers = 2, -1.0, None, None
    for k in range(2, 9):
        labels, centers = kmeans_np(X, k=k, n_init=30, max_iter=300, seed=42)
        sil = silhouette_np(X, labels)
        scores[k] = round(sil, 4)
        if sil > best_sil:
            best_sil, best_k, best_labels, best_centers = sil, k, labels, centers

    agg["cluster"] = best_labels
    out_dir = ROOT / "models" / "clustering"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "a9_market_kmeans_champion.pkl").open("wb") as fh:
        pickle.dump({"centers": best_centers, "mean": mean, "std": std, "features": feat_cols}, fh)
    agg.to_csv(out_dir / "a9_market_clusters_enriched.csv", index=False)
    (out_dir / "a9_clustering_metadata.json").write_text(
        json.dumps({"best_k": best_k, "silhouette": round(best_sil, 4), "n_markets": len(agg), "scores_by_k": scores}, indent=2),
        encoding="utf-8",
    )
    return {"best_k": best_k, "silhouette": round(best_sil, 4), "n_markets": len(agg), "scores_by_k": scores}


if __name__ == "__main__":
    summary = {
        "A3_Yield_Enriched": train_a3_yield(),
        "A5_Price_Enriched": train_a5_price(),
        "A9_Market_Clustering_Enriched": train_a9_clustering(),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
