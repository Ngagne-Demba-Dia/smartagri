"""Entraînement d'une expérience : variables, validation croisée sans fuite, optimisation, ensembles,
artefacts reproductibles et fichier de soumission validé.

Usage :
    python -m agriml.train --config configs/yield_regression.yaml [--no-tuning] [--output-dir DIR]

Artefacts (dans `<output_dir>/<name>/`) : oof.parquet, test_pred.parquet, cv_scores.json, ensemble.json,
adversarial.json, config_resolved.yaml, seeds.json, feature_columns.json, label_mapping.json,
models/<modèle>/seed<s>_fold<k>.joblib, meta_model.joblib (stacking), submission.csv.
"""

from __future__ import annotations

import argparse
import logging
import platform
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from agriml import __version__
from agriml._optional import install_hint
from agriml.adversarial import adversarial_validation
from agriml.config import ExperimentConfig, ModelConfig, dump_config, load_config
from agriml.cv import Split, assert_no_leakage, leakage_context, make_splits
from agriml.ensemble import EnsembleResult, run_all_ensembles
from agriml.features.pipeline import FoldTransformer, build_stateless_features, select_feature_columns
from agriml.io import read_table, write_json, write_table
from agriml.logs import setup_logging
from agriml.metrics import Metric, get_metric, inverse_log1p, log1p_target, optimize_f1_threshold
from agriml.models.factory import (
    BACKENDS,
    NATIVE_CATEGORICAL_KINDS,
    ONE_HOT_KINDS,
    backend_available,
    build_model,
)
from agriml.submission import align_to_sample, assert_valid_submission, build_submission, write_submission
from agriml.tracking import get_tracker
from agriml.tuning import tune

logger = logging.getLogger("agriml.train")
ADVERSARIAL_MAX_ROWS = 20_000
TEST_MARKER = "__is_test__"


@dataclass(frozen=True)
class PreparedData:
    train: pd.DataFrame
    test: pd.DataFrame | None
    y: np.ndarray
    y_eval: np.ndarray
    ids_train: np.ndarray
    ids_test: np.ndarray | None
    numeric: list[str]
    categorical: list[str]
    n_classes: int | None
    classes: list | None


@dataclass
class ModelRun:
    name: str
    oof: np.ndarray
    test: np.ndarray | None
    cv_score: float
    fold_scores: list[float]
    params: dict[str, Any]
    best_iterations: list[int] = field(default_factory=list)
    importance: pd.Series | None = None


# --------------------------------------------------------------------------- données


def load_datasets(cfg: ExperimentConfig) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
    train = read_table(cfg.resolve(cfg.data.train))
    test = read_table(cfg.resolve(cfg.data.test)) if cfg.data.test else None
    sample = read_table(cfg.resolve(cfg.data.sample_submission)) if cfg.data.sample_submission else None
    return train, test, sample


def encode_target(y_raw: pd.Series, cfg: ExperimentConfig) -> tuple[np.ndarray, np.ndarray, list | None]:
    """Cible → (cible d'apprentissage, cible d'évaluation, classes d'origine)."""
    if cfg.task == "regression":
        y_eval = y_raw.to_numpy(dtype=float)
        y_model = log1p_target(y_eval) if cfg.target_transform == "log1p" else y_eval
        return y_model, y_eval, None
    classes = sorted(pd.unique(y_raw).tolist())
    codes = y_raw.map({c: i for i, c in enumerate(classes)}).to_numpy(dtype=int)
    if cfg.task == "binary" and len(classes) != 2:
        raise ValueError(f"Tâche binaire mais {len(classes)} classes : {classes}")
    return codes, codes, classes


def decode_prediction(pred: np.ndarray, cfg: ExperimentConfig) -> np.ndarray:
    return inverse_log1p(pred) if cfg.target_transform == "log1p" else pred


def prepare_data(cfg: ExperimentConfig) -> PreparedData:
    train_raw, test_raw, _ = load_datasets(cfg)
    target = cfg.columns.target
    n_missing = int(train_raw[target].isna().sum())
    if n_missing:
        logger.warning("%d lignes sans cible retirées du train.", n_missing)
        train_raw = train_raw[train_raw[target].notna()]
    frames = [train_raw.assign(**{TEST_MARKER: False})]
    if test_raw is not None:
        frames.append(test_raw.assign(**{TEST_MARKER: True}))
    full = build_stateless_features(pd.concat(frames, ignore_index=True), cfg)
    is_test = full[TEST_MARKER].to_numpy(dtype=bool)
    train = full[~is_test].drop(columns=TEST_MARKER).reset_index(drop=True)
    test = full[is_test].drop(columns=[TEST_MARKER, target], errors="ignore").reset_index(drop=True)
    y, y_eval, classes = encode_target(train[target], cfg)
    numeric, categorical = select_feature_columns(train.drop(columns=TEST_MARKER, errors="ignore"), cfg)
    return PreparedData(
        train=train, test=test if test_raw is not None else None, y=y, y_eval=y_eval,
        ids_train=train[cfg.columns.id].to_numpy(),
        ids_test=test[cfg.columns.id].to_numpy() if test_raw is not None else None,
        numeric=numeric, categorical=categorical,
        n_classes=len(classes) if classes else None, classes=classes,
    )


def build_splits(data: PreparedData, cfg: ExperimentConfig, seed: int) -> list[Split]:
    splits = make_splits(data.train, data.y_eval, cfg, seed)
    assert_no_leakage(splits, len(data.train), **leakage_context(data.train, cfg))
    return splits


# --------------------------------------------------------------------------- modèles


def _model_categoricals(kind: str, ft: FoldTransformer) -> list[str]:
    if kind in ONE_HOT_KINDS:
        return ft.coded_categorical
    if kind in NATIVE_CATEGORICAL_KINDS:
        return ft.native_categorical
    return []


def fit_fold(model_cfg: ModelConfig, cfg: ExperimentConfig, data: PreparedData, tr: np.ndarray, va: np.ndarray,
             seed: int, params: dict[str, Any], predict_test: bool = True):
    """Ajuste transformation + modèle sur un pli ; renvoie (préd. validation, préd. test, paquet)."""
    ft = FoldTransformer.from_config(cfg, data.numeric, data.categorical, data.n_classes, seed)
    X_tr = ft.fit_transform(data.train.iloc[tr], data.y[tr])
    X_va = ft.transform(data.train.iloc[va])
    model = build_model(model_cfg.kind, cfg.task, params, seed, _model_categoricals(model_cfg.kind, ft),
                        model_cfg.early_stopping, data.n_classes)
    model.fit(X_tr, data.y[tr], X_va, data.y[va])
    test_pred = model.predict(ft.transform(data.test)) if (predict_test and data.test is not None) else None
    return model.predict(X_va), test_pred, {"transformer": ft, "model": model}


def _empty_pred(n: int, data: PreparedData, task: str) -> np.ndarray:
    return np.zeros((n, data.n_classes)) if task == "multiclass" else np.zeros(n)


def run_model_cv(model_cfg: ModelConfig, cfg: ExperimentConfig, data: PreparedData,
                 splits_by_seed: Sequence[tuple[int, list[Split]]], params: dict[str, Any],
                 report: Callable[[int, float], None] | None = None, predict_test: bool = True,
                 save_dir: Path | None = None) -> ModelRun:
    """Validation croisée multi-graines : OOF moyenné par ligne, test moyenné sur plis × graines."""
    metric = get_metric(cfg.metric)
    n = len(data.train)
    oof_sum, oof_count = _empty_pred(n, data, cfg.task), np.zeros(n)
    test_sum, n_test = None, 0
    fold_scores, iterations, importances = [], [], []
    for s_idx, (seed, splits) in enumerate(splits_by_seed):
        for k, (tr, va) in enumerate(splits):
            val, te, bundle = fit_fold(model_cfg, cfg, data, tr, va, seed, params, predict_test)
            oof_sum[va] += val
            oof_count[va] += 1
            fold_scores.append(metric(data.y_eval[va], decode_prediction(val, cfg)))
            if report is not None:
                report(s_idx * len(splits) + k, float(np.mean(fold_scores)))
            if te is not None:
                test_sum = te if test_sum is None else test_sum + te
                n_test += 1
            if (it := bundle["model"].best_iteration()) is not None:
                iterations.append(it)
            if (imp := bundle["model"].feature_importance()) is not None:
                importances.append(imp)
            if save_dir is not None:
                joblib.dump(bundle, save_dir / f"seed{seed}_fold{k}.joblib")
    return _finish_run(model_cfg.name, cfg, data, metric, oof_sum, oof_count, test_sum, n_test,
                       fold_scores, params, iterations, importances)


