"""Génère des jeux de données SYNTHÉTIQUES (aucune donnée réelle) pour tester la chaîne de bout en bout.

Sorties (dans --out, par défaut data/synthetic/) :
- yield/      : rendement par parcelle × campagne (train 2014-2023, test 2024-2025, étiquettes test cachées) ;
- disease/    : risque de foyer de maladie à 14 jours, suivi hebdomadaire (test = nouvelles parcelles) ;
- telemetry/  : télémétrie horaire au format telemetry.v1 (6 boîtiers × 45 jours) ;
- weather_mos/: prévisions numériques brutes + observations (4 stations × 90 jours, échéances 6-72 h) ;
- images/     : 3 classes (sain / suspect / malade) × N images 96×96 de feuilles dessinées.

Les relations sont plausibles (température, eau, NPK, chaleur, humidité → maladie) mais inventées :
les scores obtenus ne disent rien des performances sur données réelles.

Usage : python scripts/make_synthetic.py [--out data/synthetic] [--seed 42] [--only yield,disease]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = {
    # nom : (lat, lon, cultures, pluie de saison moyenne mm, tmax moyenne °C, irrigué)
    "Niayes": (14.85, -17.10, ["tomate", "oignon", "chou", "pomme_de_terre"], 350, 30.0, True),
    "Vallee_du_fleuve": (16.30, -15.00, ["riz", "oignon", "tomate", "mais"], 250, 35.0, True),
    "Bassin_arachidier": (14.20, -16.00, ["arachide", "mil", "sorgho", "mais"], 600, 34.0, False),
    "Casamance": (12.80, -15.60, ["riz", "mais", "arachide", "mil"], 1100, 32.0, False),
    "Senegal_oriental": (13.50, -13.00, ["mais", "sorgho", "mil", "arachide"], 800, 35.5, False),
}
POTENTIAL_T_HA = {"tomate": 25.0, "oignon": 30.0, "chou": 30.0, "pomme_de_terre": 25.0, "riz": 6.0,
                  "mais": 4.0, "mil": 1.2, "sorgho": 1.5, "arachide": 1.5}
CYCLE_DAYS = {"tomate": 120, "oignon": 130, "chou": 100, "pomme_de_terre": 110, "riz": 130, "mais": 110,
              "mil": 95, "sorgho": 110, "arachide": 100}
KC = {"tomate": 1.15, "oignon": 1.05, "chou": 1.05, "pomme_de_terre": 1.15, "riz": 1.2, "mais": 1.2,
      "mil": 1.0, "sorgho": 1.0, "arachide": 1.15}
COOL_SEASON = {"oignon", "chou", "pomme_de_terre"}
SOILS = ["dior", "deck", "deck_dior", "argileux", "limoneux"]
YEARS = range(2014, 2026)
TEST_YEARS = (2024, 2025)


# --------------------------------------------------------------------------- rendement


def _fields(rng: np.random.Generator, n_fields: int) -> pd.DataFrame:
    names = list(REGIONS)
    region = rng.choice(names, size=n_fields, p=[0.25, 0.2, 0.25, 0.15, 0.15])
    rows = []
    for i, r in enumerate(region):
        lat, lon, *_ = REGIONS[r]
        rows.append({"field_id": f"F{i:04d}", "region": r, "lat": lat + rng.normal(0, 0.25),
                     "lon": lon + rng.normal(0, 0.25), "soil_type": rng.choice(SOILS),
                     "field_effect": float(rng.lognormal(0, 0.15)), "soil_ph": rng.normal(6.3, 0.6),
                     "organic_matter_pct": rng.gamma(2.0, 0.5), "n_base": rng.gamma(4.0, 10.0),
                     "p_base": rng.gamma(3.0, 6.0), "k_base": rng.gamma(4.0, 30.0)})
    return pd.DataFrame(rows)


def _season_weather(rng, region: str, crop: str, year_anom: dict) -> dict:
    _, _, _, rain_mean, tmax_mean, irrigated = REGIONS[region]
    cool = crop in COOL_SEASON or (irrigated and crop in ("tomate",))
    sowing = int((rng.normal(320, 15) if cool else rng.normal(185, 10))) % 365
    days = int(CYCLE_DAYS[crop] + rng.integers(-10, 11))
    tmax = tmax_mean - (4.0 if cool else 0.0) + year_anom["t"] + rng.normal(0, 0.8)
    tmin = tmax - rng.normal(11 if cool else 9, 1.0)
    rain = rain_mean * year_anom["rain"] * rng.lognormal(0, 0.15) * (0.08 if cool else 1.0)
    irrigation = rng.uniform(350, 650) if (irrigated or crop == "riz" and region != "Casamance") else 0.0
    return {"sowing_doy": sowing, "season_days": days, "mid_season_doy": (sowing + days // 2) % 365 + 1,
            "tmin_mean": tmin, "tmax_mean": tmax, "rh_mean": float(np.clip(rng.normal(45 if cool else 70, 8), 15, 98)),
            "rain_mm": max(rain, 0.0), "irrigation_mm": irrigation,
            "heat_days_35": int(rng.poisson(max(0.0, (tmax - 33.0) * days / 12.0)))}


def _yield(row: dict, crop: str, npk: tuple[float, float, float], year: int, rng) -> float:
    tmean = (row["tmin_mean"] + row["tmax_mean"]) / 2
    t_opt = 21.0 if crop in COOL_SEASON else 27.0
    temp_f = np.exp(-(((tmean - t_opt) / 7.0) ** 2))
    etc = 5.5 * KC[crop] * row["season_days"]
    water_f = min(1.0, (0.8 * row["rain_mm"] + row["irrigation_mm"]) / etc) ** 0.7
    n, p, k = npk
    npk_f = (1 - 0.35 * np.exp(-n / 30)) * (1 - 0.15 * np.exp(-p / 15)) * (1 - 0.1 * np.exp(-k / 80))
    heat_f = np.exp(-0.015 * row["heat_days_35"])
    trend = 1 + 0.012 * (year - 2014)
    return float(POTENTIAL_T_HA[crop] * row["field_effect"] * temp_f * water_f * npk_f * heat_f * trend
                 * rng.lognormal(0, 0.12))


def _ndvi_series(rng, vigour: float, rainy: bool, prefix: str, scale: float) -> dict:
    t = np.linspace(0, 1, 8)
    curve = 0.15 + scale * vigour * np.exp(-((t - 0.55) / 0.25) ** 2) + rng.normal(0, 0.03, 8)
    cloud = rng.random(8) < (0.3 if rainy else 0.08)
    return {f"{prefix}{i + 1}": (np.nan if cloud[i] else float(curve[i])) for i in range(8)}


def make_yield(rng: np.random.Generator, out: Path, n_fields: int = 300) -> None:
    fields = _fields(rng, n_fields)
    anomalies = {(r, y): {"t": rng.normal(0, 0.7), "rain": rng.lognormal(0, 0.25)} for r in REGIONS for y in YEARS}
    rows = []
    for f in fields.to_dict("records"):
        crops = REGIONS[f["region"]][2]
        for year in YEARS:
            crop = str(rng.choice(crops))
            w = _season_weather(rng, f["region"], crop, anomalies[(f["region"], year)])
            npk = (f["n_base"] * rng.lognormal(0, 0.2), f["p_base"] * rng.lognormal(0, 0.2),
                   f["k_base"] * rng.lognormal(0, 0.2))
            y = _yield({**w, "field_effect": f["field_effect"]}, crop, npk, year, rng)
            vigour = min(1.5, y / POTENTIAL_T_HA[crop])
            rainy = w["rain_mm"] > 300
            rows.append({"field_id": f["field_id"], "year": year, "region": f["region"], "crop": crop,
                         "lat": f["lat"], "lon": f["lon"], "soil_type": f["soil_type"], "soil_ph": f["soil_ph"],
                         "organic_matter_pct": f["organic_matter_pct"], "n_mgkg": npk[0], "p_mgkg": npk[1],
                         "k_mgkg": npk[2], **w, **_ndvi_series(rng, vigour, rainy, "ndvi_", 0.6),
                         **_ndvi_series(rng, vigour, rainy, "evi_", 0.45), "yield_t_ha": y})
    df = pd.DataFrame(rows)
    for col in ("n_mgkg", "p_mgkg", "k_mgkg", "soil_ph", "organic_matter_pct"):
        df.loc[rng.random(len(df)) < 0.03, col] = np.nan
    df.insert(0, "row_id", [f"Y{i:06d}" for i in range(len(df))])
    _split_and_write(df, df["year"].isin(TEST_YEARS), "yield_t_ha", out / "yield", "yield", 0.0)


def _split_and_write(df, is_test, target: str, folder: Path, stem: str, sample_value) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    train, test = df[~is_test].reset_index(drop=True), df[is_test].reset_index(drop=True)
    train.to_csv(folder / f"{stem}_train.csv", index=False)
    test.drop(columns=target).to_csv(folder / f"{stem}_test.csv", index=False)
    test[["row_id", target]].to_csv(folder / f"{stem}_test_labels.csv", index=False)
    pd.DataFrame({"row_id": test["row_id"], target: sample_value}).to_csv(
        folder / f"{stem}_sample_submission.csv", index=False)
    print(f"{stem}: train {len(train)} lignes, test {len(test)} lignes -> {folder}")


# --------------------------------------------------------------------------- maladie


def _disease_field(rng, field_id: str, region: str, crop: str, resistant: int, weeks: int) -> list[dict]:
    lat, lon, *_ = REGIONS[region]
    rows, latent = [], 0.0
    for season, start in ((2024, "2024-06-03"), (2025, "2025-06-02")):
        latent, obs_prev = 0.0, 0
        dates = pd.date_range(start, periods=weeks, freq="7D")
        for w, d in enumerate(dates, start=1):
            temp = 27 + 3 * np.sin(w / 4) + rng.normal(0, 1.5)
            hum = float(np.clip(70 + 15 * np.sin(w / 3 + 1) + rng.normal(0, 8), 30, 100))
            rain = float(rng.gamma(1.2, 12) if hum > 75 else rng.gamma(0.5, 4))
            wet = float(np.clip((hum - 60) / 2 + rng.normal(0, 3), 0, 24))
            fungicide = int(obs_prev >= 1 and rng.random() < 0.6)
            favourable = (hum > 82) * np.exp(-((temp - 24) / 5) ** 2) + wet / 48
            latent = 0.6 * latent + favourable * (0.5 if resistant else 1.0) - 0.4 * fungicide + rng.normal(0, 0.1)
            latent = max(latent, 0.0)
            obs = int(np.clip(np.round(latent * 2 + rng.normal(0, 0.4)), 0, 3))
            rows.append({"field_id": field_id, "field_season": f"{field_id}_{season}", "region": region,
                         "crop": crop, "season": season, "week": w, "date": d.date().isoformat(), "lat": lat,
                         "lon": lon, "air_temp_c": temp, "air_humidity_pct": hum, "rain_mm": rain,
                         "leaf_wetness_h": wet, "soil_moisture_pct": float(np.clip(25 + rain / 3 + rng.normal(0, 4), 5, 80)),
                         "fungicide_applied": fungicide, "variety_resistant": resistant, "disease_obs": obs,
                         "_latent": latent})
            obs_prev = obs
    return rows


def make_disease(rng: np.random.Generator, out: Path, n_fields: int = 200, weeks: int = 20) -> None:
    crops = {"Niayes": ["tomate", "oignon", "chou"], "Vallee_du_fleuve": ["tomate", "oignon", "riz"],
             "Bassin_arachidier": ["mil", "arachide"], "Casamance": ["riz", "mais"],
             "Senegal_oriental": ["mais", "sorgho"]}
    rows = []
    for i in range(n_fields):
        region = str(rng.choice(list(REGIONS)))
        rows += _disease_field(rng, f"D{i:04d}", region, str(rng.choice(crops[region])), int(rng.random() < 0.3), weeks)
    df = pd.DataFrame(rows)
    event = (df["_latent"] > df["_latent"].quantile(0.90)).astype(int)
    nxt1, nxt2 = event.groupby(df["field_season"]).shift(-1), event.groupby(df["field_season"]).shift(-2)
    df["outbreak_next_14d"] = ((nxt1 == 1) | (nxt2 == 1)).astype(float).where(nxt2.notna())
    df = df[df["outbreak_next_14d"].notna()].drop(columns="_latent").reset_index(drop=True)
    df["outbreak_next_14d"] = df["outbreak_next_14d"].astype(int)
    df.insert(0, "row_id", [f"R{i:06d}" for i in range(len(df))])
    test_fields = set(df["field_id"].drop_duplicates().sample(frac=0.2, random_state=int(rng.integers(1e6))))
    print(f"disease: prévalence {df['outbreak_next_14d'].mean():.3f}")
    _split_and_write(df, df["field_id"].isin(test_fields), "outbreak_next_14d", out / "disease", "disease", 0.5)


# --------------------------------------------------------------------------- télémétrie et MOS


def _device_series(rng, device: str, hours: int, start_pct: int, stop_pct: int) -> pd.DataFrame:
    ts = pd.date_range("2026-07-01", periods=hours, freq="h", tz="UTC")
    hour = ts.hour.to_numpy()
    temp = 28 + 6 * np.sin((hour - 9) / 24 * 2 * np.pi) + rng.normal(0, 0.8, hours)
    hum = np.clip(75 - 15 * np.sin((hour - 9) / 24 * 2 * np.pi) + rng.normal(0, 4, hours), 20, 100)
    rain = (rng.random(hours) < 0.01) * rng.gamma(2, 6, hours)
    soil, pump = np.empty(hours), np.zeros(hours, dtype=int)
    level, on = rng.uniform(40, 60), False
    for t in range(hours):
        et = max(0.0, 0.08 + 0.04 * (temp[t] - 25)) * (1 if 7 <= hour[t] <= 19 else 0.3)
        on = level < start_pct or (on and level < stop_pct)
        level = min(100.0, max(0.0, level - et + (3.0 if on else 0.0) + 0.5 * rain[t]))
        soil[t], pump[t] = level, int(on)
    ok = rng.random(hours) > 0.01
    n, p, k = rng.normal(40, 3), rng.normal(25, 2), rng.normal(120, 8)
    return pd.DataFrame({
        "device_id": device, "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "soil_moisture_pct": np.where(ok, np.round(soil + rng.normal(0, 0.7, hours), 1), np.nan),
        "air_temp_c": np.round(temp, 1), "air_humidity_pct": np.round(hum, 1),
        "pressure_hpa": np.round(1010 + rng.normal(0, 2, hours), 1),
        "n_mgkg": np.round(n + rng.normal(0, 1, hours)), "p_mgkg": np.round(p + rng.normal(0, 1, hours)),
        "k_mgkg": np.round(k + rng.normal(0, 2, hours)), "pump_on": pump.astype(bool), "pump_fault": False,
        "soil_sensor_ok": ok, "bme_ok": True, "npk_ok": True, "alert_fertilizer": False, "alert_plant": False,
        "threshold_start_pct": start_pct, "threshold_stop_pct": stop_pct, "rain_mm": np.round(rain, 1),
    })


def make_telemetry(rng: np.random.Generator, out: Path, n_devices: int = 6, days: int = 45) -> None:
    frames = [_device_series(rng, f"esp32-{i:03d}", days * 24, 30 + 2 * (i % 3), 55 + 2 * (i % 3))
              for i in range(n_devices)]
    folder = out / "telemetry"
    folder.mkdir(parents=True, exist_ok=True)
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(folder / "telemetry.csv", index=False)
    print(f"telemetry: {len(df)} lignes -> {folder}")


def make_weather_mos(rng: np.random.Generator, out: Path, n_stations: int = 4, days: int = 90) -> None:
    rows = []
    for s in range(n_stations):
        bias = rng.normal(0, 1.5)
        for d in pd.date_range("2026-03-01", periods=days, freq="D", tz="UTC"):
            for lead in range(6, 73, 6):
                valid = d + pd.Timedelta(hours=lead)
                truth = 29 + 5 * np.sin((valid.hour - 9) / 24 * 2 * np.pi) + 2 * np.sin(valid.dayofyear / 20)
                diurnal_bias = 1.2 * np.cos((valid.hour - 15) / 24 * 2 * np.pi)
                nwp = truth + bias + diurnal_bias + 0.03 * lead + rng.normal(0, 0.5 + lead / 60)
                rows.append({"station_id": f"ST{s}", "issue_time": d.isoformat(), "valid_time": valid.isoformat(),
                             "lead_h": lead, "nwp_temp_c": nwp, "nwp_rh_pct": float(np.clip(rng.normal(65, 10), 10, 100)),
                             "nwp_wind_ms": float(abs(rng.normal(4, 1.5))), "obs_temp_c": truth + rng.normal(0, 0.3)})
    folder = out / "weather_mos"
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(folder / "weather_mos.csv", index=False)
    print(f"weather_mos: {len(rows)} lignes -> {folder}")


# --------------------------------------------------------------------------- images


def _leaf_image(rng, label: str, size: int = 96):
    from PIL import Image, ImageDraw, ImageFilter

    bg = tuple(int(c) for c in rng.integers([90, 60, 30], [140, 100, 60]))
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)
    green = tuple(int(c) for c in rng.integers([30, 110, 20], [70, 170, 60]))
    m = int(size * rng.uniform(0.08, 0.16))
    draw.ellipse([m, m + 8, size - m, size - m - 8], fill=green)
    draw.line([size // 2, m + 8, size // 2, size - m - 8], fill=(150, 200, 120), width=2)
    n_spots = {"sain": 0, "suspect": int(rng.integers(2, 5)), "malade": int(rng.integers(10, 22))}[label]
    for _ in range(n_spots):
        cx, cy = rng.integers(m + 6, size - m - 6, 2)
        r = int(rng.integers(2, 5 if label == "suspect" else 8))
        colour = (210, 200, 60) if label == "suspect" else tuple(int(c) for c in rng.integers([90, 50, 10], [140, 80, 30]))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)
    img = img.rotate(float(rng.uniform(0, 360)), fillcolor=bg)
    return img.filter(ImageFilter.GaussianBlur(radius=float(rng.uniform(0, 0.8))))


def make_images(rng: np.random.Generator, out: Path, per_class: int = 30, per_plant: int = 3) -> None:
    """Images + metadata.csv (plant_id, field_id) : plusieurs vues d'une même plante restent dans le même pli."""
    folder = out / "images"
    rows = []
    for label in ("sain", "suspect", "malade"):
        (folder / label).mkdir(parents=True, exist_ok=True)
        for i in range(per_class):
            _leaf_image(rng, label).save(folder / label / f"{label}_{i:03d}.png")
            plant = f"{label[:2]}{i // per_plant:03d}"
            rows.append({"path": f"{label}/{label}_{i:03d}.png", "label": label, "plant_id": plant,
                         "field_id": f"F{(i // per_plant) % 4}"})
    pd.DataFrame(rows).to_csv(folder / "metadata.csv", index=False)
    print(f"images: {3 * per_class} images 96x96 + metadata.csv -> {folder}")


GENERATORS = {"yield": make_yield, "disease": make_disease, "telemetry": make_telemetry,
              "weather_mos": make_weather_mos, "images": make_images}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "synthetic"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--only", default=",".join(GENERATORS), help="Liste séparée par des virgules.")
    args = parser.parse_args()
    out = Path(args.out)
    order = list(GENERATORS)
    for name in (n.strip() for n in args.only.split(",")):
        # graine liée au générateur (et non à sa position dans --only) : --only reproduit la génération complète
        GENERATORS[name](np.random.default_rng(args.seed + order.index(name)), out)


if __name__ == "__main__":
    main()
