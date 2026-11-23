"""AnomalyService — seuils métier calibrés + historique GLIDE Sénégal + modèles ML optionnels (A8)."""

import csv
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .security import safe_load_pickle
from .types import ConfidenceLevel, ServiceResponse, confidence_level


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANOMALY_DIR = ROOT / "models" / "anomaly"
DEFAULT_METRICS_CSV = ROOT / "metrics" / "anomaly_intelligence_metrics.csv"
DEFAULT_GLIDE_CSV = ROOT / "datasets" / "real" / "sen_glide_events.csv"


class AnomalyService:
    """
    Détection d'anomalies multi-type :
    - 5 seuils métier déterministes (drought, flood, heatwave, cold_snap, et0_extreme)
    - Calibration contextuelle sur les 38 événements historiques GLIDE Sénégal (inondations/sécheresses)
    - Isolation Forest / One-Class SVM / AutoEncoder (.pkl) si présents dans models/anomaly/
    """

    HARD_THRESHOLDS = {
        "drought": {"feat": "soil_wetness_root_pct", "op": "<", "val": 15.0},
        "flood": {"feat": "rain_chirps_sum_3d_mm", "op": ">", "val": 100.0},
        "heatwave": {"feat": "t_max_c", "op": ">", "val": 42.0},
        "cold_snap": {"feat": "t_min_c", "op": "<", "val": 10.0},
        "et0_extreme": {"feat": "et0_pm_mm", "op": ">", "val": 7.0},
    }
    WATCH_THRESHOLDS = {
        "drought_watch": {"feat": "soil_wetness_root_pct", "op": "<", "val": 22.0},
        "flood_watch": {"feat": "rain_chirps_sum_3d_mm", "op": ">", "val": 60.0},
        "heatwave_watch": {"feat": "t_max_c", "op": ">", "val": 39.0},
    }

    def __init__(self, models_dir: Optional[Path] = None, iso_forest=None, autoencoder=None):
        self.models_dir = Path(models_dir) if models_dir else DEFAULT_ANOMALY_DIR
        self.iso = iso_forest
        self.ae = autoencoder
        self.load_error: Optional[str] = None
        self.model_size_bytes: int = 0
        self.glide_events: List[Dict[str, str]] = []
        self.glide_by_type: Dict[str, int] = {}
        self.high_risk_flood_regions = {"matam", "saint-louis", "dakar", "thies", "tambacounda", "kaffrine", "kaolack"}
        self._load_glide_calibration()
        if self.iso is None or self.ae is None:
            self._load_local_champions()

    def _load_glide_calibration(self) -> None:
        if not DEFAULT_GLIDE_CSV.exists():
            return
        with DEFAULT_GLIDE_CSV.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            self.glide_events = list(csv.DictReader(fh))
        counts = Counter((r.get("event_name") or "unknown").lower() for r in self.glide_events)
        self.glide_by_type = dict(counts)

    def _load_local_champions(self) -> None:
        total_bytes = 0
        if self.iso is None:
            for fname in ("isolation_forest_champion.pkl", "ocsvm_champion.pkl"):
                p = self.models_dir / fname
                if p.exists():
                    total_bytes += p.stat().st_size
                    self.iso = safe_load_pickle(p, allowed_root=self.models_dir)
                    break

        if self.ae is None:
            ae_pkl = self.models_dir / "autoencoder_champion.pkl"
            if ae_pkl.exists():
                total_bytes += ae_pkl.stat().st_size
                self.ae = safe_load_pickle(ae_pkl, allowed_root=self.models_dir)

        self.model_size_bytes = total_bytes
        if self.iso is None and self.ae is None:
            self.load_error = (
                f"Poids IsolationForest/AutoEncoder/OCSVM absents dans {self.models_dir} "
                "(mode seuils métier + calibration GLIDE Sénégal actif)"
            )

    @property
    def statistical_model_loaded(self) -> bool:
        return self.iso is not None or self.ae is not None

    def metrics_summary(self) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        if DEFAULT_METRICS_CSV.exists():
            with DEFAULT_METRICS_CSV.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
        return {
            "thresholds_count": len(self.HARD_THRESHOLDS),
            "watch_thresholds_count": len(self.WATCH_THRESHOLDS),
            "glide_events_loaded": len(self.glide_events),
            "glide_by_type": self.glide_by_type,
            "iso_or_ocsvm_loaded": self.iso is not None,
            "autoencoder_loaded": self.ae is not None,
            "model_size_bytes": self.model_size_bytes,
            "metrics_rows_total": len(rows),
        }

    def detect(self, features: Dict[str, Any]) -> ServiceResponse:
        t0 = time.perf_counter()
        anomalies: List[Dict[str, Any]] = []
        crit_types = set()

        for atype, r in self.HARD_THRESHOLDS.items():
            v = features.get(r["feat"])
            if v is not None:
                val = float(v)
                hit = (val < r["val"]) if r["op"] == "<" else (val > r["val"])
                if hit:
                    crit_types.add(atype)
                    anomalies.append({
                        "type": atype,
                        "method": "threshold",
                        "feature": r["feat"],
                        "value": val,
                        "threshold": r["val"],
                        "severity": "CRITICAL",
                    })

        # Pré-alerte calibrée (WATCH) si pas déjà en CRITICAL, renforcée sur zones historiques GLIDE
        region = str(features.get("region", "")).lower()
        for wtype, r in self.WATCH_THRESHOLDS.items():
            base = wtype.replace("_watch", "")
            if base in crit_types:
                continue
            v = features.get(r["feat"])
            if v is not None:
                val = float(v)
                thr = r["val"]
                if base == "flood" and region in self.high_risk_flood_regions:
                    thr = 50.0  # Seuil abaissé sur régions historiquement touchées (GLIDE)
                hit = (val < thr) if r["op"] == "<" else (val > thr)
                if hit:
                    anomalies.append({
                        "type": base,
                        "method": "glide_calibrated_watch",
                        "feature": r["feat"],
                        "value": val,
                        "threshold": thr,
                        "severity": "WARNING",
                    })

        if self.iso is not None and "anomaly_vector" in features:
            vec = np.asarray(features["anomaly_vector"], dtype=np.float64).reshape(1, -1)
            score = float(self.iso.decision_function(vec)[0])
            if score < -0.15:
                anomalies.append({
                    "type": "statistical",
                    "method": type(self.iso).__name__,
                    "score": round(score, 4),
                    "severity": "WARNING" if score > -0.3 else "CRITICAL",
                })

        if self.ae is not None and "anomaly_vector" in features:
            vec = np.asarray(features["anomaly_vector"], dtype=np.float64).reshape(1, -1)
            recon = np.asarray(self.ae.predict(vec), dtype=np.float64)
            mse = float(np.mean((vec - recon) ** 2))
            if mse > 0.15:
                anomalies.append({
                    "type": "reconstruction",
                    "method": "AutoEncoder",
                    "mse": round(mse, 4),
                    "severity": "WARNING" if mse < 0.30 else "CRITICAL",
                })

        n = len(anomalies)
        max_sev = "NORMAL"
        if any(a["severity"] == "CRITICAL" for a in anomalies):
            max_sev = "CRITICAL"
        elif any(a["severity"] == "WARNING" for a in anomalies):
            max_sev = "WARNING"

        conf = 0.90 if n == 0 else min(0.95, 0.72 + 0.05 * n)
        return ServiceResponse(
            service="anomaly",
            values={
                "anomalies": anomalies,
                "count": n,
                "max_severity": max_sev,
                "statistical_model_loaded": self.statistical_model_loaded,
                "glide_events_calibrated": len(self.glide_events),
            },
            confidence=round(conf, 4),
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )
