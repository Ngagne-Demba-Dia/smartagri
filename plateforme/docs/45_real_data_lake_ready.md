# 45 — Data Lake Réel SmartAgri92 Prêt pour OctOpus (`IA-REAL-02`)

**Date** : 14 novembre 2026  
**Mission** : `IA-REAL-02` — Téléchargement réel des sources Niveau A, conversion intégrale en Parquet, audit qualité/volume/couverture et préparation OctOpus  
**Statut** : `READY_FOR_OCTOPUS` — *Confidentiel — réservé aux partenaires de travail.*  
**Script d'acquisition reproductible** : [`plateforme/ml/scripts/build_real_data_lake.py`](../ml/scripts/build_real_data_lake.py)  
**Rapport d'audit machine** : [`plateforme/ml/data/real/manifests/lake_audit_report.json`](../ml/data/real/manifests/lake_audit_report.json)

---

## 1. Synthèse Exécutive et Respect des Contraintes

Le Data Lake réel de SmartAgri92 est désormais constitué physiquement sur disque dans [`plateforme/ml/data/real/`](../ml/data/real/) et son instantané pseudonymisé prêt pour OctOpus ML est généré dans [`plateforme/ml/data/curated/octopus/soil_nowcast/v=20261114-real01/`](../ml/data/curated/octopus/soil_nowcast/v=20261114-real01/).

| Critère de la mission `IA-REAL-02` | Statut | Preuve vérifiable |
| :--- | :--- | :--- |
| **1. Téléchargement réel de toutes les sources Niveau A** | **100 % réalisé** | Requêtes HTTP/STAC/S3 exécutées sur NASA POWER, CHIRPS v3.0 COG (UCSB), ECMWF IFS 0.25° / NOAA GFS 0.25°, iSDAsoil 30 m COG, Digital Earth Africa Sentinel-2 L2A 10 m COG, ESA WorldCover 10 m COG, FAOSTAT Bulk Africa (`QCL`) et HDX WFP/VAM Sénégal. |
| **2. Construction de `ml/data/real/`** | **100 % réalisé** | **17 tables Parquet thématiques** + **17 manifestes JSON SHA-256** répartis dans les 9 sous-dossiers de sources ouvertes (+ `iot_telemetry/` réservé aux futurs kits ESP32-S3). |
| **3. Conversion intégrale vers Apache Parquet** | **100 % réalisé** | Tous les fichiers sont sérialisés en `.parquet` (compression `snappy`, moteur `fastparquet`/`pyarrow` unifié dans [`agriml/io.py`](../ml/src/agriml/io.py)). |
| **4. Vérification Qualité, Volume, Couverture temporelle & géographique** | **100 % réalisé** | **239 605 lignes** dans `ml/data/real/` (**6,11 Mo** compressés), complétude moyenne de **99,18 %**, **0 doublon**, couvrant **1961–2026** et jusqu'à **76 localités géolocalisées** au Sénégal. |
| **5. Instantané prêt pour OctOpus ML + Holdout souverain isolé** | **100 % réalisé** | `train.parquet` (**21 918 lignes**, 2015–2024), `test.parquet` sans cible (**2 190 lignes**, 2025) et `holdout_2026.parquet` (**1 878 lignes**, 2026, conservé localement avec `holdout_sent: false`). |
| **6. Aucun modèle entraîné** | **Respecté** | `models_trained = 0` (aucun appel à `fit()`, `agriml.train` ou `POST /api/run`). |
| **7. Zéro donnée synthétique utilisée** | **Respecté** | `synthetic_data_used = false` sur la totalité des 17 manifestes et sur l'instantané OctOpus. |

---

## 2. Inventaire Physique Complet du Data Lake Réel (`ml/data/real/`)

Chaque fichier `.parquet` ci-dessous possède son manifeste compagnon `<fichier>.parquet.manifest.json` contenant son empreinte cryptographique `sha256`, ses types de colonnes et ses métriques de qualité :

