"""API FastAPI locale autonome pour SmartAgri AI Runtime (Phases 0→4)."""

import hmac
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
PYDEPS = ROOT / ".pydeps"
if PYDEPS.exists() and str(PYDEPS) not in sys.path:
    sys.path.append(str(PYDEPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.db import LocalMetricsDB
from runtime.security import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES, decode_bounded_base64

from mlops.registry.registry import LocalModelRegistry
from runtime.soil_nowcast_service import SoilNowcastService
from runtime.rain_intelligence_service import RainIntelligenceService
from runtime.anomaly_service import AnomalyService
from runtime.et0_calendar_ndvi_service import (
    ET0ForecastService,
    CropCalendarService,
    NDVIAnomalyService,
)
from runtime.yield_price_market_service import (
    YieldForecastService,
    PriceForecastService,
    MarketClusteringService,
)
from runtime.disease_service import DiseaseDetectionService
from runtime.class_b_services import B1IrrigationMLService, B2WaterSavingsService
from voice.wolof_voice_service import WolofVoiceService
from voice.wolof_lexicon import interpret_wolof_text
from rag.knowledge_service import KnowledgeService
from agents.monitoring.monitoring_engine import MonitoringEngine
from agents.irrigation.irrigation_engine import IrrigationEngine
from agents.assistant.assistant_service import AssistantService
from agents.orchestrator.orchestrator import SmartAgriOrchestrator

app = FastAPI(title="SmartAgri Local AI Runtime", version="0.5.0")

_API_KEY = os.environ.get("SMARTAGRI_AI_API_KEY", "").strip()
_ALLOW_DYNAMIC_DOWNLOAD = os.environ.get("SMARTAGRI_AI_ALLOW_DYNAMIC_DOWNLOAD", "").strip().lower() in {"1", "true", "yes"}
_PRELOAD_VOICE = os.environ.get("SMARTAGRI_AI_PRELOAD_VOICE", "").strip().lower() in {"1", "true", "yes"}


@app.middleware("http")
async def _inter_service_auth(request: Request, call_next):
    if _API_KEY and request.url.path != "/health":
        provided = request.headers.get("X-API-Key", "")
        if not provided:
            auth = request.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                provided = auth[7:].strip()
        if not provided or not hmac.compare_digest(provided, _API_KEY):
            return JSONResponse({"detail": "Authentification inter-services requise."}, status_code=401)
    return await call_next(request)

registry = LocalModelRegistry()
local_db = LocalMetricsDB()
soil_service = SoilNowcastService()
et0_service = ET0ForecastService()
rain_service = RainIntelligenceService()
anomaly_service = AnomalyService()
yield_service = YieldForecastService()
price_service = PriceForecastService()
calendar_service = CropCalendarService()
ndvi_service = NDVIAnomalyService()
market_service = MarketClusteringService()
disease_service = DiseaseDetectionService()
b1_service = B1IrrigationMLService()
b2_service = B2WaterSavingsService()
voice_service = WolofVoiceService()
if _PRELOAD_VOICE:
    voice_service._ensure_asr()
knowledge_service = KnowledgeService()
monitoring_engine = MonitoringEngine(soil_service, rain_service, anomaly_service)
irrigation_engine = IrrigationEngine(soil_service, rain_service)
assistant_service = AssistantService(knowledge_service, soil_service, irrigation_engine)
orchestrator = SmartAgriOrchestrator(
    soil_service, rain_service, anomaly_service,
    knowledge_service, monitoring_engine, irrigation_engine,
    yield_svc=yield_service, price_svc=price_service, market_svc=market_service,
    et0_svc=et0_service, calendar_svc=calendar_service, ndvi_svc=ndvi_service,
)


class SoilPredictRequest(BaseModel):
    features: Dict[str, float]


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=20)
    domain: Optional[str] = Field(None, max_length=100)


class FeaturesCropRequest(BaseModel):
    features: Dict[str, Any]
    crop: str = Field("oignon", max_length=64)
    area_ha: float = Field(1.0, gt=0.0, le=100_000.0)


class OrchestratorAskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    features: Dict[str, Any] = Field(default_factory=dict)
    crop: str = Field("oignon", max_length=64)


class DiseaseImageBytesRequest(BaseModel):
    image_base64: str = Field(..., min_length=1)
    content_type: str = Field("image/jpeg", max_length=64)


def _serialize_resp(resp):
    return {
        "service": resp.service,
        "values": resp.values,
        "confidence": resp.confidence,
        "confidence_level": resp.confidence_level.value,
        "warnings": resp.warnings,
        "abstained": resp.abstained,
        "abstention_reason": resp.abstention_reason,
        "latency_ms": resp.latency_ms,
    }


@app.get("/health")
def health():
    checks = {
        "soil_nowcast": soil_service.is_ready,
        "et0": et0_service.is_ready,
        "yield": yield_service.is_ready,
        "price": price_service.is_ready,
        "calendar": calendar_service.is_ready,
        "ndvi": ndvi_service.is_ready,
        "market": market_service.is_ready,
        "disease": disease_service.is_ready,
        "rain": rain_service.is_ready,
        "knowledge": knowledge_service.is_ready,
    }
    degraded = [name for name, ready in checks.items() if not ready]
    return {
        "status": "ok" if (soil_service.is_ready and knowledge_service.is_ready) else "degraded",
        "degraded_services": degraded,
        "soil_nowcast_ready": soil_service.is_ready,
        "et0_ready": et0_service.is_ready,
        "yield_ready": yield_service.is_ready,
        "price_ready": price_service.is_ready,
        "calendar_ready": calendar_service.is_ready,
        "ndvi_ready": ndvi_service.is_ready,
        "market_ready": market_service.is_ready,
        "disease_ready": disease_service.is_ready,
        "rain_ready": rain_service.is_ready,
        "rain_error": rain_service.load_error,
        "b1_ready": True,
        "b2_ready": True,
        "voice_asr_ready": voice_service._asr is not None,
        "anomaly_thresholds_ready": True,
        "anomaly_statistical_model_loaded": anomaly_service.statistical_model_loaded,
        "knowledge_ready": knowledge_service.is_ready,
        "knowledge_chunks": len(knowledge_service.chunks),
        "agents_ready": True,
    }


@app.post("/yield/predict")
def predict_yield(crop: str = "Millet", region: str = "Kaolack", year: int = 2025, area_ha: float = 1000.0):
    return _serialize_resp(yield_service.predict(crop=crop, region=region, year=year, area_ha=area_ha))


@app.post("/price/predict")
def predict_price(commodity: str = "Onions", market: str = "Tilene", region: str = "Dakar", year: int = 2026, month: int = 11):
    return _serialize_resp(price_service.predict(commodity=commodity, market=market, region=region, year=year, month=month))


@app.get("/market/clusters")
def market_clusters(top_n: int = Query(5, ge=1, le=50)):
    return _serialize_resp(market_service.cheapest_markets(top_n=top_n))


@app.post("/disease/predict")
def predict_disease(image_path: str):
    return _serialize_resp(disease_service.predict_image(Path(image_path)))


@app.post("/disease/predict-bytes")
def predict_disease_bytes(req: DiseaseImageBytesRequest):
    try:
        raw = decode_bounded_base64(req.image_base64, MAX_IMAGE_BYTES, label="image")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_resp(disease_service.predict_image_bytes(raw))


@app.post("/b1/irrigation/predict")
def predict_b1_irrigation(req: FeaturesCropRequest):
    return _serialize_resp(b1_service.predict({**req.features, "crop_type": req.crop}))


@app.post("/b2/water-savings/estimate")
def estimate_b2_savings(recommended_mm: float, traditional_baseline_mm: float = 8.0, area_ha: float = 1.0):
    return _serialize_resp(b2_service.estimate(recommended_mm, traditional_baseline_mm, area_ha))


class VoiceTranscribeRequest(BaseModel):
    audio_base64: str = Field(..., min_length=1)
    content_type: str = Field("audio/wav", max_length=64)
    duration_s: float = Field(1.0, gt=0.0, le=300.0)
    language_hint: str = Field("wo", max_length=16)
    load_model: bool = False


class VoiceTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    load_model: bool = False


@app.post("/voice/transcribe")
def voice_transcribe(req: VoiceTranscribeRequest):
    try:
        raw = decode_bounded_base64(req.audio_base64, MAX_AUDIO_BYTES, label="audio")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    allow_load = bool(req.load_model and _ALLOW_DYNAMIC_DOWNLOAD)
    return voice_service.transcribe(
        raw, content_type=req.content_type, duration_s=req.duration_s,
        language_hint=req.language_hint, load_model=allow_load,
    )


@app.post("/voice/synthesize")
def voice_synthesize(req: VoiceTextRequest):
    allow_load = bool(req.load_model and _ALLOW_DYNAMIC_DOWNLOAD)
    return voice_service.synthesize(req.text, load_model=allow_load)


@app.post("/voice/intent")
def voice_intent(req: VoiceTextRequest):
    return interpret_wolof_text(req.text)


@app.post("/rain/predict")
def predict_rain(req: SoilPredictRequest):
    return _serialize_resp(rain_service.predict(req.features))


@app.post("/anomaly/detect")
def detect_anomaly(req: FeaturesCropRequest):
    return _serialize_resp(anomaly_service.detect(req.features))


@app.get("/mlops/registry")
def mlops_registry():
    return registry.status()


@app.post("/soil/predict")
def predict_soil(req: SoilPredictRequest):
    return _serialize_resp(soil_service.predict(req.features))


@app.post("/et0/predict")
def predict_et0(req: SoilPredictRequest):
    return _serialize_resp(et0_service.predict(req.features))


@app.post("/calendar/predict")
def predict_calendar(crop: str = "tomate", day_after_planting: int = 45):
    return _serialize_resp(calendar_service.predict(crop=crop, day_after_planting=day_after_planting))


@app.post("/ndvi/anomaly")
def predict_ndvi_anomaly(req: FeaturesCropRequest):
    return _serialize_resp(ndvi_service.predict(req.features))


@app.post("/knowledge/search")
def search_knowledge(req: KnowledgeSearchRequest):
    return _serialize_resp(knowledge_service.search(req.query, top_k=req.top_k, domain=req.domain))


@app.post("/agents/monitor")
def agents_monitor(req: FeaturesCropRequest):
    risk, level, alerts = monitoring_engine.assess(req.features)
    return {
        "risk": risk,
        "level": level.value,
        "alerts": [
            {
                "level": a.level.value,
                "category": a.category,
                "message": a.message,
                "confidence": a.confidence,
                "action": a.action,
                "escalate": a.escalate,
            }
            for a in alerts
        ],
    }


@app.post("/agents/irrigate")
def agents_irrigate(req: FeaturesCropRequest):
    rec = irrigation_engine.recommend(req.features, crop=req.crop, area_ha=req.area_ha)
    return {
        "decision": rec.decision.value,
        "dose_mm": rec.dose_mm,
        "confidence": rec.confidence,
        "reasoning": rec.reasoning,
        "hard_stop": rec.hard_stop,
        "hard_stop_reason": rec.hard_stop_reason,
    }


@app.post("/agents/assistant")
def agents_assistant(req: OrchestratorAskRequest):
    return assistant_service.ask(req.query, features=req.features, crop=req.crop)


@app.post("/orchestrator/ask")
def orchestrator_ask(req: OrchestratorAskRequest):
    resp = orchestrator.answer(req.query, req.features, crop=req.crop)
    return {
        "intent": resp.intent,
        "answer": resp.answer,
        "confidence": resp.confidence,
        "confidence_level": resp.confidence_level.value,
        "components_called": resp.components_called,
        "latency_ms": resp.latency_ms,
        "warnings": resp.warnings,
        "abstentions": resp.abstentions,
        "escalate": resp.escalate,
    }


@app.post("/orchestrator/monitor")
def orchestrator_monitor(req: FeaturesCropRequest):
    resp = orchestrator.monitor(req.features)
    return {
        "intent": resp.intent,
        "answer": resp.answer,
        "confidence": resp.confidence,
        "confidence_level": resp.confidence_level.value,
        "components_called": resp.components_called,
        "latency_ms": resp.latency_ms,
        "warnings": resp.warnings,
        "escalate": resp.escalate,
    }


@app.post("/orchestrator/recommend")
def orchestrator_recommend(req: FeaturesCropRequest):
    resp = orchestrator.recommend(req.features, crop=req.crop)
    return {
        "intent": resp.intent,
        "answer": resp.answer,
        "confidence": resp.confidence,
        "confidence_level": resp.confidence_level.value,
        "components_called": resp.components_called,
        "latency_ms": resp.latency_ms,
        "warnings": resp.warnings,
        "abstentions": resp.abstentions,
        "escalate": resp.escalate,
    }


@app.post("/orchestrator/escalate")
def orchestrator_escalate(context: Dict[str, Any]):
    return orchestrator.escalate(context)


@app.get("/db/collections")
def db_collections():
    cols = local_db.list_collections()
    return {"total_collections": len(cols), "collections": cols}


@app.get("/db/{collection}")
def db_query(collection: str, limit: int = 50, offset: int = 0):
    res = local_db.query(collection, limit=limit, offset=offset)
    if res is None:
        raise HTTPException(status_code=404, detail=f"Collection inconnue: {collection}")
    return res
