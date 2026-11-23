# SmartAgri92 — Fiches détaillées des 9 modèles Classe A

**Projet** : SmartAgri92 — PAS Challenge 2026
**Équipe** : Agri-Moderne 5.0
**Date** : 2026-11-16
**Statut** : Plan détaillé, aucun entraînement lancé

> Ce document détaille chacun des 9 modèles entraînables **immédiatement** à partir
> du bundle OCTOPUS-PACK-01 (30,4 M lignes, 28 datasets, 0 donnée synthétique).

---

## Récapitulatif rapide

| ID | Modèle | Domaine | Score | Coût est. |
|---|---|---|---:|---:|
| A1 | Soil Nowcast J+1/+2/+3 | Forecasting | 5.00 | < 2 $ |
| A2 | Soil Wetness Instantané | Forecasting | 4.15 | < 1 $ |
| A3 | Prévision ET0 J+1 | Forecasting | 3.45 | < 1 $ |
| A4 | Classif. Pluie Binaire (POWER) | Classification | 4.00 | < 1 $ |
| A5 | Classif. Saison Hydrologique | Classification | 3.60 | < 0.5 $ |
| A6 | Anomalies Pluviométriques | Anomaly Det. | 4.20 | < 0.5 $ |
| A7 | Anomalies Météo Multi-var. | Anomaly Det. | 3.65 | < 0.5 $ |
| A8 | RAG Documentation Agronomique | RAG | 4.15 | 0 $ |
| A9 | Assistant Conseil Parcellaire | Assistant IA | 4.15 | 0 $ |

---

## A1 — Soil Nowcast J+1/+2/+3

### Objectif
Prédire l'humidité racinaire du sol (`soil_wetness_root_pct`) à J+1, J+2 et J+3
pour chaque maille POWER du Sénégal. **Cible principale du challenge PAS.**

### Datasets exacts
| Dataset | Lignes | Colonnes | Rôle |
|---|---:|---:|---|
| `train.parquet` | 258,440 | 36 | Entraînement (features pré-assemblées) |
| `test.parquet` | 25,915 | 32 | Holdout à prédire (sans cible) |

### Cibles
| Colonne | Horizon | Description |
|---|---|---|
| `soil_wetness_root_pct` | J+0 | Humidité racinaire instantanée (cible proxy) |
| `y_plus_1d_pct` | J+1 | Humidité racinaire à 24 h |
| `y_plus_2d_pct` | J+2 | Humidité racinaire à 48 h |
| `y_plus_3d_pct` | J+3 | Humidité racinaire à 72 h |

### Features pressenties (34 colonnes)
**Identifiants** : `power_cell_id` (groupe spatial pseudonymisé HMAC), `ts` (timestamp)

**Météo (NASA POWER)** :
- `t_min_c`, `t_max_c`, `t_mean_c` — Températures min/max/moyenne (°C)
- `rh_mean_pct` — Humidité relative moyenne (%)
- `wind_2m_ms` — Vent à 2 m (m/s)
- `solar_rad_mj_m2` — Radiation solaire (MJ/m²)
- `pressure_hpa` — Pression atmosphérique (hPa)

**Précipitations** :
- `rain_mm` — Pluie NASA POWER (mm/jour)
- `rain_chirps_mm` — Pluie CHIRPS (mm/jour, satellite)
- `rain_nasa_sum_3d_mm`, `rain_nasa_sum_7d_mm`, `rain_nasa_sum_14d_mm` — Cumuls glissants NASA
- `rain_chirps_sum_3d_mm`, `rain_chirps_sum_7d_mm`, `rain_chirps_sum_14d_mm` — Cumuls glissants CHIRPS

**Évapotranspiration** :
- `et0_pm_mm` — ET0 Penman-Monteith (mm/jour)
- `et0_pm_mean_7d_mm` — Moyenne glissante 7j

**Calendrier** :
- `doy_sin`, `doy_cos` — Jour de l'année (encodage cyclique)

**Propriétés du sol (iSDAsoil, statiques)** :
- `sand_pct`, `clay_pct` — Texture (%)
- `soc_g_kg` — Carbone organique (g/kg)
- `ph_h2o` — pH
- `bulk_density_g_cm3` — Densité apparente
- `fc_ptf_pct` — Capacité au champ estimée (%)
- `wp_ptf_pct` — Point de flétrissement estimé (%)

**Occupation du sol (ESA WorldCover)** :
- `share_crop`, `share_tree`, `share_bare`, `share_built` — Fractions (0–1)

### Algorithmes candidats
| Algorithme | Justification | Priorité |
|---|---|---|
| **LightGBM** | Rapide, gère les features mixtes, excellent sur tabular | 🥇 |
| **XGBoost** | Robuste, bon baseline, régularisation L1/L2 | 🥈 |
| **CatBoost** | Natif catégoriel (power_cell_id si décodé) | 🥉 |
| **TabPFN** | Zero-shot, intéressant si < 10k lignes par fold | Expérimental |
| Stacking (LGB+XGB+CB) | Ensemble des 3 GBDT | Si temps restant |

### Validation
- **GroupKFold** (5 folds) sur `power_cell_id` — pas de fuite spatiale
- **Métriques** : RMSE (principal), MAE, R²
- **Attention** : le `power_cell_id` est pseudonymisé HMAC → pas de jointure directe avec les tables brutes

### Coût estimé
- ~258k lignes × 34 features × 3 cibles × 5 folds × 3 modèles ≈ **45 runs**
- Temps estimé : 15–30 min sur GPU managé OctOpus
- **Coût : < 2 $** (allowance challenge)

### Dépendances
- Aucune assemblage supplémentaire : `train.parquet` est prêt
- `test.parquet` pour la soumission (25 915 lignes sans cible)

### Risques
- ⚠️ Pseudonymisation HMAC empêche l'enrichissement par jointure spatiale
- ⚠️ Cible `soil_wetness_root_pct` est un proxy modélisé (NASA GEOS), pas une mesure terrain

---

## A2 — Soil Wetness Instantané

### Objectif
Prédire `soil_wetness_root_pct` (J+0) à partir des seules variables météo du jour.
Sert de **baseline** pour A1 et de modèle de remplissage quand les lags sont indisponibles.

### Datasets exacts
| Dataset | Lignes | Colonnes | Rôle |
|---|---:|---:|---|
| `train.parquet` | 258,440 | 36 | Même source que A1 |

### Features pressenties
Sous-ensemble de A1 **sans les lags temporels** :
- Météo jour : `t_min_c`, `t_max_c`, `t_mean_c`, `rh_mean_pct`, `wind_2m_ms`, `solar_rad_mj_m2`, `pressure_hpa`
- Pluie jour : `rain_mm`, `rain_chirps_mm`
- ET0 : `et0_pm_mm`
- Calendrier : `doy_sin`, `doy_cos`
- Sol statique : `sand_pct`, `clay_pct`, `soc_g_kg`, `ph_h2o`, `bulk_density_g_cm3`, `fc_ptf_pct`, `wp_ptf_pct`
- Occupation : `share_crop`, `share_tree`, `share_bare`, `share_built`

**Total : 23 features** (vs 34 pour A1)

### Cible
`soil_wetness_root_pct` uniquement (pas de J+1/+2/+3)

### Algorithmes candidats
| Algorithme | Justification |
|---|---|
| **LightGBM** | Baseline rapide |
| **Ridge Regression** | Interprétable, référence linéaire |
| **Random Forest** | Robuste, pas d'hyperparamètres critiques |

### Métriques
RMSE, MAE, R² — comparaison directe avec A1 pour mesurer la valeur ajoutée des lags.

### Coût estimé : < 1 $ | Dépendances : Aucune

---

## A3 — Prévision ET0 J+1

### Objectif
Prévoir l'évapotranspiration de référence (`et0_pm_mm`) à J+1 pour le calcul
des besoins en eau d'irrigation. Composante du bilan hydrique.

### Datasets exacts
| Dataset | Lignes | Colonnes | Rôle |
|---|---:|---:|---|
| `fao56_et0_national_daily.parquet` | 329,232 | 7 | ET0 calculée (Hargreaves + PM) |
| `nasa_power_national_daily.parquet` | 329,232 | 12 | Variables météo |

**Colonnes ET0** : `['power_cell_id', 'lat', 'lon', 'date', 'ra_mj_m2', 'et0_hargreaves_mm', 'et0_pm_mm']`
**Colonnes NASA POWER** : `['power_cell_id', 'lat', 'lon', 'date', 't_min_c', 't_max_c', 't_mean_c', 'rh_mean_pct', 'wind_2m_ms', 'solar_rad_mj_m2', 'pressure_hpa', 'rain_mm']`

### Jointure
`et0.power_cell_id = nasa.power_cell_id` + `et0.date = nasa.date`

### Features pressenties
- Météo J : toutes les colonnes NASA POWER (T, HR, vent, radiation, pression)
- ET0 lags : `et0_pm_mm` à J-1, J-3, J-7 (à construire)
- Ra (radiation extraterrestre, dans ET0) : `ra_mj_m2`
- Hargreaves : `et0_hargreaves_mm` comme feature complémentaire
- Calendrier : `doy_sin`, `doy_cos`

### Cible
`et0_pm_mm` décalée de +1 jour

### Algorithmes candidats
| Algorithme | Justification |
|---|---|
| **LightGBM** | Performance tabular, gestion des lags |
| **Ridge/Lasso** | Relation quasi-linéaire T↔ET0 (Hargreaves) |
| **Chronos-T5** | Foundation model forecasting (si temps) |

### Métriques : RMSE, MAE, R², MAPE
### Coût estimé : < 1 $ | Dépendances : Assemblage ET0 + NASA (jointure simple)

---

## A4 — Classification Pluie Binaire (POWER)

### Objectif
Classifier chaque jour en **pluie** (≥ 1 mm) vs **sec** (< 1 mm) à l'échelle POWER (0.5°).
Base du modèle `wx_rain_prob` objectif challenge.

### Datasets exacts
| Dataset | Lignes | Colonnes | Rôle |
|---|---:|---:|---|
| `nasa_power_national_daily.parquet` | 329,232 | 12 | Météo + pluie NASA |

### Cible à construire
`rain_binary = 1 si rain_mm >= 1.0, sinon 0`

### Features pressenties
- Température : `t2m_min`, `t2m_max`, `t2m_mean` (ou équivalents)
- Humidité : `rh2m`
- Vent : `ws2m`
- Radiation : `allsky_sfc_sw_dwn`
- Pression : `ps`
- Calendrier : mois, `doy_sin`, `doy_cos`
- Lags de pluie : `rain_mm` J-1, J-3, J-7

**Colonnes NASA exactes** : `['power_cell_id', 'lat', 'lon', 'date', 't_min_c', 't_max_c', 't_mean_c', 'rh_mean_pct', 'wind_2m_ms', 'solar_rad_mj_m2', 'pressure_hpa', 'rain_mm']`

### Algorithmes candidats
| Algorithme | Justification |
|---|---|
| **LightGBM (classif)** | Déséquilibre gérable (seuil + scale_pos_weight) |
| **XGBoost** | Robuste sur binaire déséquilibré |
| **Logistic Regression** | Baseline interprétable |

### Métriques : AUC-ROC, F1, Précision, Rappel, Brier Score
### Coût estimé : < 1 $ | Dépendances : Aucune assemblage (NASA seul)
### Risque : Déséquilibre saisonnier fort (saison sèche = majorité de jours secs)

---

## A5 — Classification Saison Hydrologique

### Objectif
Classifier chaque jour en **saison des pluies** vs **saison sèche** pour le Sénégal.
Feature utile pour tous les autres modèles.

### Datasets exacts
| Dataset | Lignes | Colonnes |
|---|---:|---:|
| `chirps_v3 (12 fichiers)` | ~28.9M | 4 |

**Colonnes** : `['date', 'cell_id', 'rain_mm', 'is_provisional']`

### Cible à construire
Règle climatologique : `saison_pluies = 1 si mois ∈ {6,7,8,9,10}, sinon 0`
(ou version ML : rolling_sum_30d > seuil)

### Features
- `rain_mm` brut + moyennes glissantes 7/14/30 jours
- Mois, `doy_sin`, `doy_cos`
- Cumul annuel courant

### Algorithmes candidats
| Algorithme | Justification |
|---|---|
| **Règle climatologique** | Baseline déterministe (pas de ML) |
| **LightGBM** | Capture les transitions floues |
| **Random Forest** | Robuste, interprétable |

### Métriques : Accuracy, F1, AUC (vs baseline règle)
### Coût : < 0.5 $ | Dépendances : Agrégation spatiale CHIRPS par `cell_id`

---

## A6 — Anomalies Pluviométriques

### Objectif
Détecter les jours de pluie anormalement élevée ou basse par rapport à la
climatologie locale. **Alertes sécheresse / inondation.**

### Datasets exacts
| Dataset | Lignes | Colonnes |
|---|---:|---:|
| `chirps_v3 (12 fichiers)` | ~28.9M | 4 |
| `senegal_grid_0p05.parquet` | 6,945 | 9 |

**Colonnes grille** : `['cell_id', 'row', 'col', 'lat', 'lon', 'region_adm1', 'power_cell_id', 'validation_zone', 'area_km2']`

### Méthode
1. Calculer la climatologie par `cell_id` × mois (moyenne + écart-type sur 2015-2024)
2. Z-score quotidien : `z = (rain_mm - μ_mois) / σ_mois`
3. Anomalie si |z| > 2.0 (configurable)
4. Validation : Isolation Forest en complément

### Features
- `rain_mm`, z-score, cumul glissant 7/14/30j
- Écart à la normale mensuelle
- Position spatiale : `lat`, `lon`, `region`

### Algorithmes candidats
| Algorithme | Justification |
|---|---|
| **Z-score climatologique** | Baseline statistique (pas de ML) |
| **Isolation Forest** | Non supervisé, détecte les outliers multidimensionnels |
| **Local Outlier Factor** | Détecte les anomalies spatiales locales |
| **DBSCAN** | Clustering spatial des anomalies |

### Métriques : Taux de faux positifs, précision@top-k anomalies, silhouette (clustering)
### Coût : < 0.5 $ (calcul statistique, pas de GPU)
### Dépendances : Grille spatiale pour la contextualisation régionale

---

## A7 — Anomalies Météo Multi-variables

### Objectif
Détecter les jours météo anormaux (vagues de chaleur, chutes de pression,
radiation extrême) combinant plusieurs variables NASA POWER.

### Datasets exacts
| Dataset | Lignes | Colonnes |
|---|---:|---:|
| `nasa_power_national_daily.parquet` | 329,232 | 12 |

**Colonnes** : `['power_cell_id', 'lat', 'lon', 'date', 't_min_c', 't_max_c', 't_mean_c', 'rh_mean_pct', 'wind_2m_ms', 'solar_rad_mj_m2', 'pressure_hpa', 'rain_mm']`

### Méthode
1. Normalisation Z par variable × mois × `power_cell_id`
2. Distance de Mahalanobis multi-variable
3. Isolation Forest sur le vecteur météo complet
4. Seuils adaptatifs par saison

### Features
- Toutes les variables NASA POWER normalisées
- Ratios : T_range/T_mean, radiation/ET0
- Lags 1-3 jours pour la persistance

### Algorithmes
| Algorithme | Justification |
|---|---|
| **Mahalanobis** | Baseline statistique multi-var |
| **Isolation Forest** | Standard anomaly detection |
| **Autoencoder** | Si pattern complexe (si GPU dispo) |

### Métriques : Taux de détection, faux positifs, rang des événements connus
### Coût : < 0.5 $ | Dépendances : Aucune

---

## A8 — RAG Documentation Agronomique

### Objectif
Indexer toute la documentation du bundle (7 documents Markdown, schémas YAML,
README) pour répondre aux questions agronomiques en langage naturel.

### Datasets exacts (documents)
| Document | Taille |
|---|---|
| `41_data_inventory.md` | 36 Ko |
| `42_octopus_onboarding_plan.md` | 25 Ko |
| `44_real_data_acquisition_plan.md` | 35 Ko |
| `45_real_data_lake_ready.md` | 9 Ko |
| `46_real_data_enrichment.md` | 6 Ko |
| `53_kit_data_model_mapping.md` | 16 Ko |
| `real_data_lake_README.md` | 4 Ko |
| Schémas YAML (sources, datasets, models) | ~140 Ko |

### Architecture
- **Indexation** : OctOpus `set_up_app_assistant` avec les fichiers du bundle
- **Retrieval** : recherche sémantique sur chunks de ~500 tokens
- **Génération** : réponse contextuelle avec citations de source

### Algorithmes
| Composant | Choix |
|---|---|
| **Chunking** | Markdown-aware, 500 tokens, overlap 50 |
| **Embedding** | Modèle OctOpus intégré |
| **Retrieval** | Top-5 chunks par cosine similarity |
| **LLM** | Modèle OctOpus intégré (pas de coût GPU) |

### Métriques : Pertinence (humaine), fidélité aux sources, taux de réponse
### Coût : 0 $ (inclus dans la plateforme OctOpus)
### Dépendances : Aucune donnée à assembler

---

## A9 — Assistant Conseil Parcellaire

### Objectif
Chatbot intégré dans une app OctOpus qui combine les prédictions des modèles
A1-A7 avec le RAG A8 pour fournir des conseils contextualisés par parcelle.

### Datasets / Sources
- Tous les modèles A1–A7 (prédictions en temps réel)
- RAG A8 (documentation)
- Tables de référence : grille, sols, WorldCover, Kc

### Architecture
- **App OctOpus** avec `octopus.ask()` pour le RAG
- **`octopus.predict()`** pour les modèles connectés
- Interface : sélection de parcelle → résumé automatique

### Algorithmes
Pas de ML propre — orchestration des modèles existants + RAG.

### Métriques : Satisfaction utilisateur, taux d'utilisation, pertinence des conseils
### Coût : 0 $ (app OctOpus gratuite)
### Dépendances : Au moins A1 + A8 entraînés/configurés

---

## Tableau de synthèse des dépendances

```
A8 (RAG) ────────────────────┐
A6 (Anomalies pluie) ───────┤
A7 (Anomalies météo) ───────┤
A4 (Pluie binaire) ─────────┤
A5 (Saison hydro) ──────────┼──→ A9 (Assistant Parcellaire)
A3 (ET0 J+1) ───────────────┤
A2 (Soil Wetness) ──────────┤
A1 (Soil Nowcast) ──────────┘
```

**Chemin critique** : A1 (indépendant, prioritaire) → A8 (indépendant) → A9 (dépend de tous)
