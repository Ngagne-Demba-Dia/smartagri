"""Kits : enregistrement, seuils désirés/rapportés et commandes MQTT `set_thresholds`.

Cycle d'un changement de seuils :
1. PUT /v1/devices/{id}/thresholds : seuils désirés, statut `pending`, nouvel identifiant de commande ;
2. le worker MQTT publie la commande (`sent`) ;
3. le kit acquitte (`applied` / `failed`) ou rapporte ses seuils dans la télémétrie (`applied` si égaux).

Si les seuils sont modifiés localement sur le kit (interface web du firmware) alors qu'aucune commande
n'est en cours, la valeur du kit devient la valeur désirée : le terrain fait foi.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, not_found
from app.core.security import generate_device_key, hash_device_key
from app.db.base import as_utc
from app.db.models import Device, DeviceThreshold, Field
from app.services.agronomy import ThresholdError, thresholds_valid, validate_thresholds

IN_FLIGHT = frozenset({"pending", "sent"})


def register_device(
    session: Session,
    settings: Settings,
    organization_id: uuid.UUID,
    serial: str,
    name: str | None = None,
    field_id: uuid.UUID | None = None,
    *,
    device_id: uuid.UUID | None = None,
    firmware_version: str | None = None,
) -> tuple[Device, str]:
    """Crée un kit et renvoie son secret en clair (affiché une seule fois, seul le HMAC est stocké)."""
    if session.scalars(select(Device.id).where(Device.serial == serial)).first() is not None:
        raise AppError("DEVICE_EXISTS", "Un kit avec ce numéro de série existe déjà.", 409)
    if field_id is not None:
        field = session.get(Field, field_id)
        if field is None or field.organization_id != organization_id:
            raise not_found("Parcelle")
    key = generate_device_key()
    kwargs: dict[str, Any] = {
        "organization_id": organization_id,
        "field_id": field_id,
        "serial": serial,
        "name": name,
        "key_hash": hash_device_key(settings, key),
    }
    if device_id is not None:
        kwargs["id"] = device_id
    if firmware_version is not None:
        kwargs["firmware_version"] = firmware_version
    device = Device(**kwargs)
    session.add(device)
    session.flush()
    return device, key


def find_device_by_key(session: Session, settings: Settings, device_key: str) -> Device | None:
    """Recherche par empreinte HMAC (index unique) ; le kit doit être actif."""
    if not device_key:
        return None
    device = session.scalars(select(Device).where(Device.key_hash == hash_device_key(settings, device_key))).first()
    if device is None or device.status != "active":
        return None
    return device


def device_view(device: Device, thresholds: DeviceThreshold | None = None) -> dict[str, Any]:
    last_seen = as_utc(device.last_seen_at)
    return {
        "id": str(device.id),
        "serial": device.serial,
        "name": device.name,
        "organization_id": str(device.organization_id),
        "field_id": str(device.field_id) if device.field_id else None,
        "firmware_version": device.firmware_version,
        "status": device.status,
        "last_seen_at": last_seen.isoformat() if last_seen else None,
        "thresholds": threshold_view(thresholds) if thresholds else None,
    }


def threshold_view(row: DeviceThreshold) -> dict[str, Any]:
    updated = as_utc(row.updated_at)
    return {
        "desired": {"start_pct": row.desired_start_pct, "stop_pct": row.desired_stop_pct},
        "reported": (
            {"start_pct": row.reported_start_pct, "stop_pct": row.reported_stop_pct}
            if row.reported_start_pct is not None and row.reported_stop_pct is not None
            else None
        ),
        "sync_status": row.sync_status,
        "command_id": str(row.command_id) if row.command_id else None,
        "updated_at": updated.isoformat() if updated else None,
    }


def get_thresholds(session: Session, device_id: uuid.UUID) -> DeviceThreshold | None:
    return session.get(DeviceThreshold, device_id)


def set_desired_thresholds(
    session: Session, device: Device, start: Any, stop: Any, user_id: uuid.UUID | None, now: datetime
) -> DeviceThreshold:
    """Valide (règle du firmware) puis enregistre une commande en attente ; 400 THRESHOLDS_INVALID sinon."""
    try:
        start_pct, stop_pct = validate_thresholds(start, stop)
    except ThresholdError as exc:
        raise AppError("THRESHOLDS_INVALID", str(exc), 400) from exc
    row = get_thresholds(session, device.id)
    if row is None:
        row = DeviceThreshold(device_id=device.id, organization_id=device.organization_id)
        session.add(row)
    row.desired_start_pct, row.desired_stop_pct = start_pct, stop_pct
    row.sync_status = "pending"
    row.command_id = uuid.uuid4()
    row.updated_at, row.updated_by = now, user_id
    session.flush()
    return row


def apply_reported_thresholds(session: Session, device: Device, start: int | None, stop: int | None,
                              now: datetime) -> None:
    """Seuils rapportés par le kit (télémétrie) ; valeurs invalides ignorées."""
    if start is None or stop is None or not thresholds_valid(start, stop):
        return
    row = get_thresholds(session, device.id)
    if row is None:
        row = DeviceThreshold(device_id=device.id, organization_id=device.organization_id,
                              desired_start_pct=start, desired_stop_pct=stop, updated_at=now)
        session.add(row)
    row.reported_start_pct, row.reported_stop_pct = start, stop
    if (row.desired_start_pct, row.desired_stop_pct) == (start, stop):
        row.sync_status = "applied"
    elif row.sync_status not in IN_FLIGHT:
        row.desired_start_pct, row.desired_stop_pct = start, stop
        row.sync_status, row.updated_at, row.updated_by = "applied", now, None


def apply_command_ack(session: Session, device: Device, command_id: str, ok: bool, now: datetime) -> bool:
    """Acquittement `commands/ack` ; ignoré si l'identifiant ne correspond pas à la commande en cours."""
    row = get_thresholds(session, device.id)
    if row is None or row.command_id is None or str(row.command_id) != str(command_id):
        return False
    row.sync_status = "applied" if ok else "failed"
    if ok:
        row.reported_start_pct, row.reported_stop_pct = row.desired_start_pct, row.desired_stop_pct
    row.updated_at = now
    return True


def pending_threshold_commands(session: Session, limit: int = 100) -> list[tuple[Device, DeviceThreshold]]:
    """Boîte d'envoi : commandes à publier (statut `pending`)."""
    rows = session.execute(
        select(Device, DeviceThreshold)
        .join(DeviceThreshold, DeviceThreshold.device_id == Device.id)
        .where(DeviceThreshold.sync_status == "pending", Device.status == "active")
        .limit(limit)
    ).all()
    return [(device, row) for device, row in rows]


def threshold_command(row: DeviceThreshold) -> dict[str, Any]:
    """Charge utile MQTT (CONVENTIONS §4)."""
    return {"cmd": "set_thresholds", "id": str(row.command_id), "start": row.desired_start_pct,
            "stop": row.desired_stop_pct}
