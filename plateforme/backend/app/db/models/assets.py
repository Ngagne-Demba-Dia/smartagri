"""Équipements des exploitations et journal de maintenance (002_extensions.sql)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import EQUIPMENT_KINDS, EQUIPMENT_STATUSES, MAINTENANCE_KINDS, sql_in
from app.db.base import Base, CreatedAt, UUIDPk


class Equipment(UUIDPk, CreatedAt, Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(sql_in("kind", EQUIPMENT_KINDS), name="kind"),
        CheckConstraint(sql_in("status", EQUIPMENT_STATUSES), name="status"),
        CheckConstraint("flow_m3h IS NULL OR flow_m3h > 0", name="flow"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(200))
    serial: Mapped[str | None] = mapped_column(String(100))
    installed_at: Mapped[date | None]
    status: Mapped[str] = mapped_column(String(20), default="ok")
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), index=True)
    # Débit nominal d'une pompe (m³/h) : sert à estimer l'eau consommée dans les rapports.
    flow_m3h: Mapped[float | None] = mapped_column(Float)


class MaintenanceEvent(UUIDPk, CreatedAt, Base):
    __tablename__ = "maintenance_events"
    __table_args__ = (
        CheckConstraint(sql_in("kind", MAINTENANCE_KINDS), name="kind"),
        CheckConstraint("cost_fcfa IS NULL OR cost_fcfa >= 0", name="cost"),
        Index("ix_maintenance_events_equipment_ts", "equipment_id", "ts"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    equipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"))
    ts: Mapped[datetime]
    kind: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    cost_fcfa: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
