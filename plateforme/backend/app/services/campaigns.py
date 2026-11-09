"""Campagnes agricoles : création, mise à jour et bilan (parcelles, cultures, eau, alertes, rendement)."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.db.base import iso_utc
from app.db.models import Campaign, CropCycle, Device, Field, YieldForecast
from app.services import access, kpis


def campaign_view(campaign: Campaign) -> dict[str, Any]:
    return {"id": str(campaign.id), "organization_id": str(campaign.organization_id), "name": campaign.name,
            "season": campaign.season, "start_date": campaign.start_date.isoformat(),
            "end_date": campaign.end_date.isoformat(), "status": campaign.status,
            "created_at": iso_utc(campaign.created_at)}


def get_campaign_for(session: Session, principal: access.Principal, campaign_id: str | uuid.UUID) -> Campaign:
    campaign = session.get(Campaign, access.parse_uuid(campaign_id, "Campagne"))
    if campaign is None or campaign.organization_id not in principal.roles_by_org:
        raise not_found("Campagne")
    return campaign


def _check_dates(start: date, end: date) -> None:
    if end < start:
        raise AppError("INVALID_DATES", "La fin de campagne ne peut pas précéder son début.", 400)


def list_campaigns(session: Session, principal: access.Principal, status: str | None, page: int,
                   limit: int) -> tuple[list[Campaign], int]:
    conditions = [Campaign.organization_id.in_(principal.org_ids)]
    if status:
        conditions.append(Campaign.status == status)
    total = session.scalar(select(func.count()).select_from(Campaign).where(*conditions)) or 0
    rows = session.scalars(
        select(Campaign).where(*conditions).order_by(Campaign.start_date.desc(), Campaign.name)
        .offset((page - 1) * limit).limit(limit)
    ).all()
    return list(rows), int(total)


def create_campaign(session: Session, organization_id: uuid.UUID, data: Mapping[str, Any]) -> Campaign:
    _check_dates(data["start_date"], data["end_date"])
    campaign = Campaign(organization_id=organization_id, **data)
    session.add(campaign)
    session.flush()
    return campaign


def update_campaign(session: Session, campaign: Campaign, changes: Mapping[str, Any]) -> Campaign:
    _check_dates(changes.get("start_date", campaign.start_date), changes.get("end_date", campaign.end_date))
    for key, value in changes.items():
        setattr(campaign, key, value)
    session.flush()
    return campaign


def campaign_period(campaign: Campaign, now: datetime) -> tuple[datetime, datetime]:
    """[début 00:00 UTC, lendemain de la fin 00:00 UTC[, borné à maintenant."""
    start = datetime.combine(campaign.start_date, time.min, tzinfo=UTC)
    end = datetime.combine(campaign.end_date + timedelta(days=1), time.min, tzinfo=UTC)
    return start, max(start, min(end, now))


def _latest_forecasts(session: Session, cycle_ids: list[uuid.UUID]) -> dict[uuid.UUID, YieldForecast]:
    rows = session.scalars(
        select(YieldForecast).where(YieldForecast.crop_cycle_id.in_(cycle_ids))
        .order_by(YieldForecast.created_at.desc())
    ).all()
    latest: dict[uuid.UUID, YieldForecast] = {}
    for row in rows:
        latest.setdefault(row.crop_cycle_id, row)
    return latest


def actual_t_ha(cycle: CropCycle, area_ha: float | None) -> float | None:
    if cycle.yield_kg is None or not area_ha:
        return None
    return round(cycle.yield_kg / area_ha / 1000.0, 2)


def _yield_rows(session: Session, cycles: Sequence[CropCycle],
                fields: Mapping[uuid.UUID, Field]) -> list[dict[str, Any]]:
    forecasts = _latest_forecasts(session, [cycle.id for cycle in cycles])
    rows = []
    for cycle in cycles:
        forecast = forecasts.get(cycle.id)
        area = fields[cycle.field_id].area_ha if cycle.field_id in fields else None
        rows.append({"crop_cycle_id": str(cycle.id), "field_id": str(cycle.field_id), "crop": cycle.crop,
                     "status": cycle.status, "area_ha": area,
                     "forecast_t_ha": forecast.predicted_t_ha if forecast else None,
                     "forecast_p10": forecast.p10 if forecast else None,
                     "forecast_p90": forecast.p90 if forecast else None,
                     "forecast_model": f"{forecast.model_name}:{forecast.model_version}" if forecast else None,
                     "actual_t_ha": actual_t_ha(cycle, area)})
    return rows


def _tonnes(rows: Sequence[Mapping[str, Any]], key: str) -> float | None:
    values = [row[key] * row["area_ha"] for row in rows if row[key] is not None and row["area_ha"]]
    return round(sum(values), 2) if values else None


def campaign_summary(session: Session, campaign: Campaign, now: datetime) -> dict[str, Any]:
    cycles = session.scalars(select(CropCycle).where(CropCycle.campaign_id == campaign.id)).all()
    field_ids = tuple(sorted({cycle.field_id for cycle in cycles}, key=str))
    fields = {f.id: f for f in session.scalars(select(Field).where(Field.id.in_(field_ids))).all()}
    device_ids = tuple(session.scalars(select(Device.id).where(Device.field_id.in_(field_ids))).all())
    start, end = campaign_period(campaign, now)
    scope = kpis.ScopeFilter(campaign.organization_id, field_ids, device_ids)
    indicators = kpis.compute_kpis(session, scope, start, end, now)
    yields = _yield_rows(session, cycles, fields)
    return {
        "campaign": campaign_view(campaign),
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "fields": len(field_ids),
        "area_ha": round(sum(f.area_ha or 0.0 for f in fields.values()), 2),
        "crops": dict(Counter(cycle.crop for cycle in cycles)),
        "water_m3": indicators["water_m3"],
        "devices_without_flow": indicators["devices_without_flow"],
        "irrigation_events": indicators["irrigation_events"],
        "alerts_by_rule": indicators["alerts_by_rule"],
        "alerts_total": sum(indicators["alerts_by_rule"].values()),
        "yield": {"cycles": yields, "forecast_tonnes": _tonnes(yields, "forecast_t_ha"),
                  "actual_tonnes": _tonnes(yields, "actual_t_ha")},
    }
