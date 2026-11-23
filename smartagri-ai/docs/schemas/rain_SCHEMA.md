# `ml/data/real/rain/` — Précipitations Réelles (Satellite & Réanalyse)

- **Sources Niveau A (immédiates)** :
  - `chirps` (CHIRPS v3) : `https://data.chc.ucsb.edu/products/CHIRPS-v3.0/` (COG / GeoTIFF / NetCDF, 0,05° ≈ 5,5 km, CC BY 4.0 ; remplace CHIRPS v2 qui s'arrête fin déc. 2026).
  - `tamsat` (TAMSAT v3.1) : NetCDF / CSV sur l'Afrique (0,0375° ≈ 4 km, quotidien depuis 1983, usage commercial autorisé).
  - `nasa_power` : paramètre `PRECTOTCORR` (mm/j corrigé, quotidien depuis 1981).
- **Sources Niveau B (avec compte Earthdata / CDS)** :
  - `imerg` (NASA GPM IMERG, 0,1°, 30 min, latence Early ~4 h).
  - `era5_land` (`total_precipitation`, horaire).
- **Sources Niveau C (partenariat)** :
  - `anacim_stations` (pluviomètres au sol), `agrhymet_presass` (prévisions saisonnières PRESASS).
- **Colonnes cibles normalisées (`Parquet`)** :
  `site_id`, `lat`, `lon`, `date`, `rain_mm`, `rain_eff_mm` ($0,8 \times \text{rain\_mm}$), `source_id`, `is_provisional`.
