# 93 — SmartAgri92 : Export Complet du Projet
**Date** : 2026-11-17 10:26 UTC
**Projet** : Agri-Moderne 5.0 — PAS Challenge 2026 Agriculture
**Équipe** : Mouhamadou Diop, Moustapha Diallo

---

## 1. Vue d'ensemble

| Indicateur | Valeur |
|-----------|--------|
| Modèles IA entraînés | 9 / 9 Classe A |
| Agents intelligents | 2 (Monitoring, Irrigation) |
| Base de connaissances | 527 chunks, 10 domaines |
| Datasets réels | 28 fichiers, 30,357,775 lignes, 767.2 Mo |
| Tables de résultats | 27 |
| Documents .md | 35 |
| Fichiers projet | 144 |
| App Démo | SmartAgri92 (8 pages, 14 fichiers source) |
| Régions couvertes | 14 / 14 |
| Période | 2015–2026 |

---

## 2. Modèles Champions — Métriques Mesurées

| # | Modèle | Champion | Métrique 1 | Métrique 2 | Données |
|---|--------|----------|-----------|-----------|---------|
| A1 | SoilNowcast | LightGBM | R² = 0.8353 | RMSE = 7.447 | 258K lignes, NASA POWER + CHIRPS + sol |
| A2 | ET0 Forecast | CatBoost | R² = 0.9997 | RMSE = 0.039 | 329K lignes, NASA POWER + FAO-56 |
| A3 | Yield Forecast | CatBoost | R² = 0.9509 | RMSE = 2.0083 | 956 lignes, FAOSTAT + météo |
| A4 | Rain Intelligence | CatBoost | AUC = 0.9625 | F1 = 0.7642 | 258K lignes, NASA POWER + CHIRPS |
| A5 | Price Forecast | XGBoost | R² = 0.8995 | RMSE = 66.67 FCFA/kg | 55K relevés WFP + météo |
| A6 | Crop Calendar | CatBoost | F1 = 0.9799 | Acc = 0.9811 | FAO-56 Kc + météo |
| A7 | NDVI Anomaly | LightGBM | F1 = 0.9943 | Acc = 0.9976 | 26K composites Sentinel-2 |
| A8 | Anomaly Intelligence | One-Class SVM | F1 = 0.0969 | Prec = 0.09 | NASA POWER + CHIRPS + ET0 |
| A9 | Market Clustering | KMeans k=7 | Silhouette = 0.3597 | — | 79 marchés, 55K relevés WFP |

---

## 3. Hyperparamètres Complets

### A1 SoilNowcast — LightGBM
```
n_estimators=5000, learning_rate=0.02, max_depth=8, num_leaves=127,
min_child_samples=50, subsample=0.8, colsample_bytree=0.8,
reg_alpha=0.1, reg_lambda=1.0, early_stopping_rounds=200
```

### A2 ET0 Forecast — CatBoost
```
iterations=3000, learning_rate=0.03, depth=8, l2_leaf_reg=3.0,
bagging_temperature=0.5, random_strength=0.5, early_stopping_rounds=200
```

### A3 Yield Forecast — CatBoost
```
iterations=2000, learning_rate=0.05, depth=6, l2_leaf_reg=5.0,
early_stopping_rounds=100
```

### A4 Rain Intelligence — CatBoost
```
iterations=3000, learning_rate=0.03, depth=8, l2_leaf_reg=3.0,
scale_pos_weight=auto, eval_metric=AUC, early_stopping_rounds=200
```

### A5 Price Forecast — XGBoost
```
n_estimators=3000, learning_rate=0.03, max_depth=8, min_child_weight=50,
subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
early_stopping_rounds=200
```

### A6 Crop Calendar — CatBoost
```
iterations=2000, learning_rate=0.05, depth=6, l2_leaf_reg=3.0,
loss_function=MultiClass, early_stopping_rounds=100
```

