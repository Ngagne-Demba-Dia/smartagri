"""Équipements des exploitations (pompes, cuves, panneaux, batteries…) et journal de maintenance."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.db.base import as_utc, iso_utc
from app.db.models import Equipment, Farm, Field, MaintenanceEvent
from app.services import access

MAX_EVENTS = 500


def equipment_view(item: Equipment) -> dict[str, Any]:
    return {"id": str(item.id), "organization_id": str(item.organization_id), "farm_id": str(item.farm_id),
            "kind": item.kind, "label": item.label, "serial": item.serial,
            "installed_at": item.installed_at.isoformat() if item.installed_at else None, "status": item.status,
            "device_id": str(item.device_id) if item.device_id else None, "flow_m3h": item.flow_m3h,
            "created_at": iso_utc(item.created_at)}


def maintenance_view(event: MaintenanceEvent) -> dict[str, Any]:
    return {"id": str(event.id), "equipment_id": str(event.equipment_id), "ts": iso_utc(event.ts),
            "kind": event.kind, "notes": event.notes, "cost_fcfa": event.cost_fcfa,
            "created_by": str(event.created_by) if event.created_by else None,
            "created_at": iso_utc(event.created_at)}


def get_equipment_for(session: Session, principal: access.Principal, equipment_id: str | uuid.UUID) -> Equipment:
    item = session.get(Equipment, access.parse_uuid(equipment_id, "Équipement"))
    if item is None or item.organization_id not in principal.roles_by_org:
        raise not_found("Équipement")
    return item


def _device_on_farm(session: Session, principal: access.Principal, farm: Farm,
                    device_ref: str | None) -> uuid.UUID | None:
    """Kit lié : visible par l'utilisateur et installé sur une parcelle de la même exploitation."""
    if device_ref is None:
        return None
    device = access.get_device_for(session, principal, device_ref)
    field = session.get(Field, device.field_id) if device.field_id else None
    if device.organization_id != farm.organization_id or field is None or field.farm_id != farm.id:
        raise AppError("DEVICE_NOT_ON_FARM", "Le kit doit être installé sur une parcelle de cette exploitation.", 400)
    return device.id


def list_equipment(session: Session, principal: access.Principal, filters: Mapping[str, Any], page: int,
                   limit: int) -> tuple[list[Equipment], int]:
    conditions = [Equipment.organization_id.in_(principal.org_ids)]
    if filters.get("farm_id") is not None:
        conditions.append(Equipment.farm_id == access.get_farm_for(session, principal, filters["farm_id"]).id)
    for key in ("kind", "status"):
        if filters.get(key):
            conditions.append(getattr(Equipment, key) == filters[key])
    total = session.scalar(select(func.count()).select_from(Equipment).where(*conditions)) or 0
    rows = session.scalars(
        select(Equipment).where(*conditions).order_by(Equipment.kind, Equipment.label)
        .offset((page - 1) * limit).limit(limit)
    ).all()
    return list(rows), int(total)


def create_equipment(session: Session, principal: access.Principal, farm: Farm, data: Mapping[str, Any]) -> Equipment:
    values = dict(data)
    values["device_id"] = _device_on_farm(session, principal, farm, values.pop("device", None))
    item = Equipment(organization_id=farm.organization_id, farm_id=farm.id, **values)
    session.add(item)
    session.flush()
    return item


def update_equipment(session: Session, principal: access.Principal, item: Equipment,
                     changes: Mapping[str, Any]) -> Equipment:
    values = dict(changes)
    if "device" in values:
        farm = session.get(Farm, item.farm_id)
        values["device_id"] = _device_on_farm(session, principal, farm, values.pop("device")) if farm else None
    for key, value in values.items():
        setattr(item, key, value)
    session.flush()
    return item


def list_maintenance(session: Session, item: Equipment) -> list[MaintenanceEvent]:
    return list(session.scalars(
        select(MaintenanceEvent).where(MaintenanceEvent.equipment_id == item.id)
        .order_by(MaintenanceEvent.ts.desc()).limit(MAX_EVENTS)
    ).all())


def add_maintenance(session: Session, item: Equipment, data: Mapping[str, Any], user_id: uuid.UUID,
                    now: datetime) -> MaintenanceEvent:
    values = dict(data)
    values["ts"] = as_utc(values.get("ts")) or now
    if values["ts"] > now:
        raise AppError("INVALID_DATES", "Une intervention ne peut pas être datée dans le futur.", 400)
    event = MaintenanceEvent(organization_id=item.organization_id, equipment_id=item.id, created_by=user_id,
                             **values)
    session.add(event)
    session.flush()
    return event
