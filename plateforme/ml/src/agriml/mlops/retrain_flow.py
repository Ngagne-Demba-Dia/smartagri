"""Flux de réentraînement : dérive → réentraînement → évaluation hold-out → porte → promotion → notification.

Chaque étape est une fonction pure ou presque, testable sans Airflow ; le DAG (`pipelines/airflow/retrain_dag.py`)
et les planifications OctOpus ne font qu'appeler `run_retrain_flow` ou les étapes une à une.

Usage : python -m agriml.mlops.retrain_flow --config configs/yield_regression.yaml --holdout recent.csv
        --reference ref.csv --current recent.csv [--champion-run artifacts/yield_regression] [--force]
"""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from agriml._optional import optional_import
from agriml.config import load_config
from agriml.evaluate import slice_scores
from agriml.io import read_table, write_json
from agriml.logs import setup_logging
from agriml.metrics import get_metric
from agriml.mlops.promotion import PromotionDecision, PromotionPolicy, decide_promotion, promote
from agriml.mlops.registry import LocalRegistry
from agriml.monitoring.drift import RetrainDecision, drift_report, should_retrain
from agriml.predict import load_run, predict_frame

logger = logging.getLogger("agriml.mlops.retrain_flow")
WEBHOOK_ENV = "AGRIML_NOTIFY_WEBHOOK"
WEBHOOK_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class HoldoutEval:
    score: float
    n_rows: int
    slices: dict[str, float]


def check_drift(reference: pd.DataFrame, current: pd.DataFrame, columns: Sequence[str],
                **kwargs: Any) -> RetrainDecision:
    decision = should_retrain(drift_report(reference, current, columns), **kwargs)
    logger.info("Dérive : réentraîner=%s %s", decision.retrain, list(decision.reasons))
    return decision


def retrain(config_path: str | Path, output_dir: str | Path, use_tuning: bool = False) -> Path:
    """Réentraîne le challenger dans un dossier horodaté (jamais par-dessus le champion)."""
    from agriml.train import run_experiment

    cfg = replace(load_config(config_path), output_dir=str(Path(output_dir).resolve()))
    run_experiment(cfg, use_tuning=use_tuning)
    return cfg.run_dir


def evaluate_on_holdout(run_dir: str | Path, holdout: pd.DataFrame, slice_column: str | None = None) -> HoldoutEval:
    art = load_run(run_dir)
    cfg = art.cfg
    metric = get_metric(cfg.metric)
    pred = predict_frame(art, holdout.drop(columns=[cfg.columns.target]))
    y_raw = holdout[cfg.columns.target]
    y = y_raw.map({c: i for i, c in enumerate(art.classes)}).to_numpy() if art.classes else y_raw.to_numpy(float)
    p = pred.filter(like="proba_").to_numpy() if cfg.task == "multiclass" else pred["prediction"].to_numpy()
    slices = {}
    if slice_column:
        by_slice = slice_scores(holdout.reset_index(drop=True), y, p, metric, [slice_column])[slice_column]
        slices = {f"{slice_column}={k}": v for k, v in by_slice.items()}
    return HoldoutEval(float(metric(y, p)), int(len(y)), slices)


def notify(summary: dict[str, Any]) -> bool:
    """Envoie un résumé (sans données) au webhook configuré par l'exploitant ; sinon journal uniquement."""
    url = os.environ.get(WEBHOOK_ENV)
    if not url:
        logger.info("Notification (journal) : %s", summary.get("message"))
        return False
    httpx = optional_import("httpx")
    if httpx is None:
        logger.warning("httpx absent : notification non envoyée.")
        return False
    try:
        httpx.post(url, json={"text": summary.get("message"), "promote": summary.get("promote")},
                   timeout=WEBHOOK_TIMEOUT_S).raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Échec de la notification : %s", type(exc).__name__)
        return False
    return True


def _register(run_dir: Path, model_name: str, ev: HoldoutEval, registry: LocalRegistry) -> int:
    return registry.register(model_name, {"run_dir": str(run_dir), "holdout_score": ev.score,
                                          "holdout_rows": ev.n_rows, "holdout_slices": ev.slices})


def run_retrain_flow(config_path: str | Path, holdout: pd.DataFrame, model_name: str, workdir: str | Path,
                     champion_run: str | Path | None = None, drift: RetrainDecision | None = None,
                     force: bool = False, policy: PromotionPolicy = PromotionPolicy(),
                     slice_column: str | None = None, registry: LocalRegistry | None = None) -> dict[str, Any]:
    """Enchaîne les étapes ; renvoie un résumé JSON-sérialisable (aussi écrit dans `workdir`)."""
    workdir = Path(workdir)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if drift is not None and not drift.retrain and not force:
        summary = {"retrained": False, "promote": False, "message": "Pas de dérive : aucun réentraînement."}
        notify(summary)
        return summary
    run_dir = retrain(config_path, workdir / f"challenger_{stamp}")
    challenger = evaluate_on_holdout(run_dir, holdout, slice_column)
    champion = evaluate_on_holdout(champion_run, holdout, slice_column) if champion_run else None
    greater = get_metric(load_run(run_dir).cfg.metric).greater_is_better
    decision: PromotionDecision = decide_promotion(
        champion.score if champion else None, challenger.score, greater, challenger.n_rows, policy,
        champion.slices if champion else None, challenger.slices)
    registry = registry or LocalRegistry(workdir / "registry")
    version = _register(run_dir, model_name, challenger, registry)
    backend = promote(model_name, version, registry=registry) if decision.promote else None
    summary = {"retrained": True, "run_dir": str(run_dir), "version": version, "backend": backend,
               "challenger": asdict(challenger), "champion": asdict(champion) if champion else None,
               "promote": decision.promote, "reasons": list(decision.reasons),
               "message": f"{model_name} v{version} : {'promu' if decision.promote else 'non promu'} "
                          f"({'; '.join(decision.reasons)})"}
    write_json(summary, workdir / f"retrain_{stamp}.json")
    notify(summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Réentraînement + porte champion/challenger.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--holdout", required=True, help="Hold-out récent étiqueté (postérieur à l'entraînement).")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--workdir", default="artifacts/_retrain")
    parser.add_argument("--champion-run")
    parser.add_argument("--reference", help="Données de référence pour la dérive.")
    parser.add_argument("--current", help="Données récentes pour la dérive.")
    parser.add_argument("--slice-column")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    drift = None
    if args.reference and args.current:
        ref, cur = read_table(args.reference), read_table(args.current)
        cols = [c for c in ref.select_dtypes(include=[np.number]).columns if c in cur]
        drift = check_drift(ref, cur, cols)
    summary = run_retrain_flow(args.config, read_table(args.holdout), args.model_name, args.workdir,
                               args.champion_run, drift, args.force, slice_column=args.slice_column)
    logger.info(summary["message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
