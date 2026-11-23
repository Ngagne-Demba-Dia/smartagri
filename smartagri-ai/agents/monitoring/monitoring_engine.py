"""MonitoringEngine (d'après 82_smartagri_ai_runtime.md §2.5)."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple


class AlertLevel(Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class MonitoringAlert:
    level: AlertLevel
    category: str
    message: str
    confidence: float
    components: List[str]
    action: str
    escalate: bool = False


class MonitoringEngine:
    """Moteur de surveillance parcellaire."""

    WEIGHTS = {"soil": 0.35, "rain": 0.25, "anomaly": 0.25, "et0": 0.15}
    RISK_BANDS = [
        (0.0, 0.30, "NORMAL"),
        (0.30, 0.55, "WATCH"),
        (0.55, 0.75, "WARNING"),
        (0.75, 1.01, "CRITICAL"),
    ]

    def __init__(self, soil, rain, anomaly):
        self.soil = soil
        self.rain = rain
        self.anomaly = anomaly

    def assess(self, features: Dict[str, Any]) -> Tuple[float, AlertLevel, List[MonitoringAlert]]:
        alerts: List[MonitoringAlert] = []
        risk = 0.0
        sr = self.soil.predict(features)
        rr = self.rain.predict(features)
        ar = self.anomaly.detect(features)

        if not sr.abstained:
            j1 = sr.values.get("y_plus_1d", 50.0)
            if j1 < 20.0:
                risk += self.WEIGHTS["soil"] * min(1.0, (20.0 - j1) / 10.0)
                alerts.append(MonitoringAlert(
                    AlertLevel.WARNING if j1 >= 15.0 else AlertLevel.CRITICAL,
                    "drought_risk",
                    f"Humidité J+1 faible ({j1:.1f}%)",
                    sr.confidence,
                    ["soil_nowcast"],
                    "Planifier irrigation",
                ))
            elif j1 > 85.0:
                risk += self.WEIGHTS["soil"] * min(1.0, (j1 - 85.0) / 15.0)
                alerts.append(MonitoringAlert(
                    AlertLevel.WARNING,
                    "saturation_risk",
                    f"Sol très humide J+1 ({j1:.1f}%)",
                    sr.confidence,
                    ["soil_nowcast"],
                    "Suspendre irrigation",
                ))

        if not rr.abstained:
            rp = rr.values.get("rain_1d_prob", 0.0)
            j1s = sr.values.get("y_plus_1d", 50.0) if not sr.abstained else 50.0
            if rp > 0.7 and j1s > 70.0:
                risk += self.WEIGHTS["rain"] * 0.8
                alerts.append(MonitoringAlert(
                    AlertLevel.WARNING,
                    "excess",
                    f"Pluie ({rp*100:.0f}%) + sol humide ({j1s:.0f}%)",
                    min(sr.confidence, rr.confidence),
                    ["soil_nowcast", "rain_intelligence"],
                    "Reporter irrigation",
                ))

        if not ar.abstained:
            sev = ar.values.get("max_severity", "NORMAL")
            if sev == "CRITICAL":
                crit_anoms = [a for a in ar.values.get("anomalies", []) if a.get("severity") == "CRITICAL"]
                risk += min(0.50, self.WEIGHTS["anomaly"] * max(1, len(crit_anoms)))
                for anom in ar.values.get("anomalies", []):
                    detail = anom.get("value", anom.get("score", anom.get("mse", "N/A")))
                    alerts.append(MonitoringAlert(
                        AlertLevel.CRITICAL if anom.get("severity") == "CRITICAL" else AlertLevel.WARNING,
                        anom.get("type", "unknown"),
                        f"Anomalie critique: {anom.get('type', 'unknown')} ({detail})",
                        ar.confidence,
                        ["anomaly"],
                        "Vérification terrain urgente",
                    ))
            elif sev == "WARNING":
                risk += self.WEIGHTS["anomaly"] * 0.6

        et0_val = features.get("et0_pm_mm")
        if et0_val is not None:
            et0_f = float(et0_val)
            if et0_f > 7.0:
                risk += self.WEIGHTS["et0"]
                alerts.append(MonitoringAlert(
                    AlertLevel.WARNING,
                    "et0_extreme",
                    f"Évapotranspiration extrême ({et0_f:.1f} mm/j)",
                    0.85,
                    ["et0"],
                    "Renforcer le suivi hydrique",
                ))
            elif et0_f > 6.0:
                risk += self.WEIGHTS["et0"] * 0.5

        risk = round(min(1.0, risk), 4)
        level = AlertLevel.NORMAL
        for lo, hi, lbl in self.RISK_BANDS:
            if lo <= risk < hi:
                level = AlertLevel[lbl]
                break
        if any(a.level == AlertLevel.CRITICAL for a in alerts) and risk >= 0.55:
            level = AlertLevel.CRITICAL
        if level == AlertLevel.CRITICAL:
            for a in alerts:
                a.escalate = True
        return risk, level, alerts
