"""Services locaux A2 (ET0 Forecast), A6 (Crop Calendar) et A7 (NDVI Anomaly)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .types import ConfidenceLevel, ServiceResponse, confidence_level

ROOT = Path(__file__).resolve().parents[1]


class ET0ForecastService:
    """A2 — Prévision d'évapotranspiration ET0 (CatBoostRegressor)."""

    BASELINE_R2 = 0.9997
    FEATURES: List[str] = [
        "t_min_c", "t_max_c", "t_mean_c", "rh_mean_pct", "wind_2m_ms",
        "solar_rad_mj_m2", "pressure_hpa", "rain_mm", "ra_mj_m2",
        "et0_hargreaves_mm", "doy_sin", "doy_cos", "month", "t_range_c", "lat", "lon",
    ]

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "et0")
        self.model_path = d / "a2_et0_champion.cbm"
        self.meta_path = d / "a2_et0_metadata.json"
        self.model = None
        self.meta: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            self.load_error = "Artefact A2 absent"
            return
        try:
            from catboost import CatBoostRegressor

            m = CatBoostRegressor()
            m.load_model(str(self.model_path))
            self.model = m
            if self.meta_path.exists():
                self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.load_error = f"Erreur chargement A2: {exc}"

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def predict(self, features: Dict[str, Any]) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse(
                "et0_forecast", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=self.load_error or "A2 non chargé",
            )
        t_min = float(features.get("t_min_c", 22.0))
        t_max = float(features.get("t_max_c", 34.0))
        enriched = {
            **features,
            "ra_mj_m2": float(features.get("ra_mj_m2", 34.5)),
            "et0_hargreaves_mm": float(features.get("et0_hargreaves_mm", features.get("et0_pm_mm", 5.0))),
            "month": float(features.get("month", 6)),
            "t_range_c": float(features.get("t_range_c", max(0.0, t_max - t_min))),
            "lat": float(features.get("lat", 15.15)),
            "lon": float(features.get("lon", -16.88)),
        }
        missing = [f for f in self.FEATURES if f not in enriched]
        if missing:
            return ServiceResponse(
                "et0_forecast", {}, 0.1, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=f"Features manquantes: {missing[:4]}",
            )
        X = np.array([[float(enriched[f]) for f in self.FEATURES]], dtype=np.float64)
        pred = max(0.0, float(self.model.predict(X)[0]))
        conf = round(float(self.meta.get("r2", self.BASELINE_R2)) * 0.95, 4)
        return ServiceResponse(
            service="et0_forecast",
            values={"et0_pred_mm": round(pred, 3), "model": "CatBoost"},
            confidence=conf,
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )


class CropCalendarService:
    """A6 — Classification stade cultural FAO-56 (CatBoostClassifier)."""

    CROP_SYNONYMS = {
        "oignon": "onion", "onion": "onion",
        "tomate": "tomato", "tomato": "tomato",
        "chou": "cabbage", "cabbage": "cabbage",
        "pomme de terre": "potato", "potato": "potato",
        "carotte": "carrot", "carrot": "carrot",
        "poivron": "pepper", "pepper": "pepper",
        "laitue": "lettuce", "lettuce": "lettuce",
    }

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "clustering")
        self.model_path = d / "a6_crop_calendar_champion.cbm"
        self.meta_path = d / "a6_crop_calendar_metadata.json"
        self.model = None
        self.meta: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists() or not self.meta_path.exists():
            self.load_error = "Artefacts A6 absents"
            return
        try:
            from catboost import CatBoostClassifier

            m = CatBoostClassifier()
            m.load_model(str(self.model_path))
            self.model = m
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.load_error = f"Erreur chargement A6: {exc}"

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def predict(self, crop: str = "tomate", day_after_planting: int = 45) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse(
                "crop_calendar", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=self.load_error or "A6 non chargé",
            )
        crops_list: List[str] = self.meta.get("crops", [])
        stages_list: List[str] = self.meta.get("stages", [])
        code = self.CROP_SYNONYMS.get(crop.lower().strip(), "tomato")
        crop_enc = crops_list.index(code) if code in crops_list else 0
        season_days = 135 if code == "tomato" else 150
        kc_ini, kc_mid, kc_end = (0.60, 1.15, 0.80) if code == "tomato" else (0.70, 1.05, 0.75)
        kc_cur = kc_mid if 30 <= day_after_planting <= 95 else (kc_ini if day_after_planting < 30 else kc_end)
        X = np.array([[crop_enc, day_after_planting, season_days, kc_cur, kc_ini, kc_mid, kc_end]], dtype=np.float64)
        probs = self.model.predict_proba(X)[0]
        idx = int(np.argmax(probs))
        stage = stages_list[idx] if idx < len(stages_list) else "mi_saison"
        conf = round(float(probs[idx]), 4)
        return ServiceResponse(
            service="crop_calendar",
            values={
                "crop": code,
                "day_after_planting": day_after_planting,
                "growth_stage": stage,
                "kc_recommended": kc_cur,
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )


class NDVIAnomalyService:
    """A7 — Détection d'anomalie NDVI satellitaire (LightGBMClassifier)."""

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "clustering")
        self.model_path = d / "a7_ndvi_anomaly_champion.txt"
        self.meta_path = d / "a7_ndvi_anomaly_metadata.json"
        self.model = None
        self.meta: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists() or not self.meta_path.exists():
            self.load_error = "Artefacts A7 absents"
            return
        try:
            import lightgbm as lgb

            self.model = lgb.Booster(model_file=str(self.model_path))
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.load_error = f"Erreur chargement A7: {exc}"

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def predict(self, features: Dict[str, Any]) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse(
                "ndvi_anomaly", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=self.load_error or "A7 non chargé",
            )
        feat_names: List[str] = self.meta.get("features", [])
        defaults = {
            "cell_id": 2500.0, "month_num": 5.0, "ndvi_mean": 0.32, "ndvi_std": 0.08,
            "n_valid_px": 150.0, "valid_fraction": 0.92,
            "share_tree": 0.15, "share_shrub": 0.05, "share_grass": 0.05,
            "share_crop": 0.55, "share_built": 0.02, "share_bare": 0.18,
            "share_water": 0.0, "share_wetland": 0.0, "share_mangrove": 0.0,
        }
        row = [float(features.get(f, defaults.get(f, 0.0))) for f in feat_names]
        X = np.array([row], dtype=np.float64)
        prob = float(self.model.predict(X)[0])
        is_anom = prob >= 0.5
        conf = round(max(prob, 1.0 - prob), 4)
        return ServiceResponse(
            service="ndvi_anomaly",
            values={
                "ndvi_anomaly": bool(is_anom),
                "anomaly_prob": round(prob, 4),
                "ndvi_mean": float(features.get("ndvi_mean", defaults["ndvi_mean"])),
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )
