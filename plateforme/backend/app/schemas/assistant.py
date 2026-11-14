"""Assistant agronomique : la longueur utile du message est contrôlée par le service (400 MESSAGE_INVALID)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field

from app.schemas.common import InputModel

HARD_MAX_CHARS = 10_000  # garde-fou de taille de corps ; la limite métier (2000) est dans le service


class ChatIn(InputModel):
    message: str = Field(max_length=HARD_MAX_CHARS)
    conversation_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    locale: Literal["fr", "wo", "ff"] | None = None


class TranscribeIn(InputModel):
    audio_base64: str = Field(min_length=1)
    content_type: str = Field(pattern=r"^(?i)audio/[a-z0-9.+-]+(;.*)?$", max_length=128)
    duration_s: float = Field(gt=0, le=60.0)
    language_hint: Literal["wo", "ff", "fr"] | None = None
