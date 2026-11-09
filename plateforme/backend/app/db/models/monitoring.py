"""Mesures (hypertable TimescaleDB), alertes, images, diagnostics, recommandations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    ALERT_SEVERITIES,
    ALERT_STATUSES,
    DIAGNOSIS_LABELS,
    RECOMMENDATION_KINDS,
    TELEMETRY_SOURCES,
    sql_in,
)
from app.db.base import Base, CreatedAt, JSONType, UUIDPk, utcnow


class Measurement(Base):
    """Point telemetry.v1 ; clé (device_id, ts) = idempotence."""

    __tablename__ = "measurements"
    __table_args__ = (CheckConstraint(sql_in("source", TELEMETRY_SOURCES), name="source"),)

    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    ts: Mapped[datetime] = mapped_column(primary_key=True)
    received_at: Mapped[datetime] = mapped_column(default=utcnow)
    source: Mapped[str] = mapped_column(String(10))
    seq: Mapped[int | None]
    fw: Mapped[str | None] = mapped_column(String(32))
    soil_moisture_pct: Mapped[float | None] = mapped_column(Float)
    air_temp_c: Mapped[float | None] = mapped_column(Float)
    air_humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    n_mgkg: Mapped[int | None]
    p_mgkg: Mapped[int | None]
    k_mgkg: Mapped[int | None]
    pump_on: Mapped[bool | None]
    pump_fault: Mapped[bool | None]
    soil_sensor_ok: Mapped[bool | None]
    bme_ok: Mapped[bool | None]
    npk_ok: Mapped[bool | None]
    alert_fertilizer: Mapped[bool | None]
    alert_plant: Mapped[bool | None]
    threshold_start_pct: Mapped[int | None]
    threshold_stop_pct: Mapped[int | None]


class Alert(UUIDPk, CreatedAt, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(sql_in("severity", ALERT_SEVERITIES), name="severity"),
        CheckConstraint(sql_in("status", ALERT_STATUSES), name="status"),
        Index("ix_alerts_org_status", "organization_id", "status"),
        # Anti-rebond : une seule alerte non résolue par (kit, règle).
        Index(
            "uq_alerts_device_rule_active",
            "device_id",
            "rule",
            unique=True,
            postgresql_where=text("status <> 'resolved'"),
            sqlite_where=text("status <> 'resolved'"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    field_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fields.id", ondelete="SET NULL"))
    rule: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(15), default="open")
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    acknowledged_at: Mapped[datetime | None]
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None]


class Image(UUIDPk, CreatedAt, Base):
    __tablename__ = "images"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))
    field_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fields.id", ondelete="SET NULL"))
    storage_key: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(50))
    sha256: Mapped[str | None] = mapped_column(String(64))
    captured_at: Mapped[datetime]


class Diagnosis(UUIDPk, CreatedAt, Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint(sql_in("label", DIAGNOSIS_LABELS), name="label"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),
        Index("ix_diagnoses_device_captured", "device_id", "captured_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"))
    label: Mapped[str] = mapped_column(String(10))
    disease_code: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(64))
    captured_at: Mapped[datetime]


class Recommendation(UUIDPk, CreatedAt, Base):
    __tablename__ = "recommendations"
    __table_args__ = (CheckConstraint(sql_in("kind", RECOMMENDATION_KINDS), name="kind"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType)
    engine_version: Mapped[str] = mapped_column(String(32))
    feedback: Mapped[str | None] = mapped_column(String(20))
