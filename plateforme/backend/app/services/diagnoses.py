"""Diagnostics de vision (image → sain / suspect / malade) et retours sur les recommandations.

Le verdict est produit ailleurs (application mobile ou kit caméra) puis transmis ici ; il reste indicatif.
L'image elle-même est stockée dans le stockage objet (S3) : seule sa clé et son empreinte sont enregistrées.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, not_found
from app.db.base import as_utc, iso_utc
from app.db.models import Device, Diagnosis, Image, Recommendation
from app.services import access, alerting
from app.services.provenance import confidence as build_confidence, provenance

UPLOAD_MAX_BYTES = 256 * 1024
UPLOAD_MAX_RAW_BYTES = ((UPLOAD_MAX_BYTES - 2048) * 3) // 4


@dataclass(frozen=True)
class VisionCandidate:
    code: str
    probability: float


@dataclass(frozen=True)
class VisionPrediction:
    label: str  # "healthy" | "suspect" | "sick"
    top3: Sequence[VisionCandidate]
    model_version: str = "1.0.0"
    source: str = "agriml"
    calibrated: bool = True


class VisionAnalyzer(Protocol):
    def analyze(self, image_bytes: bytes, content_type: str) -> VisionPrediction: ...


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


def _decode_bounded_image(image_base64: str) -> bytes:
    if len(image_base64.encode("ascii", errors="ignore")) > UPLOAD_MAX_BYTES:
        raise AppError("PAYLOAD_TOO_LARGE", "Image trop volumineuse (256 Kio max).", 413)
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppError("VALIDATION_ERROR", "Encodage base64 de l'image invalide.", 422) from exc
    if not raw:
        raise AppError("VALIDATION_ERROR", "Image vide.", 422)
    if len(raw) > UPLOAD_MAX_RAW_BYTES:
        raise AppError("PAYLOAD_TOO_LARGE", "Image décodée trop volumineuse (256 Kio max).", 413)
    return raw


def analyze_image(
    session: Session,
    settings: Settings,
    principal: access.Principal,
    data: Mapping[str, Any],
    now: datetime,
    analyzer: VisionAnalyzer | None = None,
) -> dict[str, Any]:
    """Analyse une photo (`POST /v1/diagnoses/analyze`, doc 16 § 9.3 service 8 `disease_diagnosis`).

    Vérifie d'abord la taille (<= 256 Kio), le périmètre multi-organisation (404 sinon) et la date.
    Si aucun bundle `vis_disease` vérifié n'est chargé, renvoie honnêtement `503 MODEL_UNAVAILABLE`.
    """
    raw_bytes = _decode_bounded_image(data["image_base64"])
    field = access.get_field_for(session, principal, data["field_id"]) if data.get("field_id") else None
    device = access.get_device_for(session, principal, data["device_id"]) if data.get("device_id") else None
    if field is not None and device is not None and device.organization_id != field.organization_id:
        raise not_found("Kit")
    captured_at = as_utc(data.get("captured_at")) or now
    if captured_at > now:
        raise AppError("INVALID_DATES", "Date de prise de vue dans le futur.", 400)
    if analyzer is None:
        raise AppError(
            "MODEL_UNAVAILABLE",
            "Aucun modèle de diagnostic visuel (vis_disease) vérifié n'est disponible.",
            503,
        )
    pred = analyzer.analyze(raw_bytes, data["content_type"])
    top3 = [{"code": item.code, "probability": round(float(item.probability), 4)} for item in list(pred.top3)[:3]]
    top_prob = top3[0]["probability"] if top3 else 0.0
    abstained = top_prob < settings.disease_min_confidence
    if abstained:
        label = "suspect"
        disease_code = None
    else:
        label = pred.label
        disease_code = None if label == "healthy" or not top3 else top3[0]["code"]

    return {
        "id": None,
        "label": label,
        "disease_code": disease_code,
        "top3": top3,
        "abstained": abstained,
        "captured_at": iso_utc(captured_at),
        "provenance": provenance(
            model_name="vis_disease",
            model_version=pred.model_version,
            source=pred.source,
            computed_at=now,
            fallback_step=0,
            data_as_of=captured_at,
            stale=False,
            conf=build_confidence("class_probability", value=top_prob, calibrated=pred.calibrated),
        ),
    }
