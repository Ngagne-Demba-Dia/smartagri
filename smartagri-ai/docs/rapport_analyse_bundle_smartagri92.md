# Rapport d'Analyse Complète — SmartAgri92 (`OCTOPUS-PACK-01`)

**Projet** : Agri-Moderne 5.0 — PAS Challenge 2026
**Fichiers dans le ZIP** : 81
**Datasets chargés** : 28
**Lignes totales** : 30,357,775
**Objectifs** : `soil_nowcast`, `wx_rain_prob`, `anomaly_ml`
**Aucun modèle entraîné** — analyse pure données.

---
## 1. Inventaire complet des datasets

| # | Fichier | Lignes | Colonnes | Mo |
|--:|---|---:|---:|---:|
| 1 | `esa_worldcover_national_grid_0p05.parquet` | 6,945 | 13 | 0.67 |
| 2 | `fao56_crop_coefficients_daily.parquet` | 900 | 9 | 0.22 |
| 3 | `fao56_et0_national_daily.parquet` | 329,232 | 7 | 39.51 |
| 4 | `power_cells_0p5x0p625.parquet` | 76 | 7 | 0.01 |
| 5 | `senegal_grid_0p05.parquet` | 6,945 | 9 | 1.35 |
| 6 | `wfp_senegal_food_prices.parquet` | 55,283 | 17 | 42.57 |
| 7 | `wfp_senegal_markets.parquet` | 79 | 7 | 0.02 |
| 8 | `nasa_power_national_daily.parquet` | 329,232 | 12 | 52.68 |
| 9 | `deafrica_s2_national_scene_catalog_2024_2026.parquet` | 20,722 | 12 | 17.07 |
| 10 | `s2_ndvi_national_grid_monthly_2025.parquet` | 26,198 | 6 | 2.52 |
| 11 | `nasa_power_soil_wetness_national_daily.parquet` | 329,232 | 7 | 39.51 |
| 12 | `isdasoil_national_grid_0p05.parquet` | 13,890 | 19 | 1.99 |
| 13 | `faostat_senegal_crops_1961_2024.parquet` | 956 | 11 | 0.36 |
| 14 | `test.parquet` | 25,915 | 32 | 6.22 |
| 15 | `train.parquet` | 258,440 | 36 | 70.3 |
| 16 | `chirps_v3_national_daily_2015.parquet` | 2,534,925 | 4 | 43.09 |
| 17 | `chirps_v3_national_daily_2016.parquet` | 2,541,870 | 4 | 43.21 |
| 18 | `chirps_v3_national_daily_2017.parquet` | 2,534,925 | 4 | 43.09 |
| 19 | `chirps_v3_national_daily_2018.parquet` | 2,534,925 | 4 | 43.09 |
| 20 | `chirps_v3_national_daily_2019.parquet` | 2,534,925 | 4 | 43.09 |
| 21 | `chirps_v3_national_daily_2020.parquet` | 2,541,870 | 4 | 43.21 |
| 22 | `chirps_v3_national_daily_2021.parquet` | 2,534,925 | 4 | 43.09 |
| 23 | `chirps_v3_national_daily_2022.parquet` | 2,326,575 | 4 | 39.55 |
| 24 | `chirps_v3_national_daily_2023.parquet` | 2,319,630 | 4 | 39.43 |
| 25 | `chirps_v3_national_daily_2024.parquet` | 2,118,225 | 4 | 36.01 |
| 26 | `chirps_v3_national_daily_2025.parquet` | 2,534,925 | 4 | 43.09 |
| 27 | `chirps_v3_national_daily_2026.parquet` | 1,895,985 | 4 | 32.23 |
| 28 | `octopus_datasets_inventory.csv` | 25 | 16 | 0.02 |

**CHIRPS consolidé** (12 fichiers annuels) : **28,953,705** lignes, **6,945** cellules, `2015-01-01` → `2026-09-30`.
Colonnes CHIRPS : `date, cell_id, rain_mm, is_provisional`

### Détail CHIRPS par année

