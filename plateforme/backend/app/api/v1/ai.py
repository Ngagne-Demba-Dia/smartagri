"""Routes proxy vers le runtime IA local `smartagri-ai` (/v1/ai/*)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import get_principal, get_settings
from app.core.config import Settings
from app.core.envelope import ok
from app.core.errors import AppError
from app.services.access import Principal
from app.services.inference.local_ai import SmartAgriAIClient

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_DISEASE_IMAGE_B64 = 2 * 1024 * 1024  # ~1.5 Mio décodé


class AiSoilIn(BaseModel):
    features: dict[str, float]


class AiYieldIn(BaseModel):
    crop: str = Field("Millet", min_length=1, max_length=64)
    region: str = Field("Kaolack", min_length=1, max_length=64)
    year: int = Field(2025, ge=1960, le=2100)
    area_ha: float = Field(1000.0, gt=0.0, le=1_000_000.0)


class AiPriceIn(BaseModel):
    commodity: str = Field("Onions", min_length=1, max_length=64)
    market: str = Field("Tilene", min_length=1, max_length=64)
    region: str = Field("Dakar", min_length=1, max_length=64)
    year: int = Field(2026, ge=2000, le=2100)
    month: int = Field(11, ge=1, le=12)


class AiDiseaseIn(BaseModel):
    """Image encodée en base64 (jamais de chemin disque arbitraire)."""

    image_base64: str = Field(..., min_length=1, max_length=MAX_DISEASE_IMAGE_B64)
    content_type: str = Field("image/jpeg", max_length=64)


class AiOrchestratorIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    features: dict[str, Any] = Field(default_factory=dict)
    crop: str = Field("oignon", min_length=1, max_length=64)


class AiVoiceTextIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


def _require_ai_client(request: Request, settings: Settings) -> SmartAgriAIClient:
    client = getattr(request.app.state, "smartagri_ai_client", None)
    if client is None:
        if not settings.smartagri_ai_url:
            raise AppError("MODEL_UNAVAILABLE", "Runtime smartagri-ai non configuré (SMARTAGRI_AI_URL vide).", 503)
        client = SmartAgriAIClient(
            settings.smartagri_ai_url,
            timeout_s=settings.smartagri_ai_timeout_s,
            api_key=settings.smartagri_ai_api_key,
        )
        request.app.state.smartagri_ai_client = client
    return client


@router.get("/health")
def ai_health(request: Request, principal: Principal = Depends(get_principal),
              settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    client = _require_ai_client(request, settings)
    data = client.health()
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Runtime smartagri-ai inaccessible.", 503)
    return ok(data)


@router.post("/soil/predict")
def ai_predict_soil(body: AiSoilIn, request: Request, principal: Principal = Depends(get_principal),
                    settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).predict_soil(body.features)
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Prédiction sol indisponible.", 503)
    return ok(data)


@router.post("/yield/predict")
def ai_predict_yield(body: AiYieldIn, request: Request, principal: Principal = Depends(get_principal),
                     settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).predict_yield(body.crop, body.region, body.year, body.area_ha)
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Prédiction rendement indisponible.", 503)
    return ok(data)


@router.post("/price/predict")
def ai_predict_price(body: AiPriceIn, request: Request, principal: Principal = Depends(get_principal),
                     settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).predict_price(
        body.commodity, body.market, body.region, body.year, body.month
    )
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Prédiction prix indisponible.", 503)
    return ok(data)


@router.get("/market/clusters")
def ai_market_clusters(request: Request, top_n: int = Query(5, ge=1, le=50),
                       principal: Principal = Depends(get_principal),
                       settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).market_clusters(top_n=top_n)
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Clustering marchés indisponible.", 503)
    return ok(data)


@router.post("/disease/predict")
def ai_predict_disease(body: AiDiseaseIn, request: Request, principal: Principal = Depends(get_principal),
                       settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).predict_disease_bytes(body.image_base64, body.content_type)
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Diagnostic maladie indisponible.", 503)
    return ok(data)


@router.post("/orchestrator/ask")
def ai_ask_orchestrator(body: AiOrchestratorIn, request: Request, principal: Principal = Depends(get_principal),
                        settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).ask_orchestrator(body.query, body.features, body.crop)
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Orchestrateur IA indisponible.", 503)
    return ok(data)


@router.post("/voice/intent")
def ai_voice_intent(body: AiVoiceTextIn, request: Request, principal: Principal = Depends(get_principal),
                    settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    data = _require_ai_client(request, settings).interpret_wolof(body.text)
    if data is None:
        raise AppError("MODEL_UNAVAILABLE", "Interprétation Wolof indisponible.", 503)
    return ok(data)
