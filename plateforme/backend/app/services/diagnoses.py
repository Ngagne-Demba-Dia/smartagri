"""Diagnostics de vision (image → sain / suspect / malade) et retours sur les recommandations.

Le verdict est produit ailleurs (application mobile ou kit caméra) puis transmis ici ; il reste indicatif.
L'image elle-même est stockée dans le stockage objet (S3) : seule sa clé et son empreinte sont enregistrées.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, not_found
from app.db.base import as_utc, iso_utc
from app.db.models import Device, Diagnosis, Image, Recommendation
from app.services import access, alerting


def diagnosis_view(row: Diagnosis) -> dict[str, Any]:
    return {"id": str(row.id), "organization_id": str(row.organization_id),
            "device_id": str(row.device_id) if row.device_id else None,
            "image_id": str(row.image_id) if row.image_id else None, "label": row.label,
            "disease_code": row.disease_code, "confidence": row.confidence, "model_version": row.model_version,
            "captured_at": iso_utc(row.captured_at), "created_at": iso_utc(row.created_at)}


def _store_image(session: Session, device: Device, image: Mapping[str, Any], captured_at: datetime) -> Image:
    row = Image(organization_id=device.organization_id, device_id=device.id, field_id=device.field_id,
                storage_key=image["storage_key"], content_type=image["content_type"], sha256=image.get("sha256"),
                captured_at=captured_at)
    session.add(row)
    session.flush()
    return row


def record_diagnosis(session: Session, settings: Settings, device: Device, data: Mapping[str, Any],
                     now: datetime) -> tuple[Diagnosis, Any]:
    """Enregistre le diagnostic puis applique la règle des N diagnostics consécutifs (alerte éventuelle)."""
    captured_at = as_utc(data.get("captured_at")) or now
    if captured_at > now:
        raise AppError("INVALID_DATES", "Date de prise de vue dans le futur.", 400)
    image = _store_image(session, device, data["image"], captured_at) if data.get("image") else None
    row = Diagnosis(organization_id=device.organization_id, device_id=device.id,
                    image_id=image.id if image else None, label=data["label"], disease_code=data.get("disease_code"),
                    confidence=data["confidence"], model_version=data["model_version"], captured_at=captured_at,
                    created_at=now)
    session.add(row)
    session.flush()
    alert = alerting.evaluate_diagnoses(session, settings, device, now)
    return row, alert


def get_recommendation_for(session: Session, principal: access.Principal,
                           recommendation_id: str | uuid.UUID) -> Recommendation:
    row = session.get(Recommendation, access.parse_uuid(recommendation_id, "Recommandation"))
    if row is None or row.organization_id not in principal.roles_by_org:
        raise not_found("Recommandation")
    return row


def set_feedback(session: Session, row: Recommendation, feedback: str) -> Recommendation:
    row.feedback = feedback
    session.flush()
    return row
