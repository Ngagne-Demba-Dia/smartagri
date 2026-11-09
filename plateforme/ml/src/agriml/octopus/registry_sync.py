"""Synchronisation d'un run OctOpus vers le registre de modèles (MLflow si présent, sinon registre JSON local).

Avant tout enregistrement :
- le paquet de modèle est vérifié fichier par fichier (`agriml.export.verify_bundle`) ;
- le manifeste du jeu exporté doit exister et déclarer `holdout_sent: false` ;
- la preuve OctOpus est vérifiée si un vérificateur est fourni (`OctopusClient.verify_proof`) : invalide = refus.
Le modèle est enregistré comme CHALLENGER uniquement ; la promotion reste la porte `agriml.mlops.promotion`.

Étiquettes posées : octopus_run_id, octopus_proof_sha256, bundle_sha256, dataset_manifest_sha256,
dataset_version, program, source=octopus. La preuve JSON complète est conservée avec la version.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from agriml._optional import optional_import
from agriml.export import verify_bundle
from agriml.io import read_json, sha256_file
from agriml.mlops.registry import LocalRegistry

logger = logging.getLogger(__name__)

SOURCE_TAG = "octopus"
CHALLENGER = "challenger"
PROOF_ARTIFACT = "octopus_proof.json"
BUNDLE_ARTIFACT_PATH = "bundle"
VALIDITY_KEYS = ("valid", "verified", "ok")

ProofVerifier = Callable[[Mapping[str, Any]], Any]


class SyncRefused(RuntimeError):
    """Run OctOpus refusé : paquet altéré, holdout envoyé ou preuve invalide. Rien n'a été enregistré."""


@dataclass(frozen=True)
class OctopusRunRecord:
    model_name: str
    octopus_run_id: str
    bundle_dir: Path
    dataset_manifest: Path
    proof: Mapping[str, Any] = field(repr=False)
    metrics: Mapping[str, float] = field(default_factory=dict)
    program: str | None = None


@dataclass(frozen=True)
class SyncResult:
    backend: str  # "mlflow" | "local"
    version: int | str
    bundle_sha256: str
    tags: Mapping[str, str]


def proof_sha256(proof: Mapping[str, Any]) -> str:
    """Empreinte canonique (clés triées, séparateurs compacts) : indépendante de l'ordre des champs."""
    canonical = json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def proof_is_valid(answer: Any) -> bool:
    """Interprète la réponse de /api/proof/verify (format à vérifier) : booléen ou objet {valid|verified|ok}."""
    if isinstance(answer, bool):
        return answer
    if isinstance(answer, Mapping):
        return any(answer.get(k) is True for k in VALIDITY_KEYS)
    return False


def _check_dataset(manifest_path: Path) -> tuple[str, dict[str, Any]]:
    if not manifest_path.exists():
        raise SyncRefused(f"Manifeste du jeu introuvable : {manifest_path}")
    manifest = read_json(manifest_path)
    if manifest.get("holdout_sent") is not False:
        raise SyncRefused("Le manifeste ne garantit pas que le holdout est resté chez nous (holdout_sent != false).")
    return sha256_file(manifest_path), manifest


def build_tags(record: OctopusRunRecord, bundle_sha: str, dataset_sha: str,
               dataset_manifest: Mapping[str, Any], proof_verified: bool | None) -> dict[str, str]:
    return {
        "source": SOURCE_TAG, "octopus_run_id": record.octopus_run_id,
        "octopus_proof_sha256": proof_sha256(record.proof), "octopus_proof_verified": str(proof_verified).lower(),
        "bundle_sha256": bundle_sha, "dataset_manifest_sha256": dataset_sha,
        "dataset": str(dataset_manifest.get("dataset")), "dataset_version": str(dataset_manifest.get("version")),
        "program": record.program or "",
    }


def _sync_mlflow(mlflow: ModuleType, record: OctopusRunRecord, tags: Mapping[str, str]) -> str:
    """Run MLflow + version de modèle étiquetée ; l'alias challenger est posé si le client le permet."""
    with mlflow.start_run(run_name=f"octopus-{record.octopus_run_id}") as run:
        mlflow.set_tags(dict(tags))
        if record.metrics:
            mlflow.log_metrics({k: float(v) for k, v in record.metrics.items()})
        mlflow.log_dict(dict(record.proof), PROOF_ARTIFACT)
        mlflow.log_artifacts(str(record.bundle_dir), artifact_path=BUNDLE_ARTIFACT_PATH)
        uri = f"runs:/{run.info.run_id}/{BUNDLE_ARTIFACT_PATH}"
    model_version = mlflow.register_model(uri, record.model_name, tags=dict(tags))
    mlflow.MlflowClient().set_registered_model_alias(record.model_name, CHALLENGER, model_version.version)
    return str(model_version.version)


def _sync_local(registry: LocalRegistry, record: OctopusRunRecord, tags: Mapping[str, str]) -> int:
    entry = {"source": SOURCE_TAG, "tags": dict(tags), "metrics": dict(record.metrics),
             "bundle_dir": str(record.bundle_dir), "dataset_manifest": str(record.dataset_manifest),
             "octopus_proof": dict(record.proof)}
    version = registry.register(record.model_name, entry)
    registry.set_alias(record.model_name, CHALLENGER, version)
    return version


def sync_run(record: OctopusRunRecord, registry: LocalRegistry | None = None,
             mlflow_module: ModuleType | None = None, proof_verifier: ProofVerifier | None = None,
             use_mlflow: bool = True) -> SyncResult:
    """Vérifie puis enregistre le run comme challenger ; lève SyncRefused sans rien écrire en cas de doute."""
    try:
        bundle_sha = verify_bundle(record.bundle_dir)
    except Exception as exc:  # BundleIntegrityError, manifeste absent ou illisible
        raise SyncRefused(f"Paquet de modèle invalide ({record.bundle_dir}) : {exc}") from exc
    dataset_sha, dataset_manifest = _check_dataset(Path(record.dataset_manifest))
    verified = None
    if proof_verifier is not None:
        verified = proof_is_valid(proof_verifier(record.proof))
        if not verified:
            raise SyncRefused(f"Preuve OctOpus invalide pour le run {record.octopus_run_id}.")
    tags = build_tags(record, bundle_sha, dataset_sha, dataset_manifest, verified)
    mlflow = mlflow_module if mlflow_module is not None else (optional_import("mlflow") if use_mlflow else None)
    if mlflow is not None:
        version: int | str = _sync_mlflow(mlflow, record, tags)
        backend = "mlflow"
    else:
        version = _sync_local(registry or LocalRegistry(), record, tags)
        backend = "local"
    logger.info("Run OctOpus %s enregistré (%s, version %s, challenger).", record.octopus_run_id, backend, version)
    return SyncResult(backend, version, bundle_sha, tags)
