"""Variables agronomiques : degrés-jours, VPD (Tetens), rayonnement extraterrestre et ET0 (FAO-56 / Hargreaves),
bilan hydrique saisonnier, jours de chaleur et cumuls par parcelle.

Toutes les fonctions sont « sans état » (aucune statistique apprise sur la cible) : elles peuvent être
appliquées une seule fois sur train + test concaténés sans fuite.

Références : Allen et al. (1998), FAO Irrigation and Drainage Paper 56 — éq. 11 (es), 21-25 (Ra),
52 (Hargreaves), tableau 12 (Kc mi-saison). Les températures de base et Kc sont des valeurs de littérature
à recalibrer avec l'ISRA pour les variétés locales.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields

import numpy as np
import pandas as pd

SOLAR_CONSTANT_MJ = 0.0820  # Gsc, MJ m-2 min-1
MJ_TO_MM = 0.408  # 1 MJ m-2 j-1 ≈ 0,408 mm j-1 d'eau évaporée
HARGREAVES_COEF = 0.0023
HEAT_STRESS_C = 35.0
RAIN_EFFECTIVENESS = 0.8

DEFAULT_BASE_TEMP_C = {
    "mil": 10.0, "sorgho": 10.0, "mais": 10.0, "riz": 10.0, "arachide": 10.0, "tomate": 10.0,
    "oignon": 6.0, "chou": 5.0, "pomme_de_terre": 7.0,
}
DEFAULT_KC_MID = {
    "tomate": 1.15, "oignon": 1.05, "chou": 1.05, "riz": 1.20, "mais": 1.20,
    "mil": 1.00, "sorgho": 1.00, "arachide": 1.15, "pomme_de_terre": 1.15,
}


def growing_degree_days(tmin, tmax, base: float | np.ndarray = 10.0, upper: float | None = 30.0) -> np.ndarray:
    """Degrés-jours de croissance (méthode moyenne, températures plafonnées à `upper`)."""
    tmin = np.asarray(tmin, dtype=float)
    tmax = np.asarray(tmax, dtype=float)
    if upper is not None:
        tmin, tmax = np.minimum(tmin, upper), np.minimum(tmax, upper)
    return np.maximum((tmin + tmax) / 2.0 - base, 0.0)


def saturation_vapour_pressure_kpa(temp_c) -> np.ndarray:
    """Tension de vapeur saturante (formule de Tetens, FAO-56 éq. 11)."""
    t = np.asarray(temp_c, dtype=float)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def vapour_pressure_deficit_kpa(tmin, tmax, rh_pct) -> np.ndarray:
    """Déficit de pression de vapeur : es moyen (Tmin, Tmax) − ea, avec ea = es · HR / 100."""
    es = (saturation_vapour_pressure_kpa(tmin) + saturation_vapour_pressure_kpa(tmax)) / 2.0
    ea = es * np.clip(np.asarray(rh_pct, dtype=float), 0, 100) / 100.0
    return np.maximum(es - ea, 0.0)


def extraterrestrial_radiation_mj(lat_deg, doy) -> np.ndarray:
    """Rayonnement extraterrestre Ra (MJ m-2 j-1), FAO-56 éq. 21 à 25."""
    phi = np.deg2rad(np.asarray(lat_deg, dtype=float))
    j = np.asarray(doy, dtype=float)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    delta = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))
    return (24 * 60 / np.pi) * SOLAR_CONSTANT_MJ * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )


def hargreaves_et0_mm(tmin, tmax, ra_mj) -> np.ndarray:
    """ET0 de Hargreaves (mm/j) : 0,0023 · (Tmoy + 17,8) · √(Tmax − Tmin) · 0,408 · Ra."""
    tmin = np.asarray(tmin, dtype=float)
    tmax = np.asarray(tmax, dtype=float)
    tmean = (tmin + tmax) / 2.0
    return HARGREAVES_COEF * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0.0)) * MJ_TO_MM * np.asarray(ra_mj)


@dataclass(frozen=True)
class AgronomyColumns:
    """Noms des colonnes sources (toutes optionnelles sauf tmin/tmax)."""

    tmin: str = "tmin_c"
    tmax: str = "tmax_c"
    rh: str | None = None
    rain: str | None = None
    irrigation: str | None = None
    lat: str | None = None
    doy: str | None = None
    crop: str | None = None
    season_days: str | None = None
    heat_days: str | None = None
    cumulative_by: str | None = None
    time: str | None = None
    gdd_upper: float | None = 30.0

    @classmethod
    def from_mapping(cls, mapping: Mapping) -> AgronomyColumns:
        known = {f.name for f in fields(cls)}
        unknown = set(mapping) - known
        if unknown:
            raise ValueError(f"features.agronomy : clés inconnues {sorted(unknown)}")
        return cls(**dict(mapping))


def _crop_values(df: pd.DataFrame, crop_col: str | None, table: Mapping[str, float], default: float) -> np.ndarray:
    if crop_col is None or crop_col not in df:
        return np.full(len(df), default)
    return df[crop_col].astype(str).str.lower().map(table).fillna(default).to_numpy(dtype=float)


def _season_features(out: pd.DataFrame, src: pd.DataFrame, c: AgronomyColumns) -> None:
    days = src[c.season_days].to_numpy(dtype=float)
    out["agro_gdd_season"] = out["agro_gdd_day"] * days
    if "agro_et0_mm_day" in out:
        kc = _crop_values(src, c.crop, DEFAULT_KC_MID, 1.0)
        out["agro_et0_season_mm"] = out["agro_et0_mm_day"] * days
        out["agro_etc_season_mm"] = out["agro_et0_season_mm"] * kc
        water = np.zeros(len(src))
        if c.rain and c.rain in src:
            water = water + RAIN_EFFECTIVENESS * src[c.rain].fillna(0).to_numpy(dtype=float)
        if c.irrigation and c.irrigation in src:
            water = water + src[c.irrigation].fillna(0).to_numpy(dtype=float)
        out["agro_water_balance_mm"] = water - out["agro_etc_season_mm"]
        out["agro_water_ratio"] = water / np.maximum(out["agro_etc_season_mm"].to_numpy(), 1.0)


def _cumulative_features(out: pd.DataFrame, src: pd.DataFrame, c: AgronomyColumns) -> None:
    """Cumuls par groupe dans l'ordre du temps (inclut le jour courant, jamais le futur)."""
    order = src.sort_values([c.cumulative_by, c.time], kind="stable").index
    keys = src.loc[order, c.cumulative_by]
    gdd = out.loc[order, "agro_gdd_day"]
    out.loc[order, "agro_gdd_cum"] = gdd.groupby(keys.to_numpy()).cumsum().to_numpy()
    heat = out.loc[order, "agro_heat_day"]
    out.loc[order, "agro_heat_days_cum"] = heat.groupby(keys.to_numpy()).cumsum().to_numpy()
    if c.rain and c.rain in src:
        rain = src.loc[order, c.rain].fillna(0)
        out.loc[order, "agro_rain_cum_mm"] = rain.groupby(keys.to_numpy()).cumsum().to_numpy()


