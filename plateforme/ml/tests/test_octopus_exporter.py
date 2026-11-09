"""Exporteur OctOpus : refus des données personnelles, empreintes stables, sel jamais écrit, entrée intacte."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from agriml.io import read_json, sha256_file
from agriml.octopus.exporter import (
    MANIFEST, ExportRefused, PrivacyPolicy, SnapshotSpec, apply_policy, export_snapshot, find_violations,
    load_salt, main, pseudonymize_series, snapshot_key,
)

from conftest import TEST_SALT

POLICY = PrivacyPolicy(drop=("owner_name", "phone"), pseudonymize=("field_key", "device_id"),
                       round_coords=("lat", "lon"))


def spec(version: str = "20261026-abc1234", policy: PrivacyPolicy = POLICY, fmt: str = "csv") -> SnapshotSpec:
    return SnapshotSpec("irrigation_need", version, policy, {"query_id": "irrigation_need_v1.sql"},
                        target="target_need_mm_24h", groups="field_key", time_column="ts", file_format=fmt)


def all_text(folder) -> str:
    return "\n".join(p.read_bytes().decode("utf-8", "replace") for p in folder.rglob("*") if p.is_file())


def test_export_writes_manifest_with_file_hashes_and_no_salt(tmp_path, field_frame, salt_env):
    before = field_frame.copy()
    result = export_snapshot(field_frame, tmp_path, spec(), env=salt_env)
    pd.testing.assert_frame_equal(field_frame, before)  # entrée jamais modifiée
    manifest = read_json(result.folder / MANIFEST)
    assert result.folder == tmp_path / "octopus" / "irrigation_need" / "v=20261026-abc1234"
    for name, digest in manifest["files"].items():
        assert digest == f"sha256:{sha256_file(result.folder / name)}"
    assert set(manifest["files"]) == {"train.csv", "README.md"}
    assert manifest["holdout_sent"] is False and manifest["rows"] == len(field_frame)
    assert manifest["pseudonymisation"] == {"method": "HMAC-SHA256", "salt_id": "salt-test-v1"}
    assert manifest["dropped_columns"] == ["owner_name", "phone"]
    assert manifest["rounded_columns"] == {"lat_r": 0.01, "lon_r": 0.01}
    assert result.manifest_sha256 == sha256_file(result.folder / MANIFEST)
    text = all_text(result.folder)
    assert TEST_SALT not in text and "Agriculteur" not in text and "ESP32-" not in text and "F000" not in text


def test_train_file_hash_is_stable_across_exports(tmp_path, field_frame, salt_env):
    a = export_snapshot(field_frame, tmp_path, spec("v1"), env=salt_env)
    b = export_snapshot(field_frame, tmp_path, spec("v2"), env=salt_env)
    assert a.manifest["files"]["train.csv"] == b.manifest["files"]["train.csv"]


def test_parquet_export_with_test_table(tmp_path, field_frame, salt_env):
    pytest.importorskip("pyarrow")
    test = field_frame.drop(columns=["target_need_mm_24h"]).head(20)
    result = export_snapshot(field_frame, tmp_path, spec(fmt="parquet"), test=test, env=salt_env)
    assert {"train.parquet", "test.parquet", "README.md"} == set(result.manifest["files"])
    assert result.manifest["test_rows"] == 20 and result.manifest["dropped_columns"] == ["owner_name", "phone"]


def test_same_version_is_immutable(tmp_path, field_frame, salt_env):
    export_snapshot(field_frame, tmp_path, spec(), env=salt_env)
    with pytest.raises(ExportRefused, match="déjà publiée"):
        export_snapshot(field_frame, tmp_path, spec(), env=salt_env)


@pytest.mark.parametrize("policy, needle", [
    (PrivacyPolicy(pseudonymize=("field_key", "device_id"), round_coords=("lat", "lon")), "owner_name"),
    (PrivacyPolicy(drop=("owner_name", "phone"), pseudonymize=("field_key", "device_id")), "coordonnées"),
])
def test_forbidden_columns_refuse_and_write_nothing(tmp_path, field_frame, salt_env, policy, needle):
    with pytest.raises(ExportRefused, match=needle):
        export_snapshot(field_frame, tmp_path, spec(policy=policy), env=salt_env)
    assert not any(tmp_path.rglob("*.csv")) and not any(tmp_path.rglob(MANIFEST))


def test_phone_and_email_values_in_free_text_are_refused(field_frame):
    df = field_frame.drop(columns=["owner_name", "phone"]).assign(remark="appeler le 77 123 45 67 svp")
    clean, _ = apply_policy(df, POLICY, TEST_SALT.encode())
    problems = find_violations(clean, POLICY)
    assert any("téléphone" in p for p in problems)
    clean2, _ = apply_policy(df.assign(remark="ecrire a jean@example.org"), POLICY, TEST_SALT.encode())
    assert any("e-mail" in p for p in find_violations(clean2, POLICY))


def test_allow_list_and_rounding_precision():
    df = pd.DataFrame({"variety_name": ["Mongal"], "lat_r": [14.6937]})
    problems = find_violations(df, PrivacyPolicy(allow=("variety_name",)))
    assert len(problems) == 1 and "précision" in problems[0]


def test_pseudonymization_is_stable_salted_and_keeps_missing():
    values = pd.Series(["F001", None, "F001"])
    a = pseudonymize_series(values, b"x" * 32)
    b = pseudonymize_series(values, b"y" * 32)
    assert a[0] == a[2] and len(a[0]) == 16 and pd.isna(a[1])
    assert a[0] != b[0]


def test_salt_is_required_and_long_enough():
    with pytest.raises(ExportRefused):
        load_salt({})
    with pytest.raises(ExportRefused):
        load_salt({"AGRIML_PSEUDO_SALT": "short"})
    salt, salt_id = load_salt({"AGRIML_PSEUDO_SALT": TEST_SALT})
    assert salt == TEST_SALT.encode() and salt_id.startswith("hmac-") and TEST_SALT not in salt_id


def test_snapshot_key_rejects_path_traversal():
    assert snapshot_key("yield", "20261026-abc") == "octopus/yield/v=20261026-abc/"
    with pytest.raises(ExportRefused):
        snapshot_key("../etc", "v1")


def test_policy_from_mapping_rejects_unknown_keys():
    assert PrivacyPolicy.from_mapping({"drop": ["a"]}).drop == ("a",)
    with pytest.raises(ValueError):
        PrivacyPolicy.from_mapping({"dropp": ["a"]})


def test_missing_target_is_refused(tmp_path, field_frame, salt_env):
    with pytest.raises(ExportRefused, match="Cible"):
        export_snapshot(field_frame.drop(columns=["target_need_mm_24h"]), tmp_path, spec(), env=salt_env)


def test_cli_exports_with_program_and_refuses_pii(tmp_path, field_frame, salt_env, monkeypatch):
    for key, value in salt_env.items():
        monkeypatch.setenv(key, value)
    data = tmp_path / "irrigation.csv"
    field_frame.to_csv(data, index=False)
    out = tmp_path / "curated"
    args = ["--program", "irrigation_need", "--train", str(data), "--version", "20261026-abc1234",
            "--out", str(out), "--source-query", "q1", "--format", "csv"]
    assert main(args) == 0
    manifest = json.loads((out / "octopus" / "irrigation_need" / "v=20261026-abc1234" / MANIFEST).read_text("utf-8"))
    assert manifest["source"] == {"query_id": "q1"} and "farm_key" not in manifest["schema"]
    leaky = tmp_path / "leaky.csv"
    field_frame.assign(email_contact="a@b.sn").to_csv(leaky, index=False)
    assert main([*args[:2], "--train", str(leaky), *args[4:5], "v2", *args[6:]]) == 2
