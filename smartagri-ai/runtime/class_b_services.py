"""Services Classe B1 (Irrigation ML) et B2 (Water Savings) d'après 82_class_b_readiness.md."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from runtime.security import safe_load_pickle
from runtime.types import ConfidenceLevel, ServiceResponse, confidence_level


ROOT = Path(__file__).resolve().parents[1]


class B1IrrigationMLService:
    """
    B1 — Prédiction du besoin d'irrigation (mm/jour) combinant capteur sol + FAO-56 + SoilNowcast.
    Utilise un modèle ML local (`b1_irrigation_champion.pkl`) s'il existe, sinon bilan hydrique expert FAO-56.
    """

    KC = {
        "oignon": 1.05, "tomate": 1.15, "gombo": 1.0, "riz": 1.20,
        "arachide": 1.15, "mil": 1.0, "mais": 1.20, "pomme_de_terre": 1.15,
    }

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "irrigation_b1")
        self.models_dir = d
        self.model_path = d / "b1_irrigation_champion.pkl"
        self.model = None
        if self.model_path.exists():
            try:
                self.model = safe_load_pickle(self.model_path, allowed_root=d)
            except Exception:
                self.model = None

    def _predict_with_ml(self, et0: float, kc: float, sm10: float, fc: float,
                         rain_obs: float, rain_prob: float) -> Optional[float]:
        if self.model is None or not hasattr(self.model, "predict"):
            return None
        try:
            vec = np.array([[et0, kc, sm10, fc, rain_obs, rain_prob]], dtype=np.float64)
            n_expected = getattr(self.model, "n_features_in_", vec.shape[1])
            if n_expected != vec.shape[1]:
                return None
            return round(max(0.0, float(self.model.predict(vec)[0])), 2)
        except Exception:
            return None

    def predict(self, features: Dict[str, Any]) -> ServiceResponse:
        t0 = time.perf_counter()
        days_to_harvest = features.get("days_to_harvest")
        if days_to_harvest is not None and float(days_to_harvest) <= 15.0:
            return ServiceResponse(
                service="b1_irrigation_ml",
                values={"irrigation_need_mm": 0.0, "mode": "preharvest_block_15d"},
                confidence=0.95,
                confidence_level=ConfidenceLevel.HIGH,
                warnings=["Blocage pré-récolte <= 15 jours"],
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

        crop = str(features.get("crop_type", "oignon")).lower()
        kc = float(features.get("kc", self.KC.get(crop, 1.0)))
        et0 = float(features.get("et0_pm_mm", 4.8))
        etc = et0 * kc
        sm10 = float(features.get("soil_moisture_10cm_pct", features.get("soilnowcast_root_pct", 35.0)))
        fc = float(features.get("fc_ptf_pct", 65.0))
        rain_obs = float(features.get("rain_mm_obs", 0.0))
        rain_prob = float(features.get("rain_prob_1d", 0.0))

        used_ml = False
        if rain_prob > 0.70 or rain_obs > 5.0:
            need = 0.0
            mode = "rain_delay"
        else:
            ml_pred = self._predict_with_ml(et0, kc, sm10, fc, rain_obs, rain_prob)
            if ml_pred is not None:
                need = ml_pred
                mode = "ml_model"
                used_ml = True
            else:
                deficit_ratio = max(0.0, (fc - sm10) / max(1.0, fc))
                need = round(max(0.0, etc * (0.6 + deficit_ratio) - rain_obs * 0.5), 2)
                mode = "fao56_sensor_hybrid"

        conf = 0.88 if used_ml else 0.78
        return ServiceResponse(
            service="b1_irrigation_ml",
            values={
                "irrigation_need_mm": need,
                "etc_mm": round(etc, 2),
                "soil_moisture_pct": sm10,
                "crop_type": crop,
                "mode": mode,
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )


class B2WaterSavingsService:
    """
    B2 — Estimation des économies d'eau (mm, m³/ha, %, FCFA) vs irrigation traditionnelle.
    """

    DEFAULT_WATER_COST_FCFA_M3 = 150.0

    def estimate(
        self,
        recommended_mm: float,
        traditional_baseline_mm: float = 8.0,
        area_ha: float = 1.0,
        water_cost_fcfa_m3: float = DEFAULT_WATER_COST_FCFA_M3,
    ) -> ServiceResponse:
        t0 = time.perf_counter()
        saved_mm = max(0.0, float(traditional_baseline_mm) - float(recommended_mm))
        saved_m3_ha = saved_mm * 10.0  # 1 mm = 10 m³/ha
        total_saved_m3 = saved_m3_ha * float(area_ha)
        pct_saved = (saved_mm / float(traditional_baseline_mm) * 100.0) if traditional_baseline_mm > 0 else 0.0
        fcfa_saved = total_saved_m3 * float(water_cost_fcfa_m3)

        return ServiceResponse(
            service="b2_water_savings",
            values={
                "recommended_mm": round(float(recommended_mm), 2),
                "baseline_mm": round(float(traditional_baseline_mm), 2),
                "saved_mm": round(saved_mm, 2),
                "saved_m3": round(total_saved_m3, 2),
                "pct_saved": round(pct_saved, 1),
                "fcfa_saved": round(fcfa_saved, 0),
                "area_ha": float(area_ha),
            },
            confidence=0.82,
            confidence_level=ConfidenceLevel.HIGH,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )
