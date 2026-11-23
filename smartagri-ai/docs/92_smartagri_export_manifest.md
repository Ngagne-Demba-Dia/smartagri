# 92 — SmartAgri AI Export Manifest

**Projet** : SmartAgri92 — PAS Challenge 2026, Thème Agriculture
**Équipe** : Agri-Moderne 5.0 (Mouhamadou Diop, Moustapha Diallo)
**Date** : 2026-11-17
**Objectif** : Reconstruction complète du système IA SmartAgri sur infrastructure locale.

---
## 1. Inventaire Complet des Actifs IA

### 1.1 Modèles Entraînés (9/9 Classe A)

| # | Modèle | Type | Champion | Métrique |
|---|--------|------|----------|----------|
| A1 | SoilNowcast | Régression | LightGBM | R² = 0.8353 |
| A2 | ET0 Forecast | Régression | CatBoost | R² = 0.9997 |
| A3 | Yield Forecast | Régression | CatBoost | R² = 0.9509 |
| A4 | Rain Intelligence | Classification | CatBoost | AUC = 0.9625 |
| A5 | Price Forecast | Régression | XGBoost | R² = 0.8995 |
| A6 | Crop Calendar | Multi-classes | CatBoost | F1 = 0.980 |
| A7 | NDVI Anomaly | Binaire | LightGBM | F1 = 0.994 |
| A8 | Anomaly Intelligence | Non supervisé | One-Class SVM | F1 = 0.097 |
| A9 | Market Clustering | Clustering | KMeans k=7 | Sil = 0.360 |

### 1.2 Agents & Composants

| Composant | Type | Dépendances |
|-----------|------|-------------|
| SmartAgri Knowledge | RAG vectoriel | 527 chunks, 7 domaines, Recall@5=75% |
| Assistant Parcellaire v2 | Conversationnel | Knowledge + SoilNowcast + Rain + ET0 |
| Agent Monitoring | Décision temps réel | SoilNowcast + Rain + Anomaly + ET0 |
| Agent Irrigation | Recommandation | FAO-56 Kc + ET0 + SoilNowcast + Rain |
| SmartAgri Orchestrator | Routage central | 9 modèles + 4 agents |

### 1.3 Datasets Réels

- **28 datasets** dans le Data Lake national Sénégal
- **30 073 395 lignes** totales (162,64 Mo)
- **14/14 régions** couvertes, **0 donnée synthétique**
- Sources : NASA POWER, CHIRPS, iSDAsoil, ESA WorldCover, FAOSTAT, WFP, Sentinel-2, FAO-56

---
## 2. Modèles Champions — Détails Complets

### A1 — SoilNowcast

- **Champion** : LightGBM
- **Cible** : `soil_wetness_root_pct (%)`
- **Métriques** : R²=0.8353, RMSE=7.4470, MAE=5.9614
- **Données** : 258 440 lignes, NASA POWER+CHIRPS+iSDAsoil+WorldCover
- **Validation** : GroupKFold k=3 sur power_cell_id
- **Features (30)** : doy_cos, doy_sin, et0_pm_mean_7d_mm, rain_nasa_sum_14d_mm, rain_chirps_sum_14d_mm, rh_mean_pct, rain_chirps_sum_7d_mm, rain_nasa_sum_7d_mm, t_min_c, pressure_hpa...

### A2 — ET0 Forecast

- **Champion** : CatBoost
- **Cible** : `et0_pm_mm (mm/j)`
- **Métriques** : R²=0.9997, RMSE=0.0390, MAE=0.0284
- **Données** : 329 232 lignes, NASA POWER+FAO-56
- **Validation** : GroupKFold k=3 sur power_cell_id
- **Features (16)** : wind_2m_ms, rh_mean_pct, solar_rad_mj_m2, t_max_c, et0_hargreaves_mm, t_mean_c, t_min_c, ra_mj_m2, t_range_c, doy_sin...

### A3 — Yield Forecast

- **Champion** : CatBoost
- **Cible** : `yield_t_ha (t/ha)`
- **Métriques** : R²=0.9509, RMSE=2.0083
- **Données** : 956 lignes, FAOSTAT 1961-2024+météo
- **Validation** : KFold k=5
- **Features (5)** : area_ha, crop_enc, year_norm, year, decade

### A4 — Rain Intelligence

- **Champion** : CatBoost
- **Cible** : `rain_tomorrow (binaire)`
- **Métriques** : AUC=0.9625, F1=0.7642, Brier=0.0611
- **Données** : 258 440 lignes, NASA POWER+CHIRPS
- **Validation** : GroupKFold k=3 sur power_cell_id
- **Features (30)** : doy_cos, doy_sin, solar_rad_mj_m2, pressure_hpa, wind_2m_ms, t_min_c, t_mean_c, rain_mm, rain_chirps_sum_14d_mm, rh_mean_pct...

### A5 — Price Forecast

- **Champion** : XGBoost
- **Cible** : `price (FCFA/kg)`
- **Métriques** : R²=0.8995, RMSE=66.67 FCFA/kg
- **Données** : 55 283 relevés WFP 2000-2026
- **Validation** : KFold k=5
- **Features (10)** : crop_enc, category_enc, year, lat, region_enc, lon, doy_cos, month, market_enc, doy_sin

### A6 — Crop Calendar

- **Champion** : CatBoost, **F1**=0.980, **Acc**=0.981
- Données : FAO-56 Kc + météo + CHIRPS, KFold k=3

### A7 — NDVI Anomaly

- **Champion** : LightGBM, **F1**=0.994, **Acc**=0.998
- Données : 26 198 composites Sentinel-2, KFold k=3

### A8 — Anomaly Intelligence

- **Champion** : One-Class SVM, **F1**=0.097, **Prec**=0.090, **Rec**=0.198
- Features (34) : water_balance, wind_2m_ms, doy_sin, et0_pm_mm, pressure_hpa, t_mean_c, t_min_c, t_max_c, rain_chirps_sum_7d_mm, rh_mean_pct...

### A9 — Market Clustering

- KMeans k=7, Silhouette=0.360, 67 marchés classifiés

---
## 3. Hyperparamètres Complets

| Param | LightGBM (A1,A7) | CatBoost (A2,A3,A4,A6) | XGBoost (A5) |
|-------|------------------|------------------------|--------------|
| learning_rate | 0.05 | 0.05 | 0.05 |
| max_depth | 8 | 8 | 8 |
| n_estimators | 2000 (early) | 2000 (early) | 2000 (early) |
| early_stopping | 50 | 50 | 50 |
| subsample | 0.8 | 0.8 | 0.8 |
| colsample_bytree | 0.8 | — | 0.8 |
| reg_lambda | 1.0 | 3.0 | 1.0 |
| random_state | 42 | 42 | 42 |

**A8 Anomaly** : IsoForest(n_estimators=200, contamination=0.05) + AE([in→64→32→16→32→64→in], epochs=50, threshold=Q95)
**A9 Clustering** : KMeans(k=7, init=k-means++, n_init=10, seed=42)

---
## 4. Features Utilisées par Modèle

### A1 SoilNowcast (30 features)
```
  1. doy_cos
  2. doy_sin
  3. et0_pm_mean_7d_mm
  4. rain_nasa_sum_14d_mm
  5. rain_chirps_sum_14d_mm
  6. rh_mean_pct
  7. rain_chirps_sum_7d_mm
  8. rain_nasa_sum_7d_mm
  9. t_min_c
  10. pressure_hpa
  11. ph_h2o
  12. t_max_c
  13. t_mean_c
  14. wind_2m_ms
  15. bulk_density_g_cm3
  16. solar_rad_mj_m2
  17. share_crop
  18. rain_nasa_sum_3d_mm
  19. soc_g_kg
  20. rain_chirps_sum_3d_mm
  21. rain_mm
  22. share_tree
  23. clay_pct
  24. et0_pm_mm
  25. sand_pct
  26. rain_chirps_mm
  27. share_built
  28. share_bare
  29. fc_ptf_pct
  30. wp_ptf_pct
```

### A2 ET0 (16 features)
```
  1. wind_2m_ms
  2. rh_mean_pct
  3. solar_rad_mj_m2
  4. t_max_c
  5. et0_hargreaves_mm
  6. t_mean_c
  7. t_min_c
  8. ra_mj_m2
  9. t_range_c
  10. doy_sin
  11. doy_cos
  12. pressure_hpa
  13. lon
  14. lat
  15. rain_mm
  16. month
```

### A3 Yield (5 features)
```
  1. area_ha
  2. crop_enc
  3. year_norm
  4. year
  5. decade
```

### A4 Rain (30 features)
```
  1. doy_cos
  2. doy_sin
  3. solar_rad_mj_m2
  4. pressure_hpa
  5. wind_2m_ms
  6. t_min_c
  7. t_mean_c
  8. rain_mm
  9. rain_chirps_sum_14d_mm
  10. rh_mean_pct
  11. soc_g_kg
  12. ph_h2o
  13. et0_pm_mean_7d_mm
  14. t_max_c
  15. rain_nasa_sum_3d_mm
  16. rain_chirps_mm
  17. rain_chirps_sum_7d_mm
  18. bulk_density_g_cm3
  19. rain_chirps_sum_3d_mm
  20. et0_pm_mm
  21. share_crop
  22. rain_nasa_sum_14d_mm
  23. rain_nasa_sum_7d_mm
  24. sand_pct
  25. share_tree
  26. fc_ptf_pct
  27. share_bare
  28. share_built
  29. clay_pct
  30. wp_ptf_pct
```

### A5 Price (10 features)
```
  1. crop_enc
  2. category_enc
  3. year
  4. lat
  5. region_enc
  6. lon
  7. doy_cos
  8. month
  9. market_enc
  10. doy_sin
```

### A8 Anomaly (34 features)
```
  1. water_balance
  2. wind_2m_ms
  3. doy_sin
  4. et0_pm_mm
  5. pressure_hpa
  6. t_mean_c
  7. t_min_c
  8. t_max_c
  9. rain_chirps_sum_7d_mm
  10. rh_mean_pct
  11. solar_rad_mj_m2
  12. delta_t_range
  13. doy_cos
  14. rain_chirps_sum_14d_mm
  15. et0_pm_mean_7d_mm
  16. humidity_heat_idx
  17. ph_h2o
  18. share_built
  19. sand_pct
  20. rain_intensity_3d
  21. rain_chirps_sum_3d_mm
  22. bulk_density_g_cm3
  23. wp_ptf_pct
  24. soc_g_kg
  25. share_tree
  26. fc_ptf_pct
  27. rain_nasa_sum_7d_mm
  28. share_crop
  29. rain_nasa_sum_3d_mm
  30. clay_pct
  31. rain_nasa_sum_14d_mm
  32. share_bare
  33. rain_chirps_mm
  34. rain_mm
```

### SHAP Top 5 Rain Intelligence : doy_sin(0.0706), doy_cos(0.0648), rain_mm(0.0455), rh_mean_pct(0.0182), solar_rad_mj_m2(0.0132)

---
## 5. Métriques par Fold (mean ± std)

**A1 SoilNowcast (LightGBM)** : R²=0.8353±0.0701, RMSE=7.4470±1.3175
**A2 ET0 (CatBoost)** : R²=0.9997±0.0000, RMSE=0.0390±0.0015
**A3 Yield (CatBoost)** : R²=0.9509±0.0127, RMSE=2.0083±0.1485
**A5 Price (XGBoost)** : R²=0.8995±0.0031, RMSE=66.6700±2.1162
**A4 Rain (CatBoost)** : AUC=0.9625±0.0042, F1=0.7642±0.0218
**A6 CropCal (CatBoost)** : F1=0.980±0.017, Acc=0.981±0.016
**A7 NDVI (LightGBM)** : F1=0.994±0.002
**A8 Anomaly (One-Class SVM)** : F1=0.097, Prec=0.090, Rec=0.198
**A9 Clustering** : Sil=0.360

---
## 6. Artefacts Exportables

### 6.1 Tables de Métriques (27 tables dans le projet)

| Table | Lignes | Description |
|-------|--------|-------------|
| `soilnowcast_all_metrics.csv` | 45 | Métriques SN 3×folds |
| `soilnowcast_feature_importance_all.csv` | 30 | Features SN |
| `soilnowcast_group_errors.csv` | 639 | Erreurs SN par cellule |
| `lgb_fold_metrics.csv` | 18 | LGB détails |
| `lgb_feature_importance.csv` | 30 | LGB importance |
| `et0_forecast_all_metrics.csv` | 15 | Métriques ET0 |
| `et0_forecast_feature_importance.csv` | 16 | Features ET0 |
| `et0_forecast_group_errors.csv` | 45 | Erreurs ET0 |
| `yield_forecast_all_metrics.csv` | 15 | Métriques Yield |
| `yield_forecast_feature_importance.csv` | 5 | Features Yield |
| `price_forecast_all_metrics.csv` | 15 | Métriques Price |
| `price_forecast_feature_importance.csv` | 10 | Features Price |
| `price_forecast_group_errors.csv` | 39 | Erreurs Price/marché |
| `remaining_models_all_metrics.csv` | 39 | CropCal+NDVI |
| `wx_rain_prob_all_metrics.csv` | 45 | Métriques Rain 3×3×folds |
| `wx_rain_prob_feature_importance_all.csv` | 30 | Features Rain |
| `wx_rain_prob_shap_summary.csv` | 30 | SHAP Rain |
| `wx_rain_prob_group_errors.csv` | 213 | Erreurs Rain/cellule |
| `wx_rain_prob_fold_stability.csv` | 45 | Stabilité Rain |
| `anomaly_intelligence_metrics.csv` | 30 | 5 modèles×6 types |
| `anomaly_intelligence_feature_importance.csv` | 34 | Features Anomaly |
| `market_clustering_results.csv` | 6 | 6 configs testées |
| `market_cluster_assignments.csv` | 67 | 67 marchés→cluster |
| `smartagri_knowledge_chunks.csv` | 527 | 527 chunks RAG |
| `smartagri_knowledge_eval.csv` | 20 | 20 requêtes éval |
| `inventaire_datasets.csv` | 28 | 28 datasets |
| `quality_issues.csv` | 90 | 90 problèmes qualité |

### 6.2 Documents de Conception (18 documents .md dans le projet)

| # | Document | Contenu |
|---|----------|---------|
| 56 | real_ai_portfolio.md — Portefeuille 21 modèles |
| 63 | knowledge_build_execution.md — Corpus+chunking+embeddings |
| 64 | soilnowcast_productization.md — Export local |
| 65 | assistant_v1.md — Architecture Assistant |
| 66 | wx_rain_prob_execution_plan.md |
| 67 | wx_rain_prob_training_report.md |
| 68 | wx_rain_prob_business_validation.md |
| 78 | agent_monitoring_execution.md — Prototype Monitoring |
| 79 | agent_monitoring_test_suite.md — 20 cas test |
| 80 | ai_orchestrator.md — Orchestrateur central |
| 81 | ai_execution_flows.md — 30 scénarios |
| 82 | smartagri_ai_runtime.md — Architecture runtime |
| 83 | runtime_scenarios.md — 30 scénarios runtime |
| 84 | mlops_architecture.md |
| 85 | model_registry.md |
| 86 | feature_store.md |
| 87 | retraining_strategy.md |
| 88 | smartagri_demo_app.md — Architecture App Démo |

---
## 7. Pipelines de Production

### Entraînement
```
1. pd.read_parquet() → 2. Feature engineering (lags, rolling, sin/cos DOY)
3. Split GroupKFold/KFold (seed=42) → 4. LightGBM + XGBoost + CatBoost
5. Early stopping (50) → 6. Champion = meilleur mean CV → 7. Export CSV
```

### Inférence
```
1. Requête(lat,lon,date,culture) → 2. cell_id+power_cell_id
3. Features temps réel (NASA POWER+CHIRPS API) → 4. Feature engineering
5. model.predict() → 6. Confiance → 7. Garde-fous → 8. JSON
```

### Monitoring continu
```
1. Collecte /15min → 2. SoilNowcast J+1/2/3 → 3. Rain → 4. ET0
5. Score risque composite → 6. Alerte NORMAL/WATCH/WARNING/CRITICAL → 7. Notif
```

---
## 8. Prompts Système

### Assistant Parcellaire v2
```
Tu es un agronome numérique SmartAgri pour l'agriculture sénégalaise.
Capacités : SoilNowcast (R²=0.84), Rain (AUC=0.96), ET0 (R²=0.9997),
Yield (R²=0.95), Price (R²=0.90), CropCalendar (F1=0.980), NDVI, Anomalies.
Règles : citer modèle+confiance, pas de pesticides, escalader si confiance<0.40.
```

### Orchestrateur — Routage
```
humidite→SoilNowcast | pluie→Rain | et0→ET0 | rendement→Yield | prix→Price
calendrier→CropCalendar | ndvi→NDVI | anomalie→Anomaly+Monitoring | irrigation→Irrigation
```

---
## 9. Agents — Spécifications

### Monitoring Engine

| Seuil | Valeur |
|-------|--------|
| Flétrissement | soil<15% |
| Stress sévère | soil<20% |
| Excès | soil>80% |
| Saturation | soil>90% |
| Canicule | t_max>42°C |
| Gel Niayes | t_min<10°C |
| ET0 extrême | et0>7mm/j |
| Pluie extrême | rain_3d>50mm |

Niveaux : NORMAL(0-0.30), WATCH(0.30-0.55), WARNING(0.55-0.75), CRITICAL(0.75-1.00)
Pondérations : SoilNowcast 35%, Rain 25%, Anomaly 25%, ET0 15%

### Irrigation Engine

- FAO-56 single Kc, 17 cultures, ETc=Kc×ET0, dose=ETc-pluie_effective
- Efficiences : aspersion 75%, goutte-à-goutte 90%, gravitaire 60%

---
## 10. Architecture Système

```
                    UTILISATEUR (App / API)
                         │
                ┌────────▼────────┐
                │  ORCHESTRATOR   │
                └─┬─┬─┬─┬─┬─┬─┬─┘
  ┌───┬───┬───┬──┘ │ │ │ └──┬───┬───┬───┐
  A1  A2  A3  A4   A5 A6 A7 A8  A9  MON IRR
  SN  ET0 YLD RAIN PRC CC NDV ANO MKT  │   │
                         │              │   │
                  ┌──────▼──────┐       │   │
                  │ KNOWLEDGE   │◄──────┘   │
                  │ (527 chunks)│◄──────────┘
                  └──────┬──────┘
                         ▼
                  ┌──────────────┐
                  │ ASSISTANT v2 │
                  └──────────────┘
```

### Stack de reconstruction
```yaml
python: '>=3.10'
lightgbm: '>=4.0'
xgboost: '>=2.0'
catboost: '>=1.2'
scikit-learn: '>=1.3'
pandas: '>=2.0'
fastapi: '>=0.100'
torch: '>=2.0'
sentence-transformers: '>=2.2'
faiss-cpu: '>=1.7'
```

### Reconstruction : 5 étapes
```
1. pip install -r requirements.txt
2. Charger les 28 datasets Parquet
3. Réentraîner les 9 modèles (scripts dans docs 67-87)
4. Knowledge : corpus → chunks → embeddings → FAISS
5. docker-compose up
```

---
*Généré à partir des 27 tables de métriques mesurées du projet SmartAgri92.*