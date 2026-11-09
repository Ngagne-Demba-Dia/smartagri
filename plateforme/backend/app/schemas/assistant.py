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
