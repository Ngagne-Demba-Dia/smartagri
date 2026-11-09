"""Registre de modèles local (fichiers JSON) : repli quand MLflow n'est pas installé ou pas joignable.

Structure : `<root>/<modèle>/versions/<n>.json` (une entrée par version, jamais réécrite) et
`<root>/<modèle>/aliases.json` ({"champion": 3, "challenger": 4}). Même vocabulaire que les alias MLflow,
pour basculer sur MLflow sans changer le code appelant.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agriml.io import read_json, write_json

DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[3] / "registry"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class RegistryError(RuntimeError):
    """Nom invalide, version ou alias inconnu."""


def _check_name(value: str, what: str) -> str:
    if not _SAFE_NAME.match(value):
        raise RegistryError(f"{what} invalide : {value!r} (lettres, chiffres, « _ . - »).")
    return value


class LocalRegistry:
    def __init__(self, root: str | Path = DEFAULT_REGISTRY_DIR):
        self.root = Path(root)

    def _model_dir(self, name: str) -> Path:
        return self.root / _check_name(name, "Nom de modèle")

    def versions(self, name: str) -> list[int]:
        folder = self._model_dir(name) / "versions"
        return sorted(int(p.stem) for p in folder.glob("*.json")) if folder.exists() else []

    def register(self, name: str, entry: dict[str, Any]) -> int:
        """Ajoute une version immuable ; renvoie son numéro (1, 2, …)."""
        version = (self.versions(name) or [0])[-1] + 1
        payload = {**entry, "name": name, "version": version,
                   "registered_at": datetime.now(UTC).isoformat(timespec="seconds")}
        write_json(payload, self._model_dir(name) / "versions" / f"{version}.json")
        return version

    def get(self, name: str, version: int) -> dict[str, Any]:
        path = self._model_dir(name) / "versions" / f"{int(version)}.json"
        if not path.exists():
            raise RegistryError(f"Version {version} inconnue pour {name}.")
        return read_json(path)

    def aliases(self, name: str) -> dict[str, int]:
        path = self._model_dir(name) / "aliases.json"
        return read_json(path) if path.exists() else {}

    def set_alias(self, name: str, alias: str, version: int) -> None:
        self.get(name, version)
        updated = {**self.aliases(name), _check_name(alias, "Alias"): int(version)}
        write_json(updated, self._model_dir(name) / "aliases.json")

    def get_by_alias(self, name: str, alias: str) -> dict[str, Any] | None:
        version = self.aliases(name).get(alias)
        return None if version is None else self.get(name, version)
