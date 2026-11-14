"""Transcription vocale de l'assistant (doc 16 § 9.3, service 17 `assistant_transcribe`, modèle `asst_asr`).

Valide les bornes de sécurité (taille <= 256 Kio, durée <= 60 s, format `audio/*`, langue `wo|ff|fr`).
Tant qu'aucun fournisseur ASR n'est configuré et injecté sur `app.state.transcriber`, renvoie honnêtement
`503 MODEL_UNAVAILABLE` pour laisser le Frontend basculer sur la saisie clavier / boutons rapides.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.core.errors import AppError
from app.services.provenance import confidence as build_confidence, provenance

UPLOAD_MAX_BYTES = 256 * 1024
UPLOAD_MAX_RAW_BYTES = ((UPLOAD_MAX_BYTES - 2048) * 3) // 4
MAX_DURATION_S = 60.0
SUPPORTED_LANGUAGES = frozenset({"wo", "ff", "fr"})


@dataclass(frozen=True)
class TranscribeOutput:
    text: str
    language: str  # "wo" | "ff" | "fr"
    confidence_score: float = 0.85
    model_version: str = "xlsr-300m-v1"
    source: str = "agriml"
    calibrated: bool = False


class Transcriber(Protocol):
    def transcribe(
        self, audio_bytes: bytes, content_type: str, duration_s: float, language_hint: str | None
    ) -> TranscribeOutput: ...


def _decode_bounded_audio(audio_base64: str) -> bytes:
    if len(audio_base64.encode("ascii", errors="ignore")) > UPLOAD_MAX_BYTES:
        raise AppError("PAYLOAD_TOO_LARGE", "Audio trop volumineux (256 Kio max).", 413)
    try:
        raw = base64.b64decode(audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppError("VALIDATION_ERROR", "Encodage base64 de l'audio invalide.", 422) from exc
    if not raw:
        raise AppError("VALIDATION_ERROR", "Audio vide.", 422)
    if len(raw) > UPLOAD_MAX_RAW_BYTES:
        raise AppError("PAYLOAD_TOO_LARGE", "Audio décodé trop volumineux (256 Kio max).", 413)
    return raw


def transcribe_audio(
    audio_base64: str,
    content_type: str,
    duration_s: float,
    language_hint: str | None,
    now: datetime,
    transcriber: Transcriber | None = None,
) -> dict[str, Any]:
    """Point d'entrée de `POST /v1/assistant/transcribe`."""
    raw_bytes = _decode_bounded_audio(audio_base64)
    if duration_s <= 0 or duration_s > MAX_DURATION_S:
        raise AppError("VALIDATION_ERROR", f"Durée audio invalide ({MAX_DURATION_S:g} s max).", 422)
    if language_hint is not None and language_hint not in SUPPORTED_LANGUAGES:
        raise AppError("VALIDATION_ERROR", "Langue non prise en charge (attendu : wo, ff, fr).", 422)
    if transcriber is None:
        raise AppError(
            "MODEL_UNAVAILABLE",
            "Service de transcription vocale (asst_asr) indisponible.",
            503,
        )
    out = transcriber.transcribe(raw_bytes, content_type, duration_s, language_hint)
    lang = out.language if out.language in SUPPORTED_LANGUAGES else (language_hint or "fr")
    score = max(0.0, min(1.0, float(out.confidence_score)))
    return {
        "text": out.text,
        "language": lang,
        "duration_s": round(float(duration_s), 2),
        "provenance": provenance(
            model_name="asst_asr",
            model_version=out.model_version,
            source=out.source,
            computed_at=now,
            fallback_step=0,
            data_as_of=now,
            stale=False,
            conf=build_confidence("probability", value=round(score, 4), calibrated=out.calibrated),
        ),
    }