def _finish_run(name, cfg, data, metric, oof_sum, oof_count, test_sum, n_test, fold_scores, params,
                iterations, importances) -> ModelRun:
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = oof_count[:, None] if oof_sum.ndim == 2 else oof_count
        oof = np.where(denom > 0, oof_sum / np.maximum(denom, 1), np.nan)
    oof = decode_prediction(oof, cfg)
    mask = oof_count > 0
    test = decode_prediction(test_sum / n_test, cfg) if n_test else None
    importance = pd.concat(importances, axis=1).mean(axis=1).sort_values(ascending=False) if importances else None
    return ModelRun(name, oof, test, metric(data.y_eval[mask], oof[mask]), fold_scores, dict(params),
                    iterations, importance)


def tune_model(model_cfg: ModelConfig, cfg: ExperimentConfig, data: PreparedData,
               splits_by_seed: Sequence[tuple[int, list[Split]]]) -> tuple[dict[str, Any], dict]:
    """Optimise sur la première graine uniquement (budget), renvoie (paramètres, résumé)."""
    base = dict(model_cfg.params)

    def objective(params, report):
        run = run_model_cv(model_cfg, cfg, data, splits_by_seed[:1], {**base, **params}, report, False)
        return run.cv_score

    result = tune(objective, model_cfg.search_space, cfg.tuning.n_trials, cfg.greater_is_better,
                  seed=cfg.seeds[0], timeout_s=cfg.tuning.timeout_s)
    summary = {"backend": result.backend, "best_score": result.best_score, "best_params": result.best_params,
               "n_trials": result.n_trials, "n_pruned": result.n_pruned, "history": list(result.history)}
    logger.info("Optimisation %s (%s) : %d essais, %d élagués, meilleur %s = %.5f", model_cfg.name,
                result.backend, result.n_trials, result.n_pruned, cfg.metric, result.best_score)
    return {**base, **result.best_params}, summary


# --------------------------------------------------------------------------- expérience


def _baseline_score(data: PreparedData, cfg: ExperimentConfig, splits: list[Split], metric: Metric) -> float:
    """Score d'un prédicteur constant appris pli par pli (moyenne / fréquences) : borne de bon sens."""
    oof = _empty_pred(len(data.train), data, cfg.task)
    for tr, va in splits:
        if cfg.task == "multiclass":
            oof[va] = np.bincount(data.y[tr], minlength=data.n_classes) / len(tr)
        else:
            oof[va] = data.y_eval[tr].mean()
    seen = np.unique(np.concatenate([va for _, va in splits]))
    return metric(data.y_eval[seen], oof[seen])


