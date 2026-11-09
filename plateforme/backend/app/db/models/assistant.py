"""Conversations de l'assistant agronomique (texte utilisateur/assistant uniquement)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import LOCALES, MESSAGE_ROLES, sql_in
from app.db.base import Base, CreatedAt, JSONType, UUIDPk, utcnow


class Conversation(UUIDPk, CreatedAt, Base):
    __tablename__ = "conversations"
    __table_args__ = (CheckConstraint(sql_in("locale", LOCALES), name="locale"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(2), default="fr")
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class Message(UUIDPk, CreatedAt, Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint(sql_in("role", MESSAGE_ROLES), name="role"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(64))
    stop_reason: Mapped[str | None] = mapped_column(String(32))
    tools_used: Mapped[list[Any] | None] = mapped_column(JSONType)
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cache_read_tokens: Mapped[int | None]
