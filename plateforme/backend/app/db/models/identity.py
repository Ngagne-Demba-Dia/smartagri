"""Identité : organisations, utilisateurs, appartenances, jetons de rafraîchissement, journal d'audit."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import LOCALES, ORG_KINDS, ROLES, sql_in
from app.db.base import Base, CreatedAt, JSONType, UUIDPk, utcnow


class Organization(UUIDPk, CreatedAt, Base):
    __tablename__ = "organizations"
    __table_args__ = (CheckConstraint(sql_in("kind", ORG_KINDS), name="kind"),)

    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="cooperative")
    region: Mapped[str | None] = mapped_column(String(100))


class User(UUIDPk, CreatedAt, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("phone IS NOT NULL OR email IS NOT NULL", name="contact"),
        CheckConstraint(sql_in("locale", LOCALES), name="locale"),
    )

    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(2), default="fr")
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None]


class Membership(UUIDPk, CreatedAt, Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
        CheckConstraint(sql_in("role", ROLES), name="role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))


class RefreshToken(CreatedAt, Base):
    """Jeton de rafraîchissement : seule l'empreinte SHA-256 est stockée ; `id` = jti."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    replaced_by: Mapped[uuid.UUID | None]


class AuditLog(Base):
    """Journal en ajout seul (UPDATE/DELETE bloqués par trigger sous PostgreSQL)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