| # | Domaine | Fichier Parquet (`ml/data/real/...`) | Source (`source_id`) | Lignes | Colonnes | Taille (Ko) | Complétude | Empreinte `SHA-256` (16 premiers hex.) |
| :-: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| **1** | `meteo` | [`meteo/nasa_power_senegal_daily.parquet`](../ml/data/real/meteo/nasa_power_senegal_daily.parquet) | `nasa_power` | 25 992 | 15 | 888,68 | 93,33 %* | `7b41e8ba631b78f4` |
| **2** | `meteo` | [`meteo/nasa_power_senegal_hourly.parquet`](../ml/data/real/meteo/nasa_power_senegal_hourly.parquet) | `nasa_power` | 74 592 | 11 | 1 662,63 | 99,46 % | `a350b2c3f6b9fe2a` |
| **3** | `meteo` | [`meteo/ecmwf_gfs_forecast_asof.parquet`](../ml/data/real/meteo/ecmwf_gfs_forecast_asof.parquet) | `ecmwf_open_data+noaa_gfs` | 2 880 | 15 | 63,36 | 100,00 % | `570f16c379b4b0eb` |
| **4** | `rain` | [`rain/chirps_v3_cog_hivernage_senegal.parquet`](../ml/data/real/rain/chirps_v3_cog_hivernage_senegal.parquet) | `chirps` (v3.0 COG) | 48 | 12 | 4,40 | 100,00 % | `70216424dbe13c24` |
| **5** | `rain` | [`rain/senegal_daily_rain_series_2015_2026.parquet`](../ml/data/real/rain/senegal_daily_rain_series_2015_2026.parquet) | `chirps+nasa_power` | 25 986 | 22 | 1 013,83 | 100,00 % | `d7eea55354f2dbfa` |
| **6** | `et0` | [`et0/fao56_et0_senegal_daily.parquet`](../ml/data/real/et0/fao56_et0_senegal_daily.parquet) | `nasa_power+fao56_tables` | 25 992 | 15 | 876,12 | 93,33 %* | `ecb8cee310c6c84e` |
| **7** | `soil_moisture` | [`soil_moisture/nasa_power_soil_moisture_daily.parquet`](../ml/data/real/soil_moisture/nasa_power_soil_moisture_daily.parquet) | `nasa_power` (`GWETTOP`/`ROOT`) | 25 992 | 17 | 623,52 | 100,00 % | `342eed277a733ab0` |
| **8** | `soil_properties` | [`soil_properties/isdasoil_30m_senegal_profiles.parquet`](../ml/data/real/soil_properties/isdasoil_30m_senegal_profiles.parquet) | `isdasoil+soilgrids` | 60 | 22 | 10,02 | 100,00 % | `5e4090afe54696d4` |
| **9** | `sentinel2_ndvi` | [`sentinel2_ndvi/deafrica_s2_scenes_catalog_2022_2026.parquet`](../ml/data/real/sentinel2_ndvi/deafrica_s2_scenes_catalog_2022_2026.parquet) | `deafrica+sentinel2` | 750 | 15 | 75,97 | 100,00 % | `ba822f18c290db15` |
| **10** | `sentinel2_ndvi` | [`sentinel2_ndvi/deafrica_s2_ndvi_pilot_sites.parquet`](../ml/data/real/sentinel2_ndvi/deafrica_s2_ndvi_pilot_sites.parquet) | `deafrica` (COG 10 m) | 36 | 15 | 7,35 | 100,00 % | `8d609c40f167f413` |
| **11** | `crops_senegal` | [`crops_senegal/esa_worldcover_10m_senegal_zones.parquet`](../ml/data/real/crops_senegal/esa_worldcover_10m_senegal_zones.parquet) | `worldcover` (10 m v200) | 45 | 12 | 5,04 | 100,00 % | `d374b186d3e1161f` |
| **12** | `crops_senegal` | [`crops_senegal/fao56_senegal_crops_kc_daily.parquet`](../ml/data/real/crops_senegal/fao56_senegal_crops_kc_daily.parquet) | `fao56_tables` | 900 | 10 | 14,76 | 100,00 % | `e2ff0a560c75d8d9` |
| **13** | `crops_senegal` | [`crops_senegal/csp_cilss_homologated_active_ingredients.parquet`](../ml/data/real/crops_senegal/csp_cilss_homologated_active_ingredients.parquet) | `csp_pesticides` | 8 | 8 | 3,34 | 100,00 % | `8e5873d8bec4c7c4` |
| **14** | `yields` | [`yields/faostat_senegal_crops_1961_2024.parquet`](../ml/data/real/yields/faostat_senegal_crops_1961_2024.parquet) | `faostat` (`QCL`) | 956 | 15 | 27,36 | 100,00 % | `76cfb9ad27364180` |
| **15** | `market_prices` | [`market_prices/wfp_senegal_markets.parquet`](../ml/data/real/market_prices/wfp_senegal_markets.parquet) | `hdx_wfp_senegal` | 79 | 7 | 4,73 | 100,00 % | `f962b7473bfe806c` |
| **16** | `market_prices` | [`market_prices/wfp_senegal_food_prices.parquet`](../ml/data/real/market_prices/wfp_senegal_food_prices.parquet) | `hdx_wfp_senegal` | 55 283 | 17 | 974,35 | 100,00 % | `31953057ea4332ed` |
| **17** | `market_prices` | [`market_prices/senegal_energy_irrigation_tariffs.parquet`](../ml/data/real/market_prices/senegal_energy_irrigation_tariffs.parquet) | `energy_tariffs` | 6 | 8 | 2,74 | 100,00 % | `40d7bf6ed3ae03fb` |
| — | **TOTAL `ml/data/real/`** | **17 tables Parquet + 17 manifestes JSON** | **100 % Niveau A (`open`)** | **239 605** | — | **6 258,20 Ko (6,11 Mo)** | **99,18 %** | — |

