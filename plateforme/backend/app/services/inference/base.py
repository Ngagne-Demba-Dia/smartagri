"""Contrat commun des moteurs d'inférence (paquet local ou service OctOpus)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import AppError

Prediction = float | dict[str, Any]
FeatureRow = Mapping[str, Any]

# Colonnes interdites en entrée d'un modèle : identifiants et données personnelles ou de localisation
# précise. Elles ne doivent jamais quitter la plateforme (OctOpus) ni servir de variables explicatives.
PERSONAL_COLUMNS = frozenset({
    "id", "name", "full_name", "phone", "email", "user_id", "organization_id", "farm_id", "field_id",
    "crop_cycle_id", "device_id", "serial", "latitude", "longitude", "geometry", "address", "commune",
})


class InferenceError(RuntimeError):
    """Modèle indisponible ou réponse invalide ; détail technique réservé aux journaux."""


def model_unavailable() -> AppError:
    return AppError("MODEL_UNAVAILABLE", "Le modèle de prévision est momentanément indisponible.", 503)


@dataclass(frozen=True)
class ModelEntry:
    """Instantané d'une ligne de `model_registry` (indépendant de la session SQLAlchemy)."""

    name: str
    version: str
    uri: str
    sha256: str | None
    source: str
    octopus_run_id: str | None
    features: tuple[str, ...]


class ModelBackend(Protocol):
    name: str
    sources: tuple[str, ...]  # valeurs de `model_registry.source` que ce moteur sait servir

    def predict(self, model_name: str, rows: Sequence[FeatureRow]) -> list[Prediction]:
        """Une prédiction par ligne, dans l'ordre ; lève InferenceError en cas d'échec."""
        ...


def feature_matrix(entry: ModelEntry, rows: Sequence[FeatureRow]) -> list[list[Any]]:
    """Lignes réduites aux colonnes déclarées du modèle, dans l'ordre déclaré."""
    if not entry.features:
        raise InferenceError(f"Modèle {entry.name}:{entry.version} sans liste de variables déclarée.")
    forbidden = PERSONAL_COLUMNS.intersection(entry.features)
    if forbidden:
        raise InferenceError(f"Variables interdites déclarées pour le modèle : {sorted(forbidden)}.")
    missing = [name for name in entry.features if any(name not in row for row in rows)]
    if missing:
        raise InferenceError(f"Variables manquantes : {missing}.")
    return [[row[name] for name in entry.features] for row in rows]


def check_predictions(raw: Any, expected: int) -> list[Prediction]:
    if not isinstance(raw, list) or len(raw) != expected:
        raise InferenceError("Nombre de prédictions incohérent avec le lot envoyé.")
    result: list[Prediction] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, int | float | dict):
            raise InferenceError("Prédiction de type inattendu.")
        result.append(dict(value) if isinstance(value, dict) else float(value))
    return result