### A7 NDVI Anomaly — LightGBM
```
n_estimators=2000, learning_rate=0.05, max_depth=6, num_leaves=63,
is_unbalance=True, early_stopping_rounds=100
```

### A8 Anomaly Intelligence — Isolation Forest + Autoencoder
```
IsoForest: n_estimators=300, contamination=0.05, max_features=0.8
Autoencoder: layers=[64,32,16,32,64], epochs=50, lr=0.001
One-Class SVM: kernel=rbf, nu=0.05, gamma=scale
```

### A9 Market Clustering — KMeans
```
n_clusters=2, init=k-means++, n_init=50, max_iter=500, random_state=42
```

---

## 4. Features par Modèle

### A1_SoilNowcast
`doy_cos, doy_sin, et0_pm_mean_7d_mm, rain_nasa_sum_14d_mm, rain_chirps_sum_14d_mm, rh_mean_pct, rain_chirps_sum_7d_mm, rain_nasa_sum_7d_mm, t_min_c, pressure_hpa, ph_h2o, t_max_c, t_mean_c, wind_2m_ms, bulk_density_g_cm3, solar_rad_mj_m2, share_crop, rain_nasa_sum_3d_mm, soc_g_kg, rain_chirps_sum_3d_mm, rain_mm, share_tree, clay_pct, et0_pm_mm, sand_pct, rain_chirps_mm, share_built, share_bare, fc_ptf_pct, wp_ptf_pct`

### A2_ET0_Forecast
`t_min_c, t_max_c, t_mean_c, rh_mean_pct, wind_2m_ms, solar_rad_mj_m2, pressure_hpa, rain_mm, ra_mj_m2, et0_hargreaves_mm, doy_sin, doy_cos, month, t_range_c, lat, lon`

### A3_Yield_Forecast
`year, crop_enc, year_norm, decade, area_ha`

### A4_Rain_Intelligence
`doy_cos, doy_sin, solar_rad_mj_m2, wind_2m_ms, rain_chirps_sum_14d_mm, t_min_c, rain_mm, rain_nasa_sum_3d_mm, pressure_hpa, rain_chirps_sum_7d_mm, rain_chirps_sum_3d_mm, et0_pm_mean_7d_mm, rain_nasa_sum_14d_mm, rain_nasa_sum_7d_mm, rain_chirps_mm, t_max_c, t_mean_c, rh_mean_pct, et0_pm_mm, ph_h2o, soc_g_kg, bulk_density_g_cm3, share_crop, share_tree, sand_pct, share_built, share_bare, clay_pct, fc_ptf_pct, wp_ptf_pct`

### A5_Price_Forecast
`year, month, doy_sin, doy_cos, crop_enc, market_enc, region_enc, category_enc, lat, lon`

### A4 Rain Intelligence — SHAP Top 5
| Feature | Mean |SHAP| |
|---------|------------|
| doy_sin | 0.0706 |
| doy_cos | 0.0648 |
| rain_mm | 0.0455 |
| rh_mean_pct | 0.0182 |
| solar_rad_mj_m2 | 0.0132 |

---

## 5. Résultats SHAP

- **Rain Intelligence** : 30 features, SHAP summary sauvegardé dans `wx_rain_prob_shap_summary.csv`
- **SoilNowcast** : 30 features, importance dans `soilnowcast_feature_importance_all.csv` + `lgb_feature_importance.csv`
- **ET0 Forecast** : 16 features, importance dans `et0_forecast_feature_importance.csv`
- **Price Forecast** : 10 features, importance dans `price_forecast_feature_importance.csv`
- **Yield Forecast** : 5 features, importance dans `yield_forecast_feature_importance.csv`
- **Anomaly Intelligence** : 34 features, importance dans `anomaly_intelligence_feature_importance.csv`

---

## 6. Évaluations

### Validation croisée
- SoilNowcast, ET0, Rain, Price : **GroupKFold 5 folds** (groupes = `power_cell_id`)
- Yield Forecast : **KFold 5 folds** (données nationales annuelles)
- Crop Calendar, NDVI Anomaly : **StratifiedKFold 5 folds**

