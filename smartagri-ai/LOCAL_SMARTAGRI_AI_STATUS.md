# LOCAL_SMARTAGRI_AI_STATUS — État du Patrimoine IA Local

**Date de reconstruction** : 2026-11-17  
**Périmètre** : `smartagri-ai/` uniquement (aucune archive supprimée, aucune modification sur `plateforme/web` ni `plateforme/backend`).

---

## 1. Synthèse de l'extraction et déduplication

- **Archives scannées dans `smartagri-ai/`** : 18 fichiers `.zip` (incluant les archives imbriquées).
- **Entrées analysées** : 905 entrées au total (873 fichiers non-ZIP, 32 archives imbriquées).
- **Hashes SHA-256 uniques** : 207 fichiers distincts.
- **Fichiers placés dans l'arborescence propre** : 165 fichiers (les 42 autres hashes uniques correspondent aux journaux `execution.log`, scripts d'empaquetage OctOpus `program.py`, manifests intermédiaires `manifest.json`, versions abrégées de docs `84`/`89`/`92`/`93`, anciennes versions CSV à précision flottante réduite et blob brut `pf_52f5f44d6e9445e3a7770109`).
- **Archives originales** : toutes conservées intactes à la racine de `smartagri-ai/`.

---

## 2. Arborescence reconstituée (`smartagri-ai/`)

```text
smartagri-ai/
├── docs/                       (25 docs 56→93 + rapports + sous-dossiers octopus_import/ et schemas/)
├── models/
│   ├── soilnowcast/            (15 modèles natifs LightGBM .txt + lgb_config.json)
│   ├── rain_intelligence/      (vide — poids absents, ré-entraînables)
│   ├── et0/                    (train_A2_et0.py + manifest.json ; poids absents)
│   ├── yield/                  (train_A3_yield_A5_price.py + manifest.json ; poids absents)
│   ├── anomaly/                (vide — poids absents, ré-entraînables)
│   └── clustering/             (train_A6_A7_A9.py + manifest.json ; poids absents)
├── rag/
│   ├── corpus/                 (vide — corpus déjà découpé dans chunks/)
│   ├── chunks/                 (smartagri_knowledge_chunks.csv — 527 chunks, 10 domaines)
│   ├── embeddings/             (vide — index FAISS à reconstruire localement)
│   └── evaluation/             (smartagri_knowledge_eval.csv — 20 requêtes d'évaluation)
├── agents/
│   ├── monitoring/             (vide — specs 71/73/74/77/78 manquantes, runtime dans docs/82_smartagri_ai_runtime.md)
│   ├── irrigation/             (vide — specs 72/75/76 manquantes, règles FAO-56 dans docs/93)
│   ├── assistant/              (vide — specs 65/70 manquantes, copilot dans docs/90_smartagri_copilot.md)
│   └── orchestrator/           (vide — spec complète dans docs/80_smartagri_ai_orchestrator.md)
├── mlops/
│   ├── registry/               (champions_summary.json, requirements.txt)
│   ├── feature_store/          (features_by_model.json, datasets_inventory.json, knowledge_stats.json, analysis_part1.json)
│   ├── retraining/             (vide — stratégie dans docs/87_smartagri_retraining_strategy.md)
│   └── architecture/           (datasets.yaml, models.yaml, sources.yaml, README.md)
├── datasets/
│   ├── raw/                    (25 fichiers Parquet réels + octopus_datasets_inventory.csv)
│   ├── curated/                (soil_nowcast_proxy_national/v=20261114-natl01/ : train.parquet, test.parquet, manifest.json, README.md)
│   ├── real/                   (vide — les datasets réels sont classés dans raw/ et curated/)
│   └── exports/                (vide)
├── metrics/                    (24 CSV : métriques, group_errors, fold_metrics, feature_importance, inventaire_datasets, quality_issues)
├── shap/                       (wx_rain_prob_shap_summary.csv, lgb_feature_importance.png)
└── manifests/                  (_manifest_p1.json, _manifest_p2.json, batch1_metrics_summary.json, octopus_import/*)
```

