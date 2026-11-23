"""RainIntelligenceService — chargement local champion CatBoost (A4), métriques et inférence."""

import csv
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .security import safe_load_pickle
from .types import ConfidenceLevel, ServiceResponse, confidence_level


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAIN_DIR = ROOT / "models" / "rain_intelligence"
DEFAULT_METRICS_CSV = ROOT / "metrics" / "wx_rain_prob_all_metrics.csv"
DEFAULT_SHAP_CSV = ROOT / "shap" / "wx_rain_prob_shap_summary.csv"


class RainIntelligenceService:
    """
    Probabilité pluie J+1 / J+2 / J+3.
    Champion : CatBoost — AUC = 0.9625, F1 = 0.7642, Brier = 0.0611.
    """

    BASELINE_AUC = 0.9625
    TARGETS = ("rain_1d", "rain_2d", "rain_3d")
    THRESHOLDS = {"rain_1d": 0.45, "rain_2d": 0.50, "rain_3d": 0.55}
    FEATURES: List[str] = [
        "doy_cos", "doy_sin", "solar_rad_mj_m2", "wind_2m_ms",
        "rain_chirps_sum_14d_mm", "t_min_c", "rain_mm", "rain_nasa_sum_3d_mm",
        "pressure_hpa", "rain_chirps_sum_7d_mm", "rain_chirps_sum_3d_mm",
        "et0_pm_mean_7d_mm", "rain_nasa_sum_14d_mm", "rain_nasa_sum_7d_mm",
        "rain_chirps_mm", "t_max_c", "t_mean_c", "rh_mean_pct", "et0_pm_mm",
        "ph_h2o", "soc_g_kg", "bulk_density_g_cm3", "share_crop", "share_tree",
        "sand_pct", "share_built", "share_bare", "clay_pct", "fc_ptf_pct", "wp_ptf_pct",
    ]

    def __init__(self, models_dir: Optional[Path] = None, model: Optional[Dict[str, Any]] = None):
        self.models_dir = Path(models_dir) if models_dir else DEFAULT_RAIN_DIR
        self.model = model
        self.load_error: Optional[str] = None
        self.model_size_bytes: int = 0
        if self.model is None:
            self._load_local_champion()

    def _load_local_champion(self) -> None:
        loaded: Dict[str, Any] = {}
        total_bytes = 0
        for t in self.TARGETS:
            cbm_path = self.models_dir / f"{t}_champion.cbm"
            pkl_path = self.models_dir / f"{t}_champion.pkl"
            if cbm_path.exists():
                total_bytes += cbm_path.stat().st_size
                try:
                    from catboost import CatBoostClassifier
                except ImportError as exc:
                    self.load_error = f"catboost manquant pour {cbm_path.name}: {exc}"
                    return
                clf = CatBoostClassifier()
                clf.load_model(str(cbm_path))
                loaded[t] = clf
            elif pkl_path.exists():
                total_bytes += pkl_path.stat().st_size
                loaded[t] = safe_load_pickle(pkl_path, allowed_root=self.models_dir)

        self.model_size_bytes = total_bytes
        if len(loaded) == len(self.TARGETS):
            self.model = loaded
        else:
            self.load_error = f"Artefacts champions CatBoost absents dans {self.models_dir} (0/3 cibles)"

    @property
    def is_ready(self) -> bool:
        return self.model is not None and all(t in self.model for t in self.TARGETS)

    def metrics_summary(self) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        if DEFAULT_METRICS_CSV.exists():
            with DEFAULT_METRICS_CSV.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
        cb_rows = [r for r in rows if r.get("model") == "CatBoost"]
        shap_top: List[Dict[str, str]] = []
        if DEFAULT_SHAP_CSV.exists():
            with DEFAULT_SHAP_CSV.open("r", encoding="utf-8", newline="") as fh:
                shap_top = list(csv.DictReader(fh))[:5]
        return {
            "champion": "CatBoost",
            "baseline_auc": self.BASELINE_AUC,
            "model_size_bytes": self.model_size_bytes,
            "weights_loaded": self.is_ready,
            "metrics_rows_total": len(rows),
            "catboost_rows": len(cb_rows),
            "shap_top5": shap_top,
        }

    def predict(self, features: Dict[str, Any]) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse(
                service="rain_intelligence",
                values={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.UNRELIABLE,
                abstained=True,
                abstention_reason=self.load_error or "Modèle CatBoost non chargé",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

        X = np.array([[float(features.get(f, 0.0)) for f in self.FEATURES]], dtype=np.float64)
        probs: Dict[str, float] = {}
        decisions: Dict[str, bool] = {}
        warnings: List[str] = []

        for t in self.TARGETS:
            p = float(self.model[t].predict_proba(X)[0][1])
            probs[f"{t}_prob"] = round(p, 4)
            decisions[f"{t}_rain"] = p >= self.THRESHOLDS[t]

        if probs.get("rain_1d_prob", 0.0) > 0.85:
            warnings.append("Forte probabilité pluie demain (>85%)")

        conf = self._confidence(features)
        return ServiceResponse(
            service="rain_intelligence",
            values={**probs, **decisions},
            confidence=conf,
            confidence_level=confidence_level(conf),
            warnings=warnings,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    def _confidence(self, f: Dict[str, Any]) -> float:
        c = self.BASELINE_AUC
        m = f.get("month", 6)
        if m in [11, 12, 1, 2, 3, 4, 5]:
            c *= 0.95
        age = float(f.get("data_age_hours", 0.0))
        if age > 24:
            c *= max(0.6, 1.0 - (age - 24.0) / 120.0)
        return round(min(1.0, max(0.0, c)), 4)
