"""SmartAgriRuntime — point d'entrée unifié du runtime IA local SmartAgri (9/9 Classe A)."""

from typing import Any, Dict

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
from rag.knowledge_service import KnowledgeService
from agents.monitoring.monitoring_engine import MonitoringEngine
from agents.irrigation.irrigation_engine import IrrigationEngine
from agents.assistant.assistant_service import AssistantService
from agents.orchestrator.orchestrator import SmartAgriOrchestrator, OrchestratorResponse


class SmartAgriRuntime:
    """Assemble et expose tous les composants locaux SmartAgri AI (A1–A9, RAG, Agents)."""

    def __init__(self, knowledge_mode: str = "auto"):
        self.soil = SoilNowcastService()
        self.et0_svc = ET0ForecastService()
        self.rain = RainIntelligenceService()
        self.anomaly = AnomalyService()
        self.yield_svc = YieldForecastService()
        self.price_svc = PriceForecastService()
        self.calendar_svc = CropCalendarService()
        self.ndvi_svc = NDVIAnomalyService()
        self.market_svc = MarketClusteringService()
        self.disease_svc = DiseaseDetectionService()
        self.b1_irrigation = B1IrrigationMLService()
        self.b2_water_savings = B2WaterSavingsService()
        self.knowledge = KnowledgeService(mode=knowledge_mode)
        self.monitoring = MonitoringEngine(self.soil, self.rain, self.anomaly)
        self.irrigation = IrrigationEngine(self.soil, self.rain)
        self.assistant = AssistantService(self.knowledge, self.soil, self.irrigation)
        self.orchestrator = SmartAgriOrchestrator(
            self.soil, self.rain, self.anomaly,
            self.knowledge, self.monitoring, self.irrigation,
            yield_svc=self.yield_svc,
            price_svc=self.price_svc,
            market_svc=self.market_svc,
            et0_svc=self.et0_svc,
            calendar_svc=self.calendar_svc,
            ndvi_svc=self.ndvi_svc,
        )

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok" if (self.soil.is_ready and self.knowledge.is_ready) else "degraded",
            "soil_ready": self.soil.is_ready,
            "et0_ready": self.et0_svc.is_ready,
            "yield_ready": self.yield_svc.is_ready,
            "rain_ready": self.rain.is_ready,
            "price_ready": self.price_svc.is_ready,
            "calendar_ready": self.calendar_svc.is_ready,
            "ndvi_ready": self.ndvi_svc.is_ready,
            "market_ready": self.market_svc.is_ready,
            "anomaly_statistical_ready": self.anomaly.statistical_model_loaded,
            "anomaly_thresholds": len(self.anomaly.HARD_THRESHOLDS),
            "knowledge_ready": self.knowledge.is_ready,
            "knowledge_backend": self.knowledge.active_backend,
            "knowledge_chunks": len(self.knowledge.chunks),
            "agents_ready": True,
        }

    def answer(self, query: str, features: Dict[str, Any], crop: str = "oignon") -> OrchestratorResponse:
        return self.orchestrator.answer(query, features, crop=crop)

    def monitor(self, features: Dict[str, Any]) -> OrchestratorResponse:
        return self.orchestrator.monitor(features)

    def recommend(self, features: Dict[str, Any], crop: str = "oignon") -> OrchestratorResponse:
        return self.orchestrator.recommend(features, crop=crop)

    def escalate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self.orchestrator.escalate(context)

    def ask_assistant(self, question: str, features: Dict[str, Any] = None, crop: str = "oignon") -> Dict[str, Any]:
        return self.assistant.ask(question, features=features, crop=crop)
