"""Exploitations, parcelles et carte (FeatureCollection GeoJSON)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_pagination, get_principal, get_request_meta, get_session
from app.core.constants import FARM_WRITERS
from app.core.envelope import ok, page_meta
from app.db.models import Farm, Field
from app.schemas.farms import FarmIn, FieldIn
from app.services import access, farms
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["farms"])


@router.get("/farms")
def list_farms(principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
               paging: Pagination = Depends(get_pagination)) -> dict[str, Any]:
    condition = Farm.organization_id.in_(principal.org_ids)
    total = session.scalar(select(func.count()).select_from(Farm).where(condition)) or 0
    rows = session.scalars(
        select(Farm).where(condition).order_by(Farm.name)
        .offset((paging.page - 1) * paging.limit).limit(paging.limit)
    ).all()
    return ok([farms.farm_view(farm) for farm in rows], page_meta(paging.page, paging.limit, int(total)))


@router.post("/farms", status_code=201)
def create_farm(body: FarmIn, principal: Principal = Depends(get_principal),
                session: Session = Depends(get_session),
                meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    org_id = access.resolve_org_for_write(principal, body.organization_id, FARM_WRITERS)
    farm = farms.create_farm(session, org_id, body.values())
    record_audit(session, "farm.create", actor_user_id=principal.user_id, organization_id=org_id,
                 target_type="farm", target_id=farm.id, meta=meta)
    session.commit()
    return ok(farms.farm_view(farm))


@router.get("/farms/{farm_id}/fields")
def list_fields(farm_id: str, principal: Principal = Depends(get_principal),
                session: Session = Depends(get_session),
                paging: Pagination = Depends(get_pagination)) -> dict[str, Any]:
    farm = access.get_farm_for(session, principal, farm_id)
    total = session.scalar(select(func.count()).select_from(Field).where(Field.farm_id == farm.id)) or 0
    rows = session.scalars(
        select(Field).where(Field.farm_id == farm.id).order_by(Field.name)
        .offset((paging.page - 1) * paging.limit).limit(paging.limit)
    ).all()
    return ok([farms.field_view(field) for field in rows], page_meta(paging.page, paging.limit, int(total)))


@router.post("/farms/{farm_id}/fields", status_code=201)
def create_field(farm_id: str, body: FieldIn, principal: Principal = Depends(get_principal),
                 session: Session = Depends(get_session),
                 meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    farm = access.get_farm_for(session, principal, farm_id)
    access.require_role(principal, farm.organization_id, FARM_WRITERS)
    field = farms.create_field(session, farm, body.values())
    record_audit(session, "field.create", actor_user_id=principal.user_id, organization_id=farm.organization_id,
                 target_type="field", target_id=field.id, meta=meta)
    session.commit()
    return ok(farms.field_view(field))


@router.get("/farms/{farm_id}/map")
def farm_map(farm_id: str, principal: Principal = Depends(get_principal),
             session: Session = Depends(get_session)) -> dict[str, Any]:
    farm = access.get_farm_for(session, principal, farm_id)
    return ok(farms.farm_map(session, farm))
