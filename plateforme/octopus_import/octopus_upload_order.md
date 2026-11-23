# Ordre d'Import Recommandé dans OctOpus ML (`OCTOPUS-PACK-01`)

**Principe** : Importer les jeux par vagues progressives afin de respecter les dépendances de jointure spatiale (`cell_id` 0,05° et `power_cell_id` 0,5°×0,625°) et d'isoler strictement les zones de validation spatiale (**Mboro, Potou, Richard-Toll**) hors de l'entraînement.

---

## Vague 1 — Socle Spatial, Météo, Pluie, $ET_0$ et Humidité du sol

*À importer en premier : fournit l'index spatial national (`14/14` régions) et l'ensemble des séries climatiques quotidiennes `2015–2026`.*

1. **Référentiel Grille Nationale (`geo/`)** :
   - `datasets/geo/senegal_grid_0p05.parquet` (`6 945` cellules 0,05°, colonne `validation_zone` pour Mboro/Potou/Richard-Toll)
   - `datasets/geo/power_cells_0p5x0p625.parquet` (`76` mailles NASA POWER)
2. **`weather` (`meteo/`)** :
   - `datasets/meteo/nasa_power_national_daily.parquet` (`329 232` lignes, `2015-01-01` → `2026-11-10`)
3. **`rain` (`rain/`)** :
   - `datasets/rain/chirps_v3_national_daily_2015.parquet` … `2026.parquet` (`12` fichiers annuels, `28 953 705` lignes, grille 0,05°)
4. **`ET0` (`et0/`)** :
   - `datasets/et0/fao56_et0_national_daily.parquet` (`329 232` lignes, $R_a$, Hargreaves, Penman-Monteith)
5. **`soil_wetness` (`soil_moisture/`)** :
   - `datasets/soil_moisture/nasa_power_soil_wetness_national_daily.parquet` (`329 232` lignes, proxy modélisé NASA GEOS `GWETTOP`/`GWETROOT`/`GWETPROF`)

*(Optionnel pour test technique immédiat du pipeline OctOpus : téléverser l'instantané déjà assemblé et pseudonymisé `uploads/soil_nowcast_proxy_national/v=20261114-natl01/train.parquet` et `test.parquet`, avec `holdout_sent: false`.)*

---

## Vague 2 — Propriétés des Sols & Occupation du Sol (`soils`, `worldcover`)

*Dépend des `cell_id` de la Vague 1 pour enrichir chaque cellule climatique avec les constantes pédologiques et agricoles.*

1. **`soils` (`soil_properties/`)** :
   - `datasets/soil_properties/isdasoil_national_grid_0p05.parquet` (`13 890` lignes = `6 945` cellules × `0-20 cm` & `20-50 cm`, incluant contrôle SoilGrids)
2. **`worldcover` (`crops_senegal/`)** :
   - `datasets/crops_senegal/esa_worldcover_national_grid_0p05.parquet` (`6 945` lignes, fraction cultures `share_crop`, arbres, eau, zones humides)
   - `datasets/crops_senegal/fao56_crop_coefficients_daily.parquet` (`900` lignes, courbes $K_c$ des 7 cultures maraîchères)

---

## Vague 3 — Télédétection Optique (`sentinel2`, `ndvi`)

*Dépend des `cell_id` (Vague 1) et du masque `share_crop` (Vague 2) pour filtrer les cellules agricoles.*

1. **`sentinel2` (`sentinel2_ndvi/`)** :
   - `datasets/sentinel2_ndvi/deafrica_s2_national_scene_catalog_2024_2026.parquet` (`20 722` scènes L2A sur le Sénégal, liens COG)
2. **`ndvi` (`sentinel2_ndvi/`)** :
   - `datasets/sentinel2_ndvi/s2_ndvi_national_grid_monthly_2025.parquet` (`26 198` lignes, composites mensuels `2025-02/05/08/11` à 10 m/160 m avec masque nuageux `SCL`)

---

## Vague 4 — Économie & Statistiques Historiques (`prices`, `yields`)

*Couche macro-économique et historique pour les modèles V3 (`yield_forecast`, `price_forecast`).*

1. **`prices` (`market_prices/`)** :
   - `datasets/market_prices/wfp_senegal_markets.parquet` (`79` marchés géolocalisés sur 14 régions)
   - `datasets/market_prices/wfp_senegal_food_prices.parquet` (`55 283` relevés en FCFA/XOF, `2000–2026`)
2. **`yields` (`yields/`)** :
   - `datasets/yields/faostat_senegal_crops_1961_2024.parquet` (`956` lignes, séries nationales `1961–2024`)
