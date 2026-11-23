# 57_first_octopus_projects.md — Les 5 premiers projets OctOpus SmartAgri92

**Projet** : SmartAgri92 — PAS Challenge 2026
**Équipe** : Agri-Moderne 5.0
**Date** : 2026-11-16
**Statut** : Plan détaillé, aucun entraînement lancé

> Ce document décrit les 5 projets OctOpus à créer sur la plateforme,
> leur contenu, leur ordre de déploiement et la roadmap associée.

---

## Vue d'ensemble

| # | Projet OctOpus | Modèles inclus | Priorité | Prérequis |
|---|---|---|---|---|
| 1 | SmartAgri SoilNowcast LAB | A1, A2 | 🔴 Critique | Aucun |
| 2 | SmartAgri Rain Intelligence | A4, A5, A6 | 🟠 Haute | Aucun |
| 3 | SmartAgri Anomaly Detector | A6, A7, (B3) | 🟡 Moyenne | Projet 2 partiel |
| 4 | SmartAgri Knowledge RAG | A8 | 🟡 Moyenne | Aucun |
| 5 | SmartAgri Assistant Parcellaire | A9 | 🟢 Finale | Projets 1-4 |

---

## Projet 1 — SmartAgri SoilNowcast LAB

### Objectif
Prédire l'humidité racinaire du sol à J+1, J+2 et J+3 pour les 76 mailles POWER
du Sénégal. **Cible principale du challenge PAS.**

### Données
| Source | Fichier | Usage |
|---|---|---|
| Train | `train.parquet` (258,440 × 36) | Entraînement GroupKFold |
| Test | `test.parquet` (25,915 × 32) | Soumission (holdout sans cible) |

### Modèles
| ID | Nom | Cible | Algo principal |
|---|---|---|---|
| A1 | Soil Nowcast J+1/+2/+3 | `y_plus_1d_pct`, `y_plus_2d_pct`, `y_plus_3d_pct` | LightGBM + XGBoost + CatBoost |
| A2 | Soil Wetness Instantané | `soil_wetness_root_pct` | LightGBM (baseline) |

### Architecture cible
```
train.parquet
    │
    ├── Feature Engineering
    │   ├── Lags supplémentaires (si pertinent)
    │   ├── Interactions sol×météo
    │   └── Ratios (rain/et0, fc-wp range)
    │
    ├── Modèle A2 (baseline sans lags)
    │   └── LightGBM → RMSE baseline
    │
    └── Modèle A1 (complet)
        ├── LightGBM (5-fold GroupKFold)
        ├── XGBoost (5-fold GroupKFold)
        ├── CatBoost (5-fold GroupKFold)
        └── Stacking → best.pt → submission.csv
```

### Métriques de succès
| Métrique | Objectif | Justification |
|---|---|---|
| RMSE (y_plus_1d) | < 5 % | Précision à 24 h |
| RMSE (y_plus_3d) | < 8 % | Dégradation acceptée à 72 h |
| R² | > 0.85 | Variance expliquée |
| Leaderboard PAS | Top 10 | Compétitivité challenge |

### Roadmap
| Étape | Durée | Coût |
|---|---|---|
| EDA + feature engineering | 1 h | 0 $ |
| Entraînement LightGBM baseline | 15 min | 0.5 $ |
| Entraînement 3 GBDT + tuning Optuna | 30 min | 1 $ |
| Stacking + soumission | 15 min | 0.5 $ |
| **Total** | **~2 h** | **< 2 $** |

---

## Projet 2 — SmartAgri Rain Intelligence

### Objectif
Système de classification et prévision des précipitations : pluie binaire,
intensité, probabilité, saison hydrologique.

### Données
| Source | Fichier | Lignes | Usage |
|---|---|---|---|
| NASA POWER | `nasa_power_national_daily.parquet` | 329,232 | Variables météo quotidiennes |
| CHIRPS | `chirps_v3_*.parquet` (×12) | ~28.9M | Pluie satellite grille fine |
| ET0 | `fao56_et0_national_daily.parquet` | 329,232 | Évapotranspiration |
| Grille | `senegal_grid_0p05.parquet` | 6,945 | Référentiel spatial |

### Modèles
| ID | Nom | Cible | Algo |
|---|---|---|---|
| A4 | Pluie binaire POWER | `rain_binary` (≥1 mm) | LightGBM classif |
| A5 | Saison hydrologique | `saison_pluies` | LightGBM + règle clim |
| A3 | Prévision ET0 J+1 | `et0_pm_mm` décalé +1j | LightGBM régression |

### Architecture cible
```
NASA POWER ─────────────┐
                        ├── Jointure date + power_cell_id
ET0 ────────────────────┤
                        │
                        ├── A4: Classif pluie binaire
                        ├── A3: Prévision ET0 J+1
                        │
CHIRPS (agrégé POWER) ──┤
                        └── A5: Classif saison hydro
```

### Jointures nécessaires
| Table gauche | Table droite | Clé |
|---|---|---|
| `nasa_power` | `fao56_et0` | `power_cell_id` + `date` |
| `chirps` | `senegal_grid` | `cell_id` |
| `chirps` (agrégé) | `power_cells` | `power_cell_id` (via grid) |

### Métriques
- A4 : AUC > 0.85, F1 > 0.70
- A5 : Accuracy > 0.95 (tâche facile), F1 > 0.90
- A3 : RMSE < 1.0 mm, R² > 0.80

### Roadmap
| Étape | Durée | Coût |
|---|---|---|
| Assemblage NASA + ET0 | 30 min | 0 $ |
| A4 classification pluie | 20 min | 0.5 $ |
| A5 saison hydro | 10 min | 0.2 $ |
| A3 prévision ET0 | 20 min | 0.5 $ |
| **Total** | **~1.5 h** | **< 1.5 $** |

---

## Projet 3 — SmartAgri Anomaly Detector

### Objectif
Système de détection d'anomalies agro-climatiques : pluviométrie extrême,
vagues de chaleur, sécheresses, anomalies multi-variables.

### Données
| Source | Fichier | Lignes | Usage |
|---|---|---|---|
| CHIRPS | `chirps_v3_*.parquet` (×12) | ~28.9M | Anomalies pluie |
| NASA POWER | `nasa_power_national_daily.parquet` | 329,232 | Anomalies météo |
| Grille | `senegal_grid_0p05.parquet` | 6,945 | Contexte spatial |
| Prix (optionnel) | `wfp_senegal_food_prices.parquet` | 55,283 | Anomalies prix |

### Modèles
| ID | Nom | Type | Algo |
|---|---|---|---|
| A6 | Anomalies pluviométriques | Non supervisé | Z-score + Isolation Forest |
| A7 | Anomalies météo multi-var | Non supervisé | Mahalanobis + Isolation Forest |
| (B3) | Anomalies prix alimentaires | Non supervisé | Z-score + LOF (si assemblé) |

### Architecture cible
```
CHIRPS ──── Climatologie par cell_id × mois ──── Z-score ──── A6
                                                              │
NASA POWER ── Normalisation multi-var ── Mahalanobis ──── A7  ├── Tableau d'alertes
                                                              │
WFP Prices ── Z-score par marché × produit ── LOF ──── (B3) ─┘
```

### Métriques
- Taux de faux positifs < 5 %
- Cohérence spatiale des anomalies (clustering)
- Validation croisée temporelle (événements connus)

### Roadmap
| Étape | Durée | Coût |
|---|---|---|
| Climatologie CHIRPS | 30 min | 0 $ |
| A6 Z-score + IF | 20 min | 0.2 $ |
| A7 Mahalanobis + IF | 20 min | 0.2 $ |
| Tableau d'alertes | 30 min | 0 $ |
| **Total** | **~2 h** | **< 0.5 $** |

---

## Projet 4 — SmartAgri Knowledge RAG

### Objectif
Base de connaissance agronomique interrogeable en langage naturel, construite
à partir de toute la documentation technique du bundle.

### Données (documents)
| Document | Contenu | Taille |
|---|---|---|
| 7 documents Markdown | Inventaire, plans, enrichissement, schémas | ~130 Ko |
| 3 catalogues YAML | Sources, datasets, modèles | ~140 Ko |
| 11 schémas domaine | Contrats de colonnes par domaine | ~12 Ko |
| `56_real_ai_portfolio.md` | Portefeuille IA complet | 31 Ko |

**Total** : ~313 Ko de texte technique indexable

### Architecture cible
```
Documents Markdown/YAML
    │
    ├── Chunking (500 tokens, overlap 50)
    ├── Embedding (modèle OctOpus intégré)
    ├── Index vectoriel
    │
    └── App OctOpus
        ├── octopus.ask(question, {collections, history})
        ├── Interface chat
        └── Sources citées dans chaque réponse
```

### Implémentation OctOpus
1. `set_up_app_assistant` avec les `file_ids` des documents du bundle
2. `build_app` : interface chat avec historique
3. Optionnel : `put_project_tables_in_app` pour les tables de référence

### Exemples de questions attendues
- « Quelles sont les sources de données pour la pluie au Sénégal ? »
- « Quelle est la résolution spatiale de la grille CHIRPS ? »
- « Quels modèles peuvent être entraînés avec les données actuelles ? »
- « Quelles sont les zones de validation spatiale ? »

### Métriques
- Pertinence : > 80 % des réponses correctes
- Fidélité : 0 hallucination sur les données du bundle
- Couverture : toutes les questions de documentation couvertes

### Roadmap
| Étape | Durée | Coût |
|---|---|---|
| Indexation des documents | 10 min | 0 $ |
| Construction de l'app | 20 min | 0 $ |
| Test et ajustement | 20 min | 0 $ |
| **Total** | **~1 h** | **0 $** |

---

## Projet 5 — SmartAgri Assistant Parcellaire

### Objectif
Application finale intégrant tous les modèles et le RAG dans une interface
utilisateur cohérente pour le conseil agricole parcellaire.

### Données / Sources
- **Modèles** : A1 (Soil Nowcast), A4 (Pluie), A6/A7 (Anomalies)
- **RAG** : Projet 4 (Knowledge)
- **Tables de référence** : grille, sols, WorldCover, Kc

### Architecture cible
```
┌─────────────────────────────────────────────┐
│           SmartAgri Assistant                │
│                                             │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Sélect. │  │ Tableau  │  │   Chat    │  │
│  │ Parcelle│  │ de bord  │  │   RAG     │  │
│  │ (carte) │  │ prévisions│  │ agricole  │  │
│  └────┬────┘  └────┬─────┘  └─────┬─────┘  │
│       │            │              │         │
│  ┌────▼────────────▼──────────────▼─────┐   │
│  │        Orchestrateur OctOpus         │   │
│  │  octopus.predict() + octopus.ask()   │   │
│  └──────────────────────────────────────┘   │
│       │            │              │         │
│  ┌────▼────┐ ┌─────▼─────┐ ┌─────▼─────┐   │
│  │   A1    │ │  A4/A6/A7 │ │    A8     │   │
│  │ Soil NW │ │ Pluie/Ano │ │   RAG     │   │
│  └─────────┘ └───────────┘ └───────────┘   │
└─────────────────────────────────────────────┘
```

### Pages de l'application
| Page | Contenu | Modèle(s) |
|---|---|---|
| Accueil | Carte Sénégal + sélection parcelle | — |
| Prévisions Sol | Graphe J+1/+2/+3, humidité racinaire | A1, A2 |
| Météo & Pluie | Probabilité pluie, saison, ET0 | A3, A4, A5 |
| Alertes | Anomalies en cours, historique | A6, A7 |
| Conseils | Chat RAG + recommandations | A8, A9 |
| Données | Explorer les datasets bruts | Tables |

### Implémentation OctOpus
1. `build_app` : structure multi-pages
2. `connect_model_to_app` : brancher A1, A4, A6
3. `set_up_app_assistant` : brancher le RAG A8
4. `put_project_tables_in_app` : tables de référence

### Roadmap
| Étape | Durée | Coût |
|---|---|---|
| Build app structure | 30 min | 0 $ |
| Connexion modèles | 15 min | 0 $ |
| Connexion RAG | 15 min | 0 $ |
| Tests et polish | 30 min | 0 $ |
| **Total** | **~1.5 h** | **0 $** |

### Dépendances
- Projets 1-4 doivent être au moins partiellement complétés
- Au minimum A1 + A8 pour une démo fonctionnelle

---

## Roadmap globale SmartAgri92

```
Semaine 1 (S47-2026)
├── Jour 1-2 : Projet 1 — SoilNowcast LAB (A1, A2)      ─── < 2 $
├── Jour 2-3 : Projet 2 — Rain Intelligence (A3, A4, A5) ─── < 1.5 $
└── Jour 3   : Projet 3 — Anomaly Detector (A6, A7)      ─── < 0.5 $

Semaine 1-2
├── Jour 4   : Projet 4 — Knowledge RAG (A8)             ─── 0 $
└── Jour 4-5 : Projet 5 — Assistant Parcellaire (A9)     ─── 0 $

Total estimé : < 5 $ sur 59,70 $ disponibles
```

### Budget prévisionnel

| Projet | Coût estimé | % allowance |
|---|---:|---:|
| 1. SoilNowcast LAB | 2.00 $ | 3.4 % |
| 2. Rain Intelligence | 1.50 $ | 2.5 % |
| 3. Anomaly Detector | 0.50 $ | 0.8 % |
| 4. Knowledge RAG | 0.00 $ | 0.0 % |
| 5. Assistant Parcellaire | 0.00 $ | 0.0 % |
| **Total** | **4.00 $** | **6.7 %** |
| **Marge restante** | **55.70 $** | **93.3 %** |

> La marge de 93 % permet l'itération, le tuning Optuna avancé,
> et l'expérimentation avec des modèles plus lourds si nécessaire.

---

## Critères de succès globaux

| Critère | Objectif | Mesure |
|---|---|---|
| Soumission PAS | ≥ 1 soumission valide | submission.csv acceptée |
| RMSE Soil Nowcast | Top 10 leaderboard | Classement PAS |
| Modèles entraînés | ≥ 5 modèles fonctionnels | Runs OctOpus complétés |
| Application | 1 app déployée | URL publique |
| RAG | 1 assistant fonctionnel | Réponses vérifiées |
| Budget | < 10 $ consommés | Dashboard OctOpus |
| Documentation | Complète | 56_ + 57_ + rapports |
