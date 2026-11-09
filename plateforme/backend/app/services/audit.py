"""Journal d'audit en ajout seul (actions sensibles : connexion, kits, seuils, alertes, assistant)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog


@dataclass(frozen=True)
class RequestMeta:
    """Contexte HTTP utile à l'audit (pas de corps de requête, jamais de secret)."""

    ip: str | None = None
    request_id: str | None = None


def record_audit(
    session: Session,
    action: str,
    *,
    actor_user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    meta: RequestMeta | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Ajoute une ligne au journal ; elle est validée avec la transaction de l'appelant."""
    request = meta or RequestMeta()
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            ip=request.ip,
            request_id=request.request_id,
            details=details,
        )
    )