def _train_models(cfg, data, splits_by_seed, run_dir, use_tuning) -> tuple[dict[str, ModelRun], dict]:
    runs, tuning_summaries = {}, {}
    for model_cfg in cfg.enabled_models():
        if not backend_available(model_cfg.kind):
            logger.warning("Modèle %s ignoré : bibliothèque « %s » non installée (%s).", model_cfg.name,
                           BACKENDS[model_cfg.kind], install_hint(BACKENDS[model_cfg.kind]))
            continue
        params = dict(model_cfg.params)
        if use_tuning and model_cfg.name in cfg.tuning.models and model_cfg.search_space:
            params, tuning_summaries[model_cfg.name] = tune_model(model_cfg, cfg, data, splits_by_seed)
        save_dir = run_dir / "models" / model_cfg.name
        save_dir.mkdir(parents=True, exist_ok=True)
        run = run_model_cv(model_cfg, cfg, data, splits_by_seed, params, save_dir=save_dir)
        logger.info("%-10s %s CV = %.5f (± %.5f sur %d plis)", model_cfg.name, cfg.metric, run.cv_score,
                    float(np.std(run.fold_scores)), len(run.fold_scores))
        runs[model_cfg.name] = run
    if not runs:
        raise RuntimeError("Aucun modèle entraîné (bibliothèques manquantes ?).")
    return runs, tuning_summaries


def _select_final(runs: dict[str, ModelRun], ensemble: EnsembleResult | None, metric: Metric) -> dict[str, Any]:
    """Choix final par score OOF : ensemble configuré s'il bat le meilleur modèle seul."""
    best = max(runs.values(), key=lambda r: r.cv_score if metric.greater_is_better else -r.cv_score)
    if ensemble is not None and ensemble.test is not None and metric.is_better(ensemble.score, best.cv_score):
        return {"type": "ensemble", "name": ensemble.method, "cv": ensemble.score,
                "oof": ensemble.oof, "test": ensemble.test}
    return {"type": "model", "name": best.name, "cv": best.cv_score, "oof": best.oof, "test": best.test}


def _submission_values(final_test: np.ndarray, final_oof: np.ndarray, data: PreparedData, cfg: ExperimentConfig,
                       metric: Metric) -> tuple[np.ndarray, float | None]:
    """Convertit les prédictions finales au format de la métrique (étiquettes si métrique d'étiquettes)."""
    if metric.prediction_type != "label":
        return final_test, None
    if cfg.task == "binary":
        mask = ~np.isnan(final_oof)
        thr, _ = optimize_f1_threshold(data.y_eval[mask], final_oof[mask])
        codes = (final_test >= thr).astype(int)
    else:
        thr, codes = None, final_test.argmax(axis=1)
    return np.asarray(data.classes, dtype=object)[codes], thr


def _pred_columns(cfg: ExperimentConfig, data: PreparedData, sample: pd.DataFrame | None, metric: Metric) -> list:
    if cfg.submission.pred_columns:
        return list(cfg.submission.pred_columns)
    if sample is not None:
        return [c for c in sample.columns if c != cfg.columns.id]
    if cfg.task == "multiclass" and metric.prediction_type != "label":
        return [str(c) for c in data.classes]
    return [cfg.columns.target]


def _write_submission(final, data, cfg, sample, metric, run_dir) -> tuple[Path, float | None]:
    values, threshold = _submission_values(final["test"], final["oof"], data, cfg, metric)
    pred_cols = _pred_columns(cfg, data, sample, metric)
    if metric.prediction_type == "label":
        sub = pd.DataFrame({cfg.columns.id: data.ids_test, pred_cols[0]: values})
    else:
        sub = build_submission(data.ids_test, values, cfg.columns.id, pred_cols,
                               cfg.submission.clip_min, cfg.submission.clip_max)
    if sample is not None:
        sub = align_to_sample(sub, sample, cfg.columns.id)
        task = cfg.task if metric.prediction_type == "proba" else None
        if metric.prediction_type != "label":
            assert_valid_submission(sub, sample, cfg.columns.id, task)
    return write_submission(sub, run_dir / cfg.submission.file_name), threshold