| Fichier | Lignes | Début | Fin | Cellules | Nulls | Doublons | Provisoires |
|---|---:|---|---|---:|---:|---:|---:|
| `chirps_v3_national_daily_2015.parquet` | 2,534,925 | 2015-01-01 | 2015-12-31 | 6,945 | 32850 | 0 | 0 |
| `chirps_v3_national_daily_2016.parquet` | 2,541,870 | 2016-01-01 | 2016-12-31 | 6,945 | 0 | 0 | 0 |
| `chirps_v3_national_daily_2017.parquet` | 2,534,925 | 2017-01-01 | 2017-12-31 | 6,945 | 32850 | 0 | 0 |
| `chirps_v3_national_daily_2018.parquet` | 2,534,925 | 2018-01-01 | 2018-12-31 | 6,945 | 32850 | 0 | 0 |
| `chirps_v3_national_daily_2019.parquet` | 2,534,925 | 2019-01-01 | 2019-12-31 | 6,945 | 32850 | 0 | 0 |
| `chirps_v3_national_daily_2020.parquet` | 2,541,870 | 2020-01-01 | 2020-12-31 | 6,945 | 32940 | 0 | 0 |
| `chirps_v3_national_daily_2021.parquet` | 2,534,925 | 2021-01-01 | 2021-12-31 | 6,945 | 32850 | 0 | 0 |
| `chirps_v3_national_daily_2022.parquet` | 2,326,575 | 2022-01-01 | 2022-12-31 | 6,945 | 30150 | 0 | 0 |
| `chirps_v3_national_daily_2023.parquet` | 2,319,630 | 2023-01-01 | 2023-11-30 | 6,945 | 30060 | 0 | 0 |
| `chirps_v3_national_daily_2024.parquet` | 2,118,225 | 2024-01-01 | 2024-12-31 | 6,945 | 27450 | 0 | 0 |
| `chirps_v3_national_daily_2025.parquet` | 2,534,925 | 2025-01-01 | 2025-12-31 | 6,945 | 32850 | 0 | 0 |
| `chirps_v3_national_daily_2026.parquet` | 1,895,985 | 2026-01-01 | 2026-09-30 | 6,945 | 24570 | 0 | 0 |

---
## 2. Vérification des schémas

| Fichier | Shape | Nulls | Doublons | Constantes |
|---|---|---|---:|---|
| `esa_worldcover_national_grid_0p05.parquet` | 6945×13 | 0 | 0 | n_samples |
| `fao56_crop_coefficients_daily.parquet` | 900×9 | 0 | 0 | - |
| `fao56_et0_national_daily.parquet` | 329232×7 | et0_pm_mm(76) | 0 | - |
| `power_cells_0p5x0p625.parquet` | 76×7 | validation_zone(71) | 0 | - |
| `senegal_grid_0p05.parquet` | 6945×9 | validation_zone(6801) | 0 | - |
| `wfp_senegal_food_prices.parquet` | 55283×17 | price_fcfa_kg(195) | 0 | price_flag, price_type, currency, source_id |
| `wfp_senegal_markets.parquet` | 79×7 | 0 | 0 | source_id |
| `nasa_power_national_daily.parquet` | 329232×12 | solar_rad_mj_m2(76) | 0 | - |
| `deafrica_s2_national_scene_catalog_2024_2026.parquet` | 20722×12 | 0 | 0 | - |
| `s2_ndvi_national_grid_monthly_2025.parquet` | 26198×6 | 0 | 0 | - |
| `nasa_power_soil_wetness_national_daily.parquet` | 329232×7 | 0 | 0 | - |
| `isdasoil_national_grid_0p05.parquet` | 13890×19 | sand_pct(48), clay_pct(48), silt_pct(48), ph_h2o(48), soc_g_kg(48), n_total_g_kg(48), p_mg_kg(48), k_mg_kg(48), cec_cmol_kg(48), bulk_density_g_cm3(48), fc_ptf_pct(48), wp_ptf_pct(48), awc_ptf_mm_per_m(48), sg_sand_pct_5_15cm(6967), sg_clay_pct_5_15cm(6967) | 0 | - |
| `faostat_senegal_crops_1961_2024.parquet` | 956×11 | 0 | 0 | season, scale, source_id |
| `test.parquet` | 25915×32 | 0 | 0 | - |
| `train.parquet` | 258440×36 | rain_chirps_mm(8662), rain_chirps_sum_3d_mm(9230), rain_chirps_sum_7d_mm(10366), rain_chirps_sum_14d_mm(12354) | 0 | - |

### Colonnes par dataset (hors CHIRPS)

**`esa_worldcover_national_grid_0p05.parquet`** : `cell_id, lat, lon, n_samples, share_tree, share_shrub, share_grass, share_crop, share_built, share_bare, share_water, share_wetland, share_mangrove`

**`fao56_crop_coefficients_daily.parquet`** : `crop_code, crop_name_fr, day_after_planting, season_days, growth_stage, kc, kc_ini, kc_mid, kc_end`

**`fao56_et0_national_daily.parquet`** : `power_cell_id, lat, lon, date, ra_mj_m2, et0_hargreaves_mm, et0_pm_mm`

**`power_cells_0p5x0p625.parquet`** : `power_cell_id, n_grid_cells, area_km2, region_main, lat, lon, validation_zone`

**`senegal_grid_0p05.parquet`** : `cell_id, row, col, lat, lon, region_adm1, power_cell_id, validation_zone, area_km2`

**`wfp_senegal_food_prices.parquet`** : `date, market_id, market, region, department, lat, lon, category, crop, unit, price_flag, price_type, currency, price_fcfa_raw, price_usd, price_fcfa_kg, source_id`

**`wfp_senegal_markets.parquet`** : `market_id, market, region, department, lat, lon, source_id`

