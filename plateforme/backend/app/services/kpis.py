"""Indicateurs d'activité (eau, irrigation, disponibilité des kits, alertes, diagnostics, recommandations).

Définitions (documentées aussi dans l'API) :
- épisode d'irrigation : passage observé pompe arrêtée → pompe en marche entre deux points consécutifs ;
- heures de pompage : somme des intervalles entre deux points dont le premier indique la pompe en marche,
  chaque intervalle plafonné à 30 min (un trou de données n'est pas compté comme du pompage) ;
- eau consommée (m³) : heures de pompage × débit nominal `equipment.flow_m3h` des pompes liées au kit ;
  null si aucun kit du périmètre n'a de débit connu (`devices_without_flow` compte les kits sans débit) ;
- disponibilité (%) : heures avec au moins un point / heures de la période (bornée à maintenant) × kits ;
- recommandations suivies (%) : retours « followed » / retours exprimés.

Le parcours des mesures est fait en flux (`yield_per`) : seules trois colonnes sont lues.
"""

from __future__ import annotations

import itertools
import math
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.db.base import as_utc
from app.db.models import Alert, Diagnosis, Equipment, Measurement, Recommendation

PUMP_GAP_CAP = timedelta(minutes=30)
STREAM_BATCH = 5000
HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class ScopeFilter:
    """Périmètre d'un calcul : toute l'organisation, ou une liste de parcelles et de kits."""

    organization_id: uuid.UUID
    field_ids: tuple[uuid.UUID, ...]
    device_ids: tuple[uuid.UUID, ...]
    whole_org: bool = False


@dataclass(frozen=True)
class DeviceStats:
    points: int
    irrigation_events: int
    pump_hours: float
    active_hours: int


def device_stats(rows: Iterable[tuple[datetime, bool | None]]) -> DeviceStats:
    """Statistiques d'un kit à partir de ses points (ts, pump_on) triés par date."""
    points = events = active_hours = 0
    pump_seconds = 0.0
    prev_ts: datetime | None = None
    prev_on: bool | None = None
    last_hour: datetime | None = None
    for raw_ts, pump_on in rows:
        ts = as_utc(raw_ts)
        points += 1
        hour = ts.replace(minute=0, second=0, microsecond=0)
        if hour != last_hour:
            active_hours, last_hour = active_hours + 1, hour
        if prev_ts is not None and prev_on:
            pump_seconds += min((ts - prev_ts).total_seconds(), PUMP_GAP_CAP.total_seconds())
        if pump_on and prev_on is False:
            events += 1
        prev_ts, prev_on = ts, pump_on
    return DeviceStats(points, events, pump_seconds / 3600.0, active_hours)


def activity_by_device(session: Session, device_ids: tuple[uuid.UUID, ...], start: datetime,
                       end: datetime) -> dict[uuid.UUID, DeviceStats]:
    stats = {device_id: DeviceStats(0, 0, 0.0, 0) for device_id in device_ids}
    if not device_ids:
        return stats
    query = (select(Measurement.device_id, Measurement.ts, Measurement.pump_on)
             .where(Measurement.device_id.in_(device_ids), Measurement.ts >= start, Measurement.ts < end)
             .order_by(Measurement.device_id, Measurement.ts)
             .execution_options(yield_per=STREAM_BATCH))
    for device_id, rows in itertools.groupby(session.execute(query), key=lambda row: row[0]):
        stats[device_id] = device_stats((row[1], row[2]) for row in rows)
    return stats


def pump_flows(session: Session, device_ids: tuple[uuid.UUID, ...]) -> dict[uuid.UUID, float]:
    """Débit cumulé (m³/h) des pompes liées à chaque kit."""
    if not device_ids:
        return {}
    rows = session.execute(
        select(Equipment.device_id, func.sum(Equipment.flow_m3h))
        .where(Equipment.device_id.in_(device_ids), Equipment.kind == "pump", Equipment.flow_m3h.is_not(None))
        .group_by(Equipment.device_id)
    ).all()
    return {device_id: float(flow) for device_id, flow in rows if flow}


def water_estimate(stats: Mapping[uuid.UUID, DeviceStats], flows: Mapping[uuid.UUID, float]) -> float | None:
    known = [item.pump_hours * flows[device_id] for device_id, item in stats.items() if device_id in flows]
    return round(sum(known), 2) if known else None


def uptime_pct(stats: Mapping[uuid.UUID, DeviceStats], start: datetime, end: datetime, now: datetime) -> float | None:
    effective_end = min(end, now)
    hours = math.ceil((effective_end - start) / HOUR) if effective_end > start else 0
    if not stats or hours <= 0:
        return None
    active = sum(min(item.active_hours, hours) for item in stats.values())
    return round(100.0 * active / (hours * len(stats)), 1)


def _grouped(session: Session, column: Any, conditions: list[ColumnElement[bool]]) -> dict[str, int]:
    rows = session.execute(select(column, func.count()).where(*conditions).group_by(column)).all()
    return {str(key): int(count) for key, count in rows if key is not None}


def alerts_by_rule(session: Session, scope: ScopeFilter, start: datetime, end: datetime) -> dict[str, int]:
    conditions = [Alert.organization_id == scope.organization_id, Alert.created_at >= start, Alert.created_at < end]
    if not scope.whole_org:
        conditions.append(or_(Alert.field_id.in_(scope.field_ids), Alert.device_id.in_(scope.device_ids)))
    return _grouped(session, Alert.rule, conditions)


def diagnoses_by_label(session: Session, scope: ScopeFilter, start: datetime, end: datetime) -> dict[str, int]:
    conditions = [Diagnosis.organization_id == scope.organization_id, Diagnosis.captured_at >= start,
                  Diagnosis.captured_at < end]
    if not scope.whole_org:
        conditions.append(Diagnosis.device_id.in_(scope.device_ids))
    return _grouped(session, Diagnosis.label, conditions)


def feedback_counts(session: Session, scope: ScopeFilter, start: datetime, end: datetime) -> dict[str, int]:
    conditions = [Recommendation.organization_id == scope.organization_id, Recommendation.created_at >= start,
                  Recommendation.created_at < end]
    if not scope.whole_org:
        conditions.append(Recommendation.field_id.in_(scope.field_ids))
    return _grouped(session, Recommendation.feedback, conditions)


def followed_pct(feedback: Mapping[str, int]) -> float | None:
    total = sum(feedback.values())
    return round(100.0 * feedback.get("followed", 0) / total, 1) if total else None


def compute_kpis(session: Session, scope: ScopeFilter, start: datetime, end: datetime,
                 now: datetime) -> dict[str, Any]:
    stats = activity_by_device(session, scope.device_ids, start, end)
    flows = pump_flows(session, scope.device_ids)
    feedback = feedback_counts(session, scope, start, end)
    return {
        "devices": len(scope.device_ids),
        "fields": len(scope.field_ids),
        "water_m3": water_estimate(stats, flows),
        "devices_without_flow": sum(1 for device_id in scope.device_ids if device_id not in flows),
        "pump_hours": round(sum(item.pump_hours for item in stats.values()), 2),
        "irrigation_events": sum(item.irrigation_events for item in stats.values()),
        "measurements": sum(item.points for item in stats.values()),
        "kit_uptime_pct": uptime_pct(stats, start, end, now),
        "alerts_by_rule": alerts_by_rule(session, scope, start, end),
        "diagnoses_by_label": diagnoses_by_label(session, scope, start, end),
        "recommendations_feedback": feedback,
        "recommendations_followed_pct": followed_pct(feedback),
    }