---

## 3. Vérification des documents 56 → 93

D'après `93_smartagri_full_project_export_manifest.md` (Section 8, 35 documents attendus) :

### Présents dans `smartagri-ai/docs/` (22 docs numérotés + 3 rapports/README)
- **56** : `56_real_ai_portfolio.md`, `56_classe_a_fiches_detaillees.md`
- **57** : `57_first_octopus_projects.md`
- **58** : `58_plan_A1_soil_nowcast.md`
- **63** : `63_smartagri_knowledge_build_execution.md`
- **64** : `64_soilnowcast_productization.md`
- **80** : `80_smartagri_ai_orchestrator.md`
- **81** : `81_ai_execution_flows.md`
- **82** : `82_class_b_readiness.md`, `82_smartagri_ai_runtime.md`
- **83** : `83_runtime_scenarios.md`
- **84** : `84_smartagri_mlops_architecture.md` (version complète 30 059 o retenue)
- **85** : `85_smartagri_model_registry.md`
- **86** : `86_smartagri_feature_store.md`
- **87** : `87_smartagri_retraining_strategy.md`
- **88** : `88_smartagri_digital_agronomist.md`, `88_smartagri_demo_app.md`
- **89** : `89_smartagri_knowledge_graph.md` (version complète 12 921 o retenue)
- **90** : `90_smartagri_copilot.md`
- **91** : `91_smartagri_scenario_simulator.md`
- **92** : `92_smartagri_export_manifest.md` (version complète 14 538 o retenue)
- **93** : `93_smartagri_full_project_export_manifest.md` (version complète 14 475 o retenue)
- **Compléments** : `rapport_analyse_bundle_smartagri92.md`, `README_RECONSTRUCTION.md`, `README_complete_export.md`

### Manquants dans `smartagri-ai/docs/` (14 documents listés dans le manifest 93)
- **65** : `65_smartagri_assistant_v1.md`
- **66** : `66_wx_rain_prob_execution_plan.md` *(note : `plateforme/docs/66_kit_platform_gap_analysis.md` est un autre document)*
- **67** : `67_wx_rain_prob_training_report.md` *(note : `plateforme/docs/67_firmware_v1_2_spec.md` est un autre document)*
- **68** : `68_wx_rain_prob_business_validation.md`
- **69** : `69_anomaly_intelligence_execution.md`
- **70** : `70_assistant_parcellaire_v2.md`
- **71** : `71_agent_monitoring_design.md`
- **72** : `72_agent_irrigation_design.md`
- **73** : `73_monitoring_engine_execution.md`
- **74** : `74_monitoring_test_suite.md`
- **75** : `75_irrigation_engine_execution.md`
- **76** : `76_irrigation_test_suite.md`
- **77** : `77_agent_monitoring_execution.md`
- **78** : `78_agent_monitoring_test_suite.md`
- *(Les numéros 59–62 et 79 ne figurent pas non plus dans le manifest 93.)*

---

## 4. Bilan détaillé : Récupéré / Manquant / Reconstructible / Dépendance OctOpus

