"""Équipements des exploitations et journal de maintenance."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_now, get_pagination, get_principal, get_request_meta, get_session
from app.core.constants import EQUIPMENT_WRITERS, MAINTENANCE_WRITERS
from app.core.envelope import ok, page_meta
from app.schemas.planning import EquipmentIn, EquipmentKind, EquipmentPatch, MaintenanceIn
from app.services import access, equipment
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["equipment"])


@router.get("/equipment")
def list_equipment(farm_id: uuid.UUID | None = Query(None), kind: EquipmentKind | None = Query(None),
                   status: Literal["ok", "maintenance", "out_of_service"] | None = Query(None),
                   principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
                   paging: Pagination = Depends(get_pagination)) -> dict[str, Any]:
    filters = {"farm_id": farm_id, "kind": kind, "status": status}
    rows, total = equipment.list_equipment(session, principal, filters, paging.page, paging.limit)
    return ok([equipment.equipment_view(item) for item in rows], page_meta(paging.page, paging.limit, total))


@router.post("/equipment", status_code=201)
def create_equipment(body: EquipmentIn, principal: Principal = Depends(get_principal),
                     session: Session = Depends(get_session),
                     meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    farm = access.get_farm_for(session, principal, body.farm_id)
    access.require_role(principal, farm.organization_id, EQUIPMENT_WRITERS)
    item = equipment.create_equipment(session, principal, farm, body.values())
    record_audit(session, "equipment.create", actor_user_id=principal.user_id, organization_id=item.organization_id,
                 target_type="equipment", target_id=item.id, meta=meta)
    session.commit()
    return ok(equipment.equipment_view(item))


@router.patch("/equipment/{equipment_id}")
def update_equipment(equipment_id: str, body: EquipmentPatch, principal: Principal = Depends(get_principal),
                     session: Session = Depends(get_session),
                     meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    item = equipment.get_equipment_for(session, principal, equipment_id)
    access.require_role(principal, item.organization_id, EQUIPMENT_WRITERS)
    changes = body.changes()
    equipment.update_equipment(session, principal, item, changes)
    record_audit(session, "equipment.update", actor_user_id=principal.user_id, organization_id=item.organization_id,
                 target_type="equipment", target_id=item.id, meta=meta, details={"fields": sorted(changes)})
    session.commit()
    return ok(equipment.equipment_view(item))


@router.get("/equipment/{equipment_id}/maintenance")
def list_maintenance(equipment_id: str, principal: Principal = Depends(get_principal),
                     session: Session = Depends(get_session)) -> dict[str, Any]:
    item = equipment.get_equipment_for(session, principal, equipment_id)
    return ok([equipment.maintenance_view(event) for event in equipment.list_maintenance(session, item)])


@router.post("/equipment/{equipment_id}/maintenance", status_code=201)
def add_maintenance(equipment_id: str, body: MaintenanceIn, principal: Principal = Depends(get_principal),
                    session: Session = Depends(get_session), now: datetime = Depends(get_now),
                    meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    item = equipment.get_equipment_for(session, principal, equipment_id)
    access.require_role(principal, item.organization_id, MAINTENANCE_WRITERS)
    event = equipment.add_maintenance(session, item, body.values(), principal.user_id, now)
    record_audit(session, "maintenance.create", actor_user_id=principal.user_id,
                 organization_id=item.organization_id, target_type="maintenance_event", target_id=event.id,
                 meta=meta)
    session.commit()
    return ok(equipment.maintenance_view(event))
