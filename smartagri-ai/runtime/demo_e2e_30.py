"""Démonstrateur local complet — exécute les 30 scénarios de 81_ai_execution_flows.md."""

import json
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
PYDEPS = ROOT / ".pydeps"
if PYDEPS.exists() and str(PYDEPS) not in sys.path:
    sys.path.append(str(PYDEPS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.runtime import SmartAgriRuntime


BASE_FEATURES: Dict[str, Any] = {
    "t_min_c": 22.5, "t_max_c": 34.0, "t_mean_c": 28.2, "rh_mean_pct": 58.0,
    "wind_2m_ms": 2.4, "solar_rad_mj_m2": 21.5, "pressure_hpa": 1012.0,
    "rain_mm": 0.0, "rain_chirps_mm": 0.0, "et0_pm_mm": 5.1,
    "rain_nasa_sum_3d_mm": 4.2, "rain_nasa_sum_7d_mm": 12.0, "rain_nasa_sum_14d_mm": 25.0,
    "rain_chirps_sum_3d_mm": 3.8, "rain_chirps_sum_7d_mm": 11.5, "rain_chirps_sum_14d_mm": 24.0,
    "et0_pm_mean_7d_mm": 5.0, "doy_sin": 0.65, "doy_cos": -0.76,
    "sand_pct": 72.0, "clay_pct": 14.0, "soc_g_kg": 6.5, "ph_h2o": 6.2,
    "bulk_density_g_cm3": 1.48, "fc_ptf_pct": 65.0, "wp_ptf_pct": 10.0,
    "share_crop": 0.55, "share_tree": 0.15, "share_bare": 0.20, "share_built": 0.02,
}


SCENARIOS: List[Dict[str, Any]] = [
    {"id": "S01", "title": "Irrigation simple, saison sèche", "mode": "answer", "query": "Dois-je irriguer aujourd'hui ?", "crop": "tomate", "features": BASE_FEATURES},
    {"id": "S02", "title": "Pluie imminente, reporter", "mode": "recommend", "query": "Je voulais irriguer demain ?", "crop": "oignon", "features": {**BASE_FEATURES, "rain_mm": 12.0}},
    {"id": "S03", "title": "Alerte sécheresse critique", "mode": "monitor", "query": "Etat des parcelles ?", "crop": "mil", "features": {**BASE_FEATURES, "soil_wetness_root_pct": 12.0, "et0_pm_mm": 6.2}},
    {"id": "S04", "title": "Question agronomique générale", "mode": "answer", "query": "Comment preparer le sol pour l'oignon ?", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S05", "title": "Conflit SoilNowcast vs Rain", "mode": "answer", "query": "Sol sec mais il a plu hier ?", "crop": "carotte", "features": {**BASE_FEATURES, "rain_mm": 12.0}},
    {"id": "S06", "title": "Excès d'eau, engorgement", "mode": "monitor", "query": "Il pleut beaucoup, je m'inquiète", "crop": "riz", "features": {**BASE_FEATURES, "rain_chirps_sum_3d_mm": 115.0}},
    {"id": "S07", "title": "Prévision rendement national (A3)", "mode": "answer", "query": "Rendement mil cette année ?", "crop": "mil", "features": BASE_FEATURES},
    {"id": "S08", "title": "Prix marché et tendance (A5/A9)", "mode": "answer", "query": "Prix oignon va monter ?", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S09", "title": "NDVI anormal, stress végétatif (A7)", "mode": "answer", "query": "Satellite montre anomalie ?", "crop": "arachide", "features": BASE_FEATURES},
    {"id": "S10", "title": "Phase culturale et Kc (A6)", "mode": "answer", "query": "Ma tomate est a quelle phase ?", "crop": "tomate", "features": BASE_FEATURES},
    {"id": "S11", "title": "Abstention, manque de données", "mode": "answer", "query": "Etat de mon sol ?", "crop": "oignon", "features": {"t_min_c": 22.0}},
    {"id": "S12", "title": "Rapport complet parcellaire", "mode": "answer", "query": "Rapport complet parcelle 4521", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S13", "title": "Canicule Niayes (T_max > 42C)", "mode": "monitor", "query": "Monitoring canicule", "crop": "tomate", "features": {**BASE_FEATURES, "t_max_c": 44.0, "et0_pm_mm": 7.8}},
    {"id": "S14", "title": "Gel Niayes (T_min < 10C)", "mode": "monitor", "query": "Monitoring gel", "crop": "tomate", "features": {**BASE_FEATURES, "t_min_c": 8.5}},
    {"id": "S15", "title": "Multi-cultures, même parcelle", "mode": "recommend", "query": "Eau pour mes deux cultures ?", "crop": "tomate", "features": BASE_FEATURES},
    {"id": "S16", "title": "Données météo retardées (J-4)", "mode": "answer", "query": "Etat du sol avec retard", "crop": "oignon", "features": {**BASE_FEATURES, "data_age_hours": 96}},
    {"id": "S17", "title": "Comparaison inter-marchés (A5/A9)", "mode": "answer", "query": "Ou acheter oignon moins cher ?", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S18", "title": "Stress hydrique progressif", "mode": "answer", "query": "Sol se dégrade depuis lundi", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S19", "title": "Fin hivernage, transition irrigation", "mode": "answer", "query": "Pluies finies ? Reprendre irrigation ?", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S20", "title": "Anomalie, cause inconnue", "mode": "answer", "query": "Anomalie détectée, c'est quoi ?", "crop": "oignon", "features": {**BASE_FEATURES, "t_max_c": 43.0}},
    {"id": "S21", "title": "Bilan hebdomadaire automatique", "mode": "monitor", "query": "Batch hebdo", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S22", "title": "Agriculteur hors zone couverte", "mode": "answer", "query": "Que me conseillez-vous ?", "crop": "riz", "features": {}},
    {"id": "S23", "title": "ET0 extrême + sol sec", "mode": "monitor", "query": "Ferlo mars", "crop": "mil", "features": {**BASE_FEATURES, "et0_pm_mm": 7.5, "soil_wetness_root_pct": 14.0}},
    {"id": "S24", "title": "Conflit prix vs rendement (A3/A5)", "mode": "answer", "query": "Oignon rentable cette année ?", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S25", "title": "Dose précise goutte-à-goutte", "mode": "recommend", "query": "Litres par plant de tomate ?", "crop": "tomate", "features": BASE_FEATURES},
    {"id": "S26", "title": "Pluie extrême (>100mm/3j)", "mode": "monitor", "query": "Hivernage Kédougou", "crop": "mais", "features": {**BASE_FEATURES, "rain_chirps_sum_3d_mm": 110.0, "rain_mm": 35.0}},
    {"id": "S27", "title": "Première connexion, onboarding", "mode": "answer", "query": "Bonjour, je commence", "crop": "oignon", "features": {}},
    {"id": "S28", "title": "Vérification post-irrigation", "mode": "answer", "query": "J'ai irrigué, c'est mieux ?", "crop": "oignon", "features": BASE_FEATURES},
    {"id": "S29", "title": "Requête ambiguë, clarification", "mode": "answer", "query": "Ca va pas", "crop": "oignon", "features": {}},
    {"id": "S30", "title": "Escalade humaine après conflit", "mode": "answer", "query": "Que faire pour ma parcelle ?", "crop": "oignon", "features": {**BASE_FEATURES, "t_max_c": 43.0}},
]


def run_demo() -> Dict[str, Any]:
    tracemalloc.start()
    t_init = time.perf_counter()

    rt = SmartAgriRuntime()
    init_ms = round((time.perf_counter() - t_init) * 1000.0, 2)

    results = []
    passed = 0
    partial = 0
    failed = 0
    flows_verified = {"answer": 0, "monitor": 0, "recommend": 0, "escalate": 0}

    for sc in SCENARIOS:
        try:
            mode = sc["mode"]
            if mode == "monitor":
                r = rt.monitor(sc["features"])
                flows_verified["monitor"] += 1
            elif mode == "recommend":
                r = rt.recommend(sc["features"], crop=sc["crop"])
                flows_verified["recommend"] += 1
            else:
                r = rt.answer(sc["query"], sc["features"], crop=sc["crop"])
                flows_verified["answer"] += 1

            # Check assistant integration on S04 as well
            if sc["id"] == "S04":
                _ = rt.ask_assistant(sc["query"], sc["features"], crop=sc["crop"])

            # Verify escalate flow on S30 / critical or low-confidence cases
            if r.escalate or sc["id"] == "S30":
                esc = rt.escalate({"reason": r.answer, "cell_id": sc["id"]})
                if esc.get("type") == "human_escalation":
                    flows_verified["escalate"] += 1

            if sc.get("needs_missing_model"):
                status = "PARTIAL_MISSING_MODEL"
                partial += 1
            elif r.abstentions and sc["id"] not in ("S11", "S22") and "rain_intelligence" in str(r.abstentions):
                # Rain weights absent in local exports, other components ran
                status = "PARTIAL_RAIN_ABSTAINED"
                partial += 1
            else:
                status = "PASSED"
                passed += 1

            results.append({
                "id": sc["id"],
                "title": sc["title"],
                "status": status,
                "intent": r.intent,
                "components_called": r.components_called,
                "abstentions": r.abstentions,
                "confidence": r.confidence,
                "confidence_level": r.confidence_level.value,
                "latency_ms": r.latency_ms,
                "escalate": r.escalate,
                "answer": r.answer,
            })
        except Exception as exc:
            failed += 1
            results.append({
                "id": sc["id"],
                "title": sc["title"],
                "status": "FAILED",
                "error": str(exc),
                "confidence": 0.0,
                "latency_ms": 0.0,
            })

    cur_mem, peak_mem = tracemalloc.get_traced_memory()
    avg_lat = round(sum(x["latency_ms"] for x in results) / len(results), 2)
    avg_conf = round(sum(x["confidence"] for x in results) / len(results), 4)

    summary = {
        "init_ms": init_ms,
        "total_scenarios": len(SCENARIOS),
        "passed": passed,
        "partial": partial,
        "failed": failed,
        "flows_verified": flows_verified,
        "avg_latency_ms": avg_lat,
        "avg_confidence": avg_conf,
        "peak_memory_mb": round(peak_mem / 1e6, 2),
        "current_memory_mb": round(cur_mem / 1e6, 2),
        "knowledge_backend": rt.knowledge.active_backend,
        "soil_ready": rt.soil.is_ready,
        "rain_ready": rt.rain.is_ready,
        "anomaly_thresholds": len(rt.anomaly.HARD_THRESHOLDS),
        "scenarios": results,
    }
    out_path = ROOT / "manifests" / "e2e_30_results.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


if __name__ == "__main__":
    s = run_demo()
    print(json.dumps({k: v for k, v in s.items() if k != "scenarios"}, indent=2, ensure_ascii=False))
