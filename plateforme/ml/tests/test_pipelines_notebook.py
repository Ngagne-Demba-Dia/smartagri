"""Orchestration : branchement du DAG Airflow (sans Airflow), cohérence dvc.yaml / params.yaml, carnet d'EDA."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from agriml.monitoring.drift import RetrainDecision

ML_ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ML_ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def dag_module():
    return _load("pipelines/airflow/retrain_dag.py", "retrain_dag")


@pytest.mark.parametrize("retrain, force, expected", [
    (True, False, "retrain_and_gate"), (False, False, "skip_retrain"), (False, True, "retrain_and_gate")])
def test_decide_branch(dag_module, retrain, force, expected):
    decision = RetrainDecision(retrain, ("raison",) if retrain else ())
    assert dag_module.decide_branch(decision, force=force) == expected


def test_dag_is_none_without_airflow(dag_module):
    if importlib.util.find_spec("airflow") is not None:
        pytest.skip("Airflow installé : le DAG est construit")
    assert dag_module.dag is None


def test_drift_decision_detects_shift(dag_module, tmp_path):
    # Arrange : la variable x se décale fortement entre référence et période récente
    rng = np.random.default_rng(0)
    pd.DataFrame({"x": rng.normal(0, 1, 500), "y": rng.normal(0, 1, 500)}).to_csv(tmp_path / "ref.csv", index=False)
    pd.DataFrame({"x": rng.normal(3, 1, 500), "y": rng.normal(0, 1, 500)}).to_csv(tmp_path / "cur.csv", index=False)
    params = {**dag_module.DEFAULT_PARAMS, "reference": str(tmp_path / "ref.csv"), "current": str(tmp_path / "cur.csv")}

    # Act
    decision = dag_module._drift_decision(params)

    # Assert
    assert decision.retrain and any("dérive" in r for r in decision.reasons)
    assert dag_module.decide_branch(decision) == dag_module.TASK_RETRAIN


def test_dvc_pipeline_references_existing_files():
    params = yaml.safe_load((ML_ROOT / "params.yaml").read_text(encoding="utf-8"))
    dvc = yaml.safe_load((ML_ROOT / "dvc.yaml").read_text(encoding="utf-8"))
    assert {"make_data", "train", "evaluate", "export"} <= set(dvc["stages"])
    for item in dvc["stages"]["train"]["foreach"]:
        assert (ML_ROOT / "configs" / f"{item}.yaml").exists()
    for stage in dvc["stages"].values():
        cmd = (stage.get("do") or stage)["cmd"]
        for var in re.findall(r"\$\{(\w+)\.(\w+)\}", cmd):
            assert var[1] in params[var[0]], f"paramètre manquant : {var}"
    assert (ML_ROOT / "scripts" / "make_synthetic.py").exists()


def test_eda_notebook_builds_and_compiles():
    pytest.importorskip("nbformat")
    builder = _load("scripts/build_eda_notebook.py", "build_eda_notebook")
    nb = builder.build_notebook("yield")
    code = [c.source for c in nb.cells if c.cell_type == "code"]
    assert len(code) >= 5 and 'TARGET, GROUP, TIME, ID = "yield_t_ha"' in code[0]
    for source in code:
        compile(source, "<cellule>", "exec")  # syntaxe valide sans exécuter le noyau
    assert "(ID, TIME)" in code[-1]  # le temps est exclu de la validation adversariale