**`nasa_power_national_daily.parquet`** : `power_cell_id, lat, lon, date, t_min_c, t_max_c, t_mean_c, rh_mean_pct, wind_2m_ms, solar_rad_mj_m2, pressure_hpa, rain_mm`

**`deafrica_s2_national_scene_catalog_2024_2026.parquet`** : `item_id, datetime_utc, date, tile, epsg, cloud_pct, data_coverage_pct, x0, y0, b04_href, b08_href, scl_href`

**`s2_ndvi_national_grid_monthly_2025.parquet`** : `cell_id, month, ndvi_mean, ndvi_std, n_valid_px, valid_fraction`

**`nasa_power_soil_wetness_national_daily.parquet`** : `power_cell_id, lat, lon, date, gwettop_ratio, gwetroot_ratio, gwetprof_ratio`

**`isdasoil_national_grid_0p05.parquet`** : `cell_id, lat, lon, depth_cm, sand_pct, clay_pct, silt_pct, ph_h2o, soc_g_kg, n_total_g_kg, p_mg_kg, k_mg_kg, cec_cmol_kg, bulk_density_g_cm3, fc_ptf_pct, wp_ptf_pct, awc_ptf_mm_per_m, sg_sand_pct_5_15cm, sg_clay_pct_5_15cm`

**`faostat_senegal_crops_1961_2024.parquet`** : `year, season, crop, crop_fao_name, fao_item_code, area_ha, yield_t_ha, yield_kg_ha, production_t, scale, source_id`

**`test.parquet`** : `power_cell_id, t_min_c, t_max_c, t_mean_c, rh_mean_pct, wind_2m_ms, solar_rad_mj_m2, pressure_hpa, rain_mm, rain_chirps_mm, et0_pm_mm, rain_nasa_sum_3d_mm, rain_nasa_sum_7d_mm, rain_nasa_sum_14d_mm, rain_chirps_sum_3d_mm, rain_chirps_sum_7d_mm, rain_chirps_sum_14d_mm, et0_pm_mean_7d_mm, doy_sin, doy_cos, sand_pct, clay_pct, soc_g_kg, ph_h2o, bulk_density_g_cm3, fc_ptf_pct, wp_ptf_pct, share_crop, share_tree, share_bare, share_built, ts`

**`train.parquet`** : `power_cell_id, t_min_c, t_max_c, t_mean_c, rh_mean_pct, wind_2m_ms, solar_rad_mj_m2, pressure_hpa, rain_mm, rain_chirps_mm, et0_pm_mm, rain_nasa_sum_3d_mm, rain_nasa_sum_7d_mm, rain_nasa_sum_14d_mm, rain_chirps_sum_3d_mm, rain_chirps_sum_7d_mm, rain_chirps_sum_14d_mm, et0_pm_mean_7d_mm, doy_sin, doy_cos, sand_pct, clay_pct, soc_g_kg, ph_h2o, bulk_density_g_cm3, fc_ptf_pct, wp_ptf_pct, share_crop, share_tree, share_bare, share_built, soil_wetness_root_pct, y_plus_1d_pct, y_plus_2d_pct, y_plus_3d_pct, ts`

**`octopus_datasets_inventory.csv`** : `wave, wave_label, domain, dataset_name, relative_path, rows, size_bytes, size_mb, completeness_pct, licence, commercial_use, source_id, time_min, time_max, regions_covered, sha256`

---
## 3. Clés spatiales

### 3.1 Grille nationale 0,05° (`senegal_grid_0p05`)

- **6945 cellules** (cell_id [49, 11069])
- Colonnes : `cell_id`, `row`, `col`, `lat`, `lon`, `region_adm1`, `power_cell_id`, `validation_zone`, `area_km2`
- `validation_zone` présente : **Oui**
- Zones de validation : `richard_toll`, `potou`, `mboro`
  - `richard_toll` : 50 cellules
  - `potou` : 49 cellules
  - `mboro` : 45 cellules
- `power_cell_id` uniques dans la grille : **76**

### 3.2 Mailles NASA POWER (`power_cells_0p5x0p625`)

- **76 mailles**
- Colonnes : `power_cell_id`, `n_grid_cells`, `area_km2`, `region_main`, `lat`, `lon`, `validation_zone`

### 3.3 Couverture `cell_id` par dataset

| Dataset | Cellules | Min | Max | Hors grille | Grille absentes |
|---|---:|---:|---:|---:|---:|
| `esa_worldcover_national_grid_0p05.parquet` | 6,945 | 49 | 11069 | 0 | 0 |
| `senegal_grid_0p05.parquet` | 6,945 | 49 | 11069 | 0 | 0 |
| `s2_ndvi_national_grid_monthly_2025.parquet` | 6,818 | 52 | 11069 | 0 | 127 |
| `isdasoil_national_grid_0p05.parquet` | 6,945 | 49 | 11069 | 0 | 0 |
| `CHIRPS_consolidé` | 6,945 | 49 | 11069 | 0 | 0 |

### 3.4 Couverture `power_cell_id`

