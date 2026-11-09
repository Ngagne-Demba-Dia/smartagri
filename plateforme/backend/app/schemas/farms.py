"""Exploitations et parcelles ; le contour GeoJSON est validé ici (erreur 422 en cas de contour invalide)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.common import InputModel
from app.services import geo

IrrigationType = Literal["drip", "sprinkler", "furrow", "manual"]


class FarmIn(InputModel):
    organization_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    region: str | None = Field(default=None, max_length=100)
    commune: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    area_ha: float | None = Field(default=None, gt=0, le=100_000)

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"organization_id"})


class FieldIn(InputModel):
    name: str = Field(min_length=1, max_length=200)
    area_ha: float | None = Field(default=None, gt=0, le=10_000)
    soil_type: str | None = Field(default=None, max_length=50)
    irrigation_type: IrrigationType | None = None
    geometry: dict[str, Any] | None = None

    @field_validator("geometry")
    @classmethod
    def _valid_polygon(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return geo.validate_polygon(value) if value is not None else None
