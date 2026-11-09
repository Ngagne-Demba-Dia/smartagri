"""Rapports : indicateurs (JSON) et export CSV.

L'export CSV est un fichier, pas une enveloppe JSON ; les erreurs, elles, gardent l'enveloppe standard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_now, get_principal, get_request_meta, get_session
from app.core.envelope import ok
from app.services import reports
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["reports"])


@router.get("/reports/kpis")
def report_kpis(scope: str = Query("org", max_length=10), scope_id: str | None = Query(None, alias="id", max_length=64),
                start: datetime | None = Query(None, alias="from"), end: datetime | None = Query(None, alias="to"),
                principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
                now: datetime = Depends(get_now)) -> dict[str, Any]:
    return ok(reports.build_report(session, principal, scope, scope_id, start, end, now))


@router.get("/reports/export.csv")
def report_export(scope: str = Query("org", max_length=10),
                  scope_id: str | None = Query(None, alias="id", max_length=64),
                  start: datetime | None = Query(None, alias="from"), end: datetime | None = Query(None, alias="to"),
                  principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
                  now: datetime = Depends(get_now), meta: RequestMeta = Depends(get_request_meta)) -> Response:
    report = reports.build_report(session, principal, scope, scope_id, start, end, now)
    record_audit(session, "report.export", actor_user_id=principal.user_id, target_type=report["scope"],
                 target_id=report["scope_id"], meta=meta)
    session.commit()
    filename = f"kpis-{report['scope']}-{now:%Y%m%d}.csv"
    return Response(content=reports.report_csv(report), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
