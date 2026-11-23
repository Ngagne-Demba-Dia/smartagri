# 45 — Data Lake Réel National SmartAgri92 Prêt pour OctOpus (`IA-REAL-03`)

**Date** : 16 novembre 2026  
**Mission** : `IA-REAL-03` — Refonte à l'échelle nationale du Sénégal (toutes régions, généralisation à tout futur kit)  
**Statut** : `READY_FOR_OCTOPUS` — *Confidentiel — réservé aux partenaires de travail.*  
**Script reproductible** : [`plateforme/ml/scripts/build_national_data_lake.py`](../ml/scripts/build_national_data_lake.py)  
**Rapport d'audit machine** : [`plateforme/ml/data/real/manifests/lake_audit_report.json`](../ml/data/real/manifests/lake_audit_report.json)  
**Contrôles croisés** : [`plateforme/ml/data/real/manifests/cross_checks.json`](../ml/data/real/manifests/cross_checks.json)

---

## 1. Changement de paradigme : du pilote 6 sites au Data Lake National

Conformément à la révision du plan IA réel (`IA-REAL-03`), le Data Lake ne repose plus sur une poignée de sites pilotes choisis manuellement :

1. **Grille nationale unique (`0,05° × 0,05°`, ≈ 5,5 km)** couvrant **100 % du territoire sénégalais** (**6 945 cellules** réparties sur les **14 régions** issues de geoBoundaries ADM1, `all_touched=True` pour inclure les zones côtières et frontalières), rattachée aux **76 mailles NASA POWER (`0,5° × 0,625°`)**.
2. **Rattachement universel par coordonnées GPS** : tout futur kit SmartAgri installé n'importe où au Sénégal est automatiquement indexé par son `(cell_id, power_cell_id)` sans dépendance à un nom de site.
3. **Zones de validation spatiale strictes** : **Mboro** (45 cellules), **Potou** (49 cellules) et **Richard-Toll** (50 cellules) — soit **5 mailles NASA POWER** — sont marquées `validation_zone` dans [`senegal_grid_0p05.parquet`](../ml/data/real/geo/senegal_grid_0p05.parquet) et **exclues de l'entraînement** dans l'instantané OctOpus afin de mesurer la généralisation spatiale réelle des futurs modèles.
4. **Hygiène et traçabilité strictes** :
   - Les anciens jeux limités à 6 sites (`IA-REAL-02`) sont archivés dans `ml/data/real/_legacy_pilot_6sites/`.
   - Les tables non sourcées ou issues d'API non commerciales sont placées en quarantaine dans `ml/data/real/_quarantine/`.
   - **0 modèle entraîné**, **0 donnée synthétique**, **aucune modification du Web ni du Backend**.

---

## 2. Bilan Quantitatif du Data Lake National (`ml/data/real/`)

| Indicateur global | Valeur vérifiée |
| :--- | :--- |
| **Nombre de tables Parquet actives** | **23 fichiers Parquet** (+ 23 manifestes `.manifest.json` SHA-256) |
| **Volume total de lignes** | **30 066 374 lignes** |
| **Volume disque compressé (Snappy)** | **162,58 Mo** |
| **Couverture géographique** | **14 / 14 régions du Sénégal** (`lat: 12,325°N → 16,675°N`, `lon: -17,525°E → -11,325°E`) |
| **Couverture temporelle** | **1961–2024** (FAOSTAT), **2000–2026** (prix WFP), **2015–2026** (météo, pluie, $ET_0$, humidité sol), **2024–2026** (Sentinel-2) |

### Répartition par domaine