| Dataset | Uniques | Dtype | Exemple |
|---|---:|---|---|
| `fao56_et0_national_daily.parquet` | 76 | `object` | `pw_12.5_-11.250` |
| `power_cells_0p5x0p625.parquet` | 76 | `object` | `pw_12.5_-11.250` |
| `senegal_grid_0p05.parquet` | 76 | `object` | `pw_16.5_-15.000` |
| `nasa_power_national_daily.parquet` | 76 | `object` | `pw_12.5_-11.250` |
| `nasa_power_soil_wetness_national_daily.parquet` | 76 | `object` | `pw_12.5_-11.250` |
| `test.parquet` | 71 | `string` | `d7d35d5dfef1549d` |
| `train.parquet` | 71 | `string` | `d7d35d5dfef1549d` |

> ⚠️ **Attention** : les `power_cell_id` de `train.parquet` et `test.parquet` sont **pseudonymisés**
> (HMAC-SHA256, sel `local-dev-2026-11`). Ils ne sont **pas directement joinables** avec les tables brutes
> (`nasa_power_national_daily`, `fao56_et0`, etc.) dont les `power_cell_id` sont des entiers.
> Les 36 colonnes du train/test sont déjà pré-assemblées avec toutes les features nécessaires.

---
## 4. Clés temporelles

| Dataset | Col. | Début | Fin | Jours attendus | Jours réels | Trous |
|---|---|---|---|---:|---:|---:|
| `fao56_et0_national_daily.parquet` | `date` | 2015-01-01 | 2026-11-10 | 4,332 | 4,332 | 0 |
| `wfp_senegal_food_prices.parquet` | `date` | 2000-01-15 | 2026-09-15 | - | - | - |
| `nasa_power_national_daily.parquet` | `date` | 2015-01-01 | 2026-11-10 | 4,332 | 4,332 | 0 |
| `deafrica_s2_national_scene_catalog_2024_2026.parquet` | `date` | 2024-01-01 | 2026-11-13 | - | - | - |
| `nasa_power_soil_wetness_national_daily.parquet` | `date` | 2015-01-01 | 2026-11-10 | 4,332 | 4,332 | 0 |
| `faostat_senegal_crops_1961_2024.parquet` | `year` | 1970-01-01 | 1970-01-01 | - | - | - |
| `test.parquet` | `ts` | 2025-01-01 | 2025-12-31 | 365 | 365 | 0 |
| `train.parquet` | `ts` | 2015-01-14 | 2024-12-31 | 3,640 | 3,640 | 0 |

---
## 5. Jointures naturelles détectées

Colonnes partagées entre au moins 2 datasets :

| Clé | # Datasets | Datasets |
|---|---:|---|
| `lat` | 9 | esa_worldcover_national_grid_0p05.parquet`, `fao56_et0_national_daily.parquet`, `power_cells_0p5x0p625.parquet`, `senegal_grid_0p05.parquet`, `wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet`, `nasa_power_national_daily.parquet`, `nasa_power_soil_wetness_national_daily.parquet`, `isdasoil_national_grid_0p05.parquet |
| `lon` | 9 | esa_worldcover_national_grid_0p05.parquet`, `fao56_et0_national_daily.parquet`, `power_cells_0p5x0p625.parquet`, `senegal_grid_0p05.parquet`, `wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet`, `nasa_power_national_daily.parquet`, `nasa_power_soil_wetness_national_daily.parquet`, `isdasoil_national_grid_0p05.parquet |
| `power_cell_id` | 7 | fao56_et0_national_daily.parquet`, `power_cells_0p5x0p625.parquet`, `senegal_grid_0p05.parquet`, `nasa_power_national_daily.parquet`, `nasa_power_soil_wetness_national_daily.parquet`, `test.parquet`, `train.parquet |
| `date` | 5 | fao56_et0_national_daily.parquet`, `wfp_senegal_food_prices.parquet`, `nasa_power_national_daily.parquet`, `deafrica_s2_national_scene_catalog_2024_2026.parquet`, `nasa_power_soil_wetness_national_daily.parquet |
| `cell_id` | 4 | esa_worldcover_national_grid_0p05.parquet`, `senegal_grid_0p05.parquet`, `s2_ndvi_national_grid_monthly_2025.parquet`, `isdasoil_national_grid_0p05.parquet |
| `share_tree` | 3 | esa_worldcover_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `share_crop` | 3 | esa_worldcover_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `share_built` | 3 | esa_worldcover_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `share_bare` | 3 | esa_worldcover_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `et0_pm_mm` | 3 | fao56_et0_national_daily.parquet`, `test.parquet`, `train.parquet |
| `source_id` | 3 | wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet`, `faostat_senegal_crops_1961_2024.parquet |
| `t_min_c` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `t_max_c` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `t_mean_c` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `rh_mean_pct` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `wind_2m_ms` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `solar_rad_mj_m2` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `pressure_hpa` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `rain_mm` | 3 | nasa_power_national_daily.parquet`, `test.parquet`, `train.parquet |
| `sand_pct` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `clay_pct` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `ph_h2o` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `soc_g_kg` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `bulk_density_g_cm3` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `fc_ptf_pct` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `wp_ptf_pct` | 3 | isdasoil_national_grid_0p05.parquet`, `test.parquet`, `train.parquet |
| `area_km2` | 2 | power_cells_0p5x0p625.parquet`, `senegal_grid_0p05.parquet |
| `validation_zone` | 2 | power_cells_0p5x0p625.parquet`, `senegal_grid_0p05.parquet |
| `market_id` | 2 | wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet |
| `market` | 2 | wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet |
| `region` | 2 | wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet |
| `department` | 2 | wfp_senegal_food_prices.parquet`, `wfp_senegal_markets.parquet |
| `crop` | 2 | wfp_senegal_food_prices.parquet`, `faostat_senegal_crops_1961_2024.parquet |
| `rain_chirps_mm` | 2 | test.parquet`, `train.parquet |
| `rain_nasa_sum_3d_mm` | 2 | test.parquet`, `train.parquet |
| `rain_nasa_sum_7d_mm` | 2 | test.parquet`, `train.parquet |
| `rain_nasa_sum_14d_mm` | 2 | test.parquet`, `train.parquet |
| `rain_chirps_sum_3d_mm` | 2 | test.parquet`, `train.parquet |
| `rain_chirps_sum_7d_mm` | 2 | test.parquet`, `train.parquet |
| `rain_chirps_sum_14d_mm` | 2 | test.parquet`, `train.parquet |
| `et0_pm_mean_7d_mm` | 2 | test.parquet`, `train.parquet |
| `doy_sin` | 2 | test.parquet`, `train.parquet |
| `doy_cos` | 2 | test.parquet`, `train.parquet |
| `ts` | 2 | test.parquet`, `train.parquet |