def _holdout_scores(cfg, data, runs, final, metric) -> dict[str, float]:
    """Score « privé simulé » si des étiquettes de test figées existent (jamais utilisées pour choisir)."""
    if not cfg.data.test_labels or data.test is None:
        return {}
    labels = read_table(cfg.resolve(cfg.data.test_labels))
    order = pd.Series(range(len(data.ids_test)), index=pd.Index(data.ids_test).astype(str))
    labels = labels[labels[cfg.columns.id].astype(str).isin(order.index)]
    idx = order.loc[labels[cfg.columns.id].astype(str)].to_numpy()
    y_raw = labels[cfg.columns.target]
    y_true = y_raw.to_numpy(float) if cfg.task == "regression" else y_raw.map(
        {c: i for i, c in enumerate(data.classes)}).to_numpy()
    scores = {name: metric(y_true, r.test[idx]) for name, r in runs.items() if r.test is not None}
    scores["final"] = metric(y_true, final["test"][idx])
    return scores


# --------------------------------------------------------------------------- artefacts


def _pred_frame(ids: np.ndarray, preds: dict[str, np.ndarray], id_column: str) -> pd.DataFrame:
    cols: dict[str, Any] = {id_column: ids}
    for name, p in preds.items():
        if p.ndim == 2:
            cols.update({f"{name}_c{k}": p[:, k] for k in range(p.shape[1])})
        else:
            cols[name] = p
    return pd.DataFrame(cols)


def environment_info(seeds: Sequence[int]) -> dict[str, Any]:
    import sklearn
    import xgboost

    return {"seeds": list(seeds), "agriml": __version__, "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": {"numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__,
                         "xgboost": xgboost.__version__}}


def _adversarial(data: PreparedData, cfg: ExperimentConfig, run_dir: Path) -> dict | None:
    if data.test is None or not data.numeric:
        return None
    train = data.train.sample(min(len(data.train), ADVERSARIAL_MAX_ROWS), random_state=cfg.seeds[0])
    test = data.test.sample(min(len(data.test), ADVERSARIAL_MAX_ROWS), random_state=cfg.seeds[0])
    cols = [c for c in data.numeric if c in data.test]
    report = adversarial_validation(train, test, cols, seed=cfg.seeds[0])
    logger.info(report.summary())
    write_json(report.to_dict(), run_dir / "adversarial.json")
    return report.to_dict()


def _save_artifacts(cfg, data, runs, ensemble, ens_report, final, threshold, run_dir) -> None:
    oofs = {name: r.oof for name, r in runs.items()}
    if ensemble is not None:
        oofs[f"ens_{ensemble.method}"] = ensemble.oof
    oof_df = _pred_frame(data.ids_train, oofs, cfg.columns.id).assign(**{cfg.columns.target: data.y_eval})
    write_table(oof_df, run_dir / "oof.parquet")
    if data.test is not None:
        tests = {name: r.test for name, r in runs.items()} | {"final": final["test"]}
        write_table(_pred_frame(data.ids_test, tests, cfg.columns.id), run_dir / "test_pred.parquet")
    write_json({"type": final["type"], "name": final["name"], "cv": final["cv"], "method": cfg.ensemble.method,
                "report": ens_report, "members": list(ensemble.members) if ensemble else [],
                "weights": ensemble.weights if ensemble else {}, "threshold": threshold},
               run_dir / "ensemble.json")
    if ensemble is not None and ensemble.meta_model is not None:
        joblib.dump(ensemble.meta_model, run_dir / "meta_model.joblib")
    write_json({"numeric": data.numeric, "categorical": data.categorical}, run_dir / "feature_columns.json")
    write_json({"classes": data.classes, "target_transform": cfg.target_transform}, run_dir / "label_mapping.json")
    write_json(environment_info(cfg.seeds), run_dir / "seeds.json")
    importance = {n: r.importance.head(30).to_dict() for n, r in runs.items() if r.importance is not None}
    write_json(importance, run_dir / "feature_importance.json")


def _scores_payload(cfg, metric, runs, baseline, ens_report, final, holdout, tuning) -> dict[str, Any]:
    return {
        "experiment": cfg.name, "metric": metric.name, "greater_is_better": metric.greater_is_better,
        "cv_scheme": cfg.cv.scheme, "n_splits": cfg.cv.n_splits, "seeds": list(cfg.seeds),
        "baseline_constant": baseline,
        "models": {n: {"cv": r.cv_score, "fold_mean": float(np.mean(r.fold_scores)),
                       "fold_std": float(np.std(r.fold_scores)), "params": r.params,
                       "best_iterations": r.best_iterations} for n, r in runs.items()},
        "ensembles": ens_report,
        "final": {"type": final["type"], "name": final["name"], "cv": final["cv"]},
        "holdout": holdout, "tuning": tuning,
    }