*\*Note sur la complétude à 93,33 % des tables #1 et #6 (soit exactement 1 colonne sur 15 à `NULL`) : toutes les colonnes mesurées (`t_min_c`, `t_max_c`, `rh_mean_pct`, `wind_2m_ms`, `rain_mm`, `et0_hargreaves_mm`, `et0_pm_mm`) sont complètes à **100,00 %** ; seule la colonne optionnelle de compatibilité de schéma (`issue_time` sur les observations historiques #1 et `eta_wapor_mm` Niveau B sur #6) est volontairement laissée à `NULL`.*

---

## 3. Audit Détaillé : Qualité, Volume, Couverture Temporelle et Couverture Géographique

### 3.1 Vérification de la Qualité des Données
1. **Filtrage des valeurs sentinelles et codes manquants** :
   - Les codes sentinelles `-999.0` de la NASA (notamment sur le rayonnement solaire CERES `ALLSKY_SFC_SW_DWN` lors des 2–3 derniers jours glissants) ont été convertis en `NaN` puis traités proprement ; pour $ET_0$ Penman-Monteith (`et0_pm_mm`), le calcul bascule sur Hargreaves-Samani (`et0_hargreaves_mm`) uniquement sur les rares journées où le flux radiatif satellitaire CERES est en attente de consolidation, garantissant **0 valeur manquante** sur `et0_pm_mm`.
   - La ligne de métadonnées HXL (`#date`, `#adm1+name`, `#item+name`, `#value`) présente en ligne 1 des fichiers CSV humanitaires HDX (`wfp_food_prices_sen.csv` et `wfp_markets_sen.csv`) a été purgée avant typage strict (`float64`, `Int64`).
2. **Contrôles de cohérence physique et agronomique (valeurs réelles observées au Sénégal)** :
   - **Pédologie 30 m (`isdasoil_30m_senegal_profiles.parquet`)** :
     - À **Mboro (`niayes_mboro`, 0–20 cm)** : `sand_pct = 62,7 %`, `clay_pct = 20,6 %`, `silt_pct = 16,7 %`, `ph_h2o = 6,6`, densité apparente `1,38 g/cm³`, capacité au champ `field_capacity_pct = 22,85 %`, point de flétrissement `wilting_point_pct = 13,26 %`, réserve utile `95,9 mm/m` (sol classé `deck_dior` / `dior`).
     - À **Richard-Toll / Podor (`vallee_richard_toll` & `vallee_podor`)** : teneur en argile plus marquée dans les cuvettes de décantation (`hollalde` / `fonde`), pH neutre à légèrement alcalin (`6,8` à `7,4`).
   - **Occupation du sol 10 m (`esa_worldcover_10m_senegal_zones.parquet`)** :
     - Extraction directe de **133 886 pixels à 10 m de résolution** (`1 338,86 ha` analysés autour des centroïdes des 6 bassins agricoles), isolant avec précision la classe `40 = Cropland (Terres cultivées)`, la classe `90 = Herbaceous wetland (Cuvettes humides des Niayes)` et la classe `80 = Permanent water bodies (Fleuve Sénégal / Lac de Guiers / Lac Mbawane)`.
   - **Sentinel-2 L2A 10 m (`deafrica_s2_ndvi_pilot_sites.parquet`)** :
     - Lecture directe par fenêtre `rasterio` sur les Cloud-Optimized GeoTIFFs de `s3://deafrica-sentinel-2` (bandes `B02`, `B04`, `B08` à 10 m sur une fenêtre de ~2 430 pixels par date claire `< 15 %` de nuages), donnant des valeurs réelles de `ndvi_mean` comprises entre `0,14` (sol sableux sec / début de cycle) et `0,58` (plein développement végétatif maraîcher / casiers irrigués).
   - **Zéro doublon** : `duplicate_rows = 0` sur l'ensemble des 17 tables Parquet.

