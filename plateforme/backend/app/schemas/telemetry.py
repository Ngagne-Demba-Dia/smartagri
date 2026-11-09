"""Schémas telemetry.v1 (CONVENTIONS §3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import SERIAL_PATTERN

MAX_BATCH_POINTS = 1000


class TelemetryPoint(BaseModel):
    """Un point de mesure : `m` (clés plateforme) ou `kit` (clés brutes du firmware v1.1), pas les deux."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)

    schema_: Literal["telemetry.v1"] = Field(alias="schema")
    device_id: str = Field(pattern=SERIAL_PATTERN)
    fw: str | None = Field(default=None, max_length=32)
    seq: int | None = Field(default=None, ge=0)
    ts: datetime
    source: Literal["mqtt", "relay", "http"] = "http"
    m: dict[str, Any] | None = None
    kit: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _exactly_one_payload(self) -> TelemetryPoint:
        if (self.m is None) == (self.kit is None):
            raise ValueError("Fournir exactement un des champs `m` ou `kit`.")
        return self


class TelemetryBatch(BaseModel):
    """Lot de points ; au-delà de 1000 points la requête est refusée (413 BATCH_TOO_LARGE)."""

    model_config = ConfigDict(extra="forbid")

    points: list[TelemetryPoint] = Field(min_length=1)


class IngestResultOut(BaseModel):
    accepted: int
    duplicates: int
    rejected_points: int
    rejected_values: int