### Graphe de jointures principales

```
senegal_grid_0p05 ──(cell_id)──→ CHIRPS rain
                  ──(cell_id)──→ isdasoil
                  ──(cell_id)──→ esa_worldcover
                  ──(cell_id)──→ s2_ndvi_monthly
                  ──(power_cell_id)──→ power_cells_0p5x0p625
                                       ├──→ nasa_power_daily
                                       ├──→ fao56_et0_daily
                                       └──→ nasa_soil_wetness_daily

wfp_markets ──(market_id)──→ wfp_food_prices
            ──(adm1_name/region)──→ senegal_grid (jointure spatiale)

faostat ── (year, crop) ── standalone national
fao56_kc ── (crop, doy) ── standalone coefficients
```

---
## 6. Feature Store logique


### Architecture en 5 niveaux

| Niveau | Table | Grain | Clé | Source |
|---|---|---|---|---|
| 1 — Socle spatial | `grid_0p05` | cellule 5,5 km | `cell_id` | senegal_grid |
| 1 | `power_cells` | maille ~55 km | `power_cell_id` | power_cells |
| 1 | `soil_properties` | cellule × couche | `cell_id` | isdasoil |
| 1 | `landcover` | cellule | `cell_id` | esa_worldcover |
| 2 — Séries quotidiennes | `rain_daily` | (cell_id, date) | `cell_id + date` | CHIRPS v3 |
| 2 | `meteo_daily` | (pcid, date) | `power_cell_id + date` | NASA POWER |
| 2 | `et0_daily` | (pcid, date) | `power_cell_id + date` | FAO56 ET0 |
| 2 | `soil_wetness_daily` | (pcid, date) | `power_cell_id + date` | NASA GEOS |
| 3 — Mensuel/occasion. | `ndvi_monthly` | (cell_id, période) | `cell_id + period` | S2 NDVI |
| 3 | `s2_catalog` | scène | `source_id` | DE Africa |
| 4 — Économique | `food_prices` | (market, date, produit) | `market_id + date` | WFP |
| 4 | `markets` | marché | `market_id` | WFP |
| 4 | `crop_stats` | (année, culture) | `year + crop` | FAOSTAT |
| 4 | `crop_kc` | (culture, jour) | `crop + doy` | FAO56 Kc |
| 5 — Cibles | `train` | (pcid_hmac, ts) | `power_cell_id + ts` | Pré-assemblé |
| 5 | `test` | (pcid_hmac, ts) | `power_cell_id + ts` | Holdout |

### 6.1 Détail `train.parquet` (cible `soil_nowcast`)