### 3.2 Vérification des Volumes
- **Volume dans `ml/data/real/`** : **239 605 lignes** réparties sur **17 fichiers Parquet** pour une empreinte disque compressée de **6,11 Mo** (`6 408 399 octets`).
- **Volume dans `ml/data/curated/` (Instantané OctOpus + Holdout)** : **25 986 lignes** supplémentaires (**21 918 lignes** dans `train.parquet`, **2 190 lignes** dans `test.parquet`, **1 878 lignes** dans `holdout_2026.parquet`), portant le total du lac réel à **265 591 lignes** sur **20 fichiers Parquet**.

### 3.3 Vérification de la Couverture Temporelle
| Domaine | Couverture temporelle réelle acquise | Pas de temps | Nombre de pas uniques |
| :--- | :--- | :--- | ---: |
| **Rendements agricoles (`faostat`)** | **1961 → 2024** (64 années complètes) | Annuel | 64 ans |
| **Prix de marché en FCFA (`wfp_senegal_food_prices`)** | **2000-01-15 → 2026-09-15** (> 26 ans) | Mensuel / Bimensuel | 320 dates |
| **Météo, Pluie, $ET_0$, Humidité du sol (`nasa_power`)** | **2015-01-01 → 2026-11-10** (~12 ans) | Quotidien | 4 332 jours |
| **Météo horaire (`nasa_power_senegal_hourly`)** | **2024-01-01T00:00Z → 2026-11-01T23:00Z** (~3 ans) | **Horaire (1 h UTC)** | 24 864 heures |
| **Catalogue & Indices Sentinel-2 10 m (`deafrica`)** | **2022-01-02 → 2025-04-21** (> 3 ans) | Revisite 5 jours | 244 dates de passage |
| **Rasters Pluie CHIRPS v3.0 COG (`chirps`)** | **Hivernage 2024 (`2024-07-15` → `2024-10-05`)** | Échantillon journalier | 8 dates clés d'hivernage |
| **Prévisions numériques *as-of* (`ecmwf` + `noaa_gfs`)** | **2026-11-14T00:00Z → 2026-11-23T23:00Z** | **Horaire (échéances 0 à +240 h)** | 240 échéances horaires |

### 3.4 Vérification de la Couverture Géographique (Sénégal)
Le Data Lake couvre l'intégralité du territoire agricole sénégalais à trois échelles complémentaires :
1. **Échelle des 6 bassins agro-écologiques et maraîchers (`lat: 14,1520°N à 16,6528°N`, `lon: -17,2167°E à -14,9583°E`)** :
   - `niayes_mboro` : Zone des Niayes Nord — Mboro (Région de Thiès, Département de Tivaouane, `15.1503, -16.8797`) — *Zone pilote #1*.
   - `niayes_sangalkam` : Zone des Niayes Sud — Sangalkam / Lac Mbawane (Région de Dakar, Département de Rufisque, `14.7833, -17.2167`) — *Zone pilote #2*.
   - `vallee_richard_toll` : Vallée du Fleuve Sénégal — Richard-Toll / Dagana (Région de Saint-Louis, Département de Dagana, `16.4625, -15.7008`) — *Zone pilote #3*.
   - `niayes_notto` : Zone des Niayes Centre — Notto Gouye Diama (Région de Thiès, `14.9667, -17.0167`).
   - `vallee_podor` : Moyenne Vallée du Fleuve — Podor / Guédé Chantier (Région de Saint-Louis, `16.6528, -14.9583`).
   - `bassin_kaolack` : Bassin Arachidier & Maraîcher — Kaolack / Nioro (`14.1520, -16.0726`).