def run_experiment(cfg: ExperimentConfig, use_tuning: bool = True) -> dict[str, Any]:
    """Exécute l'expérience complète et renvoie le contenu de cv_scores.json."""
    run_dir = cfg.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    dump_config(cfg, run_dir / "config_resolved.yaml")
    metric = get_metric(cfg.metric)
    data = prepare_data(cfg)
    logger.info("Train %d lignes, test %s, %d variables numériques, %d catégorielles", len(data.train),
                len(data.test) if data.test is not None else 0, len(data.numeric), len(data.categorical))
    splits_by_seed = [(seed, build_splits(data, cfg, seed)) for seed in cfg.seeds]
    adversarial = _adversarial(data, cfg, run_dir)
    tracker = get_tracker(cfg.name, cfg.resolve(cfg.output_dir))
    runs, tuning = _train_models(cfg, data, splits_by_seed, run_dir, use_tuning and cfg.tuning.enabled)
    oofs = {n: r.oof for n, r in runs.items()}
    tests = {n: r.test for n, r in runs.items() if r.test is not None}
    ensemble, ens_report = run_all_ensembles(oofs, tests if len(tests) == len(oofs) else {}, data.y_eval, metric,
                                             cfg.task, splits_by_seed[0][1], cfg.ensemble.method,
                                             cfg.ensemble.n_iter, cfg.seeds[0])
    for method, score in ens_report.items():
        logger.info("ensemble %-14s %s OOF = %.5f", method, metric.name, score)
    final = _select_final(runs, ensemble, metric)
    logger.info("Retenu : %s « %s » (%s CV = %.5f)", final["type"], final["name"], metric.name, final["cv"])
    threshold = None
    if data.test is not None and final["test"] is not None:
        sample = read_table(cfg.resolve(cfg.data.sample_submission)) if cfg.data.sample_submission else None
        path, threshold = _write_submission(final, data, cfg, sample, metric, run_dir)
        logger.info("Soumission validée : %s", path)
    holdout = _holdout_scores(cfg, data, runs, final, metric)
    if holdout:
        logger.info("Holdout figé (rapport uniquement) : %s", {k: round(v, 5) for k, v in holdout.items()})
    _save_artifacts(cfg, data, runs, ensemble, ens_report, final, threshold, run_dir)
    baseline = _baseline_score(data, cfg, splits_by_seed[0][1], metric)
    payload = _scores_payload(cfg, metric, runs, baseline, ens_report, final, holdout, tuning)
    payload["adversarial_auc"] = adversarial["auc"] if adversarial else None
    write_json(payload, run_dir / "cv_scores.json")
    tracker.log_params({"config": cfg.name, "cv_scheme": cfg.cv.scheme, "final": final["name"]})
    tracker.log_metrics({f"cv_{n}": r.cv_score for n, r in runs.items()} | {"cv_final": final["cv"]})
    tracker.end()
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Entraînement agriml (validation croisée + ensembles).")
    parser.add_argument("--config", required=True, help="Chemin du YAML d'expérience.")
    parser.add_argument("--output-dir", help="Remplace output_dir de la configuration.")
    parser.add_argument("--no-tuning", action="store_true", help="Désactive l'optimisation d'hyperparamètres.")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    cfg = load_config(args.config)
    if args.output_dir:
        cfg = replace(cfg, output_dir=str(Path(args.output_dir).resolve()))
    payload = run_experiment(cfg, use_tuning=not args.no_tuning)
    print(f"{cfg.name} : {payload['metric']} final = {payload['final']['cv']:.5f} ({payload['final']['name']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
