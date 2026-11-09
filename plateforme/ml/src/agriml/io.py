"""Lecture et écriture des tables (Parquet si pyarrow est disponible, sinon CSV)."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from agriml._optional import is_available

logger = logging.getLogger(__name__)
HASH_CHUNK_BYTES = 1 << 20


def parquet_available() -> bool:
    return is_available("pyarrow") or is_available("fastparquet")


def read_table(path: str | Path) -> pd.DataFrame:
    """Lit un fichier .parquet ou .csv ; bascule sur l'autre extension si seule celle-ci existe."""
    p = Path(path)
    if not p.exists():
        alt = p.with_suffix(".csv" if p.suffix == ".parquet" else ".parquet")
        if not alt.exists():
            raise FileNotFoundError(f"Fichier introuvable : {p}")
        p = alt
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    if p.suffix == ".csv":
        return pd.read_csv(p)
    raise ValueError(f"Format non pris en charge : {p.suffix} (attendu .parquet ou .csv)")


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    """Écrit une table ; renvoie le chemin réellement écrit (CSV si Parquet indisponible)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix == ".parquet":
        if parquet_available():
            df.to_parquet(p, index=False)
            return p
        logger.warning("pyarrow absent : %s écrit en CSV.", p.name)
        p = p.with_suffix(".csv")
    df.to_csv(p, index=False)
    return p


def write_json(obj: Any, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return p


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _json_default(value: Any) -> Any:
    """Sérialise les types numpy / pandas courants."""
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Type non sérialisable en JSON : {type(value).__name__}")


def sha256_file(path: str | Path) -> str:
    """Empreinte SHA-256 d'un fichier, lue par blocs (fichiers volumineux)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_sha(cwd: str | Path = ".") -> str | None:
    """Commit courant (None hors dépôt git ou si git est absent) : traçabilité code ↔ modèle."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True,
                             timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None
