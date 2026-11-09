"""Règles agronomiques : seuils du kit, ET0 FAO-56, coefficients culturaux, irrigation, fertilité.

Sources :
- Allen R.G., Pereira L.S., Raes D., Smith M. (1998). *Crop evapotranspiration — Guidelines for computing
  crop water requirements*. FAO Irrigation and Drainage Paper 56 (FAO-56) : éq. 21 (Ra), 52 (Hargreaves),
  66 (courbe de Kc), tableaux 11 (durée des stades) et 12 (Kc).
- Les Kc du tableau 12 valent pour un climat sub-humide (HRmin ≈ 45 %, u2 ≈ 2 m/s). L'ajustement climatique
  (éq. 62) n'est pas appliqué : à calibrer avec l'ISRA/ANCAR pour les Niayes.

Les classes NPK sont indicatives : les sondes NPK à conductivité (EC) du kit ne remplacent pas une analyse
de laboratoire. Aucune dose d'engrais n'est calculée ici.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

# --- Seuils du kit (règle identique au firmware v1.1, fonction seuilsValides) ---------------------------

THRESHOLD_MIN_GAP = 5
THRESHOLD_MAX = 100
_INT_STRING = re.compile(r"^\d{1,3}$")


class ThresholdError(ValueError):
    """Seuils refusés par la règle du firmware."""


def thresholds_valid(start: int, stop: int) -> bool:
    return 0 <= start and start + THRESHOLD_MIN_GAP <= stop <= THRESHOLD_MAX


def _as_int(value: Any) -> int | None:
    """Accepte un entier (pas un booléen) ou une chaîne de chiffres ; refuse les flottants."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _INT_STRING.match(value.strip()):
        return int(value.strip())
    return None


def validate_thresholds(start: Any, stop: Any) -> tuple[int, int]:
    """Valide des seuils bruts (JSON, formulaire, MQTT) ; lève ThresholdError sinon."""
    start_int, stop_int = _as_int(start), _as_int(stop)
    if start_int is None or stop_int is None:
        raise ThresholdError("Les seuils doivent être des entiers.")
    if not thresholds_valid(start_int, stop_int):
        raise ThresholdError("Règle : 0 ≤ démarrage, démarrage + 5 ≤ arrêt ≤ 100.")
    return start_int, stop_int


# --- Évapotranspiration de référence (FAO-56) --------------------------------------------------------------

SOLAR_CONSTANT = 0.0820  # MJ m-2 min-1
MJ_TO_MM = 0.408  # conversion de rayonnement en équivalent évaporation (mm/j)
HARGREAVES_COEF = 0.0023
HARGREAVES_OFFSET = 17.8


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Ra (MJ m-2 j-1), FAO-56 éq. 21 à 25. Latitude négative dans l'hémisphère sud."""
    if not -90 <= latitude_deg <= 90 or not 1 <= day_of_year <= 366:
        raise ValueError("Latitude ou jour de l'année hors plage.")
    phi = math.radians(latitude_deg)
    angle = 2 * math.pi * day_of_year / 365
    dr = 1 + 0.033 * math.cos(angle)
    delta = 0.409 * math.sin(angle - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    term = ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    return 24 * 60 / math.pi * SOLAR_CONSTANT * dr * term


def hargreaves_et0(t_max_c: float, t_min_c: float, ra_mj: float) -> float:
    """ET0 (mm/j) de Hargreaves, FAO-56 éq. 52, quand seules les températures sont disponibles."""
    if t_max_c < t_min_c:
        raise ValueError("Tmax doit être supérieure ou égale à Tmin.")
    t_mean = (t_max_c + t_min_c) / 2
    return HARGREAVES_COEF * (t_mean + HARGREAVES_OFFSET) * math.sqrt(t_max_c - t_min_c) * MJ_TO_MM * ra_mj


# --- Coefficients culturaux (FAO-56 tableaux 11 et 12) ----------------------------------------------------

@dataclass(frozen=True)
class CropProfile:
    code: str
    name_fr: str
    kc_ini: float
    kc_mid: float
    kc_end: float
    stage_days: tuple[int, int, int, int]  # initial, développement, mi-saison, arrière-saison
    stage_source: str

    @property
    def season_days(self) -> int:
        return sum(self.stage_days)


_SOURCE = "FAO-56 tableaux 11 et 12"
CROP_PROFILES: dict[str, CropProfile] = {
    p.code: p
    for p in (
        CropProfile("onion", "Oignon (bulbe sec)", 0.70, 1.05, 0.75, (15, 25, 70, 40), f"{_SOURCE} ; région aride"),
        CropProfile("tomato", "Tomate", 0.60, 1.15, 0.80, (30, 40, 40, 25), f"{_SOURCE} ; région aride"),
        CropProfile("cabbage", "Chou", 0.70, 1.05, 0.95, (40, 60, 50, 15), f"{_SOURCE} ; désert de Californie"),
        CropProfile("potato", "Pomme de terre", 0.50, 1.15, 0.75, (25, 30, 45, 30), f"{_SOURCE} ; climat semi-aride"),
        CropProfile("carrot", "Carotte", 0.70, 1.05, 0.95, (20, 30, 30, 20), f"{_SOURCE} ; climat aride"),
        CropProfile("pepper", "Poivron", 0.60, 1.05, 0.90, (25, 35, 40, 20), f"{_SOURCE} ; Méditerranée/aride"),
        CropProfile("lettuce", "Laitue", 0.70, 1.00, 0.95, (25, 35, 30, 10), f"{_SOURCE} ; Méditerranée"),
    )
}
STAGE_NAMES = ("initial", "developpement", "mi_saison", "arriere_saison")


def crop_profile(code: str) -> CropProfile:
    try:
        return CROP_PROFILES[code]
    except KeyError as exc:
        raise ValueError(f"Culture inconnue : {code!r}.") from exc


def growth_stage(profile: CropProfile, day: int) -> str:
    """Stade cultural au jour `day` après semis/repiquage (0 = jour du semis)."""
    boundary = 0
    for name, length in zip(STAGE_NAMES, profile.stage_days, strict=True):
        boundary += length
        if day < boundary:
            return name
    return "apres_recolte"


def kc_for_day(profile: CropProfile, day: int) -> float:
    """Courbe de Kc linéaire par morceaux (FAO-56 éq. 66)."""
    ini, dev, mid, late = profile.stage_days
    if day < ini:
        return profile.kc_ini
    if day < ini + dev:
        return profile.kc_ini + (day - ini) / dev * (profile.kc_mid - profile.kc_ini)
    if day < ini + dev + mid:
        return profile.kc_mid
    if day < profile.season_days:
        progress = (day - ini - dev - mid) / late
        return profile.kc_mid + progress * (profile.kc_end - profile.kc_mid)
    return profile.kc_end


# --- Recommandation d'irrigation ---------------------------------------------------------------------------

IRRIGATION_EFFICIENCY = {"drip": 0.90, "sprinkler": 0.75, "furrow": 0.60, "manual": 0.60}
DEFAULT_EFFICIENCY = 0.60
RAIN_SKIP_MM = 5.0
M3_PER_MM_HA = 10.0
IRRIGATION_CAVEAT = (
    "Estimation indicative fondée sur FAO-56 (Kc non ajustés au climat local) ; "
    "à confirmer par l'observation de la parcelle et un conseiller agricole."
)


@dataclass(frozen=True)
class IrrigationInput:
    soil_moisture_pct: float | None
    soil_sensor_ok: bool
    threshold_start_pct: int
    threshold_stop_pct: int
    et0_mm: float | None = None
    kc: float | None = None
    rain_forecast_mm: float | None = None
    irrigation_type: str | None = None
    area_ha: float | None = None


@dataclass(frozen=True)
class IrrigationAdvice:
    action: str  # verifier_capteur | irriguer | surveiller | ne_pas_irriguer
    reason: str
    etc_mm: float | None = None
    net_mm: float | None = None
    gross_mm: float | None = None
    volume_m3: float | None = None
    caveat: str = IRRIGATION_CAVEAT


def _water_amounts(data: IrrigationInput) -> tuple[float | None, float | None, float | None]:
    """Besoin du jour : ETc = Kc × ET0 ; brut = net / efficience ; volume (m³) = mm × ha × 10."""
    if data.et0_mm is None or data.kc is None:
        return None, None, None
    etc = round(data.kc * data.et0_mm, 2)
    gross = round(etc / IRRIGATION_EFFICIENCY.get(data.irrigation_type or "", DEFAULT_EFFICIENCY), 2)
    volume = round(gross * data.area_ha * M3_PER_MM_HA, 1) if data.area_ha else None
    return etc, gross, volume


def recommend_irrigation(data: IrrigationInput) -> IrrigationAdvice:
    """Décision simple, explicable, cohérente avec les seuils du kit."""
    if not data.soil_sensor_ok or data.soil_moisture_pct is None:
        return IrrigationAdvice("verifier_capteur", "Mesure d'humidité du sol indisponible : vérifier la sonde.")
    etc, gross, volume = _water_amounts(data)
    moisture = data.soil_moisture_pct
    rain = data.rain_forecast_mm or 0.0
    if moisture < data.threshold_start_pct:
        if rain >= max(RAIN_SKIP_MM, etc or 0.0):
            return IrrigationAdvice("surveiller", f"Sol sec mais {rain:.0f} mm de pluie prévus sous 24 h.", etc)
        reason = f"Humidité {moisture:.0f} % sous le seuil de démarrage ({data.threshold_start_pct} %)."
        return IrrigationAdvice("irriguer", reason, etc, etc, gross, volume)
    watch_limit = data.threshold_start_pct + (data.threshold_stop_pct - data.threshold_start_pct) / 3
    if moisture < watch_limit:
        return IrrigationAdvice("surveiller", f"Humidité {moisture:.0f} % proche du seuil de démarrage.", etc)
    return IrrigationAdvice("ne_pas_irriguer", f"Humidité {moisture:.0f} % suffisante.", etc)


# --- Fertilité (classes indicatives, sans dose) ----------------------------------------------------------

NPK_BANDS = {"n_mgkg": (20, 40), "p_mgkg": (10, 25), "k_mgkg": (80, 150)}
NUTRIENT_NAMES = {"n_mgkg": "Azote (N)", "p_mgkg": "Phosphore (P)", "k_mgkg": "Potassium (K)"}
FERTILITY_CAVEAT = (
    "Classes indicatives : les sondes NPK à conductivité du kit doivent être étalonnées contre des analyses "
    "de laboratoire. Aucune dose d'engrais n'est proposée : demandez conseil à un agent agricole (ANCAR/ISRA) "
    "et respectez l'étiquette des produits."
)


@dataclass(frozen=True)
class NutrientStatus:
    nutrient: str
    value: int | None
    level: str | None  # bas | moyen | eleve | None (inconnu)
    message: str


def classify_nutrient(key: str, value: int | None) -> NutrientStatus:
    name = NUTRIENT_NAMES[key]
    if value is None:
        return NutrientStatus(key, None, None, f"{name} : mesure indisponible.")
    low, high = NPK_BANDS[key]
    if value < low:
        message = f"{name} probablement bas : faire confirmer par une analyse de sol avant tout apport."
        return NutrientStatus(key, value, "bas", message)
    if value > high:
        return NutrientStatus(key, value, "eleve", f"{name} élevé : éviter tout apport supplémentaire.")
    return NutrientStatus(key, value, "moyen", f"{name} dans la plage indicative.")


def fertility_status(n_mgkg: int | None, p_mgkg: int | None, k_mgkg: int | None) -> tuple[NutrientStatus, ...]:
    values = {"n_mgkg": n_mgkg, "p_mgkg": p_mgkg, "k_mgkg": k_mgkg}
    return tuple(classify_nutrient(key, value) for key, value in values.items())
