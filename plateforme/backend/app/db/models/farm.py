"""Exploitations, parcelles (contour GeoJSON) et cycles culturaux."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import CROP_CYCLE_STATUSES, IRRIGATION_TYPES, sql_in
from app.db.base import Base, CreatedAt, JSONType, UUIDPk


class Farm(UUIDPk, CreatedAt, Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="longitude"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str | None] = mapped_column(String(100))
    commune: Mapped[str | None] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    area_ha: Mapped[float | None] = mapped_column(Float)


class Field(UUIDPk, CreatedAt, Base):
    """Parcelle. `geometry` = polygone GeoJSON (WGS 84) validé par app/services/geo.py.

    Sous PostgreSQL, la colonne PostGIS `geom geometry(Polygon,4326)` est générée depuis `geometry`
    (001_init.sql) et indexée en GiST ; sous SQLite seul le GeoJSON (texte JSON) existe.
    """

    __tablename__ = "fields"
    __table_args__ = (
        CheckConstraint("irrigation_type IS NULL OR " + sql_in("irrigation_type", IRRIGATION_TYPES), name="irrigation"),
        CheckConstraint("area_ha IS NULL OR area_ha > 0", name="area"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    area_ha: Mapped[float | None] = mapped_column(Float)
    soil_type: Mapped[str | None] = mapped_column(String(50))
    irrigation_type: Mapped[str | None] = mapped_column(String(20))
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSONType)


class CropCycle(UUIDPk, CreatedAt, Base):
    __tablename__ = "crop_cycles"
    __table_args__ = (CheckConstraint(sql_in("status", CROP_CYCLE_STATUSES), name="status"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    crop: Mapped[str] = mapped_column(String(30))
    variety: Mapped[str | None] = mapped_column(String(100))
    planted_on: Mapped[date | None]
    expected_harvest_on: Mapped[date | None]
    harvested_on: Mapped[date | None]
    yield_kg: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="active")
