"""Alertes : liste filtrée et acquittement."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_now, get_pagination, get_principal, get_request_meta, get_session
from app.core.constants import ALERT_ACKERS
from app.core.envelope import ok, page_meta
from app.db.models import Alert
from app.services import access, alerting
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def list_alerts(status: Literal["open", "acknowledged", "resolved"] | None = Query(None),
                device_id: str | None = Query(None, max_length=64),
                principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
                paging: Pagination = Depends(get_pagination)) -> dict[str, Any]:
    conditions = [Alert.organization_id.in_(principal.org_ids)]
    if status:
        conditions.append(Alert.status == status)
    if device_id:
        conditions.append(Alert.device_id == access.get_device_for(session, principal, device_id).id)
    total = session.scalar(select(func.count()).select_from(Alert).where(*conditions)) or 0
    rows = session.scalars(
        select(Alert).where(*conditions).order_by(Alert.created_at.desc())
        .offset((paging.page - 1) * paging.limit).limit(paging.limit)
    ).all()
    return ok([alerting.alert_view(alert) for alert in rows], page_meta(paging.page, paging.limit, int(total)))


@router.post("/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str, principal: Principal = Depends(get_principal),
                      session: Session = Depends(get_session), now: datetime = Depends(get_now),
                      meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    alert = access.get_alert_for(session, principal, alert_id)
    access.require_role(principal, alert.organization_id, ALERT_ACKERS)
    alerting.acknowledge(alert, principal.user_id, now)
    record_audit(session, "alert.ack", actor_user_id=principal.user_id, organization_id=alert.organization_id,
                 target_type="alert", target_id=alert.id, meta=meta)
    session.commit()
    return ok(alerting.alert_view(alert))
