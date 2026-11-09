"""Cache des prévisions météo (002_extensions.sql) ; donnée publique, non rattachée à une organisation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, UUIDPk


class WeatherCache(UUIDPk, Base):
    """Réponse météo par point arrondi au centième de degré (≈ 1 km), fournisseur et horizon."""

    __tablename__ = "weather_cache"
    __table_args__ = (UniqueConstraint("provider", "latitude", "longitude", "days", name="uq_weather_cache_key"),)

    provider: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    days: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType)