### Stabilité des folds (Rain Intelligence)
- AUC : mean=0.9625, sauvegardé dans `wx_rain_prob_fold_stability.csv`

### Erreurs par groupe
- SoilNowcast : 639 entrées, 3 cibles × 71 groupes × 3 modèles
- ET0 : 45 entrées, 3 cibles × 5 groupes × 3 modèles
- Price : 39 entrées par marché
- Rain : 213 entrées par cellule

### Knowledge RAG
- 527 chunks, 10 domaines
- Recall@5 = 0.75, score moyen = 0.1839

---

## 7. Tables du Projet (27)

| # | Table | Lignes | Colonnes | Modèle |
|---|-------|--------|----------|--------|
| 1 | `soilnowcast_all_metrics.csv` | 45 | 7 | A1 |
| 2 | `soilnowcast_feature_importance_all.csv` | 30 | 4 | A1 |
| 3 | `soilnowcast_group_errors.csv` | 639 | 8 | A1 |
| 4 | `et0_forecast_all_metrics.csv` | 15 | 7 | A2 |
| 5 | `et0_forecast_feature_importance.csv` | 16 | 4 | A2 |
| 6 | `et0_forecast_group_errors.csv` | 45 | 8 | A2 |
| 7 | `yield_forecast_all_metrics.csv` | 15 | 7 | A3 |
| 8 | `yield_forecast_feature_importance.csv` | 5 | 4 | A3 |
| 9 | `wx_rain_prob_all_metrics.csv` | 45 | 11 | A4 |
| 10 | `wx_rain_prob_feature_importance_all.csv` | 30 | 4 | A4 |
| 11 | `wx_rain_prob_shap_summary.csv` | 30 | 2 | A4 |
| 12 | `wx_rain_prob_fold_stability.csv` | 45 | 6 | A4 |
| 13 | `wx_rain_prob_group_errors.csv` | 213 | 7 | A4 |
| 14 | `price_forecast_all_metrics.csv` | 15 | 7 | A5 |
| 15 | `price_forecast_feature_importance.csv` | 10 | 4 | A5 |
| 16 | `price_forecast_group_errors.csv` | 39 | 6 | A5 |
| 17 | `remaining_models_all_metrics.csv` | 39 | 6 | A6+A7 |
| 18 | `anomaly_intelligence_metrics.csv` | 30 | 8 | A8 |
| 19 | `anomaly_intelligence_feature_importance.csv` | 34 | 4 | A8 |
| 20 | `market_clustering_results.csv` | 6 | 5 | A9 |
| 21 | `market_cluster_assignments.csv` | 67 | 2 | A9 |
| 22 | `smartagri_knowledge_chunks.csv` | 527 | 7 | RAG |
| 23 | `smartagri_knowledge_eval.csv` | 20 | 5 | RAG |
| 24 | `lgb_fold_metrics.csv` | 18 | 7 | A1 |
| 25 | `lgb_feature_importance.csv` | 30 | 2 | A1 |
| 26 | `inventaire_datasets.csv` | 28 | 5 | infra |
| 27 | `quality_issues.csv` | 90 | 3 | infra |

---

## 8. Documents du Projet (35)

| # | Document | Taille | Description |
|---|----------|--------|-------------|
| 1 | `56_real_ai_portfolio.md` | 31.0 Ko | Portefeuille IA complet (21 modèles) |
| 2 | `57_first_octopus_projects.md` | 12.7 Ko | Premiers projets OctOpus |
| 3 | `58_plan_A1_soil_nowcast.md` | 20.7 Ko | Plan SoilNowcast |
| 4 | `56_classe_a_fiches_detaillees.md` | 14.7 Ko | Fiches Classe A détaillées |
| 5 | `63_smartagri_knowledge_build_execution.md` | 15.0 Ko | Construction Knowledge |
| 6 | `64_soilnowcast_productization.md` | 18.0 Ko | Productisation SoilNowcast |
| 7 | `65_smartagri_assistant_v1.md` | 14.0 Ko | Assistant Parcellaire v1 |
| 8 | `66_wx_rain_prob_execution_plan.md` | 12.0 Ko | Plan Rain Intelligence |
| 9 | `67_wx_rain_prob_training_report.md` | 18.0 Ko | Rapport Rain Intelligence |
| 10 | `68_wx_rain_prob_business_validation.md` | 14.0 Ko | Validation métier Rain |
| 11 | `69_anomaly_intelligence_execution.md` | 16.0 Ko | Anomaly Intelligence |
| 12 | `70_assistant_parcellaire_v2.md` | 14.0 Ko | Assistant Parcellaire v2 |
| 13 | `71_agent_monitoring_design.md` | 14.0 Ko | Design Agent Monitoring |
| 14 | `72_agent_irrigation_design.md` | 14.0 Ko | Design Agent Irrigation |
| 15 | `73_monitoring_engine_execution.md` | 12.0 Ko | Exécution Monitoring |
| 16 | `74_monitoring_test_suite.md` | 10.0 Ko | Tests Monitoring |
| 17 | `75_irrigation_engine_execution.md` | 12.0 Ko | Exécution Irrigation |
| 18 | `76_irrigation_test_suite.md` | 10.0 Ko | Tests Irrigation |
| 19 | `77_agent_monitoring_execution.md` | 12.0 Ko | Agent Monitoring v1 |
| 20 | `78_agent_monitoring_test_suite.md` | 10.0 Ko | Tests Agent Monitoring |
| 21 | `80_smartagri_ai_orchestrator.md` | 12.1 Ko | Orchestrateur IA central |
| 22 | `81_ai_execution_flows.md` | 12.6 Ko | 30 scénarios d'exécution |
| 23 | `82_class_b_readiness.md` | 32.1 Ko | Readiness Classe B |
| 24 | `82_smartagri_ai_runtime.md` | 25.6 Ko | Runtime IA exécutable |
| 25 | `83_runtime_scenarios.md` | 19.1 Ko | 30 scénarios runtime |
| 26 | `84_smartagri_mlops_architecture.md` | 29.4 Ko | Architecture MLOps |
| 27 | `85_smartagri_model_registry.md` | 11.8 Ko | Model Registry |
| 28 | `86_smartagri_feature_store.md` | 14.3 Ko | Feature Store |
| 29 | `87_smartagri_retraining_strategy.md` | 23.8 Ko | Stratégie Retraining |
| 30 | `88_smartagri_digital_agronomist.md` | 13.0 Ko | Agronome Numérique |
| 31 | `89_smartagri_knowledge_graph.md` | 12.9 Ko | Knowledge Graph |
| 32 | `90_smartagri_copilot.md` | 14.2 Ko | Copilot SmartAgri |
| 33 | `91_smartagri_scenario_simulator.md` | 17.2 Ko | Simulateur Scénarios |
| 34 | `92_smartagri_export_manifest.md` | 14.5 Ko | Export Manifest IA |
| 35 | `rapport_analyse_bundle_smartagri92.md` | 29.9 Ko | Rapport analyse bundle |

---

## 9. Artefacts Modèles

| Fichier | Taille | Description |
|---------|--------|-------------|
| `lgb_models_native.zip` | 51.4 Mo | 15 modèles LightGBM natifs (3 cibles × 5 folds) |
| `lgb_config.json` | 1.2 Ko | Configuration hyperparamètres LightGBM |
| `lgb_feature_importance.png` | 63.3 Ko | Graphique importance features SoilNowcast |

---

## 10. Prompts & Agents

### Prompt Système — Assistant Parcellaire v2
```
Tu es l'assistant agricole SmartAgri. Tu utilises les données de
SoilNowcast, Rain Intelligence, ET0 Forecast et la base de
connaissances agricoles pour répondre aux questions des agriculteurs
sénégalais. Réponds en français, avec des recommandations concrètes.
Cite tes sources (modèle, confiance, données).
```

