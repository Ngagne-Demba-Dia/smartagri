"""Services locaux A3 (Yield), A5 (Price) et A9 (Market Clustering) entraînés sur données Sénégal."""

import csv
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .security import safe_load_pickle
from .types import ConfidenceLevel, ServiceResponse, confidence_level


ROOT = Path(__file__).resolve().parents[1]

SENEGAL_REGION_COORDS: Dict[str, Tuple[float, float]] = {
    "dakar": (14.6928, -17.4467),
    "diourbel": (14.6550, -16.2314),
    "fatick": (14.3390, -16.4111),
    "kaffrine": (14.1059, -15.5508),
    "kaolack": (14.1520, -16.0726),
    "kedougou": (12.5579, -12.1743),
    "kolda": (12.8939, -14.9412),
    "louga": (15.6144, -16.2287),
    "matam": (15.6559, -13.2554),
    "saint louis": (16.0179, -16.4896),
    "saint-louis": (16.0179, -16.4896),
    "sedhiou": (12.7081, -15.5569),
    "tambacounda": (13.7707, -13.6673),
    "thies": (14.7886, -16.9260),
    "ziguinchor": (12.5681, -16.2719),
}

COMMODITY_CATEGORY_MAP: Dict[str, str] = {
    "Bananas (local)": "vegetables and fruits",
    "Beans (niebe)": "pulses and nuts",
    "Cabbage": "vegetables and fruits",
    "Carrots": "vegetables and fruits",
    "Cassava": "cereals and tubers",
    "Fonio": "cereals and tubers",
    "Groundnuts (shelled)": "pulses and nuts",
    "Groundnuts (unshelled)": "pulses and nuts",
    "Livestock (Goat)": "meat, fish and eggs",
    "Maize (imported)": "cereals and tubers",
    "Maize (local)": "cereals and tubers",
    "Mangoes (local)": "vegetables and fruits",
    "Millet": "cereals and tubers",
    "Onions (dry)": "vegetables and fruits",
    "Onions (imported)": "vegetables and fruits",
    "Oranges": "vegetables and fruits",
    "Oranges (imported)": "vegetables and fruits",
    "Potatoes": "cereals and tubers",
    "Potatoes (imported)": "cereals and tubers",
    "Rice (imported)": "cereals and tubers",
    "Rice (local)": "cereals and tubers",
    "Rice (ordinary, first quality)": "cereals and tubers",
    "Rice (ordinary, second quality)": "cereals and tubers",
    "Sorghum": "cereals and tubers",
    "Sorghum (imported)": "cereals and tubers",
    "Sweet potatoes": "cereals and tubers",
    "Tomatoes": "vegetables and fruits",
    "Watermelons": "vegetables and fruits",
}


