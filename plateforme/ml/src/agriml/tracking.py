"""Suivi d'expériences : MLflow si installé, sinon journal local JSON + CSV (même interface).

Le journal local (`artifacts/_tracking/runs.csv`) sert aussi de « journal d'expériences » de compétition :
une ligne par exécution avec la configuration, le score CV et le score du classement public si saisi.
"""

from __future__ import annotations

import csv
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agriml._optional import optional_import
from agriml.io import write_json

logger = logging.getLogger(__name__)


class LocalTracker:
    backend = "local"

    def __init__(self, experiment: str, root: Path) -> None:
        self.experiment = experiment
        self.dir = Path(root) / "_tracking"
        self.run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.params: dict[str, Any] = {}
        self.metrics: dict[str, float] = {}
        self.tags: dict[str, str] = {}

    def log_params(self, params: dict[str, Any]) -> None:
        self.params.update({k: str(v) for k, v in params.items()})

    def log_metrics(self, metrics: dict[str, float]) -> None:
        self.metrics.update({k: float(v) for k, v in metrics.items()})

    def set_tags(self, tags: dict[str, str]) -> None:
        self.tags.update(tags)

    def log_artifact(self, path: Path) -> None:
        self.tags.setdefault("artifacts", "")
        self.tags["artifacts"] += f"{path};"

    def end(self) -> None:
        record = {"run_id": self.run_id, "experiment": self.experiment, "params": self.params,
                  "metrics": self.metrics, "tags": self.tags}
        write_json(record, self.dir / f"{self.run_id}.json")
        csv_path = self.dir / "runs.csv"
        new_file = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if new_file:
                writer.writerow(["run_id", "experiment", "metric", "value"])
            for name, value in self.metrics.items():
                writer.writerow([self.run_id, self.experiment, name, value])


class MlflowTracker:
    backend = "mlflow"

    def __init__(self, mlflow, experiment: str) -> None:
        self.mlflow = mlflow
        mlflow.set_experiment(experiment)
        self.run = mlflow.start_run()
        self.run_id = self.run.info.run_id

    def log_params(self, params: dict[str, Any]) -> None:
        self.mlflow.log_params({k: str(v)[:500] for k, v in params.items()})

    def log_metrics(self, metrics: dict[str, float]) -> None:
        self.mlflow.log_metrics({k: float(v) for k, v in metrics.items()})

    def set_tags(self, tags: dict[str, str]) -> None:
        self.mlflow.set_tags(tags)

    def log_artifact(self, path: Path) -> None:
        self.mlflow.log_artifact(str(path))

    def end(self) -> None:
        self.mlflow.end_run()


def get_tracker(experiment: str, root: Path) -> LocalTracker | MlflowTracker:
    mlflow = optional_import("mlflow")
    if mlflow is None:
        logger.info("MLflow non installé : suivi local JSON/CSV dans %s", Path(root) / "_tracking")
        return LocalTracker(experiment, root)
    return MlflowTracker(mlflow, experiment)