| Domaine | Fichiers | Lignes | Taille | Couverture & Contenu |
| :--- | :---: | ---: | ---: | :--- |
| **Référentiel géo (`geo/`)** | 2 | 7 021 | 60,5 Ko | [`senegal_grid_0p05.parquet`](../ml/data/real/geo/senegal_grid_0p05.parquet) (6 945 cellules, 14 régions), [`power_cells_0p5x0p625.parquet`](../ml/data/real/geo/power_cells_0p5x0p625.parquet) (76 mailles NASA POWER), contours ADM1 GeoJSON. |
| **Pluie (`rain/`)** | 12 | 28 953 705 | 141,47 Mo | 12 fichiers annuels `chirps_v3_national_daily_<2015..2026>.parquet` (grille 0,05° complète, 6 945 cellules/jour, sources CHIRPS v2.0 DE Africa S3 / v3.0). |
| **Météo (`meteo/`)** | 1 | 329 232 | 10,35 Mo | [`nasa_power_national_daily.parquet`](../ml/data/real/meteo/nasa_power_national_daily.parquet) — 76 mailles × 4 332 jours (2015-01-01 → 2026-11-10), `t_min`, `t_max`, `t_mean`, `rh`, `wind_2m`, `solar_rad`, `pressure`, `rain`. |
| **$ET_0$ (`et0/`)** | 1 | 329 232 | 3,83 Mo | [`fao56_et0_national_daily.parquet`](../ml/data/real/et0/fao56_et0_national_daily.parquet) — $R_a$, $ET_0$ Hargreaves (éq. 52) et $ET_0$ Penman-Monteith (éq. 6) sans imputation forcée (`99,997 %` complétude). |
| **Humidité sol (`soil_moisture/`)** | 1 | 329 232 | 2,89 Mo | [`nasa_power_soil_wetness_national_daily.parquet`](../ml/data/real/soil_moisture/nasa_power_soil_wetness_national_daily.parquet) — indices modélisés NASA GEOS (`GWETTOP`, `GWETROOT`, `GWETPROF`, proxy régional avant pose des sondes IoT). |
| **Sols (`soil_properties/`)** | 1 | 13 890 | 714,9 Ko | [`isdasoil_national_grid_0p05.parquet`](../ml/data/real/soil_properties/isdasoil_national_grid_0p05.parquet) — 6 945 cellules × 2 profondeurs (`0-20 cm`, `20-50 cm`) iSDAsoil (texture, pH, SOC, N, P, K, CEC, densité) + pédotransfert Saxton-Rawls + contrôle croisé SoilGrids (`sand_5_15cm`, `clay_5_15cm`). |
| **Sentinel-2 & NDVI (`sentinel2_ndvi/`)** | 2 | 46 920 | 2,24 Mo | [`deafrica_s2_national_scene_catalog_2024_2026.parquet`](../ml/data/real/sentinel2_ndvi/deafrica_s2_national_scene_catalog_2024_2026.parquet) (**20 722 scènes** sur tout le Sénégal) + [`s2_ndvi_national_grid_monthly_2025.parquet`](../ml/data/real/sentinel2_ndvi/s2_ndvi_national_grid_monthly_2025.parquet) (**26 198 lignes**, composites mensuels 2025 sur 54 tuiles S2). |
| **Cultures & Occupation (`crops_senegal/`)** | 2 | 7 845 | 122,7 Ko | [`esa_worldcover_national_grid_0p05.parquet`](../ml/data/real/crops_senegal/esa_worldcover_national_grid_0p05.parquet) (6 945 cellules, 100 % territoire, part de terres cultivées `18,08 %`) + [`fao56_crop_coefficients_daily.parquet`](../ml/data/real/crops_senegal/fao56_crop_coefficients_daily.parquet) (900 lignes extraites directement de `agronomy.py`). |
| **Marchés & Prix (`market_prices/`)** | 2 | 55 362 | 978,8 Ko | [`wfp_senegal_markets.parquet`](../ml/data/real/market_prices/wfp_senegal_markets.parquet) (79 marchés, 14 régions) + [`wfp_senegal_food_prices.parquet`](../ml/data/real/market_prices/wfp_senegal_food_prices.parquet) (55 283 relevés en FCFA, 2000–2026). |
| **Rendements (`yields/`)** | 1 | 956 | 24,4 Ko | [`faostat_senegal_crops_1961_2024.parquet`](../ml/data/real/yields/faostat_senegal_crops_1961_2024.parquet) (64 ans, échelle nationale, `lat`/`lon` factices retirés). |

---

## 3. Contrôles Croisés & Qualité Vérifiés (`cross_checks.json`)

1. **Sols (`iSDAsoil` 0–20 cm vs `SoilGrids 2.0` 5–15 cm sur 6 911 cellules)** :
   - Sable (`sand_pct`) : corrélation de Pearson **$r = 0,8302$**, écart absolu moyen **$5,99\,\%$**.
   - Argile (`clay_pct`) : corrélation de Pearson **$r = 0,7534$**, écart absolu moyen **$2,97\,\%$**.
2. **Précipitations quotidiennes (`CHIRPS` vs `NASA POWER PRECTOTCORR` sur 316 844 paires maille × jour)** :
   - Corrélation quotidienne $r = 0,3793$, moyenne NASA `2,476 mm/j` vs CHIRPS `1,896 mm/j` (ratio annuel CHIRPS/NASA = `0,7657`), confirmant la complémentarité des deux sources dans les features de pluie cumulée (`3j`, `7j`, `14j`).
3. **Complétude & Doublons** :
   - `0` doublon sur les clés primaires de toutes les tables.
   - Sentinel-2 2025 : 54/54 tuiles lues sur chacun des 4 mois saisonniers (`2025-02`, `2025-05`, `2025-08`, `2025-11`), couvrant **6 454 à 6 616 cellules** sur 6 945 par mois après masquage nuageux `SCL`.

---

## 4. Instantané National Prêt pour OctOpus ML (`v=20261114-natl01`)

Généré par [`agriml.octopus.exporter`](../ml/src/agriml/octopus/exporter.py) sous [`plateforme/ml/data/curated/octopus/soil_nowcast_proxy_national/v=20261114-natl01/`](../ml/data/curated/octopus/soil_nowcast_proxy_national/v=20261114-natl01/) :

- **`train.parquet`** : **258 440 lignes** (71 mailles NASA POWER hors zones de validation, `2015-01-14` → `2024-12-31`, 30 variables explicatives météo/pluie/sol/occupation du sol + cible proxy `soil_wetness_root_pct`).
- **`test.parquet`** : **25 915 lignes** (année 2025 sur les 71 mailles d'entraînement, sans cibles).
- **`manifest.json`** (`sha256: 20a4a2777411a03fcc257eb49165ecce78edad500f363a2fe91096b8a5d46c7f`) : `power_cell_id` pseudonymisé par **HMAC-SHA256**, `holdout_sent: false`.
- **Double Holdout souverain isolé localement** (jamais envoyé à OctOpus) :
  - **Holdout temporel 2026** ([`holdout_temporal_2026_other_cells.parquet`](../ml/data/curated/holdout/soil_nowcast_proxy_national/holdout_temporal_2026_other_cells.parquet)) : **22 294 lignes** (`2026-01-01` → `2026-11-10`).
  - **Holdout spatial pur (zones de validation Mboro, Potou, Richard-Toll)** ([`holdout_spatial_validation_zones_all_dates.parquet`](../ml/data/curated/holdout/soil_nowcast_proxy_national/holdout_spatial_validation_zones_all_dates.parquet)) : **21 660 lignes** (`2015–2026` sur les 5 mailles de validation).
