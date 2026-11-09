"""Analyse des résultats hors-pli : scores par tranche (région, culture…), résidus, calibration, seuil F1.

Usage : python -m agriml.evaluate --run artifacts/disease_risk_binary
Écrit `evaluation.json` : c'est la base du plan d'amélioration (où le modèle se trompe-t-il ?).
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from agriml.io import read_json, read_table, write_json
from agriml.logs import setup_logging
from agriml.metrics import Metric, get_metric, optimize_f1_threshold
from agriml.predict import load_run_config

logger = logging.getLogger("agriml.evaluate")
MIN_SLICE_ROWS = 30
N_CALIBRATION_BINS = 10


def final_oof_column(ensemble: dict[str, Any]) -> str:
    return ensemble["name"] if ensemble["type"] == "model" else f"ens_{ensemble['name']}"


def slice_scores(df: pd.DataFrame, y: np.ndarray, pred: np.ndarray, metric: Metric,
                 columns: Sequence[str]) -> dict[str, dict[str, float]]:
    """Score par modalité (tranches d'au moins MIN_SLICE_ROWS lignes et, en classement, deux classes)."""
    out: dict[str, dict[str, float]] = {}
    for col in columns:
        scores = {}
        for value, idx in df.groupby(col, sort=True).indices.items():
            if len(idx) < MIN_SLICE_ROWS or (metric.name == "auc" and len(np.unique(y[idx])) < 2):
                continue
            scores[str(value)] = round(metric(y[idx], pred[idx]), 6)
        out[col] = scores
    return out


def residual_summary(y: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    resid = y - pred
    deciles = pd.qcut(pred, 10, labels=False, duplicates="drop")
    by_decile = pd.DataFrame({"d": deciles, "r": resid}).groupby("d")["r"].agg(["mean", "std", "count"])
    return {"bias": float(resid.mean()), "mae": float(np.abs(resid).mean()),
            "p95_abs_error": float(np.quantile(np.abs(resid), 0.95)),
            "by_prediction_decile": by_decile.round(4).reset_index().to_dict(orient="records")}


def calibration_summary(y: np.ndarray, proba: np.ndarray, n_bins: int = N_CALIBRATION_BINS) -> dict[str, Any]:
    """Courbe de fiabilité, Brier et erreur de calibration attendue (ECE)."""
    bins = np.minimum((proba * n_bins).astype(int), n_bins - 1)
    rows, ece = [], 0.0
    for b in range(n_bins):
        m = bins == b
        if not m.any():
            continue
        gap = abs(proba[m].mean() - y[m].mean())
        ece += gap * m.mean()
        rows.append({"bin": b, "mean_pred": float(proba[m].mean()), "observed": float(y[m].mean()), "n": int(m.sum())})
    thr, f1 = optimize_f1_threshold(y, proba)
    return {"brier": float(np.mean((proba - y) ** 2)), "ece": float(ece), "reliability": rows,
            "best_f1_threshold": thr, "best_f1": f1, "prevalence": float(y.mean())}


def evaluate_run(run_dir: str | Path) -> dict[str, Any]:
    cfg = load_run_config(run_dir)
    ensemble = read_json(Path(run_dir) / "ensemble.json")
    metric = get_metric(cfg.metric)
    oof = read_table(Path(run_dir) / "oof.parquet")
    train = read_table(cfg.resolve(cfg.data.train))
    df = oof.merge(train.drop(columns=[cfg.columns.target]), on=cfg.columns.id, how="left")
    col = final_oof_column(ensemble)
    pred_cols = [c for c in df.columns if c == col or c.startswith(f"{col}_c")]
    mask = df[pred_cols].notna().all(axis=1).to_numpy()
    df = df[mask].reset_index(drop=True)
    y = df[cfg.columns.target].to_numpy()
    pred = df[pred_cols].to_numpy(dtype=float)
    pred = pred[:, 0] if pred.shape[1] == 1 else pred
    slices = [c for c in (*cfg.columns.categorical, cfg.columns.time) if c and c in df]
    report: dict[str, Any] = {"final": col, "metric": metric.name, "score": metric(y, pred), "n_rows": int(len(y)),
                              "slices": slice_scores(df, y, pred, metric, slices)}
    if cfg.task == "regression":
        report["residuals"] = residual_summary(y.astype(float), pred)
    elif cfg.task == "binary":
        report["calibration"] = calibration_summary(y.astype(int), pred)
    report["cv_scores"] = read_json(Path(run_dir) / "cv_scores.json").get("models")
    write_json(report, Path(run_dir) / "evaluation.json")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyse des prédictions hors-pli d'une expérience.")
    parser.add_argument("--run", required=True)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    report = evaluate_run(args.run)
    logger.info("%s OOF (%s) = %.5f sur %d lignes", report["metric"], report["final"], report["score"], report["n_rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