### A. Ce qui a été récupéré (100 % opérationnel localement)
1. **Modèle A1 SoilNowcast** : les 15 modèles natifs LightGBM (`lgb_y_plus_1d_pct_fold0..4.txt`, `lgb_y_plus_2d_pct_fold0..4.txt`, `lgb_y_plus_3d_pct_fold0..4.txt`) + `lgb_config.json` + métriques de référence.
2. **Data Lake réel complet** : 25 datasets Parquet sources (`datasets/raw/`) + 2 datasets curés `train.parquet` / `test.parquet` (`datasets/curated/`), couvrant 14 régions (2015–2026) avec leurs 28 manifests JSON et schémas YAML/MD.
3. **Tables de vérité & SHAP** : les 27 tables du projet (métriques des 9 modèles A1–A9, erreurs par groupe, stabilité des folds, importance des features, `wx_rain_prob_shap_summary.csv`, `lgb_feature_importance.png`).
4. **Base de connaissances RAG (texte)** : `smartagri_knowledge_chunks.csv` (527 chunks) et `smartagri_knowledge_eval.csv` (20 questions/réponses de référence).
5. **Scripts d'entraînement partiels** : `train_A2_et0.py`, `train_A3_yield_A5_price.py`, `train_A6_A7_A9.py`.
6. **Architecture IA, Runtime & MLOps** : docs `56`–`58`, `63`–`64`, `80`–`93`, configs JSON (`champions_summary.json`, `features_by_model.json`, `analysis_part1.json`).

### B. Ce qui manque
1. **Documents** : les 14 fichiers `.md` `65` à `78` (Rain Intelligence docs, Anomaly Intelligence doc, Assistant v1/v2, design/exécution/tests des agents Monitoring et Irrigation).
2. **Poids de modèles sérialisés** : aucun binaire (`.pkl`, `.cbm`, `.xgb`, `.joblib`) pour les 8 modèles **A2 (ET0)**, **A3 (Yield)**, **A4 (Rain Intelligence)**, **A5 (Price)**, **A6 (Crop Calendar)**, **A7 (NDVI Anomaly)**, **A8 (Anomaly Intelligence)**, **A9 (Market Clustering)**.
3. **Index vectoriel RAG** : pas de fichier d'index FAISS ni d'embeddings pré-calculés dans `rag/embeddings/`.
4. **Code source exécutable des agents** : aucun fichier `.py` d'implémentation pour `monitoring`, `irrigation`, `assistant`, `orchestrator` dans les archives.
5. **App Démo SmartAgri92** : les 14 fichiers React (`src/App.tsx`, pages `Dashboard.tsx`, `SoilNowcast.tsx`, etc.) ne sont pas inclus dans les ZIPs.

### C. Ce qui est reconstructible localement (sans OctOpus)
1. **Les 8 modèles A2–A9** : entièrement ré-entraînables en local à partir des 27 Parquet de `datasets/`, des hyperparamètres et listes de features documentés dans `93_smartagri_full_project_export_manifest.md` et `mlops/feature_store/features_by_model.json`, ainsi que des scripts `train_A2_et0.py`, `train_A3_yield_A5_price.py`, `train_A6_A7_A9.py` (en adaptant leurs chemins d'entrée `INPUTS`), puis validables contre `metrics/*.csv`.
2. **L'index RAG FAISS + embeddings** : reconstructible directement depuis `rag/chunks/smartagri_knowledge_chunks.csv` avec `sentence-transformers` + `faiss-cpu`, puis validable avec `rag/evaluation/smartagri_knowledge_eval.csv`.
3. **Les agents & le runtime IA** : reconstructibles en Python/FastAPI à partir des spécifications détaillées présentes dans `docs/80_smartagri_ai_orchestrator.md`, `docs/82_smartagri_ai_runtime.md`, `docs/83_runtime_scenarios.md`, `docs/90_smartagri_copilot.md` et des règles métier de `docs/93_smartagri_full_project_export_manifest.md`.

### D. Ce qui dépend encore d'OctOpus
1. **Récupération des 14 documents manquants (`65`–`78`)** : uniquement disponibles dans l'historique/workspace OctOpus s'ils n'ont pas déjà été exportés ailleurs.
2. **Code source de l'app démo `octopus.ml/a/new-app-771f89`** (14 fichiers React/TSX) : hébergé sur OctOpus si vous souhaitez récupérer cette version démo exacte (sinon le frontend `plateforme/web/` du dépôt local existe déjà).
3. **Poids exacts d'origine (bit-à-bit) des modèles A2–A9** : si vous ne voulez pas les ré-entraîner localement.
