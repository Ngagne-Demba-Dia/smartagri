"""Ingestion HTTP de télémétrie par lot (kit via X-Device-Key, ou relais/utilisateur via JWT)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, device_from_key, get_now, get_session, get_settings, principal_from_credentials
from app.core.config import Settings
from app.core.constants import TELEMETRY_WRITERS
from app.core.envelope import ok
from app.core.errors import AppError, not_found, unauthenticated
from app.db.models import Device
from app.schemas.telemetry import MAX_BATCH_POINTS, TelemetryBatch
from app.services import access, telemetry

router = APIRouter(tags=["telemetry"])


def _devices_for_key(session: Session, settings: Settings, device_key: str, serials: set[str]) -> dict[str, Device]:
    device = device_from_key(session, settings, device_key)
    if device is None:
        raise unauthenticated("Clé de kit invalide.", "DEVICE_KEY_INVALID")
    if serials != {device.serial}:
        raise AppError("DEVICE_MISMATCH", "La clé de kit ne correspond pas au numéro de série des points.", 403)
    return {device.serial: device}


def _devices_for_user(session: Session, settings: Settings, credentials: HTTPAuthorizationCredentials | None,
                      serials: set[str]) -> Mapping[str, Device]:
    principal = principal_from_credentials(session, settings, credentials)
    found = session.scalars(
        select(Device).where(Device.serial.in_(serials), Device.organization_id.in_(principal.org_ids))
    ).all()
    by_serial = {device.serial: device for device in found}
    if set(by_serial) != serials:
        raise not_found("Kit")
    for device in found:
        access.require_role(principal, device.organization_id, TELEMETRY_WRITERS)
        if device.status != "active":
            raise AppError("DEVICE_INACTIVE", f"Kit {device.serial} inactif.", 409)
    return by_serial


@router.post("/telemetry/batch")
def telemetry_batch(
    batch: TelemetryBatch,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    now: datetime = Depends(get_now),
    device_key: str | None = Header(None, alias="X-Device-Key"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if len(batch.points) > MAX_BATCH_POINTS:
        raise AppError("BATCH_TOO_LARGE", f"{MAX_BATCH_POINTS} points au maximum par lot.", 413)
    serials = {point.device_id for point in batch.points}
    if device_key:
        devices = _devices_for_key(session, settings, device_key, serials)
    else:
        devices = _devices_for_user(session, settings, credentials, serials)
    result = telemetry.ingest_points(session, settings, batch.points, devices, now)
    session.commit()
    return ok(result.as_dict())
