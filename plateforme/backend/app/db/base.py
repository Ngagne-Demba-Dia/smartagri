"""Base déclarative SQLAlchemy 2.0 et types portables PostgreSQL / SQLite."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, MetaData, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# JSONB sous PostgreSQL, JSON (texte) sous SQLite.
JSONType = JSON().with_variant(JSONB(), "postgresql")

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite perd le fuseau : on le rattache (toutes les dates sont stockées en UTC)."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def iso_utc(value: datetime | None) -> str | None:
    """Horodatage ISO 8601 en UTC (None conservé) pour les réponses JSON."""
    utc = as_utc(value)
    return utc.isoformat() if utc else None


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: dict[Any, Any] = {
        datetime: DateTime(timezone=True),
        uuid.UUID: Uuid(),
        dict[str, Any]: JSONType,
    }


class UUIDPk:
    """Clé primaire UUID générée côté application (portable)."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
