"""Choix du moteur d'inférence selon INFERENCE_BACKEND et conversion des échecs en 503."""

from __future__ import annotations

from collections.abc import Sequence

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.inference.base import (
    FeatureRow,
    ModelBackend,
    Prediction,
)
from app.services.inference.fallback import predict_with_fallback
from app.services.inference.local import LocalBundleBackend
from app.services.inference.octopus import OctopusBatchBackend


def build_backend(settings: Settings, session: Session, client: httpx.Client | None = None) -> ModelBackend | None:
    """`none` → aucun moteur (503 à l'usage) ; `local` → paquets vérifiés ; `octopus` → service distant."""
    if settings.inference_backend == "local":
        return LocalBundleBackend(session, settings.model_bundle_dir)
    if settings.inference_backend == "octopus":
        return OctopusBatchBackend(session, settings.octopus_base_url, settings.octopus_api_key,
                                   settings.octopus_timeout_s, client)
    return None


def predict_or_503(backend: ModelBackend | None, model_name: str, rows: Sequence[FeatureRow]) -> list[Prediction]:
    """Prédit ou lève 503 MODEL_UNAVAILABLE ; le détail technique reste dans les journaux.

    Cas particulier (un seul moteur, pas de règles) de `fallback.predict_with_fallback`.
    """
    return predict_with_fallback([backend], model_name, rows).predictions