def add_agronomy_features(df: pd.DataFrame, columns: AgronomyColumns | Mapping) -> pd.DataFrame:
    """Renvoie une copie de `df` enrichie des variables agronomiques (préfixe « agro_ »)."""
    c = columns if isinstance(columns, AgronomyColumns) else AgronomyColumns.from_mapping(columns)
    missing = [col for col in (c.tmin, c.tmax) if col not in df]
    if missing:
        raise KeyError(f"Colonnes agronomiques absentes : {missing}")
    out = df.copy()
    tmin, tmax = df[c.tmin].to_numpy(dtype=float), df[c.tmax].to_numpy(dtype=float)
    base = _crop_values(df, c.crop, DEFAULT_BASE_TEMP_C, 10.0)
    out["agro_tmean_c"] = (tmin + tmax) / 2.0
    out["agro_gdd_day"] = growing_degree_days(tmin, tmax, base, c.gdd_upper)
    if c.heat_days and c.heat_days in df:
        out["agro_heat_day"] = df[c.heat_days].to_numpy(dtype=float)
    else:
        out["agro_heat_day"] = (tmax >= HEAT_STRESS_C).astype(float)
    if c.rh and c.rh in df:
        out["agro_vpd_kpa"] = vapour_pressure_deficit_kpa(tmin, tmax, df[c.rh].to_numpy(dtype=float))
    if c.lat and c.doy and c.lat in df and c.doy in df:
        out["agro_ra_mj"] = extraterrestrial_radiation_mj(df[c.lat], df[c.doy])
        out["agro_et0_mm_day"] = hargreaves_et0_mm(tmin, tmax, out["agro_ra_mj"])
    if c.season_days and c.season_days in df:
        _season_features(out, df, c)
    if c.cumulative_by and c.time and c.cumulative_by in df and c.time in df:
        _cumulative_features(out, df, c)
    return out
