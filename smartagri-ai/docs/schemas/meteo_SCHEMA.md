# `ml/data/real/meteo/` — Séries Météorologiques Réelles (Horaire & Quotidien)

- **Sources Niveau A (immédiates)** :
  - `nasa_power` : API REST Agroclimatologie (`https://power.larc.nasa.gov/api/temporal/daily/point`), sans clé API, licence NASA ouverte.
  - `noaa_gfs` : GRIB2 sur AWS Open Data (`s3://noaa-gfs-bdp-pds/`), domaine public.
  - `ecmwf_open_data` : GRIB2 IFS/AIFS (`https://data.ecmwf.int/forecasts/`), CC BY 4.0.
- **Sources Niveau B (avec préparation / compte / abonnement)** :
  - `era5_land` / `agera5` : Copernicus CDS (`cdsapi`), 0,1° (~9 km), licence Copernicus libre.
  - `open_meteo` : API REST JSON (souscription Standard requise pour usage commercial ou instance auto-hébergée AGPLv3).
- **Sources Niveau C (partenariat)** :
  - `anacim_stations` (Convention ANACIM), `tahmo` (Accord TAHMO).
- **Colonnes cibles normalisées (`Parquet`)** :
  `site_id`, `lat`, `lon`, `ts` (ou `date`), `issue_time` (si prévision *as-of*), `t_min_c`, `t_max_c`, `t_mean_c`, `rh_mean_pct`, `wind_2m_ms`, `solar_rad_mj_m2`, `pressure_hpa`.
