"""Programmes OctOpus (YAML versionnés, porte d'acceptation) et synchronisation vers le registre."""

from __future__ import annotations

import contextlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from agriml.export import MANIFEST, build_manifest
from agriml.io import write_json
from agriml.mlops.registry import LocalRegistry
from agriml.octopus.programs import (
    AcceptanceCriteria, check_acceptance, list_programs, load_program,
)
from agriml.octopus.registry_sync import (
    OctopusRunRecord, SyncRefused, proof_is_valid, proof_sha256, sync_run,
)

EXPECTED_PROGRAMS = {"irrigation_need", "soil_moisture_nowcast", "yield_forecast", "disease_image_classification",
                     "competition_template"}


# --------------------------------------------------------------------------- programmes


def test_all_programs_load_with_guardrails_and_acceptance():
    assert EXPECTED_PROGRAMS <= set(list_programs())
    for name in EXPECTED_PROGRAMS:
        program = load_program(name)
        assert program.name == name and program.objective and program.acceptance.metric == program.metric
        request = program.run_request(f"s3://agri-curated-dev/octopus/{program.dataset}/v=1/")
        assert request.guardrails == program.guardrails.to_dict() and request.hints == program.hints
    irrigation = load_program("irrigation_need")
    assert {"owner_name", "phone"} <= set(irrigation.guardrails.drop)
    assert irrigation.guardrails.round_coords == ("lat", "lon")
    assert irrigation.acceptance.greater_is_better is False  # MAE : plus petit = meilleur
    assert load_program("disease_image_classification").acceptance.human_review is True


def test_load_program_from_path_and_errors(tmp_path):
    custom = tmp_path / "p.yaml"
    custom.write_text("name: p\ndataset: d\nworkspace: agri92-sandbox\ntask: binary\ntarget: y\nmetric: auc\n"
                      "objective: o\n", encoding="utf-8")
    program = load_program(custom)
    assert program.acceptance.greater_is_better is True and program.guardrails.drop == ()
    with pytest.raises(FileNotFoundError):
        load_program("does_not_exist")
    custom.write_text("name: p\ntask: clustering\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tâche inconnue"):
        load_program(custom)


MAE = AcceptanceCriteria(metric="mae", greater_is_better=False, min_relative_gain=0.02, absolute_threshold=3.0)


def test_acceptance_accepts_clear_gain_with_verified_proof():
    decision = check_acceptance(MAE, holdout_score=2.0, baseline_score=2.5, octopus_cv_score=1.9, proof_verified=True)
    assert decision.accepted and decision.reasons == ()


@pytest.mark.parametrize("kwargs, needle", [
    ({"holdout_score": 2.49, "baseline_score": 2.5, "proof_verified": True}, "gain"),
    ({"holdout_score": 3.5, "baseline_score": 5.0, "proof_verified": True}, "seuil"),
    ({"holdout_score": 2.0, "baseline_score": 2.5, "octopus_cv_score": 1.0, "proof_verified": True}, "surapprentissage"),
    ({"holdout_score": 2.0, "baseline_score": 2.5, "proof_verified": None}, "preuve"),
    ({"holdout_score": 2.0, "baseline_score": 2.5, "proof_verified": True, "slice_regressions": ["riz"]}, "riz"),
])
def test_acceptance_refusals(kwargs, needle):
    decision = check_acceptance(MAE, **kwargs)
    assert not decision.accepted and any(needle in r for r in decision.reasons)


def test_acceptance_human_review_flag():
    criteria = AcceptanceCriteria(metric="f1_macro", greater_is_better=True, human_review=True)
    decision = check_acceptance(criteria, holdout_score=0.8, baseline_score=0.7, proof_verified=True)
    assert decision.accepted and "validation humaine" in decision.reasons[0]


# --------------------------------------------------------------------------- synchronisation registre


def make_bundle(root: Path) -> Path:
    bundle = root / "bundle"
    bundle.mkdir()
    files = [bundle / "model.onnx", bundle / "model_card.md"]
    files[0].write_bytes(b"fake-onnx")
    files[1].write_text("# carte", encoding="utf-8")
    write_json(build_manifest(bundle, files), bundle / MANIFEST)
    return bundle