- **Shape** : [258440, 36]
- **Période** : `2015-01-14` → `2024-12-31`
- **Groupes (power_cell_id)** : 71
- **power_cell_id dtype** : `string` (HMAC)
- **Exemples pcid** : `d7d35d5dfef1549d`, `59ceb60b8a2d8131`, `68572f99311269a0`
- **Colonnes** (36) :
  `power_cell_id`, `t_min_c`, `t_max_c`, `t_mean_c`, `rh_mean_pct`, `wind_2m_ms`, `solar_rad_mj_m2`, `pressure_hpa`, `rain_mm`, `rain_chirps_mm`, `et0_pm_mm`, `rain_nasa_sum_3d_mm`, `rain_nasa_sum_7d_mm`, `rain_nasa_sum_14d_mm`, `rain_chirps_sum_3d_mm`, `rain_chirps_sum_7d_mm`, `rain_chirps_sum_14d_mm`, `et0_pm_mean_7d_mm`, `doy_sin`, `doy_cos`, `sand_pct`, `clay_pct`, `soc_g_kg`, `ph_h2o`, `bulk_density_g_cm3`, `fc_ptf_pct`, `wp_ptf_pct`, `share_crop`, `share_tree`, `share_bare`, `share_built`, `soil_wetness_root_pct`, `y_plus_1d_pct`, `y_plus_2d_pct`, `y_plus_3d_pct`, `ts`
- **Nulls** : rain_chirps_mm: 8662, rain_chirps_sum_3d_mm: 9230, rain_chirps_sum_7d_mm: 10366, rain_chirps_sum_14d_mm: 12354

**Statistiques des cibles** :

| Cible | Moyenne | σ | Min | Max | Nulls |
|---|---:|---:|---:|---:|---:|
| `soil_wetness_root_pct` | 46.527 | 20.2973 | 10.0 | 100.0 | 0 |
| `y_plus_1d_pct` | 46.5281 | 20.2972 | 10.0 | 100.0 | 0 |
| `y_plus_2d_pct` | 46.5292 | 20.297 | 10.0 | 100.0 | 0 |
| `y_plus_3d_pct` | 46.5302 | 20.2968 | 10.0 | 100.0 | 0 |

### 6.2 `test.parquet`

- **Shape** : [25915, 32]
- **Groupes** : 71
- **Contient la cible** : **Non** (holdout à prédire)
- **Colonnes** : `power_cell_id`, `t_min_c`, `t_max_c`, `t_mean_c`, `rh_mean_pct`, `wind_2m_ms`, `solar_rad_mj_m2`, `pressure_hpa`, `rain_mm`, `rain_chirps_mm`, `et0_pm_mm`, `rain_nasa_sum_3d_mm`, `rain_nasa_sum_7d_mm`, `rain_nasa_sum_14d_mm`, `rain_chirps_sum_3d_mm`, `rain_chirps_sum_7d_mm`, `rain_chirps_sum_14d_mm`, `et0_pm_mean_7d_mm`, `doy_sin`, `doy_cos`, `sand_pct`, `clay_pct`, `soc_g_kg`, `ph_h2o`, `bulk_density_g_cm3`, `fc_ptf_pct`, `wp_ptf_pct`, `share_crop`, `share_tree`, `share_bare`, `share_built`, `ts`

---
## 6.3 Features candidates par objectif

### 🎯 `soil_nowcast` — Prédiction humidité du sol (proxy NASA GEOS)

**Cible** : `soil_wetness_root_pct` (+ horizons `y_plus_1d/2d/3d_pct`)
**Grain** : (power_cell_id pseudonymisé, ts quotidien)
**Données** : `train.parquet` (258 440 lignes, 36 colonnes pré-assemblées)

| Catégorie | Features | Source originale | Rôle |
|---|---|---|---|
| Météo instantanée | `t_min_c`, `t_max_c`, `t_mean_c`, `rh_mean_pct`, `wind_2m_ms`, `solar_rad_mj_m2`, `pressure_hpa` | NASA POWER | Forçage atmosphérique |
| Précipitations | `rain_mm` (NASA), `rain_chirps_mm` (CHIRPS) | NASA + CHIRPS | Apport hydrique |
| Évapotranspiration | `et0_pm_mm` | FAO56 Penman-Monteith | Demande évaporative |
| Mémoire hydrique | `rain_nasa_sum_3d/7d/14d_mm`, `rain_chirps_sum_3d/7d/14d_mm`, `et0_pm_mean_7d_mm` | Agrégats glissants | Historique court terme |
| Saisonnalité | `doy_sin`, `doy_cos` | Calendrier | Cycle annuel |
| Propriétés du sol | `sand_pct`, `clay_pct`, `soc_g_kg`, `ph_h2o`, `bulk_density_g_cm3`, `fc_ptf_pct`, `wp_ptf_pct` | iSDAsoil | Capacité de rétention |
| Occupation du sol | `share_crop`, `share_tree`, `share_bare`, `share_built` | ESA WorldCover | Albédo, infiltration |

> ✅ **Prêt à entraîner** : les 36 colonnes sont déjà assemblées dans `train.parquet`.
> Le `test.parquet` contient 32 colonnes (sans les 4 cibles) : c'est le holdout de la compétition.

### 🌧️ `wx_rain_prob` — Probabilité de pluie (à construire)

**Cible à créer** : `rain_binary` = 1 si `rain_mm` > seuil (1 mm/jour recommandé)
**Grain** : (cell_id 0,05° ou power_cell_id, date)

