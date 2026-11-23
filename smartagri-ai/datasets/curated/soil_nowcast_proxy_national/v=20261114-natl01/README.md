# Jeu `soil_nowcast_proxy_national` — v=20261114-natl01

Confidentiel - réservé aux partenaires de travail.

- Cible : `soil_wetness_root_pct` ; groupes : `power_cell_id` ; temps : `ts`
- Lignes (entraînement) : 258440
- Pseudonymisation : HMAC-SHA256, sel `local-dev-2026-11`
- Colonnes supprimées : aucune
- Holdout envoyé : non

| Colonne | Type |
|---|---|
| power_cell_id | string |
| t_min_c | float |
| t_max_c | float |
| t_mean_c | float |
| rh_mean_pct | float |
| wind_2m_ms | float |
| solar_rad_mj_m2 | float |
| pressure_hpa | float |
| rain_mm | float |
| rain_chirps_mm | float |
| et0_pm_mm | float |
| rain_nasa_sum_3d_mm | float |
| rain_nasa_sum_7d_mm | float |
| rain_nasa_sum_14d_mm | float |
| rain_chirps_sum_3d_mm | float |
| rain_chirps_sum_7d_mm | float |
| rain_chirps_sum_14d_mm | float |
| et0_pm_mean_7d_mm | float |
| doy_sin | float |
| doy_cos | float |
| sand_pct | float |
| clay_pct | float |
| soc_g_kg | float |
| ph_h2o | float |
| bulk_density_g_cm3 | float |
| fc_ptf_pct | float |
| wp_ptf_pct | float |
| share_crop | float |
| share_tree | float |
| share_bare | float |
| share_built | float |
| soil_wetness_root_pct | float |
| y_plus_1d_pct | float |
| y_plus_2d_pct | float |
| y_plus_3d_pct | float |
| ts | timestamp |
