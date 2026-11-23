"""Data Lake réel NATIONAL SmartAgri92 (mission IA-REAL-03) — Sénégal entier, sans site pilote.

Principe : une grille nationale unique de 0,05° (≈ 5,5 km, alignée sur CHIRPS) couvre toutes les cellules touchant
le territoire sénégalais (14 régions, geoBoundaries ADM1). Tous les jeux sont indexés par `cell_id` (grille 0,05°)
ou `power_cell_id` (maille native NASA POWER 0,5° × 0,625°), jamais par un nom de site. Un kit installé n'importe où
est relié à ses données par simple recherche de cellule (lat, lon). Mboro, Potou et Richard-Toll ne sont gardés que
comme zones de VALIDATION (colonne `validation_zone`), exclues de l'entraînement dans l'instantané OctOpus.

Aucun modèle n'est entraîné. Aucune donnée synthétique : chaque valeur vient d'une source téléchargée ou d'un calcul
déterministe documenté (FAO-56). Rien n'est saisi à la main.

Usage : python scripts/build_national_data_lake.py --stages legacy,grid,nasa,chirps,soil,landcover,s2catalog,s2ndvi,static,reuse,octopus,audit
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import secrets
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window

ML_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ML_ROOT / "src"))

PLATEFORME = ML_ROOT.parent
REAL = ML_ROOT / "data" / "real"
CURATED = ML_ROOT / "data" / "curated"
CACHE = ML_ROOT / "data" / "_cache"
GEO_DIR = REAL / "geo"
MANIFESTS = REAL / "manifests"
MISSION = "IA-REAL-03"

# --- grille nationale 0,05° (alignée sur CHIRPS : bords multiples de 0,05°) -------------------------------------
WEST, EAST, SOUTH, NORTH, RES = -17.60, -11.30, 12.25, 16.70, 0.05
NCOLS = int(round((EAST - WEST) / RES))
NROWS = int(round((NORTH - SOUTH) / RES))
GRID_TF = from_origin(WEST, NORTH, RES, RES)
DATA_START, DATA_END = date(2015, 1, 1), date(2026, 11, 10)

# Zones de VALIDATION uniquement (jamais d'entraînement) ; coordonnées publiques de localités.
VALIDATION_ZONES = {
    "mboro": (15.1503, -16.8797),
    "potou": (15.7209, -16.5063),
    "richard_toll": (16.4625, -15.7008),
}
ZONE_RADIUS_KM = 25.0

_GRID: pd.DataFrame | None = None
_POWER: pd.DataFrame | None = None


def log(msg: str) -> None:
    print(f"[{datetime.now(UTC):%H:%M:%S}] {msg}", flush=True)


def grid() -> pd.DataFrame:
    global _GRID
    if _GRID is None:
        _GRID = pd.read_parquet(GEO_DIR / "senegal_grid_0p05.parquet", engine="fastparquet")
    return _GRID


def power_cells() -> pd.DataFrame:
    global _POWER
    if _POWER is None:
        _POWER = pd.read_parquet(GEO_DIR / "power_cells_0p5x0p625.parquet", engine="fastparquet")
    return _POWER


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def write_parquet(
    df: pd.DataFrame,
    path: Path,
    *,
    domain: str,
    source_id: str,
    owner: str,
    licence: str,
    source_url: str,
    description: str,
    commercial_use: str = "open",
    time_col: str | None = None,
    key: list[str] | None = None,
    cell_col: str | None = None,
    cell_kind: str | None = None,
    daily: bool = False,
    checks: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Écrit le Parquet + son manifeste (SHA-256, qualité, couverture temporelle et géographique)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="fastparquet", compression="snappy")
    size = path.stat().st_size
    nulls = {c: int(n) for c, n in df.isna().sum().items() if n}
    total_cells = max(1, df.shape[0] * df.shape[1])
    m: dict[str, Any] = {
        "mission": MISSION,
        "scope": "national",
        "domain": domain,
        "file_name": path.name,
        "relative_path": str(path.relative_to(ML_ROOT)).replace("\\", "/"),
        "source_id": source_id,
        "owner": owner,
        "licence": licence,
        "commercial_use": commercial_use,
        "synthetic_data": False,
        "source_url": source_url,
        "description": description,
        "fetched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": sha256_file(path),
        "size_bytes": size,
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "quality": {
            "completeness_pct": round(100.0 * (1 - sum(nulls.values()) / total_cells), 3),
            "null_cells_by_column": nulls,
            "duplicate_key_rows": int(df.duplicated(subset=key).sum()) if key else None,
            "key": key,
        },
    }
    if checks:
        m["quality"]["checks"] = checks
    if time_col and time_col in df.columns and len(df):
        t = pd.to_datetime(df[time_col])
        uniq = int(t.nunique())
        tc: dict[str, Any] = {"column": time_col, "min": str(t.min()), "max": str(t.max()), "unique_periods": uniq}
        if daily:
            expected = (t.max().normalize() - t.min().normalize()).days + 1
            tc["expected_days"] = int(expected)
            tc["missing_days"] = int(expected - t.dt.normalize().nunique())
        m["temporal_coverage"] = tc
    else:
        m["temporal_coverage"] = {"type": "static_or_not_applicable"}
    if cell_col and cell_kind and cell_col in df.columns:
        ids = df[cell_col].dropna().unique()
        ref = grid() if cell_kind == "grid" else power_cells()
        idc = "cell_id" if cell_kind == "grid" else "power_cell_id"
        reg = "region_adm1" if cell_kind == "grid" else "region_main"
        sub = ref[ref[idc].isin(ids)]
        m["geographic_coverage"] = {
            "country": "SN",
            "cell_kind": cell_kind,
            "cells_present": int(len(sub)),
            "cells_expected": int(len(ref)),
            "coverage_pct": round(100.0 * len(sub) / len(ref), 2),
            "regions_covered": int(sub[reg].nunique()),
            "regions_total": int(ref[reg].nunique()),
            "lat_min": round(float(sub["lat"].min()), 3) if len(sub) else None,
            "lat_max": round(float(sub["lat"].max()), 3) if len(sub) else None,
            "lon_min": round(float(sub["lon"].min()), 3) if len(sub) else None,
            "lon_max": round(float(sub["lon"].max()), 3) if len(sub) else None,
        }
    else:
        m["geographic_coverage"] = {"country": "SN", "cell_kind": None, "note": "table non spatialisée par cellule"}
    if extra:
        m.update(extra)
    path.with_suffix(".parquet.manifest.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"OK {m['relative_path']} | {m['rows']:,} lignes | {size / 1024:.0f} Ko | complétude {m['quality']['completeness_pct']} %")
    return m


def add_cross_check(name: str, payload: dict[str, Any]) -> None:
    p = MANIFESTS / "cross_checks.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    cur[name] = payload
    p.write_text(json.dumps(cur, indent=2, ensure_ascii=False), encoding="utf-8")


# ======================================================================================================
# 0. Rangement : les jeux 6 sites de IA-REAL-02 deviennent « legacy » ; les tables non vérifiables sont en quarantaine
# ======================================================================================================
LEGACY_FILES = [
    "meteo/nasa_power_senegal_daily.parquet",
    "meteo/nasa_power_senegal_hourly.parquet",
    "rain/chirps_v3_cog_hivernage_senegal.parquet",
    "rain/senegal_daily_rain_series_2015_2026.parquet",
    "et0/fao56_et0_senegal_daily.parquet",
    "soil_moisture/nasa_power_soil_moisture_daily.parquet",
    "soil_properties/isdasoil_30m_senegal_profiles.parquet",
    "sentinel2_ndvi/deafrica_s2_scenes_catalog_2022_2026.parquet",
    "sentinel2_ndvi/deafrica_s2_ndvi_pilot_sites.parquet",
    "crops_senegal/esa_worldcover_10m_senegal_zones.parquet",
]
QUARANTINE_FILES = {
    "meteo/ecmwf_gfs_forecast_asof.parquet": "Obtenu via l'API gratuite Open-Meteo (licence non commerciale) et non via les GRIB ECMWF/NOAA ; 6 sites seulement.",
    "crops_senegal/csp_cilss_homologated_active_ingredients.parquet": "Saisie manuelle non sourcée ligne par ligne : à remplacer par la liste officielle CSP.",
    "crops_senegal/fao56_senegal_crops_kc_daily.parquet": "Colonnes Zr, p et calendriers saisies à la main ; Kc régénérés depuis agronomy.py.",
    "market_prices/senegal_energy_irrigation_tariffs.parquet": "Tarifs saisis de mémoire, non vérifiés contre les arrêtés Senelec/CRSE.",
}


def _move(rel: str, dest_root: Path) -> bool:
    moved = False
    for suffix in ("", ".manifest.json"):
        src = REAL / (rel + suffix)
        if src.exists():
            dst = dest_root / (rel + suffix)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved = True
    return moved


def stage_legacy() -> None:
    log("== legacy : rangement des jeux 6 sites et quarantaine ==")
    legacy, quarantine = REAL / "_legacy_pilot_6sites", REAL / "_quarantine"
    for rel in LEGACY_FILES:
        _move(rel, legacy)
    for rel in QUARANTINE_FILES:
        _move(rel, quarantine)
    old_report = MANIFESTS / "lake_audit_report.json"
    if old_report.exists():
        (legacy / "manifests").mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_report), str(legacy / "manifests" / "lake_audit_report_pilot.json"))
    cur_legacy = CURATED / "_legacy_pilot_6sites"
    for sub in ("octopus", "holdout"):
        src = CURATED / sub
        if src.exists() and any(src.iterdir()):
            cur_legacy.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(cur_legacy / sub))
    old_script = ML_ROOT / "scripts" / "build_real_data_lake.py"
    if old_script.exists():
        shutil.move(str(old_script), str(ML_ROOT / "scripts" / "legacy_build_real_data_lake_pilot_6sites.py"))
    (legacy / "README.md").write_text(
        "# Jeux « 6 sites » de IA-REAL-02 — OBSOLÈTES\n\nConservés pour traçabilité uniquement. Remplacés par les jeux "
        "nationaux de IA-REAL-03. Ne pas utiliser pour l'entraînement : couverture limitée à 6 sites choisis à la main.\n"
        "Les chemins `relative_path` des manifestes ne sont plus à jour. Zones Mboro/Potou/Richard-Toll : voir la colonne "
        "`validation_zone` de `geo/senegal_grid_0p05.parquet`.\n",
        encoding="utf-8",
    )
    (quarantine / "README.md").parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"- `{k}` : {v}" for k, v in QUARANTINE_FILES.items())
    (quarantine / "README.md").write_text(
        "# Quarantaine — fichiers à ne PAS utiliser\n\nRaisons :\n" + lines + "\n", encoding="utf-8"
    )


# ======================================================================================================
# 1. Grille nationale + régions + mailles NASA POWER
# ======================================================================================================
def stage_grid() -> None:
    log("== grid : frontières geoBoundaries ADM1 + grille 0,05° ==")
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180, follow_redirects=True) as c:
        meta = c.get("https://www.geoboundaries.org/api/current/gbOpen/SEN/ADM1/").json()
        gj = c.get(meta["gjDownloadURL"]).json()
    (GEO_DIR / "senegal_admin1_geoboundaries.geojson").write_text(json.dumps(gj), encoding="utf-8")
    names = [f["properties"]["shapeName"] for f in gj["features"]]
    shapes = [(f["geometry"], i + 1) for i, f in enumerate(gj["features"])]
    mask = rasterize(shapes, out_shape=(NROWS, NCOLS), transform=GRID_TF, fill=0, all_touched=True, dtype="int16")
    rows, cols = np.nonzero(mask)
    lat = NORTH - RES * (rows + 0.5)
    lon = WEST + RES * (cols + 0.5)
    pj = np.round(lat / 0.5).astype(int)
    pi_ = np.round((lon + 180.0) / 0.625).astype(int)
    plat, plon = pj * 0.5, pi_ * 0.625 - 180.0
    zone = np.full(len(lat), "", dtype=object)
    best = np.full(len(lat), np.inf)
    for zname, (zlat, zlon) in VALIDATION_ZONES.items():
        d = haversine_km(lat, lon, zlat, zlon)
        hit = (d <= ZONE_RADIUS_KM) & (d < best)
        zone[hit] = zname
        best[hit] = d[hit]
    g = pd.DataFrame(
        {
            "cell_id": (rows * NCOLS + cols).astype("int32"),
            "row": rows.astype("int16"),
            "col": cols.astype("int16"),
            "lat": np.round(lat, 4),
            "lon": np.round(lon, 4),
            "region_adm1": [names[mask[r, c] - 1] for r, c in zip(rows, cols, strict=True)],
            "power_cell_id": [f"pw_{a:.1f}_{b:.3f}" for a, b in zip(plat, plon, strict=True)],
            "validation_zone": pd.Series(zone).replace("", None),
            "area_km2": np.round(RES * 111.32 * np.cos(np.radians(lat)) * RES * 110.57, 2),
        }
    )
    g.to_parquet(GEO_DIR / "senegal_grid_0p05.parquet", index=False, engine="fastparquet", compression="snappy")
    p = (
        g.groupby("power_cell_id")
        .agg(n_grid_cells=("cell_id", "size"), area_km2=("area_km2", "sum"), region_main=("region_adm1", lambda s: s.mode().iloc[0]))
        .reset_index()
    )
    coords = p["power_cell_id"].str.extract(r"pw_(-?[\d.]+)_(-?[\d.]+)").astype(float)
    p["lat"], p["lon"] = coords[0], coords[1]
    vz = g.dropna(subset=["validation_zone"]).groupby("power_cell_id")["validation_zone"].agg(lambda s: ",".join(sorted(set(s))))
    p["validation_zone"] = p["power_cell_id"].map(vz)
    p.to_parquet(GEO_DIR / "power_cells_0p5x0p625.parquet", index=False, engine="fastparquet", compression="snappy")
    info = {
        "mission": MISSION,
        "grid": {"west": WEST, "east": EAST, "south": SOUTH, "north": NORTH, "res_deg": RES, "ncols": NCOLS, "nrows": NROWS},
        "cells": int(len(g)),
        "power_cells": int(len(p)),
        "regions": sorted(g["region_adm1"].unique().tolist()),
        "cells_per_region": g["region_adm1"].value_counts().to_dict(),
        "validation_zone_cells": g["validation_zone"].value_counts().to_dict(),
        "boundary_source": f"{meta.get('boundarySource')} — {meta.get('boundaryLicense')}",
        "note": "all_touched=True : toute cellule touchée par le territoire est incluse (les kits côtiers/frontaliers y sont rattachés).",
    }
    (GEO_DIR / "grid_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"grille : {len(g)} cellules 0,05°, {len(p)} mailles NASA, {len(info['regions'])} régions, zones validation {info['validation_zone_cells']}")


# ======================================================================================================
# 2. NASA POWER (météo, ET0 FAO-56, humidité du sol) sur TOUTES les mailles du pays
# ======================================================================================================
POWER_PARAMS = "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PS,PRECTOTCORR,GWETTOP,GWETROOT,GWETPROF"


def _fetch_power(pid: str, lat: float, lon: float) -> dict[str, Any]:
    cache = CACHE / "nasa" / f"{pid}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={POWER_PARAMS}&community=AG&longitude={lon}&latitude={lat}"
        f"&start={DATA_START:%Y%m%d}&end={DATA_END:%Y%m%d}&format=JSON"
    )
    for attempt in range(6):
        try:
            r = httpx.get(url, timeout=180)
            if r.status_code == 200:
                data = r.json()["properties"]["parameter"]
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(data), encoding="utf-8")
                return data
            if r.status_code not in (429, 500, 502, 503, 504):
                r.raise_for_status()
        except httpx.HTTPError:
            pass
        time.sleep(6 * (attempt + 1))
    raise RuntimeError(f"NASA POWER indisponible pour {pid}")


def ra_mj(lat_deg, doy):
    phi = np.radians(lat_deg)
    ang = 2 * np.pi * doy / 365
    dr, delta = 1 + 0.033 * np.cos(ang), 0.409 * np.sin(ang - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1, 1))
    return (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))


def hargreaves(tmin, tmax, ra):
    ok = tmax >= tmin
    return np.where(ok, 0.0023 * ((tmax + tmin) / 2 + 17.8) * np.sqrt(np.where(ok, tmax - tmin, 0)) * 0.408 * ra, np.nan)


def penman_monteith(tmin, tmax, rh, u2, rs, ra, p_kpa):
    """FAO-56 éq. 6 (G ≈ 0, pas journalier). u2 plancher 0,5 m/s ; altitude déduite de la pression (formule standard)."""
    tm = (tmax + tmin) / 2
    delta = 4098 * (0.6108 * np.exp(17.27 * tm / (tm + 237.3))) / (tm + 237.3) ** 2
    gamma = 0.000665 * p_kpa
    e0 = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))  # noqa: E731
    es = (e0(tmax) + e0(tmin)) / 2
    ea = es * np.clip(rh, 5, 100) / 100
    elev = np.clip(44330 * (1 - (p_kpa / 101.325) ** 0.1903), 0, 1000)
    rso = (0.75 + 2e-5 * elev) * ra
    rel = np.clip(rs / np.maximum(rso, 0.1), 0.25, 1.0)
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rel - 0.35)
    rn = np.maximum(0.77 * rs - rnl, 0)
    u = np.maximum(u2, 0.5)
    return np.maximum((0.408 * delta * rn + gamma * 900 / (tm + 273) * u * (es - ea)) / (delta + gamma * (1 + 0.34 * u)), 0)


def stage_nasa() -> None:
    log("== nasa : NASA POWER AG sur toutes les mailles ==")
    p = power_cells()
    cells = list(p[["power_cell_id", "lat", "lon"]].itertuples(index=False, name=None))
    with ThreadPoolExecutor(3) as ex:
        payloads = list(ex.map(lambda t: _fetch_power(*t), cells))
    frames = []
    for (pid, lat, lon), data in zip(cells, payloads, strict=True):
        d = pd.DataFrame(data).replace(-999.0, np.nan)
        d.index = pd.to_datetime(d.index, format="%Y%m%d")
        d.index.name = "date"
        d["power_cell_id"], d["lat"], d["lon"] = pid, lat, lon
        frames.append(d.reset_index())
    a = pd.concat(frames, ignore_index=True)
    a = a.dropna(subset=["T2M_MAX", "T2M_MIN"]).reset_index(drop=True)
    log(f"NASA POWER : {len(a):,} lignes, {a['power_cell_id'].nunique()} mailles")

    meteo = pd.DataFrame(
        {
            "power_cell_id": a["power_cell_id"], "lat": a["lat"], "lon": a["lon"], "date": a["date"],
            "t_min_c": a["T2M_MIN"].round(2), "t_max_c": a["T2M_MAX"].round(2), "t_mean_c": a["T2M"].round(2),
            "rh_mean_pct": a["RH2M"].round(2), "wind_2m_ms": a["WS2M"].round(2),
            "solar_rad_mj_m2": a["ALLSKY_SFC_SW_DWN"].round(2), "pressure_hpa": (a["PS"] * 10).round(1),
            "rain_mm": a["PRECTOTCORR"].clip(lower=0).round(2),
        }
    )
    chk = {
        "tmin_le_tmax_share_pct": round(100 * float((meteo.t_min_c <= meteo.t_max_c).mean()), 3),
        "rh_in_0_100_share_pct": round(100 * float(meteo.rh_mean_pct.dropna().between(0, 100).mean()), 3),
        "rain_non_negative_share_pct": round(100 * float((meteo.rain_mm.dropna() >= 0).mean()), 3),
        "t_max_range_c": [float(meteo.t_max_c.min()), float(meteo.t_max_c.max())],
        "solar_rad_range_mj": [float(meteo.solar_rad_mj_m2.min()), float(meteo.solar_rad_mj_m2.max())],
    }
    common = dict(
        owner="NASA Langley Research Center — POWER (MERRA-2 / CERES), maille native 0,5° × 0,625°",
        licence="NASA Open Data (libre, citation POWER requise)",
        source_url="https://power.larc.nasa.gov/api/temporal/daily/point?community=AG",
        time_col="date", cell_col="power_cell_id", cell_kind="power", daily=True, key=["power_cell_id", "date"],
    )
    write_parquet(meteo, REAL / "meteo" / "nasa_power_national_daily.parquet", domain="meteo", source_id="nasa_power",
                  description="Météo quotidienne observée/réanalysée, toutes les mailles NASA POWER du Sénégal, 2015-2026.",
                  checks=chk, **common)

    doy = a["date"].dt.dayofyear.to_numpy()
    ra = ra_mj(a["lat"].to_numpy(), doy)
    tmin, tmax, rh, u2, rs, pk = (a[c].to_numpy() for c in ["T2M_MIN", "T2M_MAX", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS"])
    et_h, et_pm = hargreaves(tmin, tmax, ra), penman_monteith(tmin, tmax, rh, u2, rs, ra, pk)
    et0 = pd.DataFrame(
        {"power_cell_id": a["power_cell_id"], "lat": a["lat"], "lon": a["lon"], "date": a["date"],
         "ra_mj_m2": np.round(ra, 2), "et0_hargreaves_mm": np.round(et_h, 2), "et0_pm_mm": np.round(et_pm, 2)}
    )
    write_parquet(et0, REAL / "et0" / "fao56_et0_national_daily.parquet", domain="et0",
                  source_id="nasa_power+fao56", description=(
                      "ET0 FAO-56 calculée (Ra éq. 21, Hargreaves éq. 52, Penman-Monteith éq. 6) depuis NASA POWER, sans imputation : "
                      "et0_pm_mm reste vide quand le rayonnement ou le vent manque."),
                  checks={"et0_pm_range_mm": [float(np.nanmin(et_pm)), float(np.nanmax(et_pm))],
                          "et0_pm_median_mm": float(np.nanmedian(et_pm)),
                          "pm_vs_hargreaves_corr": round(float(pd.Series(et_pm).corr(pd.Series(et_h))), 4)},
                  **{**common, "owner": "NASA POWER + FAO Irrigation and Drainage Paper 56", "licence": "NASA Open Data + méthode FAO-56 publique"})

    sm = pd.DataFrame(
        {"power_cell_id": a["power_cell_id"], "lat": a["lat"], "lon": a["lon"], "date": a["date"],
         "gwettop_ratio": a["GWETTOP"].round(4), "gwetroot_ratio": a["GWETROOT"].round(4), "gwetprof_ratio": a["GWETPROF"].round(4)}
    )
    write_parquet(sm, REAL / "soil_moisture" / "nasa_power_soil_wetness_national_daily.parquet", domain="soil_moisture",
                  source_id="nasa_power", description=(
                      "Humidité du sol MODÉLISÉE (GEOS/MERRA-2) : taux de saturation relatif [0-1] en surface (0-5 cm), zone racinaire "
                      "(0-100 cm) et profil. Ce n'est PAS une mesure de capteur ni une teneur volumique."),
                  checks={"ratios_in_0_1_share_pct": round(100 * float(sm.gwetroot_ratio.dropna().between(0, 1).mean()), 3)},
                  **common)


# ======================================================================================================
# 3. CHIRPS v3 quotidien sur toute la grille nationale (une année = un fichier)
# ======================================================================================================
def _chirps_url(d: date) -> tuple[str, bool]:
    if d <= date(2026, 9, 30):
        return (
            f"https://deafrica-input-datasets.s3.af-south-1.amazonaws.com/rainfall_chirps_daily/"
            f"{d.year}/{d.month:02d}/chirps-v2.0_{d:%Y.%m.%d}.tif",
            False,
        )
    base = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily"
    if d <= date(2026, 10, 31):
        return f"{base}/final/rnl/{d.year}/chirps-v3.0.rnl.{d:%Y.%m.%d}.tif", False
    return f"{base}/prelim/sat/{d.year}/chirps-v3.0.prelim.{d:%Y.%m.%d}.tif", True


def _read_chirps_day(d: date) -> tuple[date, np.ndarray | None]:
    url, _ = _chirps_url(d)
    attempts = 3 if "deafrica-input-datasets" in url else 1
    for attempt in range(attempts):
        try:
            with rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                GDAL_HTTP_TIMEOUT="15",
                GDAL_HTTP_CONNECTTIMEOUT="8",
                GDAL_HTTP_MAX_RETRY="2",
                GDAL_HTTP_RETRY_DELAY="1",
            ):
                with rasterio.open(url) as src:
                    co = int(round((WEST - src.bounds.left) / RES))
                    ro = int(round((src.bounds.top - NORTH) / RES))
                    arr = src.read(1, window=Window(co, ro, NCOLS, NROWS)).astype("float32")
            arr[arr < 0] = np.nan
            return d, arr
        except Exception:  # noqa: BLE001
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    return d, None


def stage_chirps(years: list[int] | None = None) -> None:
    log("== chirps : CHIRPS v3 quotidien, grille nationale ==")
    g = grid()
    rr, cc, cid = g["row"].to_numpy(), g["col"].to_numpy(), g["cell_id"].to_numpy()
    for year in years or range(DATA_START.year, DATA_END.year + 1):
        out = REAL / "rain" / f"chirps_v3_national_daily_{year}.parquet"
        if out.exists():
            log(f"{year} déjà présent")
            continue
        d0, d1 = max(DATA_START, date(year, 1, 1)), min(DATA_END, date(year, 12, 31))
        days = [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]
        t0 = time.time()
        with ThreadPoolExecutor(24) as ex:
            res = list(ex.map(_read_chirps_day, days))
        ok = [(d, a) for d, a in res if a is not None]
        failed = [d.isoformat() for d, a in res if a is None]
        stack = np.stack([a[rr, cc] for _, a in ok]) if ok else np.empty((0, len(cid)), "float32")
        dates = np.array([np.datetime64(d) for d, _ in ok], dtype="datetime64[ns]")
        df = pd.DataFrame(
            {
                "date": np.repeat(dates, len(cid)),
                "cell_id": np.tile(cid, len(ok)),
                "rain_mm": np.round(stack.ravel(), 2),
                "is_provisional": np.repeat(np.array([_chirps_url(d)[1] for d, _ in ok]), len(cid)),
            }
        )
        write_parquet(
            df, out, domain="rain", source_id="chirps", owner="UCSB Climate Hazards Center (CHIRPS v3.0), 0,05°",
            licence="CC BY 4.0", source_url="https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/",
            description=f"Pluie quotidienne CHIRPS v3 {year} sur toutes les cellules 0,05° du Sénégal (final 'rnl' jusqu'au 2026-10-31, puis 'prelim sat').",
            time_col="date", cell_col="cell_id", cell_kind="grid", daily=True, key=["cell_id", "date"],
            checks={"download_failures": failed, "rain_max_mm": float(np.nanmax(stack)) if len(ok) else None,
                    "rain_negative_rows": int((df.rain_mm < 0).sum())},
        )
        log(f"{year} : {len(ok)} jours lus, {len(failed)} échecs, {time.time() - t0:.0f} s")


# ======================================================================================================
# 4. Sols : iSDAsoil (30 m → 0,05°) + contrôle croisé SoilGrids
# ======================================================================================================
ISDA = {
    "sand_content": ("sand_pct", lambda x: x),
    "clay_content": ("clay_pct", lambda x: x),
    "silt_content": ("silt_pct", lambda x: x),
    "ph": ("ph_h2o", lambda x: x / 10),
    "carbon_organic": ("soc_g_kg", lambda x: np.expm1(x / 10)),
    "nitrogen_total": ("n_total_g_kg", lambda x: np.expm1(x / 100)),
    "phosphorous_extractable": ("p_mg_kg", lambda x: np.expm1(x / 10)),
    "potassium_extractable": ("k_mg_kg", lambda x: np.expm1(x / 10)),
    "cation_exchange_capacity": ("cec_cmol_kg", lambda x: np.expm1(x / 10)),
    "bulk_density": ("bulk_density_g_cm3", lambda x: x / 100),
}


def _to_grid(url: str, bands: list[int], overview_level: int | None, nodata_out: float = -9999.0) -> np.ndarray:
    kw = {"overview_level": overview_level} if overview_level is not None else {}
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(url, **kw) as src:
            with WarpedVRT(src, crs=CRS.from_epsg(4326), transform=GRID_TF, width=NCOLS, height=NROWS,
                           resampling=Resampling.average, src_nodata=src.nodata, nodata=nodata_out, dtype="float32") as vrt:
                arr = vrt.read(bands).astype("float32")
    arr[arr == nodata_out] = np.nan
    return arr


def saxton_rawls(sand_pct, clay_pct, soc_g_kg):
    """Capacité au champ (33 kPa) et point de flétrissement (1500 kPa), Saxton & Rawls (2006), en % volumique."""
    s, c = sand_pct / 100, clay_pct / 100
    om = np.clip(soc_g_kg / 10 * 1.724, 0, 8)
    t1500 = -0.024 * s + 0.487 * c + 0.006 * om + 0.005 * s * om - 0.013 * c * om + 0.068 * s * c + 0.031
    wp = t1500 + (0.14 * t1500 - 0.02)
    t33 = -0.251 * s + 0.195 * c + 0.011 * om + 0.006 * s * om - 0.027 * c * om + 0.452 * s * c + 0.299
    fc = t33 + (1.283 * t33**2 - 0.374 * t33 - 0.015)
    return np.round(fc * 100, 2), np.round(wp * 100, 2)


def stage_soil() -> None:
    log("== soil : iSDAsoil national (overview 1,9 km → 0,05°) ==")
    g = grid()
    rr, cc = g["row"].to_numpy(), g["col"].to_numpy()
    layers: dict[str, np.ndarray] = {}
    for layer, (col, fn) in ISDA.items():
        arr = _to_grid(f"https://isdasoil.s3.amazonaws.com/soil_data/{layer}/{layer}.tif", [1, 2], overview_level=5)
        layers[col] = fn(arr)
        log(f"  {layer} lu")
    rows = []
    for bi, depth in enumerate(["0-20cm", "20-50cm"]):
        d = {"cell_id": g["cell_id"].to_numpy(), "lat": g["lat"].to_numpy(), "lon": g["lon"].to_numpy(), "depth_cm": depth}
        for col, arr in layers.items():
            d[col] = np.round(arr[bi][rr, cc], 3)
        rows.append(pd.DataFrame(d))
    soil = pd.concat(rows, ignore_index=True)
    soil["fc_ptf_pct"], soil["wp_ptf_pct"] = saxton_rawls(soil["sand_pct"], soil["clay_pct"], soil["soc_g_kg"])
    soil["awc_ptf_mm_per_m"] = np.round((soil["fc_ptf_pct"] - soil["wp_ptf_pct"]) * 10, 1)
    # contrôle croisé SoilGrids 2.0 (250 m, sable/argile 5-15 cm, g/kg)
    cross: dict[str, Any] = {}
    try:
        for prop in ("sand", "clay"):
            arr = _to_grid(f"https://files.isric.org/soilgrids/latest/data/{prop}/{prop}_5-15cm_mean.vrt", [1], None)[0] / 10
            soil.loc[soil.depth_cm == "0-20cm", f"sg_{prop}_pct_5_15cm"] = np.round(arr[rr, cc], 2)
        s0 = soil[soil.depth_cm == "0-20cm"]
        for prop in ("sand", "clay"):
            a, b = s0[f"{prop}_pct"], s0[f"sg_{prop}_pct_5_15cm"]
            cross[prop] = {"pearson_r": round(float(a.corr(b)), 4), "mean_abs_diff_pct": round(float((a - b).abs().mean()), 2),
                           "n_cells": int(a.notna().mul(b.notna()).sum())}
    except Exception as exc:  # noqa: BLE001
        cross["soilgrids_error"] = repr(exc)[:300]
        log(f"  SoilGrids indisponible : {exc!r}")
    add_cross_check("isdasoil_vs_soilgrids_0_20cm", cross)
    s0 = soil[soil.depth_cm == "0-20cm"]
    chk = {"valid_cells_0_20cm": int(s0.sand_pct.notna().sum()), "cells_total": int(len(s0)),
           "sand_range_pct": [float(s0.sand_pct.min()), float(s0.sand_pct.max())],
           "ph_range": [float(s0.ph_h2o.min()), float(s0.ph_h2o.max())],
           "texture_sum_mean_pct": round(float((s0.sand_pct + s0.clay_pct + s0.silt_pct).mean()), 2),
           "n_total_backtransform": "expm1(x/100) — à vérifier contre la documentation iSDA",
           "log_layers_note": "moyenne calculée dans l'espace transformé (≈ moyenne géométrique)"}
    write_parquet(soil, REAL / "soil_properties" / "isdasoil_national_grid_0p05.parquet", domain="soil_properties",
                  source_id="isdasoil+soilgrids", owner="iSDA / ICRAF / Rothamsted (iSDAsoil 30 m) ; ISRIC (SoilGrids 2.0)",
                  licence="CC BY 4.0", source_url="https://isdasoil.s3.amazonaws.com/soil_data/",
                  description=("Propriétés des sols agrégées à 0,05° sur tout le Sénégal depuis iSDAsoil 30 m (vue pyramide ~1,9 km, moyenne). "
                               "fc/wp/awc sont DÉRIVÉS par pédotransfert Saxton-Rawls (non mesurés)."),
                  cell_col="cell_id", cell_kind="grid", key=["cell_id", "depth_cm"], checks=chk)


# ======================================================================================================
# 5. Occupation du sol ESA WorldCover (masque cultures national)
# ======================================================================================================
WC = {10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built", 60: "bare", 80: "water", 90: "wetland", 95: "mangrove"}


def stage_landcover() -> None:
    log("== landcover : ESA WorldCover 10 m → fractions par cellule ==")
    sub = 10
    counts = {k: np.zeros((NROWS, NCOLS), "float64") for k in WC}
    valid = np.zeros((NROWS, NCOLS), "float64")
    for lat0 in (12, 15):
        for lon0 in (-18, -15, -12):
            c0 = max(0, int(round((lon0 - WEST) / RES)))
            c1 = min(NCOLS, int(round((lon0 + 3 - WEST) / RES)))
            r0 = max(0, int(round((NORTH - (lat0 + 3)) / RES)))
            r1 = min(NROWS, int(round((NORTH - lat0) / RES)))
            if c1 <= c0 or r1 <= r0:
                continue
            tag = f"N{lat0:02d}W{abs(lon0):03d}"
            url = f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tag}_Map.tif"
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(url) as src:
                px = 3 / src.width  # degrés par pixel
                col_off = int(round((WEST + c0 * RES - lon0) / px))
                row_off = int(round(((lat0 + 3) - (NORTH - r0 * RES)) / px))
                win = Window(col_off, row_off, int(round((c1 - c0) * RES / px)), int(round((r1 - r0) * RES / px)))
                arr = src.read(1, window=win, out_shape=((r1 - r0) * sub, (c1 - c0) * sub), resampling=Resampling.nearest)
            blk = arr.reshape(r1 - r0, sub, c1 - c0, sub)
            for k in WC:
                counts[k][r0:r1, c0:c1] += (blk == k).sum(axis=(1, 3))
            valid[r0:r1, c0:c1] += (blk != 0).sum(axis=(1, 3))
            log(f"  tuile {tag} lue")
    g = grid()
    rr, cc = g["row"].to_numpy(), g["col"].to_numpy()
    tot = valid[rr, cc]
    out = {"cell_id": g["cell_id"].to_numpy(), "lat": g["lat"].to_numpy(), "lon": g["lon"].to_numpy(), "n_samples": tot.astype("int32")}
    for k, name in WC.items():
        out[f"share_{name}"] = np.where(tot > 0, np.round(counts[k][rr, cc] / np.maximum(tot, 1), 4), np.nan)
    df = pd.DataFrame(out)
    chk = {"cropland_cells_over_10pct": int((df.share_crop > 0.10).sum()),
           "national_cropland_share_pct": round(100 * float((df.share_crop * df.n_samples).sum() / df.n_samples.sum()), 2),
           "sampling": "nearest 10×10 échantillons par cellule 0,05° (≈ 100 sur 360 000 pixels de 10 m)"}
    write_parquet(df, REAL / "crops_senegal" / "esa_worldcover_national_grid_0p05.parquet", domain="crops_senegal",
                  source_id="worldcover", owner="ESA WorldCover (v200, 2021)", licence="CC BY 4.0",
                  source_url="https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/",
                  description="Fractions d'occupation du sol (cultures, arbres, bâti, eau, zones humides…) par cellule 0,05° sur tout le Sénégal.",
                  cell_col="cell_id", cell_kind="grid", key=["cell_id"], checks=chk)


# ======================================================================================================
# 6. Sentinel-2 : catalogue national + composites NDVI mensuels sur la grille nationale
# ======================================================================================================
STAC = "https://explorer.digitalearth.africa/stac/search"
NDVI_MONTHS = ["2025-02", "2025-05", "2025-08", "2025-11"]


def _https(href: str) -> str:
    return href.replace("s3://deafrica-sentinel-2/", "https://deafrica-sentinel-2.s3.af-south-1.amazonaws.com/")


def stage_s2catalog() -> None:
    log("== s2catalog : catalogue Sentinel-2 L2A national 2024-2026 ==")
    rows: dict[str, dict[str, Any]] = {}
    months = pd.period_range("2024-01", "2026-11", freq="M")
    with httpx.Client(timeout=120) as c:
        for per in months:
            start = per.start_time.strftime("%Y-%m-%dT00:00:00Z")
            end = per.end_time.strftime("%Y-%m-%dT23:59:59Z")
            body: dict[str, Any] = {"collections": ["s2_l2a"], "bbox": [WEST, SOUTH, EAST, NORTH], "datetime": f"{start}/{end}", "limit": 500}
            while True:
                r = c.post(STAC, json=body)
                r.raise_for_status()
                j = r.json()
                for f in j.get("features", []):
                    p, a = f["properties"], f["assets"]
                    if not all(k in a for k in ("B04", "B08", "SCL")):
                        continue
                    tr = p.get("proj:transform", [10, 0, np.nan, 0, -10, np.nan])
                    rows[f["id"]] = {
                        "item_id": f["id"], "datetime_utc": p["datetime"], "date": p["datetime"][:10],
                        "tile": p.get("odc:region_code"), "epsg": int(p.get("proj:epsg", 0)),
                        "cloud_pct": float(p.get("eo:cloud_cover", np.nan)), "data_coverage_pct": float(p.get("sentinel:data_coverage", np.nan)),
                        "x0": tr[2], "y0": tr[5], "b04_href": _https(a["B04"]["href"]), "b08_href": _https(a["B08"]["href"]),
                        "scl_href": _https(a["SCL"]["href"]),
                    }
                nxt = next((lk for lk in j.get("links", []) if lk.get("rel") == "next"), None)
                if not nxt or not j.get("features"):
                    break
                body = {**body, **nxt.get("body", {})}
        log(f"  {per} : cumul {len(rows)} scènes")
    df = pd.DataFrame(list(rows.values())).sort_values(["date", "tile"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    write_parquet(df, REAL / "sentinel2_ndvi" / "deafrica_s2_national_scene_catalog_2024_2026.parquet", domain="sentinel2_ndvi",
                  source_id="deafrica", owner="Digital Earth Africa (Sentinel-2 L2A COG, ESA/Copernicus)", licence="CC BY 4.0",
                  source_url=STAC, time_col="date", key=["item_id"],
                  description="Catalogue de TOUTES les scènes Sentinel-2 L2A touchant le Sénégal (2024-2026), avec liens COG directs B04/B08/SCL.",
                  checks={"tiles": int(df.tile.nunique()), "scenes": int(len(df)), "median_cloud_pct": float(df.cloud_pct.median())})


def _process_scene(row: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    out = 686

    def rd(href: str, rs: Resampling) -> np.ndarray:
        for attempt in range(3):
            try:
                with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3"), rasterio.open(href) as s:
                    return s.read(1, out_shape=(out, out), resampling=rs)
            except Exception:  # noqa: BLE001
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(href)

    try:
        red, nir = rd(row["b04_href"], Resampling.average).astype("float32"), rd(row["b08_href"], Resampling.average).astype("float32")
        scl = rd(row["scl_href"], Resampling.nearest)
    except RuntimeError:
        return None
    step = 10980 * 10 / out
    xs = row["x0"] + (np.arange(out) + 0.5) * step
    ys = row["y0"] - (np.arange(out) + 0.5) * step
    xx, yy = np.meshgrid(xs, ys)
    lon, lat = warp_transform(CRS.from_epsg(int(row["epsg"])), CRS.from_epsg(4326), xx.ravel().tolist(), yy.ravel().tolist())
    lon, lat = np.asarray(lon), np.asarray(lat)
    ci, ri = np.floor((lon - WEST) / RES).astype(int), np.floor((NORTH - lat) / RES).astype(int)
    inside = (ci >= 0) & (ci < NCOLS) & (ri >= 0) & (ri < NROWS)
    flat = (ri * NCOLS + ci)[inside]
    red, nir, scl = red.ravel()[inside], nir.ravel()[inside], scl.ravel()[inside]
    has = (red > 0) & (nir > 0)
    ok = has & np.isin(scl, [4, 5])
    ndvi = np.where(ok, (nir - red) / np.maximum(nir + red, 1), 0.0)
    n = NROWS * NCOLS
    return (np.bincount(flat[ok], weights=ndvi[ok], minlength=n), np.bincount(flat[ok], weights=ndvi[ok] ** 2, minlength=n),
            np.bincount(flat[ok], minlength=n).astype(float), np.bincount(flat[has], minlength=n).astype(float))


def stage_s2ndvi() -> None:
    log("== s2ndvi : composites NDVI mensuels nationaux (meilleure scène par tuile et par mois) ==")
    cat = pd.read_parquet(REAL / "sentinel2_ndvi" / "deafrica_s2_national_scene_catalog_2024_2026.parquet", engine="fastparquet")
    cat["month"] = pd.to_datetime(cat["date"]).dt.strftime("%Y-%m")
    cat["score"] = cat["cloud_pct"] + (100 - cat["data_coverage_pct"].fillna(0))
    g = grid()
    rr, cc = g["row"].to_numpy(), g["col"].to_numpy()
    flat_ids = rr.astype(int) * NCOLS + cc.astype(int)
    frames, per_month_info = [], {}
    for month in NDVI_MONTHS:
        sel = cat[cat.month == month].sort_values("score").groupby("tile", as_index=False).head(1)
        log(f"  {month} : {len(sel)} tuiles")
        t0 = time.time()
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(_process_scene, sel.to_dict("records")))
        good = [r for r in res if r is not None]
        sums = [sum(r[i] for r in good) for i in range(4)]
        n_ok = sums[2][flat_ids]
        n_tot = sums[3][flat_ids]
        mean = np.where(n_ok > 0, sums[0][flat_ids] / np.maximum(n_ok, 1), np.nan)
        var = np.where(n_ok > 0, sums[1][flat_ids] / np.maximum(n_ok, 1) - mean**2, np.nan)
        df = pd.DataFrame({"cell_id": g["cell_id"].to_numpy(), "month": month, "ndvi_mean": np.round(mean, 4),
                           "ndvi_std": np.round(np.sqrt(np.maximum(var, 0)), 4), "n_valid_px": n_ok.astype("int32"),
                           "valid_fraction": np.where(n_tot > 0, np.round(n_ok / np.maximum(n_tot, 1), 3), np.nan)})
        frames.append(df[df.n_valid_px > 0])
        per_month_info[month] = {"tiles_requested": int(len(sel)), "tiles_read": len(good), "cells_with_ndvi": int((n_ok > 0).sum()),
                                 "cells_total": int(len(g)), "seconds": round(time.time() - t0)}
        log(f"  {month} : {per_month_info[month]}")
    out = pd.concat(frames, ignore_index=True)
    write_parquet(out, REAL / "sentinel2_ndvi" / "s2_ndvi_national_grid_monthly_2025.parquet", domain="sentinel2_ndvi",
                  source_id="deafrica", owner="Digital Earth Africa (Sentinel-2 L2A COG)", licence="CC BY 4.0",
                  source_url=STAC, time_col="month", cell_col="cell_id", cell_kind="grid", key=["cell_id", "month"],
                  description=("NDVI moyen par cellule 0,05° sur tout le Sénégal, composites mensuels (meilleure scène par tuile, masque SCL "
                               "végétation/sol nu, lecture des overviews ≈ 160 m). Cellules couvertes seulement quand un pixel valide existe."),
                  checks={"per_month": per_month_info, "ndvi_range": [float(out.ndvi_mean.min()), float(out.ndvi_mean.max())]})


# ======================================================================================================
# 7. Références : Kc depuis le code FAO-56 existant (lecture seule) ; rendements et prix existants nettoyés
# ======================================================================================================
def stage_static() -> None:
    log("== static : coefficients culturaux FAO-56 (depuis agronomy.py, lecture seule) ==")
    spec = importlib.util.spec_from_file_location("agronomy_ro", PLATEFORME / "backend" / "app" / "services" / "agronomy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agronomy_ro"] = mod  # requis par @dataclass
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    rows = []
    for code, prof in mod.CROP_PROFILES.items():
        for day in range(prof.season_days):
            rows.append({"crop_code": code, "crop_name_fr": prof.name_fr, "day_after_planting": day, "season_days": prof.season_days,
                         "growth_stage": mod.growth_stage(prof, day), "kc": round(mod.kc_for_day(prof, day), 4),
                         "kc_ini": prof.kc_ini, "kc_mid": prof.kc_mid, "kc_end": prof.kc_end})
    write_parquet(pd.DataFrame(rows), REAL / "crops_senegal" / "fao56_crop_coefficients_daily.parquet", domain="crops_senegal",
                  source_id="fao56_tables", owner="FAO-56 (Allen et al., 1998) tel qu'encodé dans backend/app/services/agronomy.py",
                  licence="Référence scientifique publiée", source_url="https://www.fao.org/3/x0490e/x0490e00.htm",
                  description="Courbe Kc journalière par culture maraîchère, générée par le code du backend (aucune saisie manuelle). Kc non ajustés au climat local.",
                  key=["crop_code", "day_after_planting"])


_KG = re.compile(r"^\s*(\d+(?:\.\d+)?)?\s*KG\s*$", re.I)


def _kg_divisor(unit: str) -> float:
    u = str(unit).strip().upper()
    if u == "MT":
        return 1000.0
    m = _KG.match(u)
    return float(m.group(1) or 1) if m else float("nan")


def stage_reuse() -> None:
    log("== reuse : rendements FAOSTAT et prix WFP (déjà nationaux) republiés sans champs trompeurs ==")
    y = pd.read_parquet(REAL / "yields" / "faostat_senegal_crops_1961_2024.parquet", engine="fastparquet")
    y = y.drop(columns=[c for c in ("lat", "lon", "region_or_field_id", "campaign_id") if c in y.columns])
    write_parquet(y, REAL / "yields" / "faostat_senegal_crops_1961_2024.parquet", domain="yields", source_id="faostat",
                  owner="FAO — FAOSTAT (QCL, Sénégal)", licence="CC BY 4.0",
                  source_url="https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip",
                  description="Surfaces, rendements, productions nationales 1961-2024. Échelle NATIONALE uniquement (pas de maille spatiale).",
                  key=["crop", "year"], checks={"scale": "national", "note": "pas de rendement régional/parcellaire en open data"})
    mk = pd.read_parquet(REAL / "market_prices" / "wfp_senegal_markets.parquet", engine="fastparquet")
    write_parquet(mk, REAL / "market_prices" / "wfp_senegal_markets.parquet", domain="market_prices", source_id="hdx_wfp_senegal",
                  owner="WFP VAM", licence="CC BY-IGO 3.0", source_url="https://data.humdata.org/dataset/wfp-food-prices-for-senegal",
                  description="Répertoire géolocalisé des marchés suivis par le PAM au Sénégal.", key=["market_id"])
    p = pd.read_parquet(REAL / "market_prices" / "wfp_senegal_food_prices.parquet", engine="fastparquet")
    p["price_fcfa_kg"] = (p["price_fcfa_raw"] / p["unit"].map(_kg_divisor)).round(2)
    write_parquet(p, REAL / "market_prices" / "wfp_senegal_food_prices.parquet", domain="market_prices", source_id="hdx_wfp_senegal",
                  owner="WFP VAM", licence="CC BY-IGO 3.0", source_url="https://data.humdata.org/dataset/wfp-food-prices-for-senegal",
                  description="Prix de marché au Sénégal. price_fcfa_kg n'est calculé que pour les unités de masse (KG, 50/90/100 KG, MT) ; sinon vide.",
                  time_col="date", key=["date", "market_id", "crop", "unit", "price_type"],
                  checks={"units": p["unit"].value_counts().head(12).to_dict(),
                          "rows_with_price_fcfa_kg": int(p["price_fcfa_kg"].notna().sum())})


# ======================================================================================================
# 8. Instantané OctOpus NATIONAL (proxy) — généralisation spatiale : zones de validation exclues de l'entraînement
# ======================================================================================================
def _salt() -> str:
    import os

    s = os.environ.get("AGRIML_PSEUDO_SALT")
    if s and len(s) >= 32:
        return s
    f = CACHE / "pseudo_salt.txt"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(32), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


def stage_octopus() -> None:
    from agriml.octopus.exporter import PrivacyPolicy, SnapshotSpec, export_snapshot

    log("== octopus : instantané national proxy ==")
    g, p = grid(), power_cells()
    met = pd.read_parquet(REAL / "meteo" / "nasa_power_national_daily.parquet", engine="fastparquet")
    et0 = pd.read_parquet(REAL / "et0" / "fao56_et0_national_daily.parquet", engine="fastparquet")[["power_cell_id", "date", "et0_pm_mm"]]
    sm = pd.read_parquet(REAL / "soil_moisture" / "nasa_power_soil_wetness_national_daily.parquet", engine="fastparquet")[
        ["power_cell_id", "date", "gwetroot_ratio"]]
    chunks = []
    for f in sorted((REAL / "rain").glob("chirps_v3_national_daily_*.parquet")):
        c = pd.read_parquet(f, engine="fastparquet", columns=["date", "cell_id", "rain_mm"])
        c = c.merge(g[["cell_id", "power_cell_id"]], on="cell_id")
        chunks.append(c.groupby(["power_cell_id", "date"], as_index=False)["rain_mm"].mean().rename(columns={"rain_mm": "rain_chirps_mm"}))
    chirps = pd.concat(chunks, ignore_index=True)
    df = met.merge(et0, on=["power_cell_id", "date"], how="left").merge(sm, on=["power_cell_id", "date"], how="left").merge(
        chirps, on=["power_cell_id", "date"], how="left")
    soil = pd.read_parquet(REAL / "soil_properties" / "isdasoil_national_grid_0p05.parquet", engine="fastparquet")
    s0 = soil[soil.depth_cm == "0-20cm"].merge(g[["cell_id", "power_cell_id"]], on="cell_id")
    static = s0.groupby("power_cell_id")[["sand_pct", "clay_pct", "soc_g_kg", "ph_h2o", "bulk_density_g_cm3", "fc_ptf_pct", "wp_ptf_pct"]].mean().round(3)
    lc = pd.read_parquet(REAL / "crops_senegal" / "esa_worldcover_national_grid_0p05.parquet", engine="fastparquet").merge(
        g[["cell_id", "power_cell_id"]], on="cell_id")
    static = static.join(lc.groupby("power_cell_id")[["share_crop", "share_tree", "share_bare", "share_built"]].mean().round(4)).reset_index()
    df = df.merge(static, on="power_cell_id", how="left").sort_values(["power_cell_id", "date"]).reset_index(drop=True)
    grp = df.groupby("power_cell_id")
    for k in (3, 7, 14):
        df[f"rain_nasa_sum_{k}d_mm"] = grp["rain_mm"].transform(lambda s, k=k: s.rolling(k, min_periods=k).sum())
        df[f"rain_chirps_sum_{k}d_mm"] = grp["rain_chirps_mm"].transform(lambda s, k=k: s.rolling(k, min_periods=k).sum())
    df["et0_pm_mean_7d_mm"] = grp["et0_pm_mm"].transform(lambda s: s.rolling(7, min_periods=7).mean())
    doy = df["date"].dt.dayofyear
    df["doy_sin"], df["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    df["soil_wetness_root_pct"] = (df["gwetroot_ratio"] * 100).round(3)
    for h in (1, 2, 3):
        df[f"y_plus_{h}d_pct"] = df.groupby("power_cell_id")["soil_wetness_root_pct"].shift(-h)
    # cross-check CHIRPS vs NASA PRECTOTCORR (par maille et par jour)
    ok = df.dropna(subset=["rain_mm", "rain_chirps_mm"])
    add_cross_check("chirps_vs_nasa_precip_daily_power_cells", {
        "n_rows": int(len(ok)), "pearson_r_daily": round(float(ok.rain_mm.corr(ok.rain_chirps_mm)), 4),
        "mean_nasa_mm_day": round(float(ok.rain_mm.mean()), 4), "mean_chirps_mm_day": round(float(ok.rain_chirps_mm.mean()), 4),
        "annual_mean_ratio_chirps_over_nasa": round(float(ok.rain_chirps_mm.sum() / ok.rain_mm.sum()), 4)})

    vz_cells = set(p.dropna(subset=["validation_zone"])["power_cell_id"])
    feat = ["t_min_c", "t_max_c", "t_mean_c", "rh_mean_pct", "wind_2m_ms", "solar_rad_mj_m2", "pressure_hpa", "rain_mm", "rain_chirps_mm",
            "et0_pm_mm", "rain_nasa_sum_3d_mm", "rain_nasa_sum_7d_mm", "rain_nasa_sum_14d_mm", "rain_chirps_sum_3d_mm",
            "rain_chirps_sum_7d_mm", "rain_chirps_sum_14d_mm", "et0_pm_mean_7d_mm", "doy_sin", "doy_cos", "sand_pct", "clay_pct",
            "soc_g_kg", "ph_h2o", "bulk_density_g_cm3", "fc_ptf_pct", "wp_ptf_pct", "share_crop", "share_tree", "share_bare", "share_built"]
    targets = ["soil_wetness_root_pct", "y_plus_1d_pct", "y_plus_2d_pct", "y_plus_3d_pct"]
    use = df[["power_cell_id", "date", *feat, *targets]].copy()
    use["ts"] = use["date"]
    is_vz = use["power_cell_id"].isin(vz_cells)
    train = use[(~is_vz) & (use.date <= "2024-12-31")].dropna(subset=["soil_wetness_root_pct", "rain_nasa_sum_14d_mm"]).drop(columns=["date"])
    test = use[(~is_vz) & (use.date.between("2025-01-01", "2025-12-31"))].drop(columns=["date", *targets])
    hold_t = use[(~is_vz) & (use.date >= "2026-01-01")].drop(columns=["date"])
    hold_s = use[is_vz].drop(columns=["date"])
    hdir = CURATED / "holdout" / "soil_nowcast_proxy_national"
    for name, d in (("holdout_temporal_2026_other_cells", hold_t), ("holdout_spatial_validation_zones_all_dates", hold_s)):
        write_parquet(d, hdir / f"{name}.parquet", domain="holdout", source_id="nasa_power+chirps+isdasoil+worldcover",
                      owner="SmartAgri92 (holdout souverain)", licence="Dérivé de sources ouvertes",
                      source_url="local://ml/data/real", description=f"Holdout {name} — jamais exporté vers OctOpus.",
                      time_col="ts", key=["power_cell_id", "ts"])
    os_dir = CURATED
    version = "20261114-natl01"
    snap = os_dir / "octopus" / "soil_nowcast_proxy_national" / f"v={version}"
    if snap.exists():
        shutil.rmtree(snap)
    import os

    env = {**os.environ, "AGRIML_PSEUDO_SALT": _salt(), "AGRIML_PSEUDO_SALT_ID": "local-dev-2026-11"}
    spec = SnapshotSpec(dataset="soil_nowcast_proxy_national", version=version, policy=PrivacyPolicy(pseudonymize=("power_cell_id",)),
                        source={"pipeline": "build_national_data_lake.py", "mission": MISSION, "synthetic": False,
                                "target_nature": "PROXY modélisé (NASA GEOS), pas une mesure de capteur",
                                "spatial_holdout_zones": sorted(VALIDATION_ZONES)},
                        target="soil_wetness_root_pct", groups="power_cell_id", time_column="ts",
                        holdout_window=("2026-01-01", "2026-11-10"))
    res = export_snapshot(train, os_dir, spec, test=test, env=env)
    info = {"snapshot": str(res.folder.relative_to(ML_ROOT)).replace("\\", "/"), "manifest_sha256": res.manifest_sha256,
            "train_rows": len(train), "test_rows": len(test), "holdout_temporal_rows": len(hold_t), "holdout_spatial_rows": len(hold_s),
            "train_cells": int(train.power_cell_id.nunique()), "validation_power_cells": sorted(vz_cells), "n_features": len(feat)}
    (MANIFESTS / "octopus_snapshot_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"snapshot : {info}")


# ======================================================================================================
# 9. Audit global
# ======================================================================================================
def stage_audit() -> None:
    log("== audit : rapport national ==")
    mans = []
    for mp in sorted(REAL.rglob("*.parquet.manifest.json")):
        if any(part.startswith("_") for part in mp.relative_to(REAL).parts):
            continue
        mans.append(json.loads(mp.read_text(encoding="utf-8")))
    hold = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((CURATED / "holdout").rglob("*.parquet.manifest.json"))]
    cross = json.loads((MANIFESTS / "cross_checks.json").read_text(encoding="utf-8")) if (MANIFESTS / "cross_checks.json").exists() else {}
    snap = json.loads((MANIFESTS / "octopus_snapshot_info.json").read_text(encoding="utf-8")) if (MANIFESTS / "octopus_snapshot_info.json").exists() else {}
    info = json.loads((GEO_DIR / "grid_info.json").read_text(encoding="utf-8"))
    by_domain: dict[str, dict[str, Any]] = {}
    for m in mans:
        d = by_domain.setdefault(m["domain"], {"files": 0, "rows": 0, "size_bytes": 0})
        d["files"] += 1
        d["rows"] += m["rows"]
        d["size_bytes"] += m["size_bytes"]
    rep = {
        "mission": MISSION, "scope": "national", "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "constraints": {"models_trained": 0, "synthetic_data_used": False},
        "grid": info,
        "totals": {"files": len(mans), "rows": sum(m["rows"] for m in mans), "size_mb": round(sum(m["size_bytes"] for m in mans) / 2**20, 2)},
        "by_domain": by_domain, "cross_checks": cross, "octopus_snapshot": snap,
        "holdouts": [{k: h[k] for k in ("relative_path", "rows", "sha256")} for h in hold],
        "datasets": [{k: m.get(k) for k in ("relative_path", "domain", "source_id", "licence", "commercial_use", "rows", "size_bytes",
                                            "sha256", "quality", "temporal_coverage", "geographic_coverage")} for m in mans],
    }
    (MANIFESTS / "lake_audit_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"audit : {rep['totals']}")


STAGES = {"legacy": stage_legacy, "grid": stage_grid, "nasa": stage_nasa, "chirps": stage_chirps, "soil": stage_soil,
          "landcover": stage_landcover, "s2catalog": stage_s2catalog, "s2ndvi": stage_s2ndvi, "static": stage_static,
          "reuse": stage_reuse, "octopus": stage_octopus, "audit": stage_audit}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default=",".join(STAGES))
    args = ap.parse_args()
    for s in args.stages.split(","):
        STAGES[s.strip()]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
