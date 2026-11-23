"""SoilNowcastService — inférence locale sur les 15 modèles natifs LightGBM."""

from pathlib import Path
from typing import Dict, List, Optional
import time
import numpy as np

from .types import ConfidenceLevel, ServiceResponse, confidence_level


DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[1] / "models" / "soilnowcast"


class SoilNowcastService:
    """
    Prédiction humidité du sol J+1 / J+2 / J+3.
    Champion : LightGBM — R² = 0.8353, RMSE = 7.45% (ensemble 5 folds × 3 cibles).
    """

    BASELINE_R2 = 0.8353
    HORIZONS = ("y_plus_1d", "y_plus_2d", "y_plus_3d")
    TARGETS = {
        "y_plus_1d": "lgb_y_plus_1d_pct_fold",
        "y_plus_2d": "lgb_y_plus_2d_pct_fold",
        "y_plus_3d": "lgb_y_plus_3d_pct_fold",
    }
    FEATURES: List[str] = [
        "t_min_c", "t_max_c", "t_mean_c", "rh_mean_pct", "wind_2m_ms",
        "solar_rad_mj_m2", "pressure_hpa", "rain_mm", "rain_chirps_mm",
        "et0_pm_mm", "rain_nasa_sum_3d_mm", "rain_nasa_sum_7d_mm",
        "rain_nasa_sum_14d_mm", "rain_chirps_sum_3d_mm",
        "rain_chirps_sum_7d_mm", "rain_chirps_sum_14d_mm",
        "et0_pm_mean_7d_mm", "doy_sin", "doy_cos", "sand_pct",
        "clay_pct", "soc_g_kg", "ph_h2o", "bulk_density_g_cm3",
        "fc_ptf_pct", "wp_ptf_pct", "share_crop", "share_tree",
        "share_bare", "share_built",
    ]
    WILTING = 15.0
    STRESS_SEV = 20.0
    STRESS_MOD = 30.0
    FC = 80.0
    SATURATION = 90.0

    def __init__(self, models_dir: Optional[Path] = None, n_folds: int = 5):
        self.models_dir = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
        self.n_folds = n_folds
        self.boosters: Dict[str, list] = {}
        self.load_error: Optional[str] = None
        self._load_models()

    def _load_models(self) -> None:
        try:
            import lightgbm as lgb
        except ImportError as exc:
            self.load_error = f"lightgbm manquant: {exc}"
            return

        loaded: Dict[str, list] = {}
        for horizon, prefix in self.TARGETS.items():
            fold_models = []
            for fold in range(self.n_folds):
                path = self.models_dir / f"{prefix}{fold}.txt"
                if not path.exists():
                    self.load_error = f"Modèle manquant: {path}"
                    return
                fold_models.append(lgb.Booster(model_file=str(path)))
            loaded[horizon] = fold_models
        self.boosters = loaded

    @property
    def is_ready(self) -> bool:
        return len(self.boosters) == len(self.TARGETS) and self.load_error is None

    def predict(self, features: Dict[str, float]) -> ServiceResponse:
        t0 = time.perf_counter()
        missing = [f for f in self.FEATURES if f not in features]
        if len(missing) > 5:
            return ServiceResponse(
                service="soil_nowcast",
                values={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.UNRELIABLE,
                abstained=True,
                abstention_reason=f"{len(missing)}/30 features manquantes",
                latency_ms=(time.perf_counter() - t0) * 1000.0,
            )
        if not self.is_ready:
            return ServiceResponse(
                service="soil_nowcast",
                values={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.UNRELIABLE,
                abstained=True,
                abstention_reason=self.load_error or "Modèles non chargés",
                latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        X = np.array([[float(features.get(f, 0.0)) for f in self.FEATURES]], dtype=np.float64)
        preds: Dict[str, float] = {}
        warnings: List[str] = []

        for h in self.HORIZONS:
            fold_preds = [float(b.predict(X)[0]) for b in self.boosters[h]]
            v = float(np.mean(fold_preds))
            if v < 0.0:
                v = 0.0
                warnings.append(f"{h} clampé à 0%")
            elif v > 100.0:
                v = 100.0
                warnings.append(f"{h} clampé à 100%")
            preds[h] = round(v, 4)
            preds[f"{h}_std"] = round(float(np.std(fold_preds)), 4)

        j1 = preds["y_plus_1d"]
        if j1 < self.WILTING:
            warnings.append(f"CRITICAL: flétrissement J+1={j1:.1f}%")
        elif j1 < self.STRESS_MOD:
            warnings.append(f"WARNING: stress hydrique J+1={j1:.1f}%")
        if j1 > self.SATURATION:
            warnings.append(f"WARNING: saturation J+1={j1:.1f}%")

        conf = self._confidence(features)
        return ServiceResponse(
            service="soil_nowcast",
            values=preds,
            confidence=conf,
            confidence_level=confidence_level(conf),
            warnings=warnings,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    def _confidence(self, f: Dict[str, float]) -> float:
        c = self.BASELINE_R2
        age = float(f.get("data_age_hours", 0.0))
        if age > 48:
            c *= max(0.5, 1.0 - (age - 48.0) / 168.0)
        if f.get("is_new_cell", False):
            c *= 0.85
        if float(f.get("rain_chirps_sum_14d_mm", 0.0)) > 200.0:
            c *= 0.80
        return round(min(1.0, max(0.0, c)), 4)
