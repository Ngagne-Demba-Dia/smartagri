"""Tests complets du runtime IA local SmartAgri (Phases 0 → 5)."""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYDEPS = ROOT / ".pydeps"
if PYDEPS.exists() and str(PYDEPS) not in sys.path:
    sys.path.append(str(PYDEPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mlops.registry.registry import LocalModelRegistry
from mlops.retraining.validate_metrics import run_mlops_checks
from runtime.soil_nowcast_service import SoilNowcastService
from runtime.rain_intelligence_service import RainIntelligenceService
from runtime.anomaly_service import AnomalyService
from rag.knowledge_service import KnowledgeService
from agents.monitoring.monitoring_engine import MonitoringEngine, AlertLevel
from agents.irrigation.irrigation_engine import IrrigationEngine, IrrigationDecision
from agents.assistant.assistant_service import AssistantService
from agents.orchestrator.orchestrator import SmartAgriOrchestrator
from api import app as api_app


SAMPLE_SENEGAL_FEATURES = {
    "t_min_c": 22.5,
    "t_max_c": 34.0,
    "t_mean_c": 28.2,
    "rh_mean_pct": 58.0,
    "wind_2m_ms": 2.4,
    "solar_rad_mj_m2": 21.5,
    "pressure_hpa": 1012.0,
    "rain_mm": 0.0,
    "rain_chirps_mm": 0.0,
    "et0_pm_mm": 5.1,
    "rain_nasa_sum_3d_mm": 4.2,
    "rain_nasa_sum_7d_mm": 12.0,
    "rain_nasa_sum_14d_mm": 25.0,
    "rain_chirps_sum_3d_mm": 3.8,
    "rain_chirps_sum_7d_mm": 11.5,
    "rain_chirps_sum_14d_mm": 24.0,
    "et0_pm_mean_7d_mm": 5.0,
    "doy_sin": 0.65,
    "doy_cos": -0.76,
    "sand_pct": 72.0,
    "clay_pct": 14.0,
    "soc_g_kg": 6.5,
    "ph_h2o": 6.2,
    "bulk_density_g_cm3": 1.48,
    "fc_ptf_pct": 22.0,
    "wp_ptf_pct": 10.0,
    "share_crop": 0.55,
    "share_tree": 0.15,
    "share_bare": 0.20,
    "share_built": 0.02,
}


def test_phase0_mlops_registry():
    st = LocalModelRegistry().status()
    assert st["total_models"] == 9
    assert st["ready_models"] == 9
    assert st["models"]["A1_SoilNowcast"]["ready_local"] is True
    assert st["models"]["A1_SoilNowcast"]["native_artifacts"] == 15
    for k in st["models"]:
        assert st["models"][k]["ready_local"] is True, f"{k} non prêt localement"


def test_phase1_soil_nowcast_inference_and_abstention():
    svc = SoilNowcastService()
    assert svc.is_ready, f"SoilNowcast non prêt: {svc.load_error}"
    resp = svc.predict(SAMPLE_SENEGAL_FEATURES)
    assert not resp.abstained
    assert 0.0 <= resp.values["y_plus_1d"] <= 100.0
    assert 0.0 <= resp.values["y_plus_2d"] <= 100.0
    assert 0.0 <= resp.values["y_plus_3d"] <= 100.0
    assert resp.confidence > 0.5

    abstain = svc.predict({"t_min_c": 22.0})
    assert abstain.abstained is True


def test_phase2_knowledge_service_and_eval():
    svc = KnowledgeService()
    assert svc.is_ready, f"KnowledgeService non prêt: {svc.load_error}"
    assert len(svc.chunks) >= 527

    eval_csv = ROOT / "rag" / "evaluation" / "smartagri_knowledge_eval.csv"
    with eval_csv.open("r", encoding="utf-8", newline="") as fh:
        queries = list(csv.DictReader(fh))
    assert len(queries) == 20

    hits = 0
    for q in queries:
        resp = svc.search(q["query"], top_k=5)
        if not resp.abstained and resp.values.get("results"):
            hits += 1
    recall_proxy = hits / len(queries)
    assert recall_proxy >= 0.75, f"Recall@5 proxy trop bas: {recall_proxy}"


def test_phase3_agents_and_orchestrator():
    soil = SoilNowcastService()
    rain = RainIntelligenceService(model=None)
    anomaly = AnomalyService()
    knowledge = KnowledgeService()
    mon = MonitoringEngine(soil, rain, anomaly)
    irr = IrrigationEngine(soil, rain)
    asst = AssistantService(knowledge, soil, irr)
    orch = SmartAgriOrchestrator(soil, rain, anomaly, knowledge, mon, irr)

    risk, level, _ = mon.assess(SAMPLE_SENEGAL_FEATURES)
    assert level == AlertLevel.NORMAL
    assert risk == 0.0

    rec_rain = irr.recommend({**SAMPLE_SENEGAL_FEATURES, "rain_mm": 12.0}, crop="oignon")
    assert rec_rain.decision == IrrigationDecision.DELAY
    assert rec_rain.hard_stop is True

    ans = asst.ask("Quel Kc pour le riz irrigué ?", SAMPLE_SENEGAL_FEATURES, crop="riz")
    assert "SoilNowcast" in ans["answer"]
    assert len(ans["sources"]) >= 1

    o_resp = orch.answer("Dois-je irriguer mon oignon demain ?", SAMPLE_SENEGAL_FEATURES, crop="oignon")
    assert o_resp.intent == "irrigation"
    assert "soil_nowcast" in o_resp.components_called


def test_phase4_fastapi_endpoints():
    h = api_app.health()
    assert h["status"] == "ok"
    assert h["soil_nowcast_ready"] is True
    assert h["knowledge_ready"] is True
    assert h["agents_ready"] is True

    reg = api_app.mlops_registry()
    assert reg["total_models"] == 9

    o = api_app.orchestrator_ask(
        api_app.OrchestratorAskRequest(
            query="Quelle humidité du sol demain ?",
            features=SAMPLE_SENEGAL_FEATURES,
        )
    )
    assert o["intent"] == "soil_forecast"
    assert o["confidence"] > 0.5


def test_phase5_mlops_validation():
    res = run_mlops_checks()
    assert res["metrics_csv_total"] == 24
    assert res["metrics_csv_valid"] == 24
    assert res["champions_registered"] == 9
    assert res["sha256_manifest_entries"] == 169


def test_rain_intelligence_service_and_api():
    rain = RainIntelligenceService()
    assert len(rain.FEATURES) == 30
    assert rain.is_ready, f"RainIntelligence non prêt: {rain.load_error}"
    resp = rain.predict(SAMPLE_SENEGAL_FEATURES)
    assert not resp.abstained
    assert 0.0 <= resp.values["rain_1d_prob"] <= 1.0
    assert 0.0 <= resp.values["rain_2d_prob"] <= 1.0
    assert 0.0 <= resp.values["rain_3d_prob"] <= 1.0

    api_resp = api_app.predict_rain(api_app.SoilPredictRequest(features=SAMPLE_SENEGAL_FEATURES))
    assert api_resp["service"] == "rain_intelligence"
    assert api_resp["abstained"] is False


def test_a2_a6_a7_a8_services_and_api():
    from runtime.runtime import SmartAgriRuntime

    rt = SmartAgriRuntime()
    assert rt.et0_svc.is_ready
    assert rt.calendar_svc.is_ready
    assert rt.ndvi_svc.is_ready
    assert rt.anomaly.statistical_model_loaded

    et0_r = rt.et0_svc.predict(SAMPLE_SENEGAL_FEATURES)
    assert not et0_r.abstained and et0_r.values["et0_pred_mm"] > 0

    cal_r = rt.calendar_svc.predict(crop="tomate", day_after_planting=45)
    assert not cal_r.abstained and cal_r.values["growth_stage"]

    ndvi_r = rt.ndvi_svc.predict(SAMPLE_SENEGAL_FEATURES)
    assert not ndvi_r.abstained and "anomaly_prob" in ndvi_r.values

    assert api_app.predict_et0(api_app.SoilPredictRequest(features=SAMPLE_SENEGAL_FEATURES))["values"]["et0_pred_mm"] > 0
    assert api_app.predict_calendar(crop="tomate", day_after_planting=45)["values"]["growth_stage"]
    assert "anomaly_prob" in api_app.predict_ndvi_anomaly(api_app.FeaturesCropRequest(features=SAMPLE_SENEGAL_FEATURES))["values"]


def test_anomaly_service_thresholds_api_and_orchestrator():
    anom = AnomalyService()
    # Cas normal
    normal = anom.detect(SAMPLE_SENEGAL_FEATURES)
    assert not normal.abstained
    assert normal.values["count"] == 0
    assert normal.values["max_severity"] == "NORMAL"

    # Cas critiques multi-anomalies (canicule + inondation + sécheresse)
    extreme_features = {
        **SAMPLE_SENEGAL_FEATURES,
        "t_max_c": 44.5,
        "rain_chirps_sum_3d_mm": 120.0,
        "soil_wetness_root_pct": 11.0,
    }
    crit = anom.detect(extreme_features)
    assert crit.values["count"] == 3
    assert crit.values["max_severity"] == "CRITICAL"

    api_resp = api_app.detect_anomaly(api_app.FeaturesCropRequest(features=extreme_features))
    assert api_resp["values"]["count"] == 3
    assert api_resp["values"]["max_severity"] == "CRITICAL"

    # Intégration orchestrateur monitor()
    soil = SoilNowcastService()
    rain = RainIntelligenceService()
    knowledge = KnowledgeService()
    mon = MonitoringEngine(soil, rain, anom)
    irr = IrrigationEngine(soil, rain)
    orch = SmartAgriOrchestrator(soil, rain, anom, knowledge, mon, irr)
    m_resp = orch.monitor(extreme_features)
    assert len(m_resp.alerts) >= 3


def test_smartagri_runtime_all_4_flows():
    from runtime.runtime import SmartAgriRuntime

    rt = SmartAgriRuntime()
    h = rt.health()
    assert h["status"] == "ok"
    assert h["knowledge_backend"] == "e5_large+faiss"

    a = rt.answer("Dois-je irriguer ?", SAMPLE_SENEGAL_FEATURES, crop="oignon")
    assert a.intent == "irrigation"

    m = rt.monitor({**SAMPLE_SENEGAL_FEATURES, "t_max_c": 44.0})
    assert m.intent == "monitoring"
    assert len(m.warnings) >= 1

    r = rt.recommend({**SAMPLE_SENEGAL_FEATURES, "rain_mm": 10.0}, crop="oignon")
    assert r.escalate is True

    e = rt.escalate({"reason": "Test escalade", "cell_id": "S30"})
    assert e["type"] == "human_escalation"

    api_m = api_app.orchestrator_monitor(api_app.FeaturesCropRequest(features=SAMPLE_SENEGAL_FEATURES))
    assert api_m["intent"] == "monitoring"
    api_r = api_app.orchestrator_recommend(api_app.FeaturesCropRequest(features=SAMPLE_SENEGAL_FEATURES))
    assert api_r["intent"] == "irrigation"
    api_e = api_app.orchestrator_escalate({"reason": "API test", "cell_id": "C1"})
    assert api_e["type"] == "human_escalation"


def test_a3_a5_a9_services_orchestrator_and_api():
    from runtime.runtime import SmartAgriRuntime

    rt = SmartAgriRuntime()
    assert rt.yield_svc.is_ready
    assert rt.price_svc.is_ready
    assert rt.market_svc.is_ready

    y_resp = rt.yield_svc.predict(crop="Millet", region="Kaolack", year=2025)
    assert not y_resp.abstained
    assert y_resp.values["yield_t_ha"] > 0

    p_resp = rt.price_svc.predict(commodity="Onions", market="Tilene", region="Dakar", year=2026, month=11)
    assert not p_resp.abstained
    assert p_resp.values["price_fcfa_kg"] > 0

    m_resp = rt.market_svc.cheapest_markets(top_n=3)
    assert not m_resp.abstained
    assert len(m_resp.values["cheapest_markets"]) == 3

    # Orchestrator S07 / S08 / S24
    s07 = rt.answer("Rendement mil cette année ?", SAMPLE_SENEGAL_FEATURES, crop="mil")
    assert "yield_forecast" in s07.components_called
    s08 = rt.answer("Prix oignon va monter ?", SAMPLE_SENEGAL_FEATURES, crop="oignon")
    assert "price_forecast" in s08.components_called
    s24 = rt.answer("Oignon rentable cette année ?", SAMPLE_SENEGAL_FEATURES, crop="oignon")
    assert "yield_forecast" in s24.components_called and "price_forecast" in s24.components_called

    # API endpoints
    assert api_app.predict_yield(crop="Millet", region="Kaolack")["values"]["yield_t_ha"] > 0
    assert api_app.predict_price(commodity="Onions", market="Tilene")["values"]["price_fcfa_kg"] > 0
    assert len(api_app.market_clusters(top_n=3)["values"]["cheapest_markets"]) == 3

    # A8 Senegal GLIDE disaster events dataset present
    glide = ROOT / "datasets" / "real" / "sen_glide_events.csv"
    assert glide.exists() and glide.stat().st_size > 5000

    # Local SQLite DB endpoint (/db/collections & /db/{collection})
    cols = api_app.db_collections()
    assert cols["total_collections"] >= 27
    q = api_app.db_query("smartagri_knowledge_chunks", limit=5, offset=0)
    assert q["total_rows"] == 527 and len(q["items"]) == 5


def test_b4_disease_detection_service_and_api():
    from runtime.disease_service import DiseaseDetectionService

    svc = DiseaseDetectionService()
    assert svc.is_ready, f"B4 non prêt: {svc.load_error}"
    sample_dir = ROOT / "datasets" / "class_b" / "rice_disease" / "images" / "Rice___Healthy"
    sample_img = next(sample_dir.glob("*.jpg"))
    resp = svc.predict_image(sample_img)
    assert not resp.abstained
    assert resp.values["predicted_class"] in svc.RECOMMENDATIONS
    assert resp.confidence > 0.25

    api_resp = api_app.predict_disease(str(sample_img))
    assert api_resp["service"] == "disease_detection"
    assert not api_resp["abstained"]


def test_irrigation_15d_preharvest_and_a8_glide_calibration():
    soil = SoilNowcastService()
    rain = RainIntelligenceService()
    irr = IrrigationEngine(soil, rain)

    # Blocage pré-récolte <= 15 jours
    rec_15d = irr.recommend({**SAMPLE_SENEGAL_FEATURES, "days_to_harvest": 10}, crop="oignon")
    assert rec_15d.decision == IrrigationDecision.NO_IRRIGATION
    assert rec_15d.dose_mm == 0.0
    assert rec_15d.hard_stop is True
    assert "15" in rec_15d.hard_stop_reason

    # A8 calibration GLIDE Sénégal (35 événements + seuil WATCH abaissé sur Matam)
    anom = AnomalyService()
    assert len(anom.glide_events) == 35
    watch = anom.detect({**SAMPLE_SENEGAL_FEATURES, "region": "Matam", "rain_chirps_sum_3d_mm": 55.0})
    assert watch.values["max_severity"] == "WARNING"
    assert watch.values["glide_events_calibrated"] == 35


def test_wolof_voice_service_and_lexicon():
    import base64
    import io
    import wave
    import numpy as np
    from voice.wolof_lexicon import interpret_wolof_text
    from voice.wolof_voice_service import WolofVoiceService

    interp = interpret_wolof_text("Ndox mi ci soble bi, taw dina am?")
    assert interp["detected_crop"] == "oignon"
    assert "irriguer" in interp["normalized_fr"]
    assert "pluie" in interp["normalized_fr"]

    # Mini WAV valide 16 kHz mono 0.2 s
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(np.zeros(3200, dtype=np.int16).tobytes())
    wav_bytes = buf.getvalue()

    svc = WolofVoiceService(
        asr_pipeline=lambda _: {"text": "Ndox mi ci ceeb bi"},
        tts_pipeline=lambda _: {"audio": np.zeros(1600, dtype=np.float32), "sampling_rate": 16000},
    )
    tr = svc.transcribe(wav_bytes, duration_s=0.2, language_hint="wo")
    assert not tr["abstained"]
    assert tr["detected_crop"] == "riz"
    assert tr["audio_info"]["valid_wav"] is True

    sy = svc.synthesize("Jërëjëf, soble bi baax na.")
    assert not sy["abstained"]
    assert len(base64.b64decode(sy["audio_base64"])) > 44

    # API /voice/intent
    vi = api_app.voice_intent(api_app.VoiceTextRequest(text="Njëg tamaate bi ci marse"))
    assert vi["detected_crop"] == "tomate"
    assert "prix" in vi["normalized_fr"]

    # Corpus sample present
    corpus = ROOT / "datasets" / "voice" / "wolof_corpus_sample.jsonl"
    assert corpus.exists() and corpus.stat().st_size > 10000


def test_b1_b2_and_enriched_rag():
    from runtime.class_b_services import B1IrrigationMLService, B2WaterSavingsService

    b1 = B1IrrigationMLService()
    r1 = b1.predict({**SAMPLE_SENEGAL_FEATURES, "crop_type": "oignon", "days_to_harvest": 10})
    assert r1.values["irrigation_need_mm"] == 0.0
    assert r1.values["mode"] == "preharvest_block_15d"

    r2 = b1.predict({**SAMPLE_SENEGAL_FEATURES, "crop_type": "tomate", "soil_moisture_10cm_pct": 25.0})
    assert r2.values["irrigation_need_mm"] > 0.0

    b2 = B2WaterSavingsService()
    s = b2.estimate(recommended_mm=3.5, traditional_baseline_mm=8.0, area_ha=2.0)
    assert s.values["saved_mm"] == 4.5
    assert s.values["saved_m3"] == 90.0
    assert s.values["pct_saved"] > 50.0

    ks = KnowledgeService()
    assert len(ks.chunks) >= 535
    res = ks.search("stopper irrigation oignon 15 jours avant recolte Niayes", top_k=3)
    assert not res.abstained
    assert any("ISRA_ANCAR_Oignon_Niayes" in r["doc_source"] for r in res.values["results"])


def test_security_and_architecture_hardening():
    from runtime.disease_service import DiseaseDetectionService
    from runtime.runtime import SmartAgriRuntime

    # 1. Path traversal bloqué sur B4 + inférence en mémoire via octets
    ds = DiseaseDetectionService()
    traversal = ds.predict_image(ROOT / "api" / "app.py")
    assert traversal.abstained is True
    sample_dir = ROOT / "datasets" / "class_b" / "rice_disease" / "images" / "Rice___Healthy"
    sample_img = next(sample_dir.glob("*.jpg"))
    by_bytes = ds.predict_image_bytes(sample_img.read_bytes())
    assert not by_bytes.abstained
    assert by_bytes.values["predicted_class"] in ds.RECOMMENDATIONS

    # 2. Orchestrator: pas de faux positifs sous-chaîne + _assemble couvre ET0/NDVI/Calendrier
    rt = SmartAgriRuntime()
    assert rt.orchestrator._classify("désolé, quelle solution pour le niveau de sécurité ?") == "general"
    et0_ans = rt.answer("Quelle est l'ET0 aujourd'hui ?", SAMPLE_SENEGAL_FEATURES)
    assert "ET0 prévue" in et0_ans.answer
    cal_ans = rt.answer("Quel stade du calendrier cultural ?", SAMPLE_SENEGAL_FEATURES, crop="tomate")
    assert "Stade" in cal_ans.answer

    # 3. Yield fallback avertit et baisse la confiance ; Price utilise la vraie catégorie WFP
    y_unk = rt.yield_svc.predict(crop="Tomate", region="Kaolack")
    assert y_unk.values["fallback_used"] is True
    assert len(y_unk.warnings) >= 1
    assert y_unk.confidence < rt.yield_svc.BASELINE_R2

    p_onion = rt.price_svc.predict(commodity="Onions", market="Tilene", region="Dakar")
    assert p_onion.values["category"] == "vegetables and fruits"

    # 4. MonitoringEngine: pas de KeyError sur anomalie statistique + escalade CRITICAL sur sécheresse extrême
    class _FakeStatAnom:
        def detect(self, _f):
            from runtime.types import ConfidenceLevel, ServiceResponse
            return ServiceResponse(
                "anomaly",
                {"anomalies": [{"type": "statistical", "method": "IsolationForest", "score": -0.42, "severity": "CRITICAL"}], "count": 1, "max_severity": "CRITICAL"},
                0.85,
                ConfidenceLevel.HIGH,
            )

    class _FakeDrySoil:
        def predict(self, _f):
            from runtime.types import ConfidenceLevel, ServiceResponse
            return ServiceResponse("soil_nowcast", {"y_plus_1d": 10.0}, 0.83, ConfidenceLevel.HIGH)

    mon = MonitoringEngine(_FakeDrySoil(), rt.rain, _FakeStatAnom())
    risk, lvl, alerts = mon.assess({**SAMPLE_SENEGAL_FEATURES, "et0_pm_mm": 7.5})
    assert lvl == AlertLevel.CRITICAL
    assert any(a.escalate for a in alerts)
    assert any("-0.42" in a.message for a in alerts)
