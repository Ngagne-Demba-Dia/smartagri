"""Kits et seuils d'irrigation.

Les seuils sont acceptés sous forme brute (`Any`) : leur validation suit exactement la règle du
firmware (agronomy.validate_thresholds) et renvoie 400 THRESHOLDS_INVALID, jamais 422.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.core.constants import SERIAL_PATTERN
from app.schemas.common import InputModel


class DeviceIn(InputModel):
    organization_id: uuid.UUID | None = None
    serial: str = Field(pattern=SERIAL_PATTERN)
    name: str | None = Field(default=None, max_length=200)
    field_id: uuid.UUID | None = None


class ThresholdsIn(InputModel):
    start: Any = None
    stop: Any = None
