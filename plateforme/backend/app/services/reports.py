"""Rapports : indicateurs par organisation, exploitation ou campagne, et export CSV.

L'export CSV est protégé contre l'injection de formules (tableurs) : toute cellule texte commençant par
`=`, `+`, `-`, `@`, une tabulation ou un retour chariot est préfixée d'une apostrophe. Les nombres sont
écrits tels quels (un nombre négatif n'est pas une formule).
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found
from app.db.base import as_utc
from app.db.models import CropCycle, Device, Field
from app.services import access, campaigns, kpis

SCOPES = ("org", "farm", "campaign")
MAX_RANGE = timedelta(days=366)
DEFAULT_RANGE = timedelta(days=30)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
CSV_COLUMNS = ("scope", "scope_id", "from", "to", "indicator", "key", "value")


@dataclass(frozen=True)
class ReportScope:
    kind: str
    scope_id: uuid.UUID
    filter: kpis.ScopeFilter
    default_period: tuple[datetime, datetime] | None = None


def _devices_on(session: Session, field_ids: tuple[uuid.UUID, ...]) -> tuple[uuid.UUID, ...]:
    return tuple(session.scalars(select(Device.id).where(Device.field_id.in_(field_ids))).all())


def _org_scope(session: Session, principal: access.Principal, scope_id: uuid.UUID | None) -> ReportScope:
    if scope_id is None:
        if len(principal.org_ids) != 1:
            raise AppError("ORGANIZATION_REQUIRED", "Précisez l'organisation (id).", 400)
        scope_id = principal.org_ids[0]
    if scope_id not in principal.roles_by_org:
        raise not_found("Organisation")
    field_ids = tuple(session.scalars(select(Field.id).where(Field.organization_id == scope_id)).all())
    device_ids = tuple(session.scalars(select(Device.id).where(Device.organization_id == scope_id)).all())
    return ReportScope("org", scope_id, kpis.ScopeFilter(scope_id, field_ids, device_ids, whole_org=True))


def resolve_scope(session: Session, principal: access.Principal, kind: str, scope_id: str | None,
                  now: datetime) -> ReportScope:
    """Périmètre visible par l'utilisateur ; un identifiant étranger ou mal formé donne 404."""
    if kind not in SCOPES:
        raise AppError("INVALID_SCOPE", f"scope doit valoir : {', '.join(SCOPES)}.", 400)
    if kind == "org":
        return _org_scope(session, principal, access.parse_uuid(scope_id, "Organisation") if scope_id else None)
    if not scope_id:
        raise AppError("SCOPE_ID_REQUIRED", "Paramètre `id` obligatoire pour ce périmètre.", 400)
    if kind == "farm":
        farm = access.get_farm_for(session, principal, scope_id)
        field_ids = tuple(session.scalars(select(Field.id).where(Field.farm_id == farm.id)).all())
        scope = kpis.ScopeFilter(farm.organization_id, field_ids, _devices_on(session, field_ids))
        return ReportScope("farm", farm.id, scope)
    campaign = campaigns.get_campaign_for(session, principal, scope_id)
    field_ids = tuple(set(session.scalars(select(CropCycle.field_id).where(CropCycle.campaign_id == campaign.id))))
    scope = kpis.ScopeFilter(campaign.organization_id, field_ids, _devices_on(session, field_ids))
    return ReportScope("campaign", campaign.id, scope, campaigns.campaign_period(campaign, now))


def resolve_period(scope: ReportScope, start: datetime | None, end: datetime | None,
                   now: datetime) -> tuple[datetime, datetime]:
    """Période [from, to[ : celle demandée, sinon celle de la campagne, sinon les 30 derniers jours."""
    default_start, default_end = scope.default_period or (now - DEFAULT_RANGE, now)
    end_utc = as_utc(end) or default_end
    start_utc = as_utc(start) or (default_start if end is None else end_utc - DEFAULT_RANGE)
    if start_utc >= end_utc:
        raise AppError("INVALID_RANGE", "`from` doit précéder `to`.", 400)
    if end_utc - start_utc > MAX_RANGE:
        raise AppError("RANGE_TOO_LARGE", f"Plage maximale : {MAX_RANGE.days} jours.", 400)
    return start_utc, end_utc


def build_report(session: Session, principal: access.Principal, kind: str, scope_id: str | None,
                 start: datetime | None, end: datetime | None, now: datetime) -> dict[str, Any]:
    scope = resolve_scope(session, principal, kind, scope_id, now)
    period_start, period_end = resolve_period(scope, start, end, now)
    return {"scope": scope.kind, "scope_id": str(scope.scope_id), "from": period_start.isoformat(),
            "to": period_end.isoformat(),
            "kpis": kpis.compute_kpis(session, scope.filter, period_start, period_end, now)}


def safe_cell(value: Any) -> Any:
    """Neutralise une cellule texte interprétable comme formule par un tableur."""
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return "" if value is None else value


def report_rows(report: Mapping[str, Any]) -> Iterator[list[Any]]:
    """Format long : une ligne par indicateur (ou par clé pour les répartitions)."""
    head = [report["scope"], report["scope_id"], report["from"], report["to"]]
    for indicator, value in report["kpis"].items():
        if isinstance(value, Mapping):
            for key, count in sorted(value.items()):
                yield [*head, indicator, key, count]
        else:
            yield [*head, indicator, "", value]


def report_csv(report: Mapping[str, Any]) -> bytes:
    """CSV UTF-8 avec BOM (ouverture correcte des accents dans Excel)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for row in report_rows(report):
        writer.writerow([safe_cell(cell) for cell in row])
    return buffer.getvalue().encode("utf-8-sig")