def make_record(tmp_path: Path, holdout_sent: bool = False) -> OctopusRunRecord:
    dataset_manifest = write_json({"dataset": "irrigation_need", "version": "v=1", "holdout_sent": holdout_sent},
                                  tmp_path / "dataset_manifest.json")
    return OctopusRunRecord(model_name="irrigation_need", octopus_run_id="run_42", bundle_dir=make_bundle(tmp_path),
                            dataset_manifest=dataset_manifest, proof={"run_id": "run_42", "sig": "abc"},
                            metrics={"mae": 2.1}, program="irrigation_need")


def test_sync_local_registers_challenger_with_tags(tmp_path):
    registry = LocalRegistry(tmp_path / "registry")
    record = make_record(tmp_path)
    result = sync_run(record, registry=registry, proof_verifier=lambda p: {"valid": True}, use_mlflow=False)
    assert result.backend == "local" and result.version == 1
    entry = registry.get_by_alias("irrigation_need", "challenger")
    assert entry["tags"]["octopus_run_id"] == "run_42"
    assert entry["tags"]["bundle_sha256"] == result.bundle_sha256
    assert entry["tags"]["octopus_proof_sha256"] == proof_sha256(record.proof)
    assert entry["tags"]["octopus_proof_verified"] == "true" and len(entry["tags"]["dataset_manifest_sha256"]) == 64
    assert entry["octopus_proof"] == {"run_id": "run_42", "sig": "abc"}
    assert registry.aliases("irrigation_need") == {"challenger": 1}


def test_sync_refuses_tampered_bundle_holdout_and_bad_proof(tmp_path):
    registry = LocalRegistry(tmp_path / "registry")
    record = make_record(tmp_path)
    (record.bundle_dir / "model.onnx").write_bytes(b"tampered")
    with pytest.raises(SyncRefused, match="Paquet"):
        sync_run(record, registry=registry, use_mlflow=False)
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(SyncRefused, match="holdout"):
        sync_run(make_record(other, holdout_sent=True), registry=registry, use_mlflow=False)
    third = tmp_path / "third"
    third.mkdir()
    with pytest.raises(SyncRefused, match="Preuve"):
        sync_run(make_record(third), registry=registry, proof_verifier=lambda p: {"valid": False}, use_mlflow=False)
    assert registry.versions("irrigation_need") == []


def test_sync_uses_injected_mlflow(tmp_path):
    calls: dict[str, object] = {}

    @contextlib.contextmanager
    def start_run(run_name):
        calls["run_name"] = run_name
        yield SimpleNamespace(info=SimpleNamespace(run_id="mlrun1"))

    client = SimpleNamespace(set_registered_model_alias=lambda *a: calls.setdefault("alias", a))
    fake = SimpleNamespace(
        start_run=start_run, set_tags=lambda t: calls.setdefault("tags", t),
        log_metrics=lambda m: calls.setdefault("metrics", m), log_dict=lambda d, f: calls.setdefault("proof", f),
        log_artifacts=lambda path, artifact_path: calls.setdefault("artifacts", artifact_path),
        register_model=lambda uri, name, tags: SimpleNamespace(version=7, uri=calls.setdefault("uri", uri)),
        MlflowClient=lambda: client,
    )
    result = sync_run(make_record(tmp_path), mlflow_module=fake)
    assert result.backend == "mlflow" and result.version == "7"
    assert calls["uri"] == "runs:/mlrun1/bundle" and calls["alias"] == ("irrigation_need", "challenger", 7)
    assert calls["tags"]["octopus_run_id"] == "run_42" and calls["metrics"] == {"mae": 2.1}


def test_proof_helpers():
    assert proof_sha256({"a": 1, "b": 2}) == proof_sha256({"b": 2, "a": 1})
    assert proof_is_valid(True) and proof_is_valid({"verified": True})
    assert not proof_is_valid({"valid": "yes"}) and not proof_is_valid(None)
