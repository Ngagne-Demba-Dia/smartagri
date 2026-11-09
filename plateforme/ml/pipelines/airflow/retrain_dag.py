"""DAG Airflow hebdomadaire : dérive → (réentraînement + porte champion/challenger) ou rien.

La logique de branchement est une fonction pure (`decide_branch`), testée sans Airflow. Le DAG n'est construit
que si `apache-airflow` est installé (extra `pipelines`) ; sinon le module s'importe sans effet.
Non exécuté sous Airflow dans l'environnement de développement actuel : à vérifier au premier déploiement.

Chemins par défaut (surchargeables via les `params` du DAG) : configuration d'expérience, données de référence,
données récentes et hold-out récent étiqueté. Le webhook de notification se règle par AGRIML_NOTIFY_WEBHOOK.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime
from typing import Any

from agriml.monitoring.drift import RetrainDecision

DAG_ID = "agriml_retrain_weekly"
TASK_RETRAIN = "retrain_and_gate"
TASK_SKIP = "skip_retrain"
DEFAULT_PARAMS = {
    "config": "configs/yield_regression.yaml",
    "reference": "data/curated/yield/reference.parquet",
    "current": "data/curated/yield/current.parquet",
    "holdout": "data/curated/yield/holdout_recent.parquet",
    "model_name": "yield_regression",
    "workdir": "artifacts/_retrain",
    "model_age_days": 0,
    "n_new_labels": 0,
}


def decide_branch(decision: RetrainDecision, force: bool = False) -> str:
    """Identifiant de la tâche suivante : réentraîner si une raison existe (ou si forcé), sinon ignorer."""
    return TASK_RETRAIN if (force or decision.retrain) else TASK_SKIP


def _drift_decision(params: dict[str, Any]) -> RetrainDecision:
    import numpy as np

    from agriml.io import read_table
    from agriml.monitoring.drift import drift_report, should_retrain

    ref, cur = read_table(params["reference"]), read_table(params["current"])
    cols = [c for c in ref.select_dtypes(include=[np.number]).columns if c in cur]
    return should_retrain(drift_report(ref, cur, cols), model_age_days=int(params["model_age_days"]),
                          n_new_labels=int(params["n_new_labels"]))


def _branch_callable(**context: Any) -> str:
    params = {**DEFAULT_PARAMS, **(context.get("params") or {})}
    return decide_branch(_drift_decision(params), bool(params.get("force", False)))


def _retrain_callable(**context: Any) -> dict[str, Any]:
    from agriml.io import read_table
    from agriml.mlops.retrain_flow import run_retrain_flow

    params = {**DEFAULT_PARAMS, **(context.get("params") or {})}
    return run_retrain_flow(params["config"], read_table(params["holdout"]), params["model_name"],
                            params["workdir"], force=True)


def build_dag():
    """Construit le DAG (API Airflow 2.x) ; lève ImportError si Airflow est absent."""
    from airflow import DAG
    from airflow.operators.empty import EmptyOperator
    from airflow.operators.python import BranchPythonOperator, PythonOperator

    with DAG(DAG_ID, start_date=datetime(2026, 1, 5), schedule="0 3 * * 1", catchup=False,
             params=DEFAULT_PARAMS, tags=["agriml", "mlops"]) as dag:
        branch = BranchPythonOperator(task_id="check_drift", python_callable=_branch_callable)
        retrain = PythonOperator(task_id=TASK_RETRAIN, python_callable=_retrain_callable)
        skip = EmptyOperator(task_id=TASK_SKIP)
        branch >> [retrain, skip]
    return dag


dag = build_dag() if importlib.util.find_spec("airflow") is not None else None
