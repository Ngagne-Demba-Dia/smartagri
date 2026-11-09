"""Contrôle d'accès multi-organisation.

Règle unique : une ressource d'une autre organisation est « introuvable » (404), jamais « interdite »
(403), pour ne pas révéler son existence. Le 403 est réservé au cas où la ressource est visible mais
où le rôle de l'utilisateur ne permet pas l'action demandée.

Ces fonctions servent à l'API **et** aux outils de l'assistant : un identifiant fourni par le client
ou par le modèle de langage passe toujours par elles.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import SERIAL_PATTERN
from app.core.errors import AppError, forbidden, not_found
from app.db.models import Alert, Device, Farm, Field

_SERIAL_RE = re.compile(SERIAL_PATTERN)


@dataclass(frozen=True)
class Principal:
    """Utilisateur authentifié et ses rôles par organisation (lecture seule)."""

    user_id: uuid.UUID
    roles_by_org: Mapping[uuid.UUID, str]

    @classmethod
    def build(cls, user_id: uuid.UUID, roles: Mapping[uuid.UUID, str]) -> Principal:
        return cls(user_id=user_id, roles_by_org=MappingProxyType(dict(roles)))

    @property
    def org_ids(self) -> tuple[uuid.UUID, ...]:
        return tuple(self.roles_by_org)

    def role_in(self, org_id: uuid.UUID) -> str | None:
        return self.roles_by_org.get(org_id)

    def has_role(self, org_id: uuid.UUID, roles: Collection[str]) -> bool:
        return self.roles_by_org.get(org_id) in roles


def parse_uuid(value: str | uuid.UUID, resource: str = "Ressource") -> uuid.UUID:
    """Un identifiant mal formé est traité comme introuvable (même réponse qu'un identifiant étranger)."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise not_found(resource) from exc


def require_role(principal: Principal, org_id: uuid.UUID, roles: Collection[str]) -> None:
    if not principal.has_role(org_id, roles):
        raise forbidden()


def get_device_for(session: Session, principal: Principal, ref: str | uuid.UUID) -> Device:
    """Kit par UUID ou numéro de série (SA92-NNNNNN), limité aux organisations de l'utilisateur."""
    if not principal.org_ids:
        raise not_found("Kit")
    ref_text = str(ref).strip()
    query = select(Device).where(Device.organization_id.in_(principal.org_ids))
    if _SERIAL_RE.match(ref_text):
        query = query.where(Device.serial == ref_text)
    else:
        query = query.where(Device.id == parse_uuid(ref_text, "Kit"))
    device = session.scalars(query).first()
    if device is None:
        raise not_found("Kit")
    return device


def get_farm_for(session: Session, principal: Principal, farm_id: str | uuid.UUID) -> Farm:
    farm = session.get(Farm, parse_uuid(farm_id, "Exploitation"))
    if farm is None or farm.organization_id not in principal.roles_by_org:
        raise not_found("Exploitation")
    return farm


def get_field_for(session: Session, principal: Principal, field_id: str | uuid.UUID) -> Field:
    field = session.get(Field, parse_uuid(field_id, "Parcelle"))
    if field is None or field.organization_id not in principal.roles_by_org:
        raise not_found("Parcelle")
    return field


def get_alert_for(session: Session, principal: Principal, alert_id: str | uuid.UUID) -> Alert:
    alert = session.get(Alert, parse_uuid(alert_id, "Alerte"))
    if alert is None or alert.organization_id not in principal.roles_by_org:
        raise not_found("Alerte")
    return alert


def resolve_org_for_write(
    principal: Principal, requested: uuid.UUID | None, roles: Collection[str]
) -> uuid.UUID:
    """Organisation cible d'une création.

    - organisation demandée dont l'utilisateur n'est pas membre : 404 ;
    - membre sans le rôle requis : 403 ;
    - aucune organisation demandée et plusieurs possibles : 400 ORGANIZATION_REQUIRED.
    """
    if requested is not None:
        if requested not in principal.roles_by_org:
            raise not_found("Organisation")
        require_role(principal, requested, roles)
        return requested
    allowed = [org_id for org_id, role in principal.roles_by_org.items() if role in roles]
    if len(allowed) == 1:
        return allowed[0]
    if not allowed:
        raise forbidden()
    raise AppError("ORGANIZATION_REQUIRED", "Précisez l'organisation (organization_id).", 400)