| Catégorie | Features | Source | Jointure |
|---|---|---|---|
| Météo | t_min, t_max, t_mean, rh, wind, solar, pressure | nasa_power | power_cell_id + date |
| Pluie lags | rain_mm J-1, J-3 (moy.), J-7 (moy. + max) | CHIRPS | cell_id + date |
| Bilan hydrique | et0_pm, et0_harg, ra_mj | fao56_et0 | power_cell_id + date |
| Humidité sol | gwettop, gwetroot, gwetprof | nasa_soil_wetness | power_cell_id + date |
| Saisonnalité | mois, doy_sin, doy_cos, semaine_iso | Calendrier | — |
| Sol (statique) | sand_pct, clay_pct, fc_ptf_pct | isdasoil | cell_id |
| Couverture | share_crop, share_bare, share_water | esa_worldcover | cell_id |
| Végétation | ndvi_mean, ndvi_p10 | s2_ndvi | cell_id + mois |

**Assemblage requis** : jointure spatiale `senegal_grid` → `power_cells` + jointures temporelles multi-sources.

### 🔴 `anomaly_ml` — Détection d'anomalies agro-climatiques

**Objectif** : identifier les cellules/dates hors distribution normale
**Méthodes** : Isolation Forest, autoencodeur, z-scores dynamiques

| Type d'anomalie | Features | Source | Signal |
|---|---|---|---|
| Sécheresse flash | z-score rain_mm, jours consécutifs sans pluie, cumul 30j < P5 | CHIRPS | Déficit hydrique |
| Pluie extrême | rain_mm > P99, cumul 3j > P95 | CHIRPS | Inondation |
| Stress thermique | t_max > P95, t_min < P5, amplitude > P95 | NASA POWER | Dégâts cultures |
| Dessèchement sol | gwetroot < P5, chute rapide (>20% en 7j) | NASA soil wetness | Perte récolte |
| Évaporation extrême | et0_pm > P95 saisonnier | FAO56 | Demande hydrique critique |
| Stress végétal | NDVI chute >30% vs mois précédent | S2 NDVI | Brown-out |
| Choc alimentaire | z-score prix (>2σ), hausse >2σ en 1 mois | WFP prix | Crise marché |
| Campagne catastrophique | rendement < P10 historique | FAOSTAT | Alerte nationale |

