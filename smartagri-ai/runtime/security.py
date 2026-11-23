"""Primitives de sécurité pour le runtime local SmartAgri AI."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp"})
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 Mio
MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 Mio


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_sha256_from_manifest(path: Path) -> Optional[str]:
    """Lit l'empreinte SHA-256 attendue dans un manifest.json voisin s'il existe."""
    manifest = path.parent / "manifest.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict):
        # Formats supportés : {"files": {"name": "sha256"}} ou {"artifacts": [{"file": ..., "sha256": ...}]}
        files_map = data.get("files")
        if isinstance(files_map, dict) and isinstance(files_map.get(path.name), str):
            return files_map[path.name].lower()
        for entry in data.get("artifacts", []) if isinstance(data.get("artifacts"), list) else []:
            if isinstance(entry, dict) and entry.get("file") == path.name and isinstance(entry.get("sha256"), str):
                return entry["sha256"].lower()
    return None


def ensure_within_root(path: Path, allowed_roots: Iterable[Path]) -> Path:
    resolved = path.resolve(strict=True)
    for root in allowed_roots:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
    raise ValueError(f"Chemin hors périmètre autorisé: {path.name}")


def safe_load_pickle(path: Path, allowed_root: Optional[Path] = None, expected_sha256: Optional[str] = None) -> Any:
    """Charge un artefact pickle uniquement depuis un répertoire autorisé et vérifie son SHA-256 si déclaré."""
    root = allowed_root or (ROOT / "models")
    resolved = ensure_within_root(path, [root])
    sha = expected_sha256.lower() if expected_sha256 else _expected_sha256_from_manifest(resolved)
    if sha is not None:
        actual = sha256_file(resolved)
        if actual != sha:
            raise ValueError(f"Empreinte SHA-256 invalide pour {resolved.name}")
    with resolved.open("rb") as fh:
        return pickle.load(fh)


def validate_safe_image_path(image_path: Path, allowed_roots: Optional[Iterable[Path]] = None) -> Path:
    """Valide qu'un chemin image local reste dans les dossiers autorisés et porte une extension image."""
    roots = list(allowed_roots) if allowed_roots is not None else [ROOT / "datasets", ROOT / "data"]
    resolved = ensure_within_root(Path(image_path), roots)
    if not resolved.is_file():
        raise ValueError("Le chemin ne désigne pas un fichier valide.")
    if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"Extension image non autorisée: {resolved.suffix}")
    if resolved.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("Image trop volumineuse.")
    return resolved


def decode_bounded_base64(payload_b64: str, max_raw_bytes: int, label: str = "données") -> bytes:
    """Décode une chaîne base64 avec plafond strict avant et après décodage."""
    max_b64_len = ((max_raw_bytes + 2) // 3) * 4 + 64
    if len(payload_b64) > max_b64_len:
        raise ValueError(f"Charge {label} trop volumineuse ({max_raw_bytes} octets max).")
    try:
        raw = base64.b64decode(payload_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Encodage base64 invalide pour {label}.") from exc
    if not raw:
        raise ValueError(f"Charge {label} vide.")
    if len(raw) > max_raw_bytes:
        raise ValueError(f"Charge {label} décodée trop volumineuse ({max_raw_bytes} octets max).")
    return raw
