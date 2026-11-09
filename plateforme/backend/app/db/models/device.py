"""Kits Smart Agri92 et seuils d'irrigation (désirés côté plateforme, rapportés par le kit)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import DEVICE_STATUSES, SYNC_STATUSES, sql_in
from app.db.base import Base, CreatedAt, UUIDPk, utcnow

# Même règle que le firmware v1.1 (seuilsValides) et que services/agronomy.validate_thresholds.
THRESHOLD_RULE = "desired_start_pct >= 0 AND desired_start_pct + 5 <= desired_stop_pct AND desired_stop_pct <= 100"


class Device(UUIDPk, CreatedAt, Base):
    __tablename__ = "devices"
    __table_args__ = (CheckConstraint(sql_in("status", DEVICE_STATUSES), name="status"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fields.id", ondelete="SET NULL"), index=True)
    serial: Mapped[str] = mapped_column(String(11), unique=True)
    name: Mapped[str | None] = mapped_column(String(200))
    firmware_version: Mapped[str | None] = mapped_column(String(32))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_seen_at: Mapped[datetime | None]


class DeviceThreshold(Base):
    __tablename__ = "device_thresholds"
    __table_args__ = (
        CheckConstraint(THRESHOLD_RULE, name="desired_rule"),
        CheckConstraint(sql_in("sync_status", SYNC_STATUSES), name="sync_status"),
    )

    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    desired_start_pct: Mapped[int]
    desired_stop_pct: Mapped[int]
    reported_start_pct: Mapped[int | None]
    reported_stop_pct: Mapped[int | None]
    sync_status: Mapped[str] = mapped_column(String(10), default="pending")
    command_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
