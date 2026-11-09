"""Campagnes agricoles et prévisions de rendement (002_extensions.sql)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import CAMPAIGN_STATUSES, SEASONS, sql_in
from app.db.base import Base, CreatedAt, UUIDPk


class Campaign(UUIDPk, CreatedAt, Base):
    """Campagne (ex. « Contre-saison 2026-27 ») regroupant des cycles culturaux."""

    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(sql_in("season", SEASONS), name="season"),
        CheckConstraint(sql_in("status", CAMPAIGN_STATUSES), name="status"),
        CheckConstraint("end_date >= start_date", name="dates"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    season: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date]
    end_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(10), default="planned")


class YieldForecast(UUIDPk, CreatedAt, Base):
    """Prévision de rendement (t/ha) d'un cycle cultural, avec intervalle p10–p90."""

    __tablename__ = "yield_forecasts"
    __table_args__ = (
        CheckConstraint("predicted_t_ha >= 0", name="predicted"),
        CheckConstraint("p10 IS NULL OR p10 <= predicted_t_ha", name="p10"),
        CheckConstraint("p90 IS NULL OR p90 >= predicted_t_ha", name="p90"),
        Index("ix_yield_forecasts_cycle_created", "crop_cycle_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    crop_cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crop_cycles.id", ondelete="CASCADE"))
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(64))
    predicted_t_ha: Mapped[float] = mapped_column(Float)
    p10: Mapped[float | None] = mapped_column(Float)
    p90: Mapped[float | None] = mapped_column(Float)
