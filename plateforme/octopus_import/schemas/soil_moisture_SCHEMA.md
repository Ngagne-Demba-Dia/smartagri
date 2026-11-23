# `ml/data/real/soil_moisture/` — Humidité du Sol Réelle (Satellite, Réanalyse & Sondes)

- **Sources Niveau A (immédiates, maille régionale)** :
  - `nasa_power` : `GWETTOP` (humidité relative de surface 0–5 cm, `[0, 1]`), `GWETROOT` (zone racinaire 0–100 cm, `[0, 1]`), `GWETPROF` (profil complet), quotidien depuis 1981 via REST JSON/CSV sans clé.
- **Sources Niveau B (préparation CDS / SAR / Kits pilotes)** :
  - `era5_land` : `swvl1` (0–7 cm), `swvl2` (7–28 cm), `swvl3` (28–100 cm) en $\text{m}^3/\text{m}^3$ au pas horaire (0,1°).
  - `sentinel1` : rétrodiffusion radar SAR bande C (`VV`, `VH` à 10 m, tous les 6–12 j, insensible aux nuages d'hivernage).
  - `kit_telemetry` : humidité capacitive horaire réelle à $-20\text{ cm}$ (`soil_moisture_pct`) après étalonnage gravimétrique `sm_calibration`.
- **Colonnes cibles normalisées (`Parquet`)** :
  `site_id`, `device_id`, `ts`, `sm_surface_pct`, `sm_root_pct`, `vwc_m3_m3`, `calibrated`, `source_id`.
