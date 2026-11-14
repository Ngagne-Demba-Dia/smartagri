"""Diagnostics de vision et retours sur les recommandations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.common import InputModel

STORAGE_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9/_.\-]{0,511}$"


class ImageRef(InputModel):
    """Image déjà déposée dans le stockage objet (clé relative, jamais d'URL arbitraire)."""

    storage_key: str = Field(pattern=STORAGE_KEY_PATTERN)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class DiagnosisIn(InputModel):
    device: str = Field(min_length=1, max_length=64, description="UUID ou numéro de série du kit")
    label: Literal["healthy", "suspect", "sick"]
    confidence: float = Field(ge=0, le=1)
    model_version: str = Field(min_length=1, max_length=64)
    disease_code: str | None = Field(default=None, max_length=64)
    captured_at: AwareDatetime | None = None
    image: ImageRef | None = None

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"device"})


class FeedbackIn(InputModel):
    feedback: Literal["followed", "partially_followed", "ignored", "not_applicable"]


class DiagnosisAnalyzeIn(InputModel):
    image_base64: str = Field(min_length=1)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    field_id: str | None = Field(default=None, min_length=1, max_length=64)
    device_id: str | None = Field(default=None, min_length=1, max_length=64)
    captured_at: AwareDatetime

    @model_validator(mode="after")
    def _require_scope(self) -> DiagnosisAnalyzeIn:
        if self.field_id is None and self.device_id is None:
            raise ValueError("field_id ou device_id obligatoire.")
        return self
