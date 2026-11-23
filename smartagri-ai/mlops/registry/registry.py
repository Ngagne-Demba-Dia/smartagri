"""Registre MLOps local SmartAgri — charge champions_summary.json, features_by_model.json et vérifie les artefacts."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[2]


class LocalModelRegistry:
    """Registre local des 9 modèles Classe A et de leurs artefacts sur disque."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else ROOT
        self.champions_path = self.root / "mlops" / "registry" / "champions_summary.json"
        self.features_path = self.root / "mlops" / "feature_store" / "features_by_model.json"
        self.champions: Dict[str, Any] = json.loads(self.champions_path.read_text(encoding="utf-8"))
        self.features: Dict[str, List[str]] = json.loads(self.features_path.read_text(encoding="utf-8"))

    def _artifact_check(self, model_key: str) -> tuple[int, bool]:
        m = self.root / "models"
        if model_key == "A1_SoilNowcast":
            n = len(list((m / "soilnowcast").glob("lgb_y_plus_*_pct_fold*.txt")))
            return n, n == 15
        if model_key == "A2_ET0_Forecast":
            ok = (m / "et0" / "a2_et0_champion.cbm").exists()
            return (1 if ok else 0), ok
        if model_key == "A3_Yield_Forecast":
            ok = (m / "yield" / "a3_yield_champion.pkl").exists()
            return (1 if ok else 0), ok
        if model_key == "A4_Rain_Intelligence":
            n = sum((m / "rain_intelligence" / f"rain_{h}d_champion.cbm").exists() for h in (1, 2, 3))
            return n, n == 3
        if model_key == "A5_Price_Forecast":
            ok = (m / "yield" / "a5_price_champion.pkl").exists()
            return (1 if ok else 0), ok
        if model_key == "A6_Crop_Calendar":
            ok = (m / "clustering" / "a6_crop_calendar_champion.cbm").exists()
            return (1 if ok else 0), ok
        if model_key == "A7_NDVI_Anomaly":
            ok = (m / "clustering" / "a7_ndvi_anomaly_champion.txt").exists()
            return (1 if ok else 0), ok
        if model_key == "A8_Anomaly_Intelligence":
            n = sum(
                (m / "anomaly" / fn).exists()
                for fn in ("isolation_forest_champion.pkl", "ocsvm_champion.pkl", "autoencoder_champion.pkl")
            )
            return n, n >= 2
        if model_key == "A9_Market_Clustering":
            ok = (m / "clustering" / "a9_market_kmeans_champion.pkl").exists()
            return (1 if ok else 0), ok
        return 0, False

    def status(self) -> Dict[str, Any]:
        models_out: Dict[str, Any] = {}
        for k, v in self.champions.items():
            cnt, ready = self._artifact_check(k)
            models_out[k] = {
                **v,
                "features_count": len(self.features.get(k, [])),
                "native_artifacts": cnt,
                "ready_local": ready,
            }
        ready_count = sum(1 for m in models_out.values() if m["ready_local"])
        return {
            "total_models": len(self.champions),
            "ready_models": ready_count,
            "models": models_out,
        }
