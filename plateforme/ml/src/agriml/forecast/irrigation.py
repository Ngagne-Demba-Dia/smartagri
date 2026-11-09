"""Besoin en irrigation : règles agronomiques simples + recommandation à partir de la prévision d'humidité du sol.

Les seuils respectent la règle du firmware SmartAgri92 (entiers, 0 ≤ start, start + 5 ≤ stop ≤ 100) : toute
proposition de seuils envoyée à un boîtier passe par `validate_thresholds`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from agriml.features.agronomy import RAIN_EFFECTIVENESS

MIN_HYSTERESIS_PCT = 5
MAX_PCT = 100
RAIN_SKIP_MM = 10.0          # pluie prévue suffisante pour différer l'arrosage (à calibrer localement)
DEFAULT_ROOT_DEPTH_MM = 300  # profondeur racinaire utile (maraîchage) ; céréales : 600–1000
ACTION_NOW = "irriguer_maintenant"
ACTION_SOON = "irriguer_bientot"
ACTION_DEFER = "differer_pluie"
ACTION_NONE = "aucune"


def validate_thresholds(start_pct: int, stop_pct: int) -> tuple[int, int]:
    """Valide une paire de seuils comme le firmware ; lève ValueError sinon."""
    for name, value in (("start", start_pct), ("stop", stop_pct)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Seuil {name} non entier : {value!r}")
    if start_pct < 0:
        raise ValueError(f"start ({start_pct}) doit être ≥ 0.")
    if start_pct + MIN_HYSTERESIS_PCT > stop_pct:
        raise ValueError(f"stop ({stop_pct}) doit être ≥ start + {MIN_HYSTERESIS_PCT} ({start_pct + MIN_HYSTERESIS_PCT}).")
    if stop_pct > MAX_PCT:
        raise ValueError(f"stop ({stop_pct}) doit être ≤ {MAX_PCT}.")
    return start_pct, stop_pct


def crop_water_need_mm(et0_mm: float, kc: float, rain_mm: float = 0.0,
                       rain_effectiveness: float = RAIN_EFFECTIVENESS) -> float:
    """Besoin net (mm) = ETc − pluie efficace = ET0·Kc − η·pluie, borné à 0 (méthode FAO-56 simplifiée)."""
    return max(0.0, et0_mm * kc - rain_effectiveness * rain_mm)


def irrigation_depth_mm(current_pct: float, target_pct: float, root_depth_mm: float = DEFAULT_ROOT_DEPTH_MM) -> float:
    """Lame d'eau (mm) pour remonter l'humidité volumique de `current` à `target` sur la zone racinaire."""
    return max(0.0, (target_pct - current_pct) / 100.0 * root_depth_mm)


def pump_minutes(depth_mm: float, area_m2: float, flow_l_min: float) -> float:
    """Durée de pompage : 1 mm sur 1 m² = 1 litre."""
    if flow_l_min <= 0:
        raise ValueError("Le débit de la pompe doit être > 0.")
    return depth_mm * area_m2 / flow_l_min


@dataclass(frozen=True)
class IrrigationAdvice:
    action: str
    reason: str
    hours_to_start: int | None = None
    depth_mm: float = 0.0
    forecast: dict[int, float] = field(default_factory=dict)


def recommend_irrigation(current_pct: float, forecast_pct: Mapping[int, float], start_pct: int, stop_pct: int,
                         rain_forecast_mm: float = 0.0, root_depth_mm: float = DEFAULT_ROOT_DEPTH_MM) -> IrrigationAdvice:
    """Recommandation à partir de l'humidité actuelle et prévue ({horizon_h: %}).

    Le boîtier reste maître de la pompe (hystérésis start/stop) : cette recommandation sert à l'anticipation
    (alerte, planification de l'eau disponible), pas à commander la pompe à distance.
    """
    validate_thresholds(start_pct, stop_pct)
    fc = {int(h): float(v) for h, v in sorted(forecast_pct.items())}
    depth = irrigation_depth_mm(min([current_pct, *fc.values()]), stop_pct, root_depth_mm)
    if current_pct < start_pct:
        return IrrigationAdvice(ACTION_NOW, f"humidité {current_pct:.1f} % < seuil {start_pct} %", 0, depth, fc)
    below = [h for h, v in fc.items() if v < start_pct]
    if not below:
        return IrrigationAdvice(ACTION_NONE, "humidité prévue au-dessus du seuil de démarrage", None, 0.0, fc)
    if rain_forecast_mm >= RAIN_SKIP_MM:
        return IrrigationAdvice(ACTION_DEFER, f"pluie prévue {rain_forecast_mm:.0f} mm ≥ {RAIN_SKIP_MM:.0f} mm",
                                below[0], depth, fc)
    return IrrigationAdvice(ACTION_SOON, f"passage sous {start_pct} % prévu d'ici {below[0]} h", below[0], depth, fc)