class YieldForecastService:
    """A3 — Prévision de rendement subnationale (CatBoost sur HarvestStat Sénégal)."""

    BASELINE_R2 = 0.7832

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "yield")
        self.model_path = d / "a3_yield_champion.pkl"
        self.meta_path = d / "a3_yield_metadata.json"
        self.model = None
        self.meta: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists() or not self.meta_path.exists():
            self.load_error = "Artefacts A3 absents"
            return
        self.model = safe_load_pickle(self.model_path, allowed_root=self.model_path.parent)
        self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def predict(
        self,
        crop: str = "Millet",
        region: str = "Kaolack",
        department: str = "UNKNOWN",
        year: int = 2025,
        area_ha: float = 1000.0,
        season: str = "Main",
    ) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse("yield_forecast", {}, 0.0, ConfidenceLevel.UNRELIABLE, abstained=True, abstention_reason=self.load_error or "Non chargé")

        enc = self.meta["encoders"]
        crop_key, crop_matched = self._match_key(crop, enc["crop"], fallback="Millet")
        reg_key, reg_matched = self._match_key(region, enc["admin1"], fallback="Kaolack")
        dept_key, _ = self._match_key(department, enc["admin2"], fallback="UNKNOWN")
        season_key, _ = self._match_key(season, enc["season"], fallback="Main")

        warnings: List[str] = []
        conf = self.BASELINE_R2
        if not crop_matched:
            warnings.append(f"Culture '{crop}' hors périmètre A3 — repli sur '{crop_key}' (estimation indicative).")
            conf *= 0.45
        if not reg_matched:
            warnings.append(f"Région '{region}' non reconnue — repli sur '{reg_key}'.")
            conf *= 0.75
        conf = round(conf, 4)

        year_norm = (year - 1960) / 55.0
        decade = (year // 10) * 10
        log_area = math.log1p(max(1.0, float(area_ha)))

        X = np.array([[
            year, year_norm, decade, log_area,
            enc["crop"][crop_key], enc["admin1"][reg_key],
            enc["admin2"][dept_key], enc["season"][season_key],
        ]], dtype=np.float64)
        pred = max(0.0, float(self.model.predict(X)[0]))

        return ServiceResponse(
            service="yield_forecast",
            values={
                "yield_t_ha": round(pred, 4),
                "crop": crop_key,
                "requested_crop": crop,
                "fallback_used": (not crop_matched) or (not reg_matched),
                "region": reg_key,
                "department": dept_key,
                "year": year,
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            warnings=warnings,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    @staticmethod
    def _match_key(val: str, mapping: Dict[str, int], fallback: str) -> Tuple[str, bool]:
        if val in mapping:
            return val, True
        vl = val.lower().strip()
        aliases = {"mil": "Millet", "mais": "Maize", "riz": "Rice", "arachide": "Groundnuts (In Shell)", "sorgho": "Sorghum", "niebe": "Cowpea", "manioc": "Cassava", "fonio": "Fonio", "sesame": "Sesame Seed"}
        if vl in aliases and aliases[vl] in mapping:
            return aliases[vl], True
        for k in mapping:
            if vl and vl in k.lower():
                return k, True
        return (fallback if fallback in mapping else next(iter(mapping))), False


class PriceForecastService:
    """A5 — Prévision de prix marchés Sénégal (XGBoost sur WFP HDX 2000–2026)."""

    BASELINE_R2 = 0.9855

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "yield")
        self.model_path = d / "a5_price_champion.pkl"
        self.meta_path = d / "a5_price_metadata.json"
        self.model = None
        self.meta: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists() or not self.meta_path.exists():
            self.load_error = "Artefacts A5 absents"
            return
        self.model = safe_load_pickle(self.model_path, allowed_root=self.model_path.parent)
        self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    def predict(
        self,
        commodity: str = "Onions (dry)",
        market: str = "Tilene",
        region: str = "Dakar",
        year: int = 2026,
        month: int = 11,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse("price_forecast", {}, 0.0, ConfidenceLevel.UNRELIABLE, abstained=True, abstention_reason=self.load_error or "Non chargé")

        enc = self.meta["encoders"]
        comm_key, comm_matched = self._match_key(commodity, enc["commodity"], fallback="Onions (dry)")
        mkt_key, mkt_matched = self._match_key(market, enc["market"], fallback="Tilene")
        reg_key, reg_matched = self._match_key(region, enc["region"], fallback="Dakar")
        mapped_cat = COMMODITY_CATEGORY_MAP.get(comm_key)
        cat_key = mapped_cat if (mapped_cat and mapped_cat in enc["category"]) else next(iter(enc["category"]))

        default_lat, default_lon = SENEGAL_REGION_COORDS.get(reg_key.lower(), (14.6928, -17.4467))
        lat_val = float(latitude) if latitude is not None else default_lat
        lon_val = float(longitude) if longitude is not None else default_lon

        warnings: List[str] = []
        conf = self.BASELINE_R2
        if not comm_matched:
            warnings.append(f"Denrée '{commodity}' non couverte — repli sur '{comm_key}'.")
            conf *= 0.50
        if not mkt_matched:
            warnings.append(f"Marché '{market}' non reconnu — repli sur '{mkt_key}'.")
            conf *= 0.80
        if not reg_matched:
            warnings.append(f"Région '{region}' non reconnue — repli sur '{reg_key}'.")
            conf *= 0.85
        conf = round(conf, 4)

        doy = min(365, max(1, (month - 1) * 30 + 15))
        doy_sin = math.sin(2 * math.pi * doy / 365.25)
        doy_cos = math.cos(2 * math.pi * doy / 365.25)

        X = np.array([[
            year, month, doy_sin, doy_cos,
            enc["commodity"][comm_key], enc["market"][mkt_key],
            enc["region"][reg_key], enc["category"][cat_key],
            lat_val, lon_val,
        ]], dtype=np.float64)
        pred = max(0.0, float(self.model.predict(X)[0]))

        return ServiceResponse(
            service="price_forecast",
            values={
                "price_fcfa_kg": round(pred, 2),
                "commodity": comm_key,
                "category": cat_key,
                "market": mkt_key,
                "region": reg_key,
                "year": year,
                "month": month,
                "fallback_used": not (comm_matched and mkt_matched and reg_matched),
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            warnings=warnings,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    @staticmethod
    def _match_key(val: str, mapping: Dict[str, int], fallback: str) -> Tuple[str, bool]:
        if val in mapping:
            return val, True
        vl = val.lower().strip()
        aliases = {
            "oignon": "Onions (dry)", "onions": "Onions (dry)", "tomate": "Tomatoes",
            "riz": "Rice (imported)", "mais": "Maize (local)", "mil": "Millet",
            "niebe": "Beans (niebe)", "arachide": "Groundnuts (unshelled)",
            "chou": "Cabbage", "carotte": "Carrots", "pomme de terre": "Potatoes",
            "pomme_de_terre": "Potatoes", "pasteque": "Watermelons", "mangue": "Mangoes (local)",
            "manioc": "Cassava", "sorgho": "Sorghum",
        }
        if vl in aliases and aliases[vl] in mapping:
            return aliases[vl], True
        for k in mapping:
            if vl and vl in k.lower():
                return k, True
        return (fallback if fallback in mapping else next(iter(mapping))), False


class MarketClusteringService:
    """A9 — Segmentation des marchés sénégalais (KMeans k=2, Silhouette=0.6069)."""

    def __init__(self, models_dir: Optional[Path] = None):
        d = Path(models_dir) if models_dir else (ROOT / "models" / "clustering")
        self.csv_path = d / "a9_market_clusters_enriched.csv"
        self.meta_path = d / "a9_clustering_metadata.json"
        self.markets: List[Dict[str, Any]] = []
        self.meta: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.csv_path.exists():
            with self.csv_path.open("r", encoding="utf-8", newline="") as fh:
                self.markets = list(csv.DictReader(fh))
        if self.meta_path.exists():
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))

    @property
    def is_ready(self) -> bool:
        return len(self.markets) > 0

    def cheapest_markets(self, top_n: int = 3) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse("market_clustering", {}, 0.0, ConfidenceLevel.UNRELIABLE, abstained=True, abstention_reason="Clusters A9 absents")
        ranked = sorted(self.markets, key=lambda r: float(r.get("mean_price", 1e9)))[:top_n]
        return ServiceResponse(
            service="market_clustering",
            values={
                "cheapest_markets": [
                    {"market": r["market"], "region": r["admin1"], "mean_price": round(float(r["mean_price"]), 1), "cluster": int(r["cluster"])}
                    for r in ranked
                ],
                "total_markets": len(self.markets),
                "silhouette": self.meta.get("silhouette", 0.6069),
            },
            confidence=0.80,
            confidence_level=ConfidenceLevel.HIGH,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )
