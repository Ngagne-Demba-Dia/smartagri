"""Diagnostics de vision et retours des producteurs sur les recommandations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_now, get_principal, get_request_meta, get_session, get_settings
from app.core.config import Settings
from app.core.constants import DIAGNOSIS_WRITERS, FEEDBACK_WRITERS
from app.core.envelope import ok
from app.schemas.monitoring import DiagnosisAnalyzeIn, DiagnosisIn, FeedbackIn
from app.services import access, alerting, diagnoses, recommendations
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["diagnoses"])


@router.post("/diagnoses", status_code=201)
def create_diagnosis(body: DiagnosisIn, principal: Principal = Depends(get_principal),
                     session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
                     now: datetime = Depends(get_now),
                     meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    device = access.get_device_for(session, principal, body.device)
    access.require_role(principal, device.organization_id, DIAGNOSIS_WRITERS)
    row, alert = diagnoses.record_diagnosis(session, settings, device, body.values(), now)
    record_audit(session, "diagnosis.create", actor_user_id=principal.user_id,
                 organization_id=device.organization_id, target_type="diagnosis", target_id=row.id, meta=meta,
                 details={"label": row.label})
    session.commit()
    return ok({**diagnoses.diagnosis_view(row), "alert": alerting.alert_view(alert) if alert else None})


@router.post("/diagnoses/analyze")
def analyze_diagnosis(body: DiagnosisAnalyzeIn, request: Request, principal: Principal = Depends(get_principal),
                      session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
                      now: datetime = Depends(get_now)) -> dict[str, Any]:
    analyzer = getattr(request.app.state, "vision_analyzer", None)
    result = diagnoses.analyze_image(session, settings, principal, body.values(), now, analyzer=analyzer)
    return ok(result)


@router.post("/recommendations/{recommendation_id}/feedback")
def recommendation_feedback(recommendation_id: str, body: FeedbackIn, principal: Principal = Depends(get_principal),
                            session: Session = Depends(get_session),
                            meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    row = diagnoses.get_recommendation_for(session, principal, recommendation_id)
    access.require_role(principal, row.organization_id, FEEDBACK_WRITERS)
    diagnoses.set_feedback(session, row, body.feedback)
    record_audit(session, "recommendation.feedback", actor_user_id=principal.user_id,
                 organization_id=row.organization_id, target_type="recommendation", target_id=row.id, meta=meta,
                 details={"feedback": body.feedback})
    session.commit()
    return ok(recommendations.recommendation_view(row))
