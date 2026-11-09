"""Registre des modèles servis par la couche d'inférence (002_extensions.sql)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import MODEL_SOURCES, MODEL_STAGES, sql_in
from app.db.base import Base, CreatedAt, JSONType, UUIDPk


class ModelRegistry(UUIDPk, CreatedAt, Base):
    """Modèle entraîné (agriml ou OctOpus). L'empreinte SHA-256 du paquet est vérifiée à chaque chargement.

    `features` liste les colonnes d'entrée attendues : seules ces colonnes quittent la plateforme
    lorsqu'un lot est envoyé à OctOpus (aucune donnée personnelle).
    """

    __tablename__ = "model_registry"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_registry_name_version"),
        CheckConstraint(sql_in("stage", MODEL_STAGES), name="stage"),
        CheckConstraint(sql_in("source", MODEL_SOURCES), name="source"),
    )

    name: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(12), default="none")
    uri: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(10))
    octopus_run_id: Mapped[str | None] = mapped_column(String(100))
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    proof: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    features: Mapped[list[str] | None] = mapped_column(JSONType)
