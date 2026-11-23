# 46 — Plan d'Enrichissement National et Stratégie de Généralisation (`IA-REAL-03`)

**Date** : 16 novembre 2026  
**Statut** : Feuille de route d'enrichissement du Data Lake National — *Confidentiel — réservé aux partenaires de travail.*  
**Références** : [`44_real_data_acquisition_plan.md`](./44_real_data_acquisition_plan.md), [`45_real_data_lake_ready.md`](./45_real_data_lake_ready.md), [`16_architecture_octopus.md`](./16_architecture_octopus.md).

---

## 1. Principe directeur : Généralisation à tout kit installé au Sénégal

Les kits SmartAgri92 pourront être déployés dans n'importe quelle région du Sénégal (Niayes, Vallée du Fleuve, Bassin Arachidier, Sénégal Oriental, Casamance). Aucun modèle ne doit dépendre d'identifiants de sites pilotes ni de paramètres locaux codés en dur :

1. **Indexation spatiale universelle** : à l'enrôlement d'un kit `(lat, lon)`, le pipeline rattache automatiquement le kit à :
   - sa cellule `cell_id` de la grille nationale `0,05°` (`senegal_grid_0p05.parquet`),
   - sa maille `power_cell_id` NASA POWER (`0,5° × 0,625°`),
   - son profil de sol local extrait à la volée à **30 m** depuis `iSDAsoil` (`s3://isdasoil/`) et son occupation du sol à **10 m** depuis `ESA WorldCover` (`s3://esa-worldcover/`),
   - les scènes Sentinel-2 L2A de sa tuile MGRS (`deafrica_s2_national_scene_catalog_2024_2026.parquet`).
2. **Validation croisée spatiale (*Leave-Region-Out* / *Spatial Holdout*)** :
   - Les bassins **Mboro**, **Potou** et **Richard-Toll** sont conservés exclusivement comme **zones de validation spatiale** (`validation_zone` dans `senegal_grid_0p05.parquet`) pour mesurer l'erreur d'un modèle sur un territoire jamais vu à l'entraînement.
   - Pour les modèles nationaux futurs (télémétrie IoT multi-régions), l'évaluation devra systématiquement combiner un split temporel purgé et un split spatial par bloc (`GroupKFold` sur `region_adm1` ou `power_cell_id`).
3. **Interdiction des proxies comme cible finale de production** :
   - L'instantané actuel `soil_nowcast_proxy_national` utilise l'humidité modélisée NASA GEOS (`GWETROOT`) comme proxy macro-climatique pour valider l'infrastructure OctOpus de bout en bout.
   - Le modèle de production `soil_nowcast` (service `#2`) sera entraîné uniquement lorsque la télémétrie horaire réelle des sondes IoT (`iot_telemetry/measurements_1h`) et l'étalonnage gravimétrique (`sm_calibration`) seront disponibles.

---

## 2. Priorités d'enrichissement national (Niveau B → Niveau C)

### 2.1 Enrichissements techniques immédiats (Niveau B — sans partenariat)

| Priorité | Domaine | Source à intégrer | Apport pour la généralisation nationale |
| :---: | :--- | :--- | :--- |
| **P1** | **Météo & Prévisions *As-Of*** | **ECMWF Open Data (IFS 0,25° GRIB2)** + **NOAA GFS** (via `ecmwf-opendata` / AWS S3, licence `open`) | Remplacer la table mise en quarantaine par une collecte automatisée 4×/jour des GRIB2 natifs sur la boîte `[-17.6, 12.25, -11.3, 16.7]` avec archivage strict `(issue_time, valid_time)` (aucune fuite future). |
| **P2** | **Réanalyse haute résolution** | **ERA5-Land (0,1° ≈ 9 km)** & **AgERA5** via Copernicus CDS (`cdsapi`) | Affiner la grille météo et l'humidité du sol de référence de `0,5°` (~55 km) à `0,1°` (~9 km) sur les 14 régions. |
| **P3** | **Sentinel-2 continu & Radar SAR** | **Digital Earth Africa STAC** (tous les mois 2024–2026) + **Sentinel-1 GRD (`VV`, `VH`)** via CDSE | Étendre les composites NDVI mensuels sur les 36 mois (actuellement 4 mois saisonniers 2025) et combler les nuages d'hivernage (juillet–septembre) par le radar Sentinel-1. |
| **P4** | **Pluie 2022–2026 complète** | **CHIRPS v3.0 final (`rnl`) + prelim (`sat`)** sur `data.chc.ucsb.edu` | Combler les jours manquants sur 2022–2024 et octobre–novembre 2026 dès rétablissement du serveur UCSB CHC (en complément du miroir DE Africa S3 v2.0). |
| **P5** | **Référentiels réglementaires** | **Liste officielle CSP/CILSS** (PDF/CSV officiel) & **Arrêtés CRSE / Senelec** | Remplacer les deux tables mises en quarantaine dans `_quarantine/` par les documents officiels sourcés et datés. |

### 2.2 Enrichissements terrain & partenariats nationaux (Niveau C)

| Priorité | Donnée attendue | Partenaire / Source | Modèle ou service débloqué à l'échelle nationale |
| :---: | :--- | :--- | :--- |
| **C1** | **Télémétrie horaire des kits ESP32-S3 + étalonnage gravimétrique** | Déploiement kits SmartAgri92 (multi-régions) | `soil_nowcast` (`#2`) et `sensor_anomaly` (`#13`) sur mesures réelles de capteurs. |
| **C2** | **Observations stations synoptiques** | **ANACIM** / **TAHMO** | Correction de biais météo local `wx_local_bias` sur tout le Sénégal. |
| **C3** | **Rendements départementaux & barèmes culturaux** | **DAPSA**, **ISRA / CDH**, **DPV** | `fertilization` (`#6`), `pest_risk` (`#9`) et `yield_forecast` (`#12`) calibrés par zone agro-écologique. |
| **C4** | **Mercuriales hebdomadaires maraîchères** | **SIM / CSA** & **ARM** | `price_forecast` (`#15`) sur l'oignon, la tomate, la pomme de terre et la carotte. |

---

## 3. Règles d'audit avant tout export vers OctOpus

1. **Aucune donnée de `_legacy_pilot_6sites/` ni de `_quarantine/`** ne doit être référencée par les scripts d'entraînement ou d'export.
2. **Contrôle de couverture spatiale** : chaque nouveau jeu de features national doit vérifier `regions_covered == 14` dans son manifeste avant validation.
3. **Holdout double obligatoire** : conserver localement un holdout temporel récent **et** un holdout spatial (zones de validation `mboro`, `potou`, `richard_toll` ou régions réservées), avec `holdout_sent: false` vérifié par `agriml.octopus.exporter`.
