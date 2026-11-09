"""Campagnes agricoles (saison sèche / hivernage) et leur bilan."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_now, get_pagination, get_principal, get_request_meta, get_session
from app.core.constants import CAMPAIGN_WRITERS
from app.core.envelope import ok, page_meta
from app.schemas.planning import CampaignIn, CampaignPatch
from app.services import access, campaigns
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["campaigns"])


@router.get("/campaigns")
def list_campaigns(status: Literal["planned", "active", "closed"] | None = Query(None),
                   principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
                   paging: Pagination = Depends(get_pagination)) -> dict[str, Any]:
    rows, total = campaigns.list_campaigns(session, principal, status, paging.page, paging.limit)
    return ok([campaigns.campaign_view(row) for row in rows], page_meta(paging.page, paging.limit, total))


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn, principal: Principal = Depends(get_principal),
                    session: Session = Depends(get_session),
                    meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    org_id = access.resolve_org_for_write(principal, body.organization_id, CAMPAIGN_WRITERS)
    campaign = campaigns.create_campaign(session, org_id, body.values())
    record_audit(session, "campaign.create", actor_user_id=principal.user_id, organization_id=org_id,
                 target_type="campaign", target_id=campaign.id, meta=meta)
    session.commit()
    return ok(campaigns.campaign_view(campaign))


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str, principal: Principal = Depends(get_principal),
                 session: Session = Depends(get_session)) -> dict[str, Any]:
    return ok(campaigns.campaign_view(campaigns.get_campaign_for(session, principal, campaign_id)))


@router.patch("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, body: CampaignPatch, principal: Principal = Depends(get_principal),
                    session: Session = Depends(get_session),
                    meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    campaign = campaigns.get_campaign_for(session, principal, campaign_id)
    access.require_role(principal, campaign.organization_id, CAMPAIGN_WRITERS)
    changes = body.changes()
    campaigns.update_campaign(session, campaign, changes)
    record_audit(session, "campaign.update", actor_user_id=principal.user_id,
                 organization_id=campaign.organization_id, target_type="campaign", target_id=campaign.id,
                 meta=meta, details={"fields": sorted(changes)})
    session.commit()
    return ok(campaigns.campaign_view(campaign))


@router.get("/campaigns/{campaign_id}/summary")
def campaign_summary(campaign_id: str, principal: Principal = Depends(get_principal),
                     session: Session = Depends(get_session), now: datetime = Depends(get_now)) -> dict[str, Any]:
    campaign = campaigns.get_campaign_for(session, principal, campaign_id)
    return ok(campaigns.campaign_summary(session, campaign, now))
