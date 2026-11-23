"""IrrigationEngine (d'après 82_smartagri_ai_runtime.md §2.6)."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class IrrigationDecision(Enum):
    IRRIGATE_NOW = "irrigate_now"
    IRRIGATE_TOMORROW = "irrigate_tomorrow"
    DELAY = "delay"
    NO_IRRIGATION = "no_irrigation"
    ABSTAIN = "abstain"


@dataclass
class IrrigationRec:
    decision: IrrigationDecision
    dose_mm: float
    confidence: float
    reasoning: List[str]
    hard_stop: bool = False
    hard_stop_reason: str = ""


class IrrigationEngine:
    """Moteur FAO-56 + SoilNowcast (R²=0.8353) + Rain (AUC=0.9625)."""

    KC = {
        "oignon": 1.05, "tomate": 1.15, "gombo": 1.0, "aubergine": 1.05,
        "piment": 1.05, "chou": 1.05, "carotte": 1.05, "pomme_de_terre": 1.15,
        "pasteque": 1.0, "melon": 1.05, "mais": 1.20, "riz": 1.20,
        "arachide": 1.15, "mil": 1.0, "sorgho": 1.0, "niebe": 1.05, "mangue": 0.75,
    }
    DEFICIT_THR = 0.55

    def __init__(self, soil, rain):
        self.soil = soil
        self.rain = rain

    def recommend(self, features: Dict[str, Any], crop: str = "oignon", area_ha: float = 1.0) -> IrrigationRec:
        reasons: List[str] = []
        days_to_harvest = features.get("days_to_harvest")
        if days_to_harvest is not None and float(days_to_harvest) <= 15.0:
            return IrrigationRec(
                IrrigationDecision.NO_IRRIGATION,
                0.0,
                0.95,
                [f"Blocage pré-récolte actif ({float(days_to_harvest):.0f} jours avant récolte <= 15j)"],
                True,
                "Blocage pré-récolte (<= 15 jours)",
            )
        sr = self.soil.predict(features)
        rr = self.rain.predict(features)
        if sr.abstained:
            return IrrigationRec(
                IrrigationDecision.ABSTAIN, 0.0, 0.0,
                ["SoilNowcast indisponible"], True, "Pas de données sol",
            )
        j1 = sr.values.get("y_plus_1d", 50.0)
        rp = rr.values.get("rain_1d_prob", 0.0) if not rr.abstained else 0.0
        rain_24h = float(features.get("rain_mm", 0.0))
        if rain_24h > 5.0:
            return IrrigationRec(
                IrrigationDecision.DELAY, 0.0, sr.confidence,
                [f"Pluie observée/prévue ({rain_24h:.1f}mm > 5mm)"], True, "Règle pluie > 5mm",
            )
        if rp > 0.70:
            return IrrigationRec(
                IrrigationDecision.DELAY, 0.0, min(sr.confidence, rr.confidence),
                [f"Pluie probable ({rp*100:.0f}%)"], True, "Pluie imminente",
            )
        if j1 > 90.0:
            return IrrigationRec(
                IrrigationDecision.NO_IRRIGATION, 0.0, sr.confidence,
                [f"Sol saturé ({j1:.0f}%)"], True, "Saturation",
            )
        et0 = float(features.get("et0_pm_mm", 4.5))
        kc = self.KC.get(crop.lower(), 1.0)
        etc = et0 * kc
        fc = float(features.get("fc_ptf_pct", 65.0))
        if fc <= 0:
            fc = 65.0
        deficit = max(0.0, fc - j1) / fc
        reasons.append(f"ETc={etc:.1f}mm (Kc={kc}), humidité J+1={j1:.1f}%, déficit={deficit*100:.0f}%")
        if deficit > (1.0 - self.DEFICIT_THR):
            dose = round(etc * (1.0 + deficit * 0.5), 1)
            dec = IrrigationDecision.IRRIGATE_NOW if deficit > 0.6 else IrrigationDecision.IRRIGATE_TOMORROW
            reasons.append(f"Dose={dose}mm ({round(dose * area_ha * 10.0, 1)} m³ pour {area_ha} ha)")
        elif rp > 0.40:
            dec = IrrigationDecision.DELAY
            dose = 0.0
            reasons.append("Risque pluie — reporter")
        else:
            dec = IrrigationDecision.NO_IRRIGATION
            dose = 0.0
            reasons.append("Sol OK — pas d'irrigation")
        conf = min(sr.confidence, rr.confidence if not rr.abstained else 1.0)
        return IrrigationRec(dec, dose, round(conf, 4), reasons)
