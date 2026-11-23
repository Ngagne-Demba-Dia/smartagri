# 56_real_ai_portfolio.md
# Portefeuille IA Complet — SmartAgri92
## Agri-Moderne 5.0 · PAS Challenge 2026

**Date** : 2026-11-16
**Auteur** : OctOpus (Mouhamadou Diop, Moustapha Diallo, équipe Agri-Moderne 5.0)
**Données** : 28 datasets · 30,4 M lignes · OCTOPUS-PACK-01
**Périmètre** : Sénégal national · grille 0,05° (6 945 cellules) · 2015–2026

> **Aucun modèle entraîné.** Ce document est un inventaire décisionnel.
> Il recense les modèles IA réalisables, les classe par maturité et
> recommande les 5 premiers projets OctOpus à créer.

---

## Table des matières

1. [Synthèse exécutive](#1-synthèse-exécutive)
2. [Inventaire des données exploitées](#2-inventaire-des-données-exploitées)
3. [Classement A / B / C des modèles](#3-classement-a--b--c)
4. [Fiches détaillées par modèle](#4-fiches-détaillées)
   - 4.1 Forecasting
   - 4.2 Classification
   - 4.3 Anomaly Detection
   - 4.4 Computer Vision
   - 4.5 NLP
   - 4.6 RAG
   - 4.7 Agents IA
   - 4.8 Assistants IA
5. [Top 5 projets OctOpus à créer](#5-top-5-projets-octopus)
6. [Matrice de priorisation](#6-matrice-de-priorisation)
7. [Risques transversaux et mitigations](#7-risques-transversaux)
8. [Feuille de route recommandée](#8-feuille-de-route)

---

## 1. Synthèse exécutive

Le bundle SmartAgri92 contient **28 datasets** couvrant 7 domaines :
météorologie (NASA POWER), pluviométrie haute résolution (CHIRPS v3),
sols (iSDAsoil), occupation du sol (ESA WorldCover), végétation (Sentinel-2 NDVI),
prix alimentaires (WFP) et statistiques agricoles (FAOSTAT).

À partir de ces données, **21 modèles IA** sont identifiés :

| Catégorie | Modèles | Classe A | Classe B | Classe C |
|---|---:|---:|---:|---:|
| **Forecasting** | 5 | 3 | 1 | 1 |
| **Classification** | 4 | 2 | 1 | 1 |
| **Anomaly Detection** | 3 | 2 | 1 | 0 |
| **Computer Vision** | 2 | 0 | 1 | 1 |
| **NLP** | 1 | 0 | 0 | 1 |
| **RAG** | 2 | 1 | 1 | 0 |
| **Agents IA** | 2 | 0 | 1 | 1 |
| **Assistants IA** | 2 | 1 | 1 | 0 |
| **Total** | **21** | **9** | **7** | **5** |

**Classe A** (entraînable immédiatement) : données dans le bundle, feature store
assemblé ou assemblable sans source externe supplémentaire.
**Classe B** (après kits complémentaires) : nécessite un assemblage, un dataset externe
identifié ou des labels à créer.
**Classe C** (bloqué) : données absentes, infrastructure requise non disponible,
ou dépendance à un pipeline non encore construit.

---

## 2. Inventaire des données exploitées

### 2.1 Résumé du Feature Store logique (5 niveaux)

| Niveau | Contenu | Lignes | Grain |
|---|---|---:|---|
| 1 — Socle spatial | grille 0,05°, mailles POWER, sols, landcover | 34 801 | cellule ou maille |
| 2 — Séries quotidiennes | CHIRPS, NASA POWER, ET0, soil wetness | 29,9 M | (espace, date) |
| 3 — Mensuel/occasionnel | NDVI S2, catalogue scènes | 46 920 | (cellule, mois) |
| 4 — Économique | prix WFP, marchés, FAOSTAT, Kc FAO56 | 57 218 | (marché/culture, date) |
| 5 — Cibles compétition | train + test pré-assemblés | 284 355 | (pcid_hmac, ts) |

### 2.2 Point d'attention : pseudonymisation

Les `power_cell_id` de `train.parquet` et `test.parquet` sont des hachés HMAC-SHA256
(sel `local-dev-2026-11`). Les **36 colonnes sont déjà pré-assemblées** : on n'a pas besoin
de rejoindre les tables brutes pour `soil_nowcast`. En revanche, construire `wx_rain_prob`
et `anomaly_ml` sur les données brutes implique de travailler avec les `power_cell_id`
en clair, puis de prédire sur le test pseudonymisé via les features pré-assemblées.

---

## 3. Classement A / B / C

### 🟢 Classe A — Entraînables immédiatement (9 modèles)

| # | Modèle | Domaine | Données prêtes |
|--:|---|---|---|
| A1 | **Soil Nowcast J+1/+2/+3** | Forecasting | train.parquet (258 440 × 36) |
| A2 | **Soil Wetness Instantané** | Forecasting | train.parquet (cible: soil_wetness_root_pct) |
| A3 | **Prévision ET0 J+1** | Forecasting | fao56_et0 + nasa_power (329 232 × 19 jointes) |
| A4 | **Classification pluie binaire (POWER)** | Classification | nasa_power_daily (rain_mm > seuil) |
| A5 | **Classification saison hydrologique** | Classification | CHIRPS + calendrier (saison sèche/humide/transition) |
| A6 | **Anomalies pluviométriques** | Anomaly Detection | CHIRPS 2015-2026 (z-scores, percentiles) |
| A7 | **Anomalies météo multi-variables** | Anomaly Detection | NASA POWER (T, RH, vent, pression, radiation) |
| A8 | **RAG Documentation agronomique** | RAG | FAO56 Kc + FAOSTAT + inventaire OctOpus |
| A9 | **Assistant Conseil Parcellaire** | Assistant IA | Toutes tables statiques + méta-données |

### 🟡 Classe B — Après kits complémentaires (7 modèles)

| # | Modèle | Domaine | Kit requis |
|--:|---|---|---|
| B1 | **wx_rain_prob (grille fine)** | Classification | Assemblage CHIRPS × grid × POWER × sols |
| B2 | **Prévision rendement régional** | Forecasting | FAOSTAT + assemblage météo agrégé régional |
| B3 | **Anomalies prix alimentaires** | Anomaly Detection | WFP prix + saisonnalité par marché |
| B4 | **NDVI prédiction mensuelle** | Computer Vision / TS | S2 NDVI + météo + sols (assemblage spatial) |
| B5 | **RAG Alertes agro-climatiques** | RAG | Pipeline anomaly_ml produit + templates alertes |
| B6 | **Agent Monitoring parcellaire** | Agent IA | Pipelines soil + rain + anomaly opérationnels |
| B7 | **Assistant Marché agricole** | Assistant IA | WFP prix + FAOSTAT + modèle de prévision prix |

### 🔴 Classe C — Bloqués (5 modèles)

| # | Modèle | Domaine | Blocage |
|--:|---|---|---|
| C1 | **Segmentation cultures (S2)** | Computer Vision | Pas d'images S2 brutes dans le bundle (URLs seulement) |
| C2 | **NLP Extraction bulletins météo** | NLP | Aucun corpus texte (bulletins ANACIM non fournis) |
| C3 | **Prévision prix par marché** | Forecasting | Séries WFP trop irrégulières (pas de fréquence fixe) |
| C4 | **Agent Pilotage irrigation** | Agent IA | Pas de données terrain (capteurs, compteurs, parcelles) |
| C5 | **Détection maladies foliaires** | Computer Vision | Aucune image de feuille/plant dans le bundle |

---

## 4. Fiches détaillées par modèle

---

### 4.1 FORECASTING

---

#### A1 · Soil Nowcast J+1 / J+2 / J+3

| Champ | Détail |
|---|---|
| **ID** | `FORECAST-01` |
| **Classe** | 🟢 A — Entraînable immédiatement |
| **Objectif** | Prédire l'humidité racinaire du sol (%) à J+1, J+2, J+3 |
| **Cibles** | `y_plus_1d_pct`, `y_plus_2d_pct`, `y_plus_3d_pct` |
| **Données** | `train.parquet` (258 440 lignes, 36 cols), `test.parquet` (25 915 lignes, 32 cols) |
| **Features** | 31 colonnes pré-assemblées : météo instantanée (7), précipitations (2), ET0 (1), cumuls glissants (7), saisonnalité (2), sols (7), landcover (4) |
| **Grain** | (power_cell_id pseudonymisé, date quotidienne) |
| **Période** | Train: 2015-01-14 → 2024-12-31, Test: 2025-01-01 → 2025-12-31 |
| **Groupes** | 71 mailles POWER pseudonymisées |
| **Valeur métier** | 🔴 **Critique** — calendrier d'irrigation, semis, récolte ; alertes sécheresse précoce |
| **Difficulté** | ⭐⭐ Moyenne — données prêtes, mais multi-horizon et autocorrélation spatiale |
| **Risque** | Nulls CHIRPS (3-5 %), pseudonymisation empêche enrichissement externe |
| **Métriques** | RMSE (primaire), MAE, R², RMSE par horizon (J+1, J+2, J+3 séparément) |
| **Validation** | GroupKFold sur `power_cell_id` (pas de fuite spatiale) ; holdout temporel 2024 |
| **Algorithmes** | LightGBM, XGBoost, CatBoost, TabPFN (si ≤10k lignes par fold), MLP |
| **Baseline** | Persistance (y_t = soil_wetness_root_pct du jour courant) |
| **Entraîn. estimé** | ~5 min (LightGBM, 258k lignes, CPU) |
| **Priorité compétition** | ★★★★★ C'est la cible principale du challenge |

---

#### A2 · Soil Wetness Instantané

| Champ | Détail |
|---|---|
| **ID** | `FORECAST-02` |
| **Classe** | 🟢 A |
| **Objectif** | Estimer `soil_wetness_root_pct` du jour courant à partir de la météo et des sols |
| **Données** | `train.parquet` — cible : `soil_wetness_root_pct` (mean=46.5, σ=20.3, range [10, 100]) |
| **Valeur métier** | Diagnostic temps réel de la capacité hydrique — complément du nowcast |
| **Difficulté** | ⭐ Faible — même données que A1, cible unique |
| **Risque** | Faible — pas de décalage temporel |
| **Métriques** | RMSE, MAE, R² |
| **Algorithmes** | LightGBM, XGBoost |
| **Priorité** | ★★★★☆ Utile comme feature intermédiaire pour A1 |

---

#### A3 · Prévision ET0 J+1

| Champ | Détail |
|---|---|
| **ID** | `FORECAST-03` |
| **Classe** | 🟢 A |
| **Objectif** | Prévoir l'évapotranspiration de référence Penman-Monteith du lendemain |
| **Données** | `fao56_et0_national_daily` (329 232 lignes) JOIN `nasa_power_national_daily` sur (power_cell_id, date) |
| **Features** | T_min/max/mean, RH, vent, radiation solaire, pression, ra_mj_m2, doy_sin/cos |
| **Cible** | `et0_pm_mm` (J+1) — construire le décalage temporel |
| **Valeur métier** | Pilotage irrigation : savoir combien d'eau la plante demandera demain |
| **Difficulté** | ⭐⭐ Moyenne — jointure + lag engineering |
| **Risque** | 76 nulls sur et0_pm_mm (0,02 %) — négligeable |
| **Métriques** | RMSE (mm), MAE, R² |
| **Algorithmes** | LightGBM, XGBoost, Linear Regression (baseline physique) |
| **Priorité** | ★★★☆☆ |

---

#### B2 · Prévision Rendement Régional

| Champ | Détail |
|---|---|
| **ID** | `FORECAST-04` |
| **Classe** | 🟡 B |
| **Objectif** | Prévoir le rendement (t/ha) par culture et par année |
| **Données** | `faostat_senegal_crops_1961_2024` (956 lignes, 15 cultures × 55 ans) |
| **Kit requis** | Agrégation météo nationale annuelle (cumul pluie, GDD, stress jours) depuis CHIRPS + POWER |
| **Features à construire** | cumul_pluie_saison, nb_jours_secs_consecutifs, GDD_saison, NDVI_pic, surface_ha |
| **Cible** | `yield_t_ha` |
| **Valeur métier** | Sécurité alimentaire, planification des importations |
| **Difficulté** | ⭐⭐⭐ Élevée — peu de lignes (956), signal faible, multi-cultures |
| **Risque** | Overfitting probable (< 60 obs par culture), données nationales uniquement |
| **Métriques** | RMSE, MAPE, R² ; leave-one-year-out CV |
| **Algorithmes** | Ridge Regression, ElasticNet, Random Forest (peu de lignes) |
| **Priorité** | ★★☆☆☆ |

---

#### C3 · Prévision Prix par Marché

| Champ | Détail |
|---|---|
| **ID** | `FORECAST-05` |
| **Classe** | 🔴 C |
| **Objectif** | Prévoir les prix alimentaires par marché à horizon 1–3 mois |
| **Données** | `wfp_senegal_food_prices` (55 283 lignes, 79 marchés, 2000–2026) |
| **Blocage** | Séries temporelles très irrégulières (pas de fréquence fixe, trous fréquents). 195 nulls sur price_fcfa_kg. Pas de date de relevé régulière. Nécessite un nettoyage lourd + imputation + resampling mensuel par (marché, crop). |
| **Valeur métier** | 🔴 Haute — alertes crises alimentaires |
| **Difficulté** | ⭐⭐⭐⭐ Très élevée |
| **Risque** | Données trop irrégulières pour un forecasting fiable sans retraitement majeur |
| **Métriques** | MAPE, RMSE sur prix mensuels reconstitués |
| **Algorithmes** | Prophet, NBEATS (si resamplé), LightGBM avec lags |
| **Priorité** | ★☆☆☆☆ (débloquable si resampling mensuel validé) |

---

### 4.2 CLASSIFICATION

---

#### A4 · Classification Pluie Binaire (maille POWER)

| Champ | Détail |
|---|---|
| **ID** | `CLASSIF-01` |
| **Classe** | 🟢 A |
| **Objectif** | Prédire P(pluie > 1 mm demain) par maille POWER |
| **Données** | `nasa_power_national_daily` (329 232 lignes, 76 mailles) — cible à créer : `rain_binary = (rain_mm > 1.0)` |
| **Features** | T_min/max/mean, RH, vent, radiation, pression, rain_mm lags (J-1, J-3, J-7), doy_sin/cos |
| **Valeur métier** | Alerte pluie pour les agriculteurs — décision semis/récolte/traitement |
| **Difficulté** | ⭐⭐ Moyenne — feature engineering (lags) + déséquilibre classes (Sahel = peu de jours de pluie) |
| **Risque** | Déséquilibre fort en saison sèche (~90% pas de pluie) — pondérer ou SMOTE |
| **Métriques** | AUC-ROC (primaire), F1, Precision, Recall, Brier Score |
| **Validation** | GroupKFold sur power_cell_id + holdout temporel 2024 |
| **Algorithmes** | LightGBM, XGBoost, Logistic Regression (baseline), CatBoost |
| **Priorité** | ★★★★☆ — objectif `wx_rain_prob` du challenge |

---

#### A5 · Classification Saison Hydrologique

| Champ | Détail |
|---|---|
| **ID** | `CLASSIF-02` |
| **Classe** | 🟢 A |
| **Objectif** | Classer chaque jour dans `saison_seche` / `transition` / `hivernage` par cellule |
| **Données** | CHIRPS consolidé (29 M lignes) + calendrier |
| **Features** | rain_mm, cumul_30j, nb_jours_pluie_30j, doy, lat |
| **Cible** | Label dérivé par seuil (cumul 30j > 50 mm = hivernage, etc.) |
| **Valeur métier** | Segmentation temporelle pour tous les autres modèles |
| **Difficulté** | ⭐ Faible — règles connues, classification supervisée simple |
| **Risque** | Faible |
| **Métriques** | Accuracy, F1-macro |
| **Algorithmes** | Random Forest, règles expertes (baseline) |
| **Priorité** | ★★★☆☆ |

---

#### B1 · wx_rain_prob (grille fine 0,05°)

| Champ | Détail |
|---|---|
| **ID** | `CLASSIF-03` |
| **Classe** | 🟡 B |
| **Objectif** | P(pluie > seuil) à résolution 5,5 km |
| **Données** | CHIRPS (cell_id, date) × nasa_power (power_cell_id, date) via `senegal_grid` + isdasoil + worldcover |
| **Kit requis** | (1) Consolider les 12 CHIRPS en une table unique, (2) joindre via senegal_grid → power_cell_id → tables POWER, (3) feature engineering (lags, cumuls), (4) joindre sols et landcover par cell_id |
| **Cible** | `rain_binary` (CHIRPS rain_mm > seuil) |
| **Valeur métier** | 🔴 Critique — même objectif que A4 mais à résolution 10× plus fine |
| **Difficulté** | ⭐⭐⭐ Élevée — volume (29 M lignes brutes), jointures multi-niveaux |
| **Risque** | Mémoire (29 M × ~30 features), nulls CHIRPS, résolution POWER plus grossière |
| **Métriques** | AUC-ROC, F1, Brier Score |
| **Algorithmes** | LightGBM, XGBoost, TabNet |
| **Priorité** | ★★★★★ — objectif challenge, version haute résolution |

---

#### C1 · Segmentation Cultures (Sentinel-2)

| Champ | Détail |
|---|---|
| **ID** | `CLASSIF-04` |
| **Classe** | 🔴 C |
| **Objectif** | Cartographier les types de cultures à partir d'images Sentinel-2 |
| **Données** | `deafrica_s2_national_scene_catalog` (20 722 scènes) — **mais seulement les URLs** (b04_href, b08_href, scl_href), pas les images elles-mêmes |
| **Blocage** | Il faudrait télécharger ~21 000 scènes S2 (centaines de Go), constituer un jeu de labels de cultures, et disposer d'un GPU. Budget et infra insuffisants. |
| **Valeur métier** | Très haute — cartographie des parcelles |
| **Difficulté** | ⭐⭐⭐⭐⭐ |
| **Priorité** | ★☆☆☆☆ |

---

### 4.3 ANOMALY DETECTION

---

#### A6 · Anomalies Pluviométriques

| Champ | Détail |
|---|---|
| **ID** | `ANOMALY-01` |
| **Classe** | 🟢 A |
| **Objectif** | Détecter les événements pluviométriques extrêmes (sécheresses flash, pluies torrentielles) |
| **Données** | CHIRPS 2015-2026, 6 945 cellules × ~4 000 jours |
| **Features** | rain_mm, cumul_3j/7j/14j/30j, jours_secs_consecutifs, z-score_saisonnier, percentile_vs_historique |
| **Méthode** | Z-scores dynamiques (par cellule × jour_de_année sur 2015-2024), puis flagging 2025-2026 |
| **Types détectés** | Sécheresse flash (cumul_30j < P5), pluie extrême (rain > P99), séquence sèche anormale |
| **Valeur métier** | 🔴 Critique — alertes précoces inondation/sécheresse |
| **Difficulté** | ⭐⭐ Moyenne — calcul statistique + seuillage |
| **Risque** | Faible — méthode robuste, pas de ML complexe |
| **Métriques** | Precision@recall sur événements historiques connus (à valider manuellement) |
| **Algorithmes** | Z-scores saisonniers (baseline), Isolation Forest, DBSCAN temporel |
| **Priorité** | ★★★★☆ — objectif `anomaly_ml` du challenge |

---

#### A7 · Anomalies Météo Multi-variables

| Champ | Détail |
|---|---|
| **ID** | `ANOMALY-02` |
| **Classe** | 🟢 A |
| **Objectif** | Identifier les combinaisons météo anormales (stress thermique + vent + radiation) |
| **Données** | `nasa_power_national_daily` (329 232 lignes, 8 variables météo) |
| **Features** | t_max, t_min, amplitude_thermique, rh_mean, wind, solar_rad, pressure + z-scores saisonniers |
| **Valeur métier** | Alertes stress cultures (canicule, gel relatif, vent violent) |
| **Difficulté** | ⭐⭐ Moyenne |
| **Risque** | Faible |
| **Métriques** | Taux d'anomalies, silhouette score (clustering), validation experte |
| **Algorithmes** | Isolation Forest, One-Class SVM, autoencodeur (si >100k lignes par cellule) |
| **Priorité** | ★★★☆☆ |

---

#### B3 · Anomalies Prix Alimentaires

| Champ | Détail |
|---|---|
| **ID** | `ANOMALY-03` |
| **Classe** | 🟡 B |
| **Objectif** | Détecter les hausses anormales de prix sur les marchés sénégalais |
| **Données** | `wfp_senegal_food_prices` (55 283 relevés, 79 marchés) |
| **Kit requis** | (1) Resampling mensuel par (market_id, crop), (2) calcul saisonnalité par produit, (3) z-scores mensuels |
| **Valeur métier** | Haute — alerte crise alimentaire, sécurité nutritionnelle |
| **Difficulté** | ⭐⭐⭐ Élevée — séries irrégulières |
| **Risque** | Moyen — 195 nulls prix, fréquence non uniforme |
| **Métriques** | Precision sur événements de crise connus (ex. 2008, 2022) |
| **Algorithmes** | Z-scores mensuels, STL decomposition, Isolation Forest |
| **Priorité** | ★★★☆☆ |

---

### 4.4 COMPUTER VISION

---

#### B4 · Prédiction NDVI Mensuel

| Champ | Détail |
|---|---|
| **ID** | `CV-01` |
| **Classe** | 🟡 B |
| **Objectif** | Prévoir le NDVI moyen du mois suivant par cellule |
| **Données** | `s2_ndvi_national_grid_monthly_2025` (26 198 lignes, 6 818 cellules, 2025 uniquement) |
| **Kit requis** | (1) Historique NDVI pré-2025 (non fourni, à calculer depuis S2 ou à chercher sur DE Africa), (2) jointure avec météo et sols |
| **Features** | ndvi_mean, ndvi_std lags, rain cumuls, et0, sols, saison |
| **Valeur métier** | Suivi végétation, détection stress hydrique, estimation biomasse |
| **Difficulté** | ⭐⭐⭐ Élevée — peu d'historique (2025 seul), signal bruité (nuages) |
| **Risque** | Moyen — 127 cellules absentes vs grille complète |
| **Métriques** | RMSE, MAE, R² |
| **Algorithmes** | LightGBM, LSTM (si séries suffisantes), Prophet par cellule |
| **Priorité** | ★★☆☆☆ |

---

#### C5 · Détection Maladies Foliaires

| Champ | Détail |
|---|---|
| **ID** | `CV-02` |
| **Classe** | 🔴 C |
| **Objectif** | Classifier les maladies des feuilles depuis photos terrain |
| **Blocage** | Aucune image de plante/feuille dans le bundle. Nécessite un dataset type PlantVillage ou une collecte terrain. |
| **Valeur métier** | Haute — diagnostic phytosanitaire mobile |
| **Difficulté** | ⭐⭐⭐ |
| **Priorité** | ★☆☆☆☆ |

---

### 4.5 NLP

---

#### C2 · Extraction Bulletins Météo ANACIM

| Champ | Détail |
|---|---|
| **ID** | `NLP-01` |
| **Classe** | 🔴 C |
| **Objectif** | Parser les bulletins météo textuels de l'ANACIM pour en extraire des prévisions structurées |
| **Blocage** | Aucun corpus texte dans le bundle. Les bulletins ANACIM ne sont pas fournis. |
| **Valeur métier** | Moyenne — enrichissement contextuel pour les alertes |
| **Difficulté** | ⭐⭐⭐ |
| **Si débloqué** | NER avec spaCy/CamemBERT, extraction de : zones, dates, phénomènes, intensités |
| **Priorité** | ★☆☆☆☆ |

---

### 4.6 RAG (Retrieval-Augmented Generation)

---

#### A8 · RAG Documentation Agronomique

| Champ | Détail |
|---|---|
| **ID** | `RAG-01` |
| **Classe** | 🟢 A |
| **Objectif** | Répondre aux questions sur les cultures sénégalaises, coefficients Kc, calendriers culturaux |
| **Données** | `fao56_crop_coefficients_daily` (900 lignes, 5 cultures × 180 jours), `faostat_senegal_crops` (956 lignes, 15 cultures), `octopus_datasets_inventory` (métadonnées bundle) |
| **Architecture** | Index vectoriel sur les tables + documentation FAO56 → LLM en retrieval |
| **Valeur métier** | Moyenne — aide à la décision pour techniciens agricoles |
| **Difficulté** | ⭐ Faible — tables structurées, pas de gros corpus |
| **Risque** | Qualité des réponses dépend du LLM ; hallucinations possibles sur les chiffres |
| **Métriques** | Pertinence des réponses (évaluation humaine), taux de réponses sourcées |
| **Algorithmes** | Embedding (sentence-transformers) + recherche vectorielle + LLM |
| **Priorité** | ★★★☆☆ |

---

#### B5 · RAG Alertes Agro-climatiques

| Champ | Détail |
|---|---|
| **ID** | `RAG-02` |
| **Classe** | 🟡 B |
| **Objectif** | Générer des bulletins d'alerte en langage naturel à partir des anomalies détectées |
| **Kit requis** | Pipeline `anomaly_ml` opérationnel (A6 + A7) + templates d'alertes FAO/ANACIM |
| **Architecture** | Anomalies détectées → contexte (cellule, date, type, sévérité) → RAG → texte d'alerte |
| **Valeur métier** | 🔴 Haute — communication directe vers les agriculteurs |
| **Difficulté** | ⭐⭐ Moyenne |
| **Risque** | Dépendance au pipeline anomaly_ml |
| **Priorité** | ★★★☆☆ |

---

### 4.7 AGENTS IA

---

#### B6 · Agent Monitoring Parcellaire

| Champ | Détail |
|---|---|
| **ID** | `AGENT-01` |
| **Classe** | 🟡 B |
| **Objectif** | Agent autonome qui surveille quotidiennement l'état hydrique, météo et végétal d'un ensemble de parcelles et déclenche des alertes |
| **Kit requis** | Modèles A1 (soil nowcast), A4 (rain prob), A6 (anomalies) opérationnels + API de notification |
| **Architecture** | Orchestrateur (LangChain/CrewAI) → appelle les modèles → évalue les seuils → génère alertes → notifie |
| **Valeur métier** | 🔴 Très haute — pilotage automatisé |
| **Difficulté** | ⭐⭐⭐ Élevée — intégration multi-modèles |
| **Risque** | Fiabilité de la chaîne (un modèle défaillant = fausse alerte) |
| **Métriques** | Taux de fausses alertes, latence, couverture des événements |
| **Priorité** | ★★★★☆ (après validation des modèles unitaires) |

---

#### C4 · Agent Pilotage Irrigation

| Champ | Détail |
|---|---|
| **ID** | `AGENT-02` |
| **Classe** | 🔴 C |
| **Objectif** | Recommander le volume et le moment d'irrigation par parcelle |
| **Blocage** | Pas de données terrain (débit, compteurs, type d'irrigation, parcelles géolocalisées). Les données bundle sont à l'échelle de la grille 5,5 km, pas de la parcelle. |
| **Valeur métier** | Très haute |
| **Difficulté** | ⭐⭐⭐⭐⭐ |
| **Priorité** | ★☆☆☆☆ |

---

### 4.8 ASSISTANTS IA

---

#### A9 · Assistant Conseil Parcellaire

| Champ | Détail |
|---|---|
| **ID** | `ASSIST-01` |
| **Classe** | 🟢 A |
| **Objectif** | Chatbot qui répond aux questions d'un agriculteur sur sa zone : « Quel temps fait-il à Kaolack ? », « Quand semer l'arachide ? », « Mon sol est-il assez humide ? » |
| **Données** | Toutes les tables statiques (grille, sols, landcover, Kc, FAOSTAT) + dernières données météo/sol |
| **Architecture** | App OctOpus avec `octopus.ask()` sur les tables du projet |
| **Valeur métier** | Haute — interface utilisateur finale, vulgarisation des données |
| **Difficulté** | ⭐ Faible — infrastructure OctOpus existante |
| **Risque** | Qualité des réponses, couverture des questions hors périmètre |
| **Métriques** | Satisfaction utilisateur, taux de réponses pertinentes |
| **Priorité** | ★★★☆☆ |

---

#### B7 · Assistant Marché Agricole

| Champ | Détail |
|---|---|
| **ID** | `ASSIST-02` |
| **Classe** | 🟡 B |
| **Objectif** | Chatbot spécialisé sur les prix et la disponibilité des produits agricoles |
| **Kit requis** | Tables WFP nettoyées + modèle anomalie prix (B3) + prévision tendance |
| **Données** | `wfp_food_prices`, `wfp_markets`, `faostat` |
| **Architecture** | RAG sur tables prix + modèle tendance → réponses contextualisées |
| **Valeur métier** | Haute — aide aux commerçants et coopératives |
| **Difficulté** | ⭐⭐ |
| **Priorité** | ★★☆☆☆ |

---

## 5. Top 5 Projets OctOpus à Créer

Voici les **5 premiers projets** à créer dans OctOpus, ordonnés par impact et faisabilité :

---

### 🥇 Projet 1 : `SmartAgri92-SoilNowcast`

| Champ | Détail |
|---|---|
| **Modèles** | A1 (Soil Nowcast J+1/+2/+3) + A2 (instantané) |
| **Données** | `train.parquet` → charger directement |
| **Cible** | `y_plus_1d_pct` (puis `y_plus_2d_pct`, `y_plus_3d_pct`) |
| **Tâche OctOpus** | Régression, GroupKFold sur power_cell_id |
| **Algorithmes** | LightGBM, XGBoost, CatBoost |
| **Livrable** | Modèle entraîné + submission test.parquet + dashboard résultats |
| **Coût estimé** | < 2 $ de crédits compute |
| **Justification** | C'est la **cible principale** de la compétition PAS 2026. Données prêtes, aucun assemblage requis. |

---

### 🥈 Projet 2 : `SmartAgri92-RainProb`

| Champ | Détail |
|---|---|
| **Modèles** | A4 (rain prob POWER) → puis B1 (grille fine) |
| **Données** | Phase 1 : `nasa_power_national_daily` ; Phase 2 : CHIRPS consolidé + jointures |
| **Cible** | `rain_binary` = (rain_mm > 1.0) |
| **Tâche** | Classification binaire, GroupKFold |
| **Algorithmes** | LightGBM, XGBoost (avec class_weight balanced) |
| **Livrable** | Modèle + carte de probabilité de pluie + dashboard |
| **Coût estimé** | Phase 1 : < 1 $ ; Phase 2 : < 5 $ (volume CHIRPS) |
| **Justification** | Objectif `wx_rain_prob` du challenge. Phase 1 rapide sur POWER, phase 2 monte en résolution. |

---

### 🥉 Projet 3 : `SmartAgri92-AnomalyDetector`

| Champ | Détail |
|---|---|
| **Modèles** | A6 (anomalies pluie) + A7 (anomalies météo) |
| **Données** | CHIRPS consolidé + NASA POWER |
| **Méthode** | Z-scores saisonniers (baseline) + Isolation Forest |
| **Livrable** | Table d'anomalies datées/géolocalisées + dashboard carte des alertes |
| **Coût estimé** | < 2 $ |
| **Justification** | Objectif `anomaly_ml` du challenge. Deux modèles complémentaires (pluie + multi-météo). |

---

### 4️⃣ Projet 4 : `SmartAgri92-AgriAssistant`

| Champ | Détail |
|---|---|
| **Modèles** | A8 (RAG agronomique) + A9 (assistant parcellaire) |
| **Données** | Tables statiques (sols, landcover, Kc FAO56, FAOSTAT) + résultats des projets 1-3 |
| **Architecture** | App OctOpus avec `octopus.ask()` alimenté par les tables du projet |
| **Livrable** | Application chatbot déployée |
| **Coût estimé** | < 1 $ |
| **Justification** | Interface utilisateur qui valorise tous les modèles. Démontre l'impact métier pour le jury PAS. |

---

### 5️⃣ Projet 5 : `SmartAgri92-Dashboard`

| Champ | Détail |
|---|---|
| **Contenu** | Dashboard interactif unifié : carte Sénégal + courbes météo + état des sols + alertes anomalies + prix marchés |
| **Données** | Toutes les tables du Feature Store |
| **Sections** | (1) Carte grille avec NDVI/pluie/sol, (2) Courbes temporelles par cellule, (3) Tableau alertes, (4) Prix marchés, (5) Rendements historiques |
| **Livrable** | Dashboard OctOpus publiable |
| **Coût estimé** | 0 $ (pas de compute ML) |
| **Justification** | Vitrine du projet pour le jury. Synthétise visuellement toute la donnée. |

---

## 6. Matrice de priorisation

| Modèle | Impact métier | Faisabilité | Données prêtes | Score |
|---|:---:|:---:|:---:|:---:|
| A1 Soil Nowcast | 🔴 5 | 🟢 5 | ✅ Oui | **25** |
| B1 wx_rain_prob fine | 🔴 5 | 🟡 3 | ⚠️ Assemblage | **15** |
| A4 rain prob POWER | 🟠 4 | 🟢 5 | ✅ Presque | **20** |
| A6 Anomalies pluie | 🟠 4 | 🟢 4 | ✅ Oui | **16** |
| A7 Anomalies météo | 🟡 3 | 🟢 4 | ✅ Oui | **12** |
| A8 RAG agro | 🟡 3 | 🟢 5 | ✅ Oui | **15** |
| A9 Assistant | 🟡 3 | 🟢 5 | ✅ Oui | **15** |
| B6 Agent monitoring | 🔴 5 | 🟠 2 | ⚠️ Dépendant | **10** |
| A2 Soil instantané | 🟡 3 | 🟢 5 | ✅ Oui | **15** |
| A3 ET0 J+1 | 🟡 3 | 🟢 4 | ✅ Presque | **12** |
| A5 Saison hydro | 🟢 2 | 🟢 5 | ✅ Oui | **10** |

---

## 7. Risques transversaux et mitigations

| Risque | Sévérité | Probabilité | Mitigation |
|---|:---:|:---:|---|
| **Pseudonymisation HMAC** empêche enrichissement du train/test | 🔴 Haute | Certaine | Accepter les 36 features pré-assemblées ; construire wx_rain_prob et anomaly_ml sur les données brutes (hors holdout) |
| **Nulls CHIRPS** (3-5 % dans train) | 🟡 Moyenne | Certaine | Imputation médiane glissante 7j par cellule ; ou drop lignes (< 5 %) |
| **Volume CHIRPS** (29 M lignes) | 🟡 Moyenne | Probable | Traitement par année, échantillonnage spatial, ou agrégation power_cell |
| **Déséquilibre classes** (pluie rare en saison sèche) | 🟡 Moyenne | Certaine | class_weight balanced, sous-échantillonnage majoritaire, seuil optimisé |
| **Overfitting rendements** (956 lignes FAOSTAT) | 🟠 Haute | Probable | Modèles simples (Ridge), leave-one-year-out, régularisation forte |
| **Trou CHIRPS 2023** (décembre manquant) | 🟢 Faible | Certaine | Exclure décembre 2023 ou imputer depuis POWER rain_mm |
| **Budget challenge** ($59.76 restants) | 🟡 Moyenne | Possible | Prioriser A1 (< 2 $), puis A4 (< 1 $), puis A6 (< 2 $) |
| **Pas d'images satellite brutes** | 🟡 Moyenne | Certaine | Reporter C1 ; utiliser NDVI pré-calculé pour les besoins végétation |

---

## 8. Feuille de route recommandée

### Semaine 1 (immédiat)

| Jour | Action | Projet |
|---|---|---|
| J1 | Entraîner soil_nowcast (A1) sur train.parquet | SmartAgri92-SoilNowcast |
| J1 | Soumettre prédictions test.parquet | Compétition |
| J2 | Construire rain_binary, entraîner A4 sur POWER | SmartAgri92-RainProb |
| J3 | Calculer z-scores CHIRPS, lancer A6 | SmartAgri92-AnomalyDetector |
| J4 | Dashboard unifié | SmartAgri92-Dashboard |
| J5 | App assistant (A9) | SmartAgri92-AgriAssistant |

### Semaine 2 (consolidation)

| Action | Détail |
|---|---|
| Assembler CHIRPS consolidé | 12 fichiers → table unique |
| Construire vue wx_rain_prob fine (B1) | Jointures multi-niveaux |
| Anomalies multi-variables (A7) | NASA POWER |
| RAG alertes (B5) | Si anomaly_ml opérationnel |
| Itérer soil_nowcast | Feature engineering avancé, stacking |

### Semaine 3+ (extension)

| Action | Condition |
|---|---|
| Agent monitoring (B6) | Modèles A1+A4+A6 validés |
| Rendements (B2) | Si agrégation météo nationale prête |
| Anomalies prix (B3) | Si resampling WFP validé |
| NDVI prédiction (B4) | Si historique NDVI disponible |

---

## Annexe : Couverture par domaine IA

| Domaine | Modèles identifiés | Classe A | Classe B | Classe C |
|---|---:|---:|---:|---:|
| Forecasting | 5 | 3 | 1 | 1 |
| Classification | 4 | 2 | 1 | 1 |
| Anomaly Detection | 3 | 2 | 1 | 0 |
| Computer Vision | 2 | 0 | 1 | 1 |
| NLP | 1 | 0 | 0 | 1 |
| RAG | 2 | 1 | 1 | 0 |
| Agents IA | 2 | 0 | 1 | 1 |
| Assistants IA | 2 | 1 | 1 | 0 |
| **TOTAL** | **21** | **9** | **7** | **5** |

---

*Document généré par OctOpus pour l'équipe Agri-Moderne 5.0 — PAS Challenge 2026.*
*Aucun modèle n'a été entraîné. Ce portefeuille est un plan décisionnel basé sur l'analyse effective des 28 datasets (30,4 M lignes).*