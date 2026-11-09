"""Cycles culturaux d'une parcelle (semis → récolte), éventuellement rattachés à une campagne."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.db.base import iso_utc
from app.db.models import Campaign, CropCycle, Field
from app.services import access

MAX_CYCLES_PER_FIELD = 200


def cycle_view(cycle: CropCycle) -> dict[str, Any]:
    return {"id": str(cycle.id), "organization_id": str(cycle.organization_id), "field_id": str(cycle.field_id),
            "campaign_id": str(cycle.campaign_id) if cycle.campaign_id else None, "crop": cycle.crop,
            "variety": cycle.variety, "planted_on": _iso_date(cycle.planted_on),
            "expected_harvest_on": _iso_date(cycle.expected_harvest_on),
            "harvested_on": _iso_date(cycle.harvested_on), "yield_kg": cycle.yield_kg, "status": cycle.status,
            "created_at": iso_utc(cycle.created_at)}


def _iso_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def get_cycle_for(session: Session, principal: access.Principal, cycle_id: str | uuid.UUID) -> CropCycle:
    cycle = session.get(CropCycle, access.parse_uuid(cycle_id, "Cycle cultural"))
    if cycle is None or cycle.organization_id not in principal.roles_by_org:
        raise not_found("Cycle cultural")
    return cycle


def campaign_for_cycle(session: Session, principal: access.Principal, organization_id: uuid.UUID,
                       campaign_id: uuid.UUID | None) -> uuid.UUID | None:
    """Campagne visible ET de la même organisation que la parcelle (sinon 404, sans fuite)."""
    if campaign_id is None:
        return None
    campaign = session.get(Campaign, campaign_id)
    if campaign is None or campaign.organization_id not in principal.roles_by_org \
            or campaign.organization_id != organization_id:
        raise not_found("Campagne")
    return campaign.id


def _check_dates(values: Mapping[str, Any]) -> None:
    planted = values.get("planted_on")
    for key in ("expected_harvest_on", "harvested_on"):
        later = values.get(key)
        if planted is not None and later is not None and later < planted:
            raise AppError("INVALID_DATES", "La récolte ne peut pas précéder le semis.", 400)


def list_cycles(session: Session, field: Field) -> list[CropCycle]:
    return list(session.scalars(
        select(CropCycle).where(CropCycle.field_id == field.id)
        .order_by(CropCycle.planted_on.desc(), CropCycle.created_at.desc()).limit(MAX_CYCLES_PER_FIELD)
    ).all())


def create_cycle(session: Session, principal: access.Principal, field: Field, data: Mapping[str, Any]) -> CropCycle:
    values = dict(data)
    values["campaign_id"] = campaign_for_cycle(session, principal, field.organization_id, values.get("campaign_id"))
    _check_dates(values)
    cycle = CropCycle(organization_id=field.organization_id, field_id=field.id, **values)
    session.add(cycle)
    session.flush()
    return cycle


def update_cycle(session: Session, principal: access.Principal, cycle: CropCycle,
                 changes: Mapping[str, Any]) -> CropCycle:
    """Mise à jour partielle (statut, récolte, rendement, campagne) ; seules les clés fournies changent."""
    values = dict(changes)
    if "campaign_id" in values:
        values["campaign_id"] = campaign_for_cycle(session, principal, cycle.organization_id, values["campaign_id"])
    merged = {key: getattr(cycle, key) for key in ("planted_on", "expected_harvest_on", "harvested_on")}
    merged.update({key: value for key, value in values.items() if key in merged})
    _check_dates(merged)
    if values.get("status") == "harvested" and values.get("harvested_on") is None and cycle.harvested_on is None:
        raise AppError("HARVEST_DATE_REQUIRED", "Indiquez la date de récolte (harvested_on).", 400)
    for key, value in values.items():
        setattr(cycle, key, value)
    session.flush()
    return cycle
