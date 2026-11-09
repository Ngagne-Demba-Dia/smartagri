"""Registre des modèles : sélection du modèle servi et vérification d'intégrité des paquets locaux."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.db.models import ModelRegistry
from app.services.inference.base import InferenceError, ModelEntry

HASH_CHUNK_BYTES = 1 << 20
_STAGE_ORDER = case((ModelRegistry.stage == "production", 0), (ModelRegistry.stage == "staging", 1), else_=2)


def to_entry(row: ModelRegistry) -> ModelEntry:
    return ModelEntry(name=row.name, version=row.version, uri=row.uri, sha256=row.sha256, source=row.source,
                      octopus_run_id=row.octopus_run_id, features=tuple(row.features or ()))


def serving_entry(session: Session, name: str, sources: tuple[str, ...]) -> ModelEntry:
    """Modèle servi pour `name` : en production d'abord, sinon en préproduction ; le plus récent l'emporte."""
    row = session.scalars(
        select(ModelRegistry)
        .where(ModelRegistry.name == name, ModelRegistry.stage.in_(("production", "staging")),
               ModelRegistry.source.in_(sources))
        .order_by(_STAGE_ORDER, ModelRegistry.created_at.desc()).limit(1)
    ).first()
    if row is None:
        raise InferenceError(f"Aucun modèle en production ou préproduction pour « {name} ».")
    return to_entry(row)


def resolve_bundle_path(bundle_dir: str, uri: str) -> Path:
    """Chemin du paquet, obligatoirement sous MODEL_BUNDLE_DIR (pas de traversée de répertoire)."""
    relative = uri.removeprefix("file://")
    root = Path(bundle_dir).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise InferenceError("Chemin de paquet hors du répertoire des modèles.")
    if not path.is_file():
        raise InferenceError(f"Paquet de modèle absent : {path.name}.")
    return path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(path: Path, expected_sha256: str | None) -> None:
    """Refuse un paquet sans empreinte enregistrée ou dont l'empreinte diffère (paquet altéré)."""
    if not expected_sha256:
        raise InferenceError("Empreinte SHA-256 absente du registre : chargement refusé.")
    if file_sha256(path) != expected_sha256.lower():
        raise InferenceError("Empreinte SHA-256 du paquet différente du registre : chargement refusé.")