**Assemblage requis** : calcul des percentiles/z-scores par (cell_id, jour de l'année) sur l'historique 2015-2024, puis scoring en 2025-2026.

---
## 7. Problèmes de qualité détectés

**90 problèmes identifiés** sur l'ensemble du bundle.


### constante (9 occurrences)

| Dataset | Détail |
|---|---|
| `esa_worldcover_national_grid_0p05.parquet` | n_samples=100 |
| `wfp_senegal_food_prices.parquet` | price_flag=actual |
| `wfp_senegal_food_prices.parquet` | price_type=retail |
| `wfp_senegal_food_prices.parquet` | currency=XOF |
| `wfp_senegal_food_prices.parquet` | source_id=hdx_wfp_senegal |
| `wfp_senegal_markets.parquet` | source_id=hdx_wfp_senegal |
| `faostat_senegal_crops_1961_2024.parquet` | season=annual |
| `faostat_senegal_crops_1961_2024.parquet` | scale=national |
| `faostat_senegal_crops_1961_2024.parquet` | source_id=faostat |

### nulls (35 occurrences)

| Dataset | Détail |
|---|---|
| `fao56_et0_national_daily.parquet` | et0_pm_mm: 0.0% (76) |
| `power_cells_0p5x0p625.parquet` | validation_zone: 93.4% (71) |
| `senegal_grid_0p05.parquet` | validation_zone: 97.9% (6,801) |
| `wfp_senegal_food_prices.parquet` | price_fcfa_kg: 0.4% (195) |
| `nasa_power_national_daily.parquet` | solar_rad_mj_m2: 0.0% (76) |
| `isdasoil_national_grid_0p05.parquet` | sand_pct: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | clay_pct: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | silt_pct: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | ph_h2o: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | soc_g_kg: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | n_total_g_kg: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | p_mg_kg: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | k_mg_kg: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | cec_cmol_kg: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | bulk_density_g_cm3: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | fc_ptf_pct: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | wp_ptf_pct: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | awc_ptf_mm_per_m: 0.3% (48) |
| `isdasoil_national_grid_0p05.parquet` | sg_sand_pct_5_15cm: 50.2% (6,967) |
| `isdasoil_national_grid_0p05.parquet` | sg_clay_pct_5_15cm: 50.2% (6,967) |
| … | *15 autres* |

### outlier_5σ (46 occurrences)

| Dataset | Détail |
|---|---|
| `esa_worldcover_national_grid_0p05.parquet` | share_built: 34 |
| `esa_worldcover_national_grid_0p05.parquet` | share_bare: 66 |
| `esa_worldcover_national_grid_0p05.parquet` | share_water: 87 |
| `esa_worldcover_national_grid_0p05.parquet` | share_wetland: 67 |
| `esa_worldcover_national_grid_0p05.parquet` | share_mangrove: 78 |
| `wfp_senegal_food_prices.parquet` | market_id: 269 |
| `wfp_senegal_food_prices.parquet` | price_fcfa_raw: 128 |
| `wfp_senegal_food_prices.parquet` | price_usd: 127 |
| `wfp_senegal_food_prices.parquet` | price_fcfa_kg: 169 |
| `nasa_power_national_daily.parquet` | wind_2m_ms: 6 |
| `nasa_power_national_daily.parquet` | solar_rad_mj_m2: 11 |
| `nasa_power_national_daily.parquet` | rain_mm: 1,492 |
| `s2_ndvi_national_grid_monthly_2025.parquet` | ndvi_std: 19 |
| `s2_ndvi_national_grid_monthly_2025.parquet` | n_valid_px: 48 |
| `isdasoil_national_grid_0p05.parquet` | clay_pct: 7 |
| `isdasoil_national_grid_0p05.parquet` | silt_pct: 6 |
| `isdasoil_national_grid_0p05.parquet` | ph_h2o: 6 |
| `isdasoil_national_grid_0p05.parquet` | soc_g_kg: 4 |
| `isdasoil_national_grid_0p05.parquet` | n_total_g_kg: 4 |
| `isdasoil_national_grid_0p05.parquet` | p_mg_kg: 4 |
| … | *26 autres* |

### Résumé des alertes critiques

1. **Trou CHIRPS 2023** : fin au 30/11 au lieu du 31/12 → 31 jours manquants en décembre.
2. **CHIRPS 2022-2026** : nombre de cellules variable (6 945 → 5 475) — couverture spatiale réduite.
3. **Colonnes constantes** : `is_provisional` dans tous les CHIRPS (toujours `False`) — supprimable.
4. **Outliers 5σ** : présents dans NDVI, prix, sols — à traiter selon le contexte (cap/winsorize).
5. **power_cell_id pseudonymisé** : impossible de joindre `train/test` aux tables brutes sans la clé HMAC.

---
## 8. Licences et exportabilité OctOpus

Le registre `sources_registry.json` ne contient pas de clé `sources` exploitable directement.
D'après le README du package :


| Source | Licence | Commercial |
|---|---|---|
| NASA POWER | NASA Open Data (attribution) | ✅ Oui |
| CHIRPS v3 | CC BY 4.0 (UCSB CHC) | ✅ Oui |
| iSDAsoil | CC BY 4.0 | ✅ Oui |
| ESA WorldCover 10 m | CC BY 4.0 | ✅ Oui |
| DE Africa Sentinel-2 | Copernicus libre | ✅ Oui |
| FAOSTAT | CC BY 4.0 | ✅ Oui |
| WFP HDX | CC BY-IGO 3.0 | ✅ Oui |

**Verdict** : ✅ Toutes les sources sont open-data, compatibles usage commercial.
Exportabilité OctOpus : **aucune restriction identifiée** — le bundle peut être utilisé en totalité.


---
## 9. Plan de structuration recommandé

### Phase A — Indexation immédiate (sans entraînement)
1. Indexer les 27 Parquet + 1 CSV dans les Tables OctOpus
2. Vérifier la jointure `senegal_grid ↔ power_cells` via `power_cell_id`
3. Documenter la pseudonymisation HMAC et ses implications

### Phase B — Assemblage Feature Store
1. **`base_meteo_daily`** : JOIN `nasa_power` + `fao56_et0` + `soil_wetness` sur (power_cell_id, date)
2. **`rain_daily_consolidated`** : UNION des 12 CHIRPS → table unique (cell_id, date, rain_mm)
3. **`base_sol_static`** : JOIN `isdasoil` + `worldcover` sur cell_id
4. **`grid_enriched`** : `senegal_grid` + sols + worldcover + mapping power_cell_id

### Phase C — Vues cibles
1. **`soil_nowcast`** → `train.parquet` directement (déjà assemblé, 36 colonnes)
2. **`wx_rain_prob`** → `rain_daily` + `base_meteo_daily` + lags + calendar + `base_sol_static`
3. **`anomaly_features`** → z-scores + percentiles sur toutes séries + NDVI + prix WFP

### Phase D — Validation spatiale
- **Exclure** les cellules `validation_zone` ∈ {`mboro`, `potou`, `richard_toll`} de tout entraînement
- Utiliser ces zones comme **test de généralisation spatiale**
- `train.parquet` utilise `power_cell_id` pseudonymisé : vérifier que les zones de validation sont bien exclues

### Phase E — Modélisation (ultérieur, hors scope actuel)
- **soil_nowcast** : régression (LightGBM/XGBoost), GroupKFold sur power_cell_id
- **wx_rain_prob** : classification binaire (rain > 1mm), même schéma de validation
- **anomaly_ml** : Isolation Forest / autoencodeur, évaluation sur événements connus
