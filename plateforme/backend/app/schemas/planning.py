"""Campagnes, cycles culturaux, équipements et maintenance."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, ClassVar, Literal

from pydantic import AwareDatetime, Field

from app.schemas.common import InputModel, PatchModel

Season = Literal["dry", "rainy"]
CampaignStatus = Literal["planned", "active", "closed"]
CycleStatus = Literal["planned", "active", "harvested", "abandoned"]
EquipmentKind = Literal["pump", "tank", "solar_panel", "battery", "sensor", "camera", "gateway", "other"]
EquipmentStatus = Literal["ok", "maintenance", "out_of_service"]
MaintenanceKind = Literal["inspection", "preventive", "corrective", "replacement", "other"]
CROP_PATTERN = r"^[a-z][a-z_]{1,29}$"
MAX_FCFA = 1_000_000_000


class CampaignIn(InputModel):
    organization_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    season: Season
    start_date: date
    end_date: date
    status: CampaignStatus = "planned"

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"organization_id"})


class CampaignPatch(PatchModel):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset({"name", "season", "start_date", "end_date", "status"})

    name: str | None = Field(default=None, min_length=1, max_length=120)
    season: Season | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: CampaignStatus | None = None


class CropCycleIn(InputModel):
    crop: str = Field(pattern=CROP_PATTERN, description="Code culture (ex. onion, tomato, cabbage)")
    variety: str | None = Field(default=None, max_length=100)
    planted_on: date | None = None
    expected_harvest_on: date | None = None
    status: CycleStatus = "active"
    campaign_id: uuid.UUID | None = None


class CropCyclePatch(PatchModel):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset({"crop", "status"})

    crop: str | None = Field(default=None, pattern=CROP_PATTERN)
    variety: str | None = Field(default=None, max_length=100)
    planted_on: date | None = None
    expected_harvest_on: date | None = None
    harvested_on: date | None = None
    yield_kg: float | None = Field(default=None, ge=0, le=10_000_000)
    status: CycleStatus | None = None
    campaign_id: uuid.UUID | None = None


class EquipmentIn(InputModel):
    farm_id: uuid.UUID
    kind: EquipmentKind
    label: str = Field(min_length=1, max_length=200)
    serial: str | None = Field(default=None, max_length=100)
    installed_at: date | None = None
    status: EquipmentStatus = "ok"
    device: str | None = Field(default=None, max_length=64, description="Kit lié : UUID ou numéro de série")
    flow_m3h: float | None = Field(default=None, gt=0, le=1000)

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"farm_id"})


class EquipmentPatch(PatchModel):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset({"kind", "label", "status"})

    kind: EquipmentKind | None = None
    label: str | None = Field(default=None, min_length=1, max_length=200)
    serial: str | None = Field(default=None, max_length=100)
    installed_at: date | None = None
    status: EquipmentStatus | None = None
    device: str | None = Field(default=None, max_length=64)
    flow_m3h: float | None = Field(default=None, gt=0, le=1000)


class MaintenanceIn(InputModel):
    ts: AwareDatetime | None = None
    kind: MaintenanceKind
    notes: str | None = Field(default=None, max_length=2000)
    cost_fcfa: int | None = Field(default=None, ge=0, le=MAX_FCFA)