2. **Échelle parcellaire 30 m (`soil_properties/`)** : **30 points GPS distincts** (grilles de 5 parcelles par bassin : `centre`, `nord_est`, `nord_ouest`, `sud_est`, `sud_ouest`) extraits à 30 m de résolution sur 2 horizons (`0-20 cm` et `20-50 cm`).
3. **Échelle nationale des marchés (`market_prices/wfp_senegal_markets.parquet`)** : **79 marchés (76 coordonnées GPS uniques)** couvrant les **14 régions du Sénégal** de la Casamance au Fleuve (`lat: 12,38°N à 16,52°N`, `lon: -17,46°E à -11,76°E` : Dakar, Tilène, Castors, Gueule Tapée, Thiaroye, Thiès, Mboro, Tivaouane, Saint-Louis, Richard-Toll, Dagana, Podor, Matam, Louga, Touba, Diourbel, Kaolack, Fatick, Kaffrine, Tambacounda, Kédougou, Ziguinchor, Kolda, Sédhiou).

---

## 4. Instantané Réel Prêt pour OctOpus ML (`octopus/soil_nowcast/v=20261114-real01/`)

Conformément au plan d'onboarding [`42_octopus_onboarding_plan.md`](./42_octopus_onboarding_plan.md), le pipeline [`agriml/octopus/exporter.py`](../ml/src/agriml/octopus/exporter.py) a été exécuté sur les données réelles fusionnées (`soil_moisture` + `meteo` + `et0` FAO-56 + `isdasoil` 30 m) pour produire le premier instantané immuable destiné à OctOpus :

- **Dossier d'instantané OctOpus** : [`plateforme/ml/data/curated/octopus/soil_nowcast/v=20261114-real01/`](../ml/data/curated/octopus/soil_nowcast/v=20261114-real01/)
  - [`train.parquet`](../ml/data/curated/octopus/soil_nowcast/v=20261114-real01/train.parquet) : **21 918 lignes × 21 colonnes** (`2015-01-01` → `2024-12-31`), `sha256: aa1b58f6191b084a5f3b3ef51074533f024b1b4770096a6da9d84ecdf985632d`.
  - [`test.parquet`](../ml/data/curated/octopus/soil_nowcast/v=20261114-real01/test.parquet) : **2 190 lignes × 20 colonnes** (`2025-01-01` → `2025-12-31`, **sans la colonne cible `soil_moisture_pct`** pour le test de scoring distant `predict-file`), `sha256: ade5c57424c33c72a90545cc733e09e93c79825c92a01adb27f6a9b9da520163`.
  - [`manifest.json`](../ml/data/curated/octopus/soil_nowcast/v=20261114-real01/manifest.json) : `sha256: b69ed17b0f999f98ad1b4a4dd37f52757299b96ff5b608324942e6927e33aa84`.
  - [`README.md`](../ml/data/curated/octopus/soil_nowcast/v=20261114-real01/README.md) : documentation automatique du schéma exporté.
- **Garde-fous de confidentialité appliqués et vérifiés par `find_violations()` (`0` violation)** :
  - `device_id` pseudonymisé par **HMAC-SHA256** (16 caractères hexadécimaux, `salt_id: "real-lake-2026-11"`),
  - `site_id` en clair supprimé (`dropped_columns: ["site_id"]`),
  - Coordonnées GPS arrondies à $0,01^\circ$ (`lat_r`, `lon_r`).
- **Holdout souverain isolé localement (`holdout_sent: false`)** :
  - [`plateforme/ml/data/curated/holdout/soil_nowcast_real/holdout_2026.parquet`](../ml/data/curated/holdout/soil_nowcast_real/holdout_2026.parquet) : **1 878 lignes × 22 colonnes** couvrant l'année **2026 (`2026-01-01` → `2026-11-09`)**, `sha256: fe55bb3bcd52635f2369e2dab9a8234b9b52caf1b16aae68f3be8cbdaa28e132`. Ce fichier ne quitte jamais l'infrastructure SmartAgri92 et servira d'arbitre indépendant lors de l'évaluation des modèles de référence `agriml` et challenger `OctOpus`.
