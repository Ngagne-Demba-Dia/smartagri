"""Kits : enregistrement, consultation, seuils d'irrigation et séries de mesures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    Pagination,
    get_now,
    get_pagination,
    get_principal,
    get_request_meta,
    get_session,
    get_settings,
)
from app.core.config import Settings
from app.core.constants import DEVICE_WRITERS, THRESHOLD_WRITERS
from app.core.envelope import ok, page_meta
from app.db.models import Device, DeviceThreshold
from app.schemas.devices import DeviceIn, ThresholdsIn
from app.services import access, devices, measurements
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["devices"])


@router.post("/devices", status_code=201)
def register_device(body: DeviceIn, principal: Principal = Depends(get_principal),
                    session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
                    meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    org_id = access.resolve_org_for_write(principal, body.organization_id, DEVICE_WRITERS)
    device, key = devices.register_device(session, settings, org_id, body.serial, body.name, body.field_id)
    record_audit(session, "device.create", actor_user_id=principal.user_id, organization_id=org_id,
                 target_type="device", target_id=device.id, meta=meta, details={"serial": device.serial})
    session.commit()
    # Secret affiché une seule fois : seule son empreinte HMAC est conservée.
    return ok({**devices.device_view(device), "device_key": key})


@router.get("/devices")
def list_devices(status: str | None = Query(None, max_length=20), principal: Principal = Depends(get_principal),
                 session: Session = Depends(get_session),
                 paging: Pagination = Depends(get_pagination)) -> dict[str, Any]:
    conditions = [Device.organization_id.in_(principal.org_ids)]
    if status:
        conditions.append(Device.status == status)
    total = session.scalar(select(func.count()).select_from(Device).where(*conditions)) or 0
    rows = session.execute(
        select(Device, DeviceThreshold).outerjoin(DeviceThreshold, DeviceThreshold.device_id == Device.id)
        .where(*conditions).order_by(Device.serial)
        .offset((paging.page - 1) * paging.limit).limit(paging.limit)
    ).all()
    data = [devices.device_view(device, threshold) for device, threshold in rows]
    return ok(data, page_meta(paging.page, paging.limit, int(total)))


@router.get("/devices/{device_id}")
def get_device(device_id: str, principal: Principal = Depends(get_principal),
               session: Session = Depends(get_session)) -> dict[str, Any]:
    device = access.get_device_for(session, principal, device_id)
    latest = measurements.latest_measurement(session, device.id)
    view = devices.device_view(device, devices.get_thresholds(session, device.id))
    return ok({**view, "latest_measurement": measurements.measurement_view(latest) if latest else None})


@router.get("/devices/{device_id}/thresholds")
def get_thresholds(device_id: str, principal: Principal = Depends(get_principal),
                   session: Session = Depends(get_session)) -> dict[str, Any]:
    device = access.get_device_for(session, principal, device_id)
    row = devices.get_thresholds(session, device.id)
    return ok(devices.threshold_view(row) if row else None)


@router.put("/devices/{device_id}/thresholds")
def put_thresholds(device_id: str, body: ThresholdsIn, principal: Principal = Depends(get_principal),
                   session: Session = Depends(get_session), now: datetime = Depends(get_now),
                   meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    device = access.get_device_for(session, principal, device_id)
    access.require_role(principal, device.organization_id, THRESHOLD_WRITERS)
    row = devices.set_desired_thresholds(session, device, body.start, body.stop, principal.user_id, now)
    record_audit(session, "device.thresholds_set", actor_user_id=principal.user_id,
                 organization_id=device.organization_id, target_type="device", target_id=device.id, meta=meta,
                 details={"start": row.desired_start_pct, "stop": row.desired_stop_pct,
                          "command_id": str(row.command_id)})
    session.commit()
    return ok(devices.threshold_view(row))


@router.get("/devices/{device_id}/measurements")
def get_measurements(device_id: str, bucket: str = Query("raw", max_length=4),
                     start: datetime | None = Query(None, alias="from"),
                     end: datetime | None = Query(None, alias="to"),
                     principal: Principal = Depends(get_principal), session: Session = Depends(get_session),
                     now: datetime = Depends(get_now)) -> dict[str, Any]:
    device = access.get_device_for(session, principal, device_id)
    series = measurements.query_series(session, device.id, bucket, start, end, now)
    return ok({"device_id": str(device.id), "bucket": series.bucket, "from": series.start.isoformat(),
               "to": series.end.isoformat(), "rows": series.rows},
              {"count": len(series.rows), "truncated": series.truncated})
