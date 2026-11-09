"""Choix du moteur d'inférence selon INFERENCE_BACKEND et conversion des échecs en 503."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.inference.base import (
    FeatureRow,
    InferenceError,
    ModelBackend,
    Prediction,
    model_unavailable,
)
from app.services.inference.local import LocalBundleBackend
from app.services.inference.octopus import OctopusBatchBackend

logger = logging.getLogger(__name__)


def build_backend(settings: Settings, session: Session, client: httpx.Client | None = None) -> ModelBackend | None:
    """`none` → aucun moteur (503 à l'usage) ; `local` → paquets vérifiés ; `octopus` → service distant."""
    if settings.inference_backend == "local":
        return LocalBundleBackend(session, settings.model_bundle_dir)
    if settings.inference_backend == "octopus":
        return OctopusBatchBackend(session, settings.octopus_base_url, settings.octopus_api_key,
                                   settings.octopus_timeout_s, client)
    return None


def predict_or_503(backend: ModelBackend | None, model_name: str, rows: Sequence[FeatureRow]) -> list[Prediction]:
    """Prédit ou lève 503 MODEL_UNAVAILABLE ; le détail technique reste dans les journaux."""
    if backend is None:
        raise model_unavailable()
    try:
        return backend.predict(model_name, rows)
    except InferenceError as exc:
        logger.warning("Inférence %s via %s impossible : %s", model_name, backend.name, exc)
        raise model_unavailable() from exc
