"""Sondes de vie / disponibilité et métriques Prometheus (hors /v1, hors enveloppe pour /metrics)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.envelope import fail, ok
from app.core.metrics import metrics_available, render_metrics

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, Any]:
    """Vivacité : le processus répond (aucune dépendance externe vérifiée)."""
    return ok({"status": "ok"})


@router.get("/readyz", response_model=None)
def readyz(request: Request, session: Session = Depends(get_session)) -> dict[str, Any] | JSONResponse:
    """Disponibilité : la base de données répond à un ping ; état du runtime IA reporté s'il est configuré."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("readyz : base de données injoignable")
        return JSONResponse(fail("NOT_READY", "Base de données indisponible."), status_code=503)
    payload: dict[str, Any] = {"status": "ready", "database": "ok"}
    ai_client = getattr(request.app.state, "smartagri_ai_client", None)
    if ai_client is not None and ai_client.enabled:
        ai_health = ai_client.health()
        payload["smartagri_ai"] = "ok" if (ai_health and ai_health.get("status") == "ok") else "degraded"
    return ok(payload)


@router.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    if not request.app.state.settings.metrics_enabled or not metrics_available():
        return JSONResponse(fail("NOT_FOUND", "Ressource introuvable."), status_code=404)
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
