"""SmartAgriOrchestrator (d'après 80_smartagri_ai_orchestrator.md et 82_smartagri_ai_runtime.md §3)."""

import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from runtime.types import ConfidenceLevel, ServiceResponse, confidence_level
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
from rag.knowledge_service import KnowledgeService
from agents.monitoring.monitoring_engine import MonitoringEngine, MonitoringAlert, AlertLevel
from agents.irrigation.irrigation_engine import IrrigationEngine


@dataclass
class OrchestratorResponse:
    intent: str
    answer: str
    confidence: float
    confidence_level: ConfidenceLevel
    components_called: List[str]
    latency_ms: float
    warnings: List[str]
    alerts: List[MonitoringAlert]
    abstentions: List[str]
    escalate: bool = False


class SmartAgriOrchestrator:
    """Point d'entrée unique — route vers les 6 services SmartAgri."""

    ROUTING = {
        "soil_status": ["soil_nowcast"],
        "soil_forecast": ["soil_nowcast", "rain_intelligence"],
        "irrigation": ["irrigation_engine", "soil_nowcast", "rain_intelligence"],
        "rain_forecast": ["rain_intelligence"],
        "anomaly_check": ["anomaly", "monitoring_engine"],
        "monitoring": ["monitoring_engine"],
        "crop_advice": ["knowledge", "soil_nowcast", "irrigation_engine"],
        "pest_info": ["knowledge"],
        "fertilizer": ["knowledge", "soil_nowcast"],
        "price": ["price_forecast", "market_clustering"],
        "yield_estimate": ["yield_forecast"],
        "yield_and_price": ["yield_forecast", "price_forecast"],
        "calendar": ["crop_calendar", "knowledge"],
        "ndvi_check": ["ndvi_anomaly", "monitoring_engine"],
        "et0_forecast": ["et0_forecast"],
        "general": ["knowledge"],
        "alert_check": ["monitoring_engine", "anomaly"],
        "full_report": [
            "soil_nowcast", "rain_intelligence", "anomaly",
            "monitoring_engine", "irrigation_engine", "knowledge",
        ],
    }

    def __init__(self, soil, rain, anomaly, knowledge, monitoring, irrigation,
                 yield_svc=None, price_svc=None, market_svc=None,
                 et0_svc=None, calendar_svc=None, ndvi_svc=None):
        self.svc = {
            "soil_nowcast": soil,
            "rain_intelligence": rain,
            "anomaly": anomaly,
            "knowledge": knowledge,
            "monitoring_engine": monitoring,
            "irrigation_engine": irrigation,
            "yield_forecast": yield_svc,
            "price_forecast": price_svc,
            "market_clustering": market_svc,
            "et0_forecast": et0_svc,
            "crop_calendar": calendar_svc,
            "ndvi_anomaly": ndvi_svc,
        }

    def answer(self, query: str, features: Dict[str, Any], crop: str = "oignon") -> OrchestratorResponse:
        t0 = time.perf_counter()
        intent = self._classify(query)
        if intent == "ambiguous":
            return OrchestratorResponse(
                intent="ambiguous",
                answer="Précisez votre demande : sol, cultures, météo, irrigation ou prix ?",
                confidence=0.25,
                confidence_level=ConfidenceLevel.LOW,
                components_called=[],
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
                warnings=[],
                alerts=[],
                abstentions=[],
                escalate=False,
            )
        if intent == "onboarding":
            return OrchestratorResponse(
                intent="onboarding",
                answer="Bienvenue sur SmartAgri92. Indiquez votre région et vos cultures pour commencer.",
                confidence=0.80,
                confidence_level=ConfidenceLevel.HIGH,
                components_called=["knowledge"],
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
                warnings=[],
                alerts=[],
                abstentions=[],
                escalate=False,
            )
        comps = self.ROUTING.get(intent, ["knowledge"])
        resps: Dict[str, ServiceResponse] = {}
        abstentions: List[str] = []
        warnings: List[str] = []

        call_features = {**features, "query": query}
        cache: Dict[str, ServiceResponse] = {}
        for c in comps:
            r = cache.get(c)
            if r is None:
                r = self._call(c, call_features, crop)
                cache[c] = r
            if r.abstained:
                abstentions.append(f"{c}: {r.abstention_reason}")
            else:
                resps[c] = r
                warnings.extend(r.warnings)

        if not resps and "knowledge" not in comps:
            kr = self._call("knowledge", call_features, crop)
            if not kr.abstained:
                resps["knowledge"] = kr

        conf = round(sum(r.confidence for r in resps.values()) / max(1, len(resps)), 4)
        ans = self._assemble(intent, resps, abstentions, crop)
        return OrchestratorResponse(
            intent=intent,
            answer=ans,
            confidence=conf,
            confidence_level=confidence_level(conf),
            components_called=list(resps.keys()),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            warnings=warnings,
            alerts=[],
            abstentions=abstentions,
            escalate=conf < 0.30,
        )

    def monitor(self, features: Dict[str, Any]) -> OrchestratorResponse:
        t0 = time.perf_counter()
        risk, level, alerts = self.svc["monitoring_engine"].assess(features)
        ar = self.svc["anomaly"].detect(features)
        conf = 0.85 if not ar.abstained else 0.60
        return OrchestratorResponse(
            intent="monitoring",
            answer=f"Risque: {risk:.2f} ({level.value})",
            confidence=conf,
            confidence_level=confidence_level(conf),
            components_called=["monitoring_engine", "anomaly"],
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            warnings=[a.message for a in alerts],
            alerts=alerts,
            abstentions=[],
            escalate=(level == AlertLevel.CRITICAL),
        )

    def recommend(self, features: Dict[str, Any], crop: str = "oignon") -> OrchestratorResponse:
        t0 = time.perf_counter()
        rec = self.svc["irrigation_engine"].recommend(features, crop)
        return OrchestratorResponse(
            intent="irrigation",
            answer=f"{rec.decision.value}, dose={rec.dose_mm}mm",
            confidence=rec.confidence,
            confidence_level=confidence_level(rec.confidence),
            components_called=["irrigation_engine", "soil_nowcast", "rain_intelligence"],
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            warnings=rec.reasoning,
            alerts=[],
            abstentions=[rec.hard_stop_reason] if rec.hard_stop else [],
            escalate=rec.hard_stop,
        )

    def escalate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "human_escalation",
            "reason": context.get("reason", "Confiance insuffisante"),
            "parcelle": context.get("cell_id", "?"),
            "contact": "conseiller@smartagri92.sn",
        }

    def _classify(self, q: str) -> str:
        ql = q.lower().strip()
        if ql in ("ca va pas", "ça va pas", "aide", "help"):
            return "ambiguous"
        if any(re.search(p, ql) for p in (r"\bbonjour\b", r"\bje commence\b", r"\bdébuter\b", r"\bcommencer\b")):
            return "onboarding"
        patterns = [
            ([r"\birrigu\w*", r"\barros\w*", r"\beau\b", r"\bdose\b", r"\blitres?\b"], "irrigation"),
            ([r"\bhumid\w*", r"\bsol\b", r"\bterre\b", r"\bsec\b", r"\bsèche\b", r"\bparcelle\w*"], "soil_forecast"),
            ([r"\bpluie\w*", r"\bpleuv\w*", r"\bprécip\w*"], "rain_forecast"),
            ([r"\banomal\w*", r"\bbizarre\b"], "anomaly_check"),
            ([r"\balerte\w*", r"\bdanger\w*", r"\brisque\w*"], "alert_check"),
            ([r"\brapport\b", r"\bbilan\b", r"\brésumé\b", r"\b[eé]tat des parcelles\b"], "full_report"),
            ([r"\bravageur\w*", r"\binsecte\w*", r"\bmaladie\w*"], "pest_info"),
            ([r"\bengrais\b", r"\bfertili\w*", r"\bnpk\b"], "fertilizer"),
            ([r"\brentable\w*"], "yield_and_price"),
            ([r"\brendement\w*", r"\br[eé]colte\w*", r"\bproduction\b"], "yield_estimate"),
            ([r"\bprix\b", r"\bmarch[eé]s?\b", r"\bvendre\b", r"\bacheter\b"], "price"),
            ([r"\bsatellite\w*", r"\bndvi\b", r"\bvégétation\b"], "ndvi_check"),
            ([r"\bet0\b", r"\bévapotranspiration\b"], "et0_forecast"),
            ([r"\bcalendrier\b", r"\bsemer\b", r"\bplanter\b", r"\bphase\b", r"\bstade\b"], "calendar"),
        ]
        for regexes, intent in patterns:
            if any(re.search(rx, ql) for rx in regexes):
                return intent
        return "general"

    def _call(self, name: str, features: Dict[str, Any], crop: str) -> ServiceResponse:
        s = self.svc.get(name)
        if s is None:
            return ServiceResponse(name, {}, 0.0, ConfidenceLevel.UNRELIABLE, abstained=True, abstention_reason="Service indisponible")
        if isinstance(s, SoilNowcastService):
            return s.predict(features)
        if isinstance(s, RainIntelligenceService):
            return s.predict(features)
        if isinstance(s, AnomalyService):
            return s.detect(features)
        if isinstance(s, KnowledgeService):
            return s.search(features.get("query", ""))
        if isinstance(s, MonitoringEngine):
            risk, level, al = s.assess(features)
            return ServiceResponse("monitoring", {"risk": risk, "level": level.value, "alerts": len(al)}, 0.80, ConfidenceLevel.HIGH)
        if isinstance(s, IrrigationEngine):
            r = s.recommend(features, crop)
            return ServiceResponse("irrigation", {"decision": r.decision.value, "dose": r.dose_mm}, r.confidence, confidence_level(r.confidence), r.reasoning)
        if isinstance(s, YieldForecastService):
            return s.predict(crop=crop, region=features.get("region", "Kaolack"), year=int(features.get("year", 2025)), area_ha=float(features.get("area_ha", 1000.0)))
        if isinstance(s, PriceForecastService):
            return s.predict(commodity=crop, market=features.get("market", "Tilene"), region=features.get("region", "Dakar"))
        if isinstance(s, MarketClusteringService):
            return s.cheapest_markets(top_n=3)
        if isinstance(s, ET0ForecastService):
            return s.predict(features)
        if isinstance(s, CropCalendarService):
            return s.predict(crop=crop, day_after_planting=int(features.get("day_after_planting", 45)))
        if isinstance(s, NDVIAnomalyService):
            return s.predict(features)
        return ServiceResponse(name, {}, 0.0, ConfidenceLevel.UNRELIABLE, abstained=True, abstention_reason="Type inconnu")

    def _assemble(self, intent: str, resps: Dict[str, ServiceResponse], abstentions: List[str], crop: str) -> str:
        parts = []
        if "soil_nowcast" in resps:
            v = resps["soil_nowcast"].values
            parts.append(f"Humidité: J+1={v.get('y_plus_1d', 0):.1f}%")
        if "rain_intelligence" in resps:
            v = resps["rain_intelligence"].values
            parts.append(f"Pluie J+1: {v.get('rain_1d_prob', 0)*100:.0f}%")
        if "irrigation_engine" in resps:
            v = resps["irrigation_engine"].values
            parts.append(f"Irrigation ({crop}): {v.get('decision', '?')} ({v.get('dose', 0)}mm)")
        if "yield_forecast" in resps:
            v = resps["yield_forecast"].values
            parts.append(f"Rendement ({v.get('crop', crop)}/{v.get('region', '')}): {v.get('yield_t_ha', 0)} t/ha")
        if "price_forecast" in resps:
            v = resps["price_forecast"].values
            parts.append(f"Prix ({v.get('commodity', crop)}/{v.get('market', '')}): {v.get('price_fcfa_kg', 0)} FCFA/kg")
        if "market_clustering" in resps:
            mkts = [m["market"] for m in resps["market_clustering"].values.get("cheapest_markets", [])]
            if mkts:
                parts.append(f"Marchés compétitifs: {', '.join(mkts)}")
        if "et0_forecast" in resps:
            v = resps["et0_forecast"].values
            parts.append(f"ET0 prévue: {v.get('et0_pred_mm', 0):.2f} mm/j")
        if "crop_calendar" in resps:
            v = resps["crop_calendar"].values
            parts.append(f"Stade ({v.get('crop', crop)}): {v.get('growth_stage', '?')} (Kc={v.get('kc_recommended', '?')})")
        if "ndvi_anomaly" in resps:
            v = resps["ndvi_anomaly"].values
            etat = "anomalie détectée" if v.get("ndvi_anomaly") else "normal"
            parts.append(f"NDVI: {v.get('ndvi_mean', 0):.2f} ({etat}, p={v.get('anomaly_prob', 0)*100:.0f}%)")
        if "anomaly" in resps:
            v = resps["anomaly"].values
            parts.append(f"Anomalies: {v.get('count', 0)} ({v.get('max_severity', 'NORMAL')})")
        if "monitoring_engine" in resps:
            v = resps["monitoring_engine"].values
            parts.append(f"Surveillance: risque {v.get('risk', 0):.2f} ({v.get('level', 'NORMAL')}, {v.get('alerts', 0)} alerte(s))")
        if "knowledge" in resps:
            top = resps["knowledge"].values.get("results", [{}])[0]
            if top:
                parts.append(f"Source RAG: {top.get('doc_source', '')}")
        if abstentions:
            parts.append(f"Indisponible: {len(abstentions)} composant(s)")
        return " | ".join(parts) if parts else "Consulter un conseiller."