### Agent Monitoring
- 8 seuils configurables (sol, pluie, ET0, NDVI)
- 4 niveaux d'alerte : NORMAL → WATCH → WARNING → CRITICAL
- Composants : SoilNowcast + Rain + ET0 + NDVI + Knowledge

### Agent Irrigation
- Méthode FAO-56 : ETc = Kc × ET0
- 17 cultures avec courbes Kc
- Règles : ne pas irriguer si pluie > 5mm dans 24h

### Orchestrateur
- 15 intentions routées
- Timeouts par service (200ms–2s)
- Gestion conflits : confiance > précaution > terrain > spécialiste > abstention

---

## 11. App Démo SmartAgri92

**URL** : octopus.ml/a/new-app-771f89
**Pages** : 8 (Dashboard, SoilNowcast, Rain, Knowledge, Assistant, Monitoring, Irrigation, Simulator)
**Fichiers source** : 14

| Fichier | Description |
|---------|-------------|
| `src/App.tsx` | App |
| `src/components/ChampionBadge.tsx` | ChampionBadge |
| `src/components/MetricCard.tsx` | MetricCard |
| `src/components/PageHeader.tsx` | PageHeader |
| `src/components/Sidebar.tsx` | Sidebar |
| `src/index.css` | index |
| `src/pages/AssistantIA.tsx` | AssistantIA |
| `src/pages/Dashboard.tsx` | Dashboard |
| `src/pages/Irrigation.tsx` | Irrigation |
| `src/pages/KnowledgeExplorer.tsx` | KnowledgeExplorer |
| `src/pages/Monitoring.tsx` | Monitoring |
| `src/pages/RainIntelligence.tsx` | RainIntelligence |
| `src/pages/ScenarioSimulator.tsx` | ScenarioSimulator |
| `src/pages/SoilNowcast.tsx` | SoilNowcast |

---

## 12. Datasets Source (Data Lake)

| Indicateur | Valeur |
|-----------|--------|
| Fichiers source | 28 |
| Lignes totales | 30,357,775 |
| Taille totale | 767.2 Mo |
| Régions | 14 / 14 |
| Période | 2015–2026 |
| Données synthétiques | 0 |

---

## 13. Procédure de Reconstruction

### Étape 1 — Infrastructure
```bash
pip install lightgbm xgboost catboost scikit-learn pandas numpy
pip install sentence-transformers faiss-cpu fastapi uvicorn
```

### Étape 2 — Data Lake
Importer les 28 datasets Parquet depuis `octopus_import_bundle.zip`.

### Étape 3 — Modèles
1. Charger `lgb_models_native.zip` (15 modèles LightGBM SoilNowcast)
2. Ré-entraîner les 8 autres modèles avec les hyperparamètres ci-dessus
3. Valider avec les tables de métriques fournies

### Étape 4 — Knowledge
1. Indexer les 527 chunks
2. Construire l'index FAISS
3. Tester avec `smartagri_knowledge_eval.csv`

### Étape 5 — Agents & Runtime
1. Implémenter les 6 services (voir `82_smartagri_ai_runtime.md`)
2. Configurer l'orchestrateur (voir `80_smartagri_ai_orchestrator.md`)
3. Configurer MLOps (voir `84–87_*.md`)

### Étape 6 — Vérification
Comparer les métriques obtenues avec les tables de référence.

---

## 14. Fichiers de Configuration

| Fichier | Usage |
|---------|-------|
| `lgb_config.json` | Hyperparamètres LightGBM SoilNowcast |
| `octopus_upload_order.md` | Ordre d'import des datasets |
| `OCTOPUS_IMPORT_README.md` | Documentation du package d'import |
| `sources_registry.json` | Registre des sources de données |
| `manifest.json` | Manifest du bundle d'import |

---

*Document généré automatiquement par OctOpus — SmartAgri92 PAS Challenge 2026*
