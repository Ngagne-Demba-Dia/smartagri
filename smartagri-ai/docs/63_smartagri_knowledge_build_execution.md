# 63 — SmartAgri Knowledge : Rapport d'Exécution

**Date** : 2026-11-16 15:20 UTC
**Projet** : SmartAgri92 — PAS Challenge 2026

---

## 1. Corpus construit

| Métrique | Valeur |
|----------|--------|
| Documents extraits | **70** |
| Caractères totaux | **544,923** |
| Sources ZIP (texte) | 54 fichiers |
| Sources projet (MD/CSV/JSON) | 10 documents |
| Résumés data (parquet) | 6 fichiers |

### Répartition par domaine

| Domaine | Documents | Chunks |
|---------|-----------|--------|
| architecture_ia | 1 | 17 |
| cultures | 8 | 36 |
| général | 20 | 170 |
| géospatial | 4 | 18 |
| marchés | 4 | 20 |
| modélisation | 10 | 86 |
| météo | 2 | 12 |
| pluviométrie | 13 | 121 |
| sol | 5 | 25 |
| télédétection | 3 | 22 |

### Fichiers texte extraits du bundle

- `41_data_inventory.md`
- `42_octopus_onboarding_plan.md`
- `44_real_data_acquisition_plan.md`
- `45_real_data_lake_ready.md`
- `46_real_data_enrichment.md`
- `53_kit_data_model_mapping.md`
- `OCTOPUS_IMPORT_README.md`
- `README.md`
- `chirps_v3_national_daily_2015.parquet.manifest.json`
- `chirps_v3_national_daily_2016.parquet.manifest.json`
- `chirps_v3_national_daily_2017.parquet.manifest.json`
- `chirps_v3_national_daily_2018.parquet.manifest.json`
- `chirps_v3_national_daily_2019.parquet.manifest.json`
- `chirps_v3_national_daily_2020.parquet.manifest.json`
- `chirps_v3_national_daily_2021.parquet.manifest.json`
- `chirps_v3_national_daily_2022.parquet.manifest.json`
- `chirps_v3_national_daily_2023.parquet.manifest.json`
- `chirps_v3_national_daily_2024.parquet.manifest.json`
- `chirps_v3_national_daily_2025.parquet.manifest.json`
- `chirps_v3_national_daily_2026.parquet.manifest.json`
- `crops_senegal_SCHEMA.md`
- `cross_checks.json`
- `datasets.yaml`
- `deafrica_s2_national_scene_catalog_2024_2026.parquet.manifest.json`
- `esa_worldcover_national_grid_0p05.parquet.manifest.json`
- `et0_SCHEMA.md`
- `fao56_crop_coefficients_daily.parquet.manifest.json`
- `fao56_et0_national_daily.parquet.manifest.json`
- `faostat_senegal_crops_1961_2024.parquet.manifest.json`
- `grid_info.json`
- `iot_telemetry_SCHEMA.md`
- `isdasoil_national_grid_0p05.parquet.manifest.json`
- `lake_audit_report.json`
- `manifest.json`
- `market_prices_SCHEMA.md`
- `meteo_SCHEMA.md`
- `models.yaml`
- `nasa_power_national_daily.parquet.manifest.json`
- `nasa_power_soil_wetness_national_daily.parquet.manifest.json`
- `octopus_datasets_inventory.csv`
- `octopus_snapshot_info.json`
- `octopus_upload_order.md`
- `rain_SCHEMA.md`
- `real_data_lake_README.md`
- `s2_ndvi_national_grid_monthly_2025.parquet.manifest.json`
- `sentinel2_ndvi_SCHEMA.md`
- `soil_moisture_SCHEMA.md`
- `soil_properties_SCHEMA.md`
- `sources.yaml`
- `sources_registry.json`
- `wfp_senegal_food_prices.parquet.manifest.json`
- `wfp_senegal_markets.parquet.manifest.json`
- `yields_SCHEMA.md`

## 2. Chunking sémantique

| Paramètre | Valeur |
|-----------|--------|
| Méthode | Sections MD + paragraphes, JSON par clé, CSV par blocs |
| Cible tokens | 512 |
| Overlap | 64 tokens (entre sections) |
| Chunks produits | **527** |
| Tokens moyen/chunk | **232** |
| Min chars | 51 |
| Max chars | 2812 |
| Médiane chars | 604 |

## 3. Embeddings

| Paramètre | Baseline (ici) | Production |
|-----------|----------------|------------|
| Modèle | TF-IDF scikit-learn | `intfloat/multilingual-e5-large` |
| Dimensions | **8000** | **1024** |
| Ngrams | (1, 2) | N/A (transformer) |
| Langues | français | fr, wo, ff (partiel) |
| Licence | BSD-3 | MIT |

> **Note** : TF-IDF = baseline fonctionnelle. En production, `multilingual-e5-large`
> captera la sémantique multilingue (synonymes, reformulations, wolof partiel).

## 4. Index vectoriel

| Paramètre | Baseline | Production |
|-----------|----------|------------|
| Moteur | numpy cosine_similarity | ChromaDB |
| Chunks indexés | **527** | idem + sources externes |
| Stockage | matrice sparse mémoire | SQLite persistant |
| Reranker | aucun | `ms-marco-MiniLM-L-12-v2` |

## 5. Résultats d'évaluation

### Métriques globales (20 requêtes agricoles)

| Métrique | Score |
|----------|-------|
| Recall@1 | **40.0%** |
| Recall@3 | **65.0%** |
| Recall@5 | **75.0%** |
| Recall@10 | **80.0%** |
| MRR | **54.7%** |

### Recall@5 par catégorie

| Catégorie | Recall@5 | Requêtes |
|-----------|----------|----------|
| anomalie | [+] 100% | 1 |
| données | [+] 100% | 1 |
| sol | [+] 100% | 4 |
| ia | [+] 100% | 2 |
| irrigation | [+] 100% | 3 |
| marchés | [+] 100% | 2 |
| cultures | [~] 50% | 2 |
| pluie | [-] 33% | 3 |
| géospatial | [-] 0% | 1 |
| télédétection | [-] 0% | 1 |

### Détail par requête (k=5)

| # | Requête | Hit | Score | Source top-1 |
|---|---------|-----|-------|--------------|
| 1 | Quelle est l'humidité du sol prédite pour demain ? | OUI | 0.161 | bundle:nasa_power_soil_wetness_national_daily.parquet.manifest.json |
| 2 | Comment le modèle SoilNowcast fonctionne-t-il ? | OUI | 0.114 | projet:62_smartagri_rag_design.md |
| 3 | Variables importantes pour prédire l'humidité du sol | OUI | 0.156 | bundle:nasa_power_soil_wetness_national_daily.parquet.manifest.json |
| 4 | Pluviométrie moyenne au Sénégal en saison des pluies | NON | 0.214 | bundle:wfp_senegal_markets.parquet.manifest.json |
| 5 | Comment interpréter les données CHIRPS ? | NON | 0.116 | projet:56_real_ai_portfolio.md |
| 6 | Cumuls de pluie 7 et 14 jours du modèle | OUI | 0.100 | bundle:53_kit_data_model_mapping.md |
| 7 | Coefficient cultural Kc pour le riz irrigué au Sénégal | OUI | 0.200 | bundle:wfp_senegal_markets.parquet.manifest.json |
| 8 | Calculer évapotranspiration ET0 Penman-Monteith | OUI | 0.236 | bundle:fao56_et0_national_daily.parquet.manifest.json |
| 9 | Cultures cultivées au Sénégal et rendements récents | OUI | 0.213 | bundle:wfp_senegal_markets.parquet.manifest.json |
| 10 | Marchés agricoles suivis par le WFP au Sénégal | OUI | 0.483 | bundle:wfp_senegal_markets.parquet.manifest.json |
| 11 | Prix moyen de l'oignon sur les marchés sénégalais | OUI | 0.253 | bundle:44_real_data_acquisition_plan.md |
| 12 | Propriétés du sol mesurées par iSDAsoil | OUI | 0.186 | projet:rapport_analyse_bundle_smartagri92.md |
| 13 | Détecter une anomalie de sécheresse satellite | OUI | 0.115 | projet:56_real_ai_portfolio.md |
| 14 | Résolution spatiale grille nationale du Sénégal | NON | 0.153 | bundle:46_real_data_enrichment.md |
| 15 | NDVI pour suivre la santé des cultures | NON | 0.157 | bundle:octopus_upload_order.md |
| 16 | Algorithmes machine learning de SmartAgri | OUI | 0.085 | projet:62_smartagri_rag_design.md |
| 17 | Sources de données ouvertes utilisées par SmartAgri | OUI | 0.093 | bundle:README.md |
| 18 | Fonctionnement du RAG SmartAgri Knowledge | OUI | 0.283 | projet:62_smartagri_rag_design.md |
| 19 | Ravageurs menaçant les cultures maraîchères au Sénégal | NON | 0.168 | bundle:wfp_senegal_markets.parquet.manifest.json |
| 20 | Adapter irrigation en fonction humidité du sol prédite | OUI | 0.194 | bundle:nasa_power_soil_wetness_national_daily.parquet.manifest.json |

## 6. Exemples de recherche

### Requête : *humidité du sol prédiction demain*

**#1** (score 0.174) — `bundle:nasa_power_soil_wetness_national_daily.parquet.manifest.json` [sol]
> description: "Humidité du sol MODÉLISÉE (GEOS/MERRA-2) : taux de saturation relatif [0-1] en surface (0-5 cm), zone racinaire (0-100 cm) et profil. Ce n'est PAS une mesure de capteur ni une teneur vol...

**#2** (score 0.159) — `projet:rapport_analyse_bundle_smartagri92.md` [général]
> ## 6.3 Features candidates par objectif  ### 🎯 `soil_nowcast` — Prédiction humidité du sol (proxy NASA GEOS)  **Cible** : `soil_wetness_root_pct` (+ horizons `y_plus_1d/2d/3d_pct`) **Grain** : (power_...

**#3** (score 0.120) — `projet:62_smartagri_rag_design.md` [architecture_ia]
> ### 9.1 Prompt système (français)  ``` Tu es SmartAgri, un assistant agricole expert pour le Sénégal.  RÈGLES : 1. Réponds UNIQUEMENT à partir des documents fournis ci-dessous. 2. Si l'information n'e...

### Requête : *prix oignon marché Sénégal*

**#1** (score 0.216) — `bundle:wfp_senegal_food_prices.parquet.manifest.json` [marchés]
> description: "Prix de marché au Sénégal. price_fcfa_kg n'est calculé que pour les unités de masse (KG, 50/90/100 KG, MT) ; sinon vide."...

**#2** (score 0.137) — `bundle:market_prices_SCHEMA.md` [marchés]
> # `ml/data/real/market_prices/` — Prix Agricoles & Mercuriales du Sénégal (FCFA/kg)  - **Sources Niveau A (immédiates)** :   - `hdx_wfp_senegal` : jeu ouvert **WFP / VAM Food Prices for Senegal** sur ...

**#3** (score 0.122) — `bundle:sources.yaml` [général]
> licence: "SARRA-Py GPLv3 ; SARRA-O CeCILL-C (à confirmer) ; SARRA-H non publié (contact CIRAD)",      commercial: open, cost: "Gratuit (paramétrage local avec l'ISRA conseillé)", access: "Dépôts GitH...

### Requête : *NDVI santé cultures satellite*

**#1** (score 0.146) — `bundle:datasets.yaml` [général]
> content: "Profil de sol par parcelle : RU (TAW), CC, PF, pH, MO, CE ; source = labo sinon grille (avec incertitude)",      grain: "parcelle", refresh: "à chaque analyse", retention: "illimitée", volu...

**#2** (score 0.131) — `bundle:datasets.yaml` [général]
> - {id: raw.satellite.optical, zone: raw, domain: satellite, available: V2, classification: publique,      inputs: [sentinel2, landsat, hls], content: "Scènes L2A optiques (références STAC, découpes C...

**#3** (score 0.106) — `bundle:models.yaml` [modélisation]
> - id: ndvi_gapfill     use_case: IA-8     name: "Reconstruction des séries NDVI sous nuages"     kind: statistics     version: V2     platform: [web:4, web:6]     data:       mandatory: [satellite.fie...

## 7. Limites détectées

| # | Limite | Impact | Mitigation |
|---|--------|--------|------------|
| 1 | TF-IDF baseline | Synonymes et reformulations ratés | multilingual-e5-large en production |
| 2 | Corpus 100% français | Inaccessible wolof/pulaar | ASR wolof (OctOpus ASR 5) + traduction |
| 3 | Pas de PDF FAO/ISRA externes | Guides terrain manquants | Télécharger et indexer en V2 |
| 4 | Pas de reranker | Top-3 sous-optimal | ms-marco-MiniLM en production |
| 5 | Données proxy NASA GEOS | Calibration à valider | Recalibrer avec capteurs kits (V2) |
| 6 | Manifests JSON techniques | Bruit dans résultats | Filtrer type=json pour utilisateur final |

## 8. Artefacts produits

| Artefact | Fichier | Contenu |
|----------|---------|---------|
| Chunks indexés | `smartagri_knowledge_chunks.csv` | 527 chunks + métadonnées |
| Évaluation | `smartagri_knowledge_eval.csv` | 20 requêtes scored |
| Ce rapport | `63_smartagri_knowledge_build_execution.md` | mesures complètes |

## 9. Stack production recommandé

```
multilingual-e5-large  ->  ChromaDB  ->  ms-marco-MiniLM  ->  Mistral-7B-Instruct
     (embeddings)          (index)        (reranker)            (génération)
```

**Coût** : < 0.50 $ (CPU, pas de GPU pour le RAG)
**Licence** : 100% Apache 2.0 / MIT

---
*OctOpus — 70 documents, 527 chunks, 20 requêtes.*