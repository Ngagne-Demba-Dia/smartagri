# 58 — Plan Détaillé : Projet A1 Soil Nowcast

> **SmartAgri92 — Produit commercial, pas seulement un challenge**
> 
> Ce document décrit l'intégralité du projet A1, de l'entraînement
> dans OctOpus jusqu'à la reproduction autonome dans SmartAgri.
> Aucun entraînement n'est lancé par ce plan.

---
## 1. Vue d'ensemble

| Attribut | Valeur |
|---|---|
| **Objectif** | Prédire l'humidité racinaire du sol à J+1, J+2, J+3 |
| **Dataset train** | `train.parquet` — 258,440 lignes × 36 colonnes |
| **Dataset test** | `test.parquet` — 25,915 lignes × 32 colonnes (sans cible) |
| **Cibles** | `y_plus_1d_pct`, `y_plus_2d_pct`, `y_plus_3d_pct` |
| **Cible auxiliaire** | `soil_wetness_root_pct` (état courant, sert de feature lag) |
| **Groupes spatiaux** | `power_cell_id` — 71 groupes train, 71 groupes test |
| **Groupes communs** | 71 sur 71 (100%) |
| **Période train** | 2015-01-14 → 2024-12-31 |
| **Période test** | 2025-01-01 → 2025-12-31 |
| **Chevauchement temporel** | Non |
| **Pseudonymisation** | HMAC-SHA256 sur `power_cell_id` |
| **Coût estimé** | < 2 $ (budget disponible : 59,70 $) |

---
## 2. Features — Inventaire complet colonne par colonne

**30 features** disponibles, organisées en 7 groupes thématiques.

### 🌡️ Météo (température)

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `t_min_c` | 10.43 | 34.03 | 22.33 | 0 | 0.104 |
| `t_max_c` | 18.36 | 47.46 | 34.70 | 0 | -0.508 |
| `t_mean_c` | 16.09 | 40.01 | 28.04 | 0 | -0.275 |

### 💧 Humidité & Pression

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `rh_mean_pct` | 4.32 | 97.68 | 52.48 | 0 | 0.668 |
| `pressure_hpa` | 974.30 | 1018.40 | 1004.37 | 0 | -0.184 |

### 🌬️ Vent & Radiation

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `wind_2m_ms` | 0.26 | 8.92 | 2.62 | 0 | -0.576 |
| `solar_rad_mj_m2` | 1.75 | 29.68 | 21.22 | 0 | -0.302 |

### 🌧️ Pluie (NASA POWER)

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `rain_mm` | 0.00 | 611.79 | 2.61 | 0 | 0.334 |
| `rain_nasa_sum_3d_mm` | 0.00 | 717.42 | 7.83 | 0 | 0.450 |
| `rain_nasa_sum_7d_mm` | 0.00 | 1061.06 | 18.28 | 0 | 0.547 |
| `rain_nasa_sum_14d_mm` | 0.00 | 1122.07 | 36.55 | 0 | 0.625 |

### 🌧️ Pluie (CHIRPS)

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `rain_chirps_mm` | 0.00 | 99.44 | 1.96 | 8662 | 0.362 |
| `rain_chirps_sum_3d_mm` | 0.00 | 184.21 | 5.88 | 9230 | 0.490 |
| `rain_chirps_sum_7d_mm` | 0.00 | 284.91 | 13.69 | 10366 | 0.568 |
| `rain_chirps_sum_14d_mm` | 0.00 | 496.06 | 27.25 | 12354 | 0.623 |

### 🌱 Évapotranspiration

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `et0_pm_mm` | 0.75 | 15.80 | 6.34 | 0 | -0.649 |
| `et0_pm_mean_7d_mm` | 2.50 | 13.31 | 6.34 | 0 | -0.688 |

### 📅 Encodage temporel

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `doy_sin` | -1.00 | 1.00 | -0.00 | 0 | -0.543 |
| `doy_cos` | -1.00 | 1.00 | -0.00 | 0 | -0.070 |

### 🏜️ Propriétés sol

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `sand_pct` | 45.55 | 80.79 | 59.63 | 0 | -0.514 |
| `clay_pct` | 10.22 | 32.08 | 20.76 | 0 | 0.451 |
| `soc_g_kg` | 2.15 | 65.70 | 6.45 | 0 | 0.324 |
| `ph_h2o` | 5.59 | 6.77 | 6.14 | 0 | -0.603 |
| `bulk_density_g_cm3` | 1.07 | 1.62 | 1.47 | 0 | -0.450 |

### 💦 Capacité hydrique

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `fc_ptf_pct` | 11.74 | 31.02 | 22.61 | 0 | 0.511 |
| `wp_ptf_pct` | 6.09 | 19.66 | 13.00 | 0 | 0.479 |

### 🗺️ Occupation du sol

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `share_crop` | 0.00 | 0.86 | 0.15 | 0 | -0.113 |
| `share_tree` | 0.00 | 0.85 | 0.16 | 0 | 0.498 |
| `share_bare` | 0.00 | 0.09 | 0.01 | 0 | -0.127 |
| `share_built` | 0.00 | 0.31 | 0.01 | 0 | -0.092 |

### 🎯 État courant (feature lag)

| Colonne | Min | Max | Moyenne | Nulls | Corr. y+1d |
|---|---|---|---|---|---|
| `soil_wetness_root_pct` | 10.00 | 100.00 | 46.53 | 0 | feature lag |

### 📊 Top 15 features par corrélation absolue avec `y_plus_1d_pct`

| Rang | Feature | |r| | Signe |
|---|---|---|---|
| 1 | `et0_pm_mean_7d_mm` | 0.6884 | − |
| 2 | `rh_mean_pct` | 0.6676 | + |
| 3 | `et0_pm_mm` | 0.6488 | − |
| 4 | `rain_nasa_sum_14d_mm` | 0.6252 | + |
| 5 | `rain_chirps_sum_14d_mm` | 0.6233 | + |
| 6 | `ph_h2o` | 0.6026 | − |
| 7 | `wind_2m_ms` | 0.5761 | − |
| 8 | `rain_chirps_sum_7d_mm` | 0.5681 | + |
| 9 | `rain_nasa_sum_7d_mm` | 0.5470 | + |
| 10 | `doy_sin` | 0.5430 | − |
| 11 | `sand_pct` | 0.5141 | − |
| 12 | `fc_ptf_pct` | 0.5109 | + |
| 13 | `t_max_c` | 0.5075 | − |
| 14 | `share_tree` | 0.4985 | + |
| 15 | `rain_chirps_sum_3d_mm` | 0.4902 | + |

---
## 3. Cibles — Statistiques et corrélations

| Cible | Min | Max | Moyenne | Std | Médiane |
|---|---|---|---|---|---|
| `soil_wetness_root_pct` | 10.00 | 100.00 | 46.53 | 20.30 | 42.00 |
| `y_plus_1d_pct` | 10.00 | 100.00 | 46.53 | 20.30 | 42.00 |
| `y_plus_2d_pct` | 10.00 | 100.00 | 46.53 | 20.30 | 42.00 |
| `y_plus_3d_pct` | 10.00 | 100.00 | 46.53 | 20.30 | 42.00 |

### Matrice de corrélation inter-cibles

| | swrp | y+1d | y+2d | y+3d |
|---|---|---|---|---|
| `soil_wetness_root_pct` | 1.000 | 0.999 | 0.997 | 0.995 |
| `y_plus_1d_pct` | 0.999 | 1.000 | 0.999 | 0.997 |
| `y_plus_2d_pct` | 0.997 | 0.999 | 1.000 | 0.999 |
| `y_plus_3d_pct` | 0.995 | 0.997 | 0.999 | 1.000 |

> **Observation** : les cibles sont fortement corrélées (auto-régression
> du sol). `soil_wetness_root_pct` → `y_plus_1d_pct` : r = 0.999.
> C'est la feature la plus prédictive, ce qui est physiquement logique.

---
## 4. Algorithmes candidats

### 4.1 Stratégie multi-modèles

Pour un produit SmartAgri **commercialisable**, on entraîne **3 familles**
et on conserve le meilleur par cible + un ensemble (stacking) :

| # | Algorithme | Justification | Hyperparamètres clés | Export |
|---|---|---|---|---|
| 1 | **LightGBM** | Rapide, excellent sur tabular, natif catégoriel, export ONNX | `n_estimators=2000`, `learning_rate=0.03`, `num_leaves=63`, `min_child_samples=50`, `reg_alpha=0.1`, `reg_lambda=1.0`, early stopping 100 | ONNX, pickle, txt |
| 2 | **XGBoost** | Robuste, GPU possible, bon sur données denses | `n_estimators=2000`, `learning_rate=0.03`, `max_depth=8`, `subsample=0.8`, `colsample_bytree=0.8`, early stopping 100 | ONNX, pickle, JSON |
| 3 | **CatBoost** | Gestion native des catégoriels, ordered boosting | `iterations=2000`, `learning_rate=0.03`, `depth=8`, `l2_leaf_reg=3`, early stopping 100 | ONNX, cbm, JSON |
| 4 | **Stacking (Ridge)** | Combine les 3 via méta-apprenant linéaire | `alpha` via CV | pickle |

### 4.2 Pourquoi pas de deep learning ?

- 258k lignes × 32 features = **domaine tabular classique** → GBDT domine.
- Exportabilité : GBDT → ONNX en une ligne, réseau de neurones → beaucoup plus complexe.
- Interprétabilité : SHAP sur GBDT est mature et rapide.
- Coût : GBDT s'entraîne en minutes sur CPU, DL nécessite GPU.
- **Exception** : si un Transformer tabular (TabPFN, FT-Transformer) est
  disponible, il peut être testé comme 4e candidat. Mais le stacking GBDT
  reste le favori pour un produit embarqué.

---
## 5. Stratégie de validation

### 5.1 GroupKFold sur `power_cell_id`

- **71 groupes** dans train (pseudonymisés HMAC).
- **71 groupes** dans test.
- **71 groupes communs** train ∩ test = 100%.

> ⚠️ **Tous les groupes test sont dans train.** Le challenge ne teste PAS
> la généralisation spatiale (pas de mailles inconnues). GroupKFold reste
> utile pour estimer la variance inter-mailles, mais le risque de fuite
> spatiale est faible.

### 5.2 Protocole de validation

```
┌──────────────────────────────────────────────┐
│         train.parquet (258 440 lignes)        │
│                                               │
│  ┌─── GroupKFold k=5 sur power_cell_id ───┐  │
│  │                                         │  │
│  │  Fold 1: groups {A,B,C,D} → train      │  │
│  │          groups {E}       → val OOF     │  │
│  │  Fold 2: groups {A,B,C,E} → train      │  │
│  │          groups {D}       → val OOF     │  │
│  │  ... (5 folds)                          │  │
│  │                                         │  │
│  │  → Prédictions OOF sur 100% du train    │  │
│  │  → Métriques par fold + agrégées        │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─── Modèle final (retrain all) ─────────┐  │
│  │  100% train → fit → predict test.parquet│  │
│  └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 5.3 Métriques

| Métrique | Usage | Formule |
|---|---|---|
| **RMSE** | Métrique principale (challenge) | √(Σ(ŷ−y)²/n) |
| **MAE** | Robuste aux outliers | Σ|ŷ−y|/n |
| **R²** | Variance expliquée | 1 − SS_res/SS_tot |
| **RMSE par horizon** | J+1 vs J+2 vs J+3 | RMSE séparé par cible |
| **RMSE par groupe** | Variance inter-mailles | RMSE par `power_cell_id` |
| **Résidus vs temps** | Détection de drift | Plot résidus(ts) |

---
## 6. Pipeline de preprocessing (reproductible)

### 6.1 Étapes

```python
# ── Pipeline SmartAgri A1 Soil Nowcast ──
# Reproductible hors OctOpus

FEATURE_COLS = [
    "bulk_density_g_cm3",
    "clay_pct",
    "doy_cos",
    "doy_sin",
    "et0_pm_mean_7d_mm",
    "et0_pm_mm",
    "fc_ptf_pct",
    "ph_h2o",
    "pressure_hpa",
    "rain_chirps_mm",
    "rain_chirps_sum_14d_mm",
    "rain_chirps_sum_3d_mm",
    "rain_chirps_sum_7d_mm",
    "rain_mm",
    "rain_nasa_sum_14d_mm",
    "rain_nasa_sum_3d_mm",
    "rain_nasa_sum_7d_mm",
    "rh_mean_pct",
    "sand_pct",
    "share_bare",
    "share_built",
    "share_crop",
    "share_tree",
    "soc_g_kg",
    "solar_rad_mj_m2",
    "t_max_c",
    "t_mean_c",
    "t_min_c",
    "wind_2m_ms",
    "wp_ptf_pct"
]

TARGET_COLS = ['y_plus_1d_pct', 'y_plus_2d_pct', 'y_plus_3d_pct']
GROUP_COL = 'power_cell_id'

# Étape 1 : Chargement
import pandas as pd
train = pd.read_parquet('train.parquet')
test  = pd.read_parquet('test.parquet')

# Étape 2 : Pas de preprocessing nécessaire
# - Pas de nulls dans les features
# - Pas de catégoriels (power_cell_id = groupe, pas feature)
# - Features déjà normalisées (encodage doy_sin/cos, %)
# - Pas de scaling nécessaire pour GBDT

# Étape 3 : Extraction X, y, groups
X_train = train[FEATURE_COLS]
y_train = {t: train[t] for t in TARGET_COLS}
groups  = train[GROUP_COL]
X_test  = test[FEATURE_COLS]

# Étape 4 : GroupKFold + entraînement (voir section 5)
```

### 6.2 Observations critiques

- ⚠️ **4 features avec nulls** : ['rain_chirps_mm', 'rain_chirps_sum_3d_mm', 'rain_chirps_sum_7d_mm', 'rain_chirps_sum_14d_mm']
- ✅ **32 features numériques** pures → pas d'encodage catégoriel.
- ✅ **`power_cell_id` est un groupe**, pas une feature (jamais dans X).
- ✅ **`ts` est un timestamp**, utilisé pour la validation temporelle, pas comme feature
  (la saisonnalité est déjà encodée dans `doy_sin`, `doy_cos`).
- ⚠️ **`soil_wetness_root_pct`** est l'état J+0 du sol. C'est la feature la plus
  prédictive (r = 0.000 avec y+1d) mais elle est
  **absente du test** → c'est une cible auxiliaire, pas une feature d'inférence.
  → **ABSENTE du test** : NE PAS utiliser comme feature. Le modèle doit prédire SANS.

---
## 7. Procédure d'export complète — OctOpus → SmartAgri

### 7.1 Philosophie

Le PAS Challenge valide le modèle. SmartAgri le **commercialise**.
Tout artefact produit dans OctOpus doit être **reproductible localement**
sans dépendance à la plateforme.

### 7.2 Artefacts à récupérer

| # | Artefact | Format | Usage SmartAgri | Taille estimée |
|---|---|---|---|---|
| 1 | **Poids du modèle** | `.pkl` (pickle) | Inférence Python | ~5 Mo × 3 cibles × 3 algos |
| 2 | **Modèle ONNX** | `.onnx` | Inférence multi-langage (C++, Java, Rust) | ~2 Mo × 3 cibles |
| 3 | **Feature importance** | `.csv` + `.json` | Explicabilité, monitoring, debug | < 100 Ko |
| 4 | **Hyperparamètres** | `.json` | Reproductibilité, ré-entraînement | < 10 Ko |
| 5 | **Métriques CV** | `.json` + `.csv` | Baseline, monitoring drift | < 50 Ko |
| 6 | **Prédictions OOF** | `.parquet` | Analyse d'erreurs, calibration | ~5 Mo |
| 7 | **Pipeline config** | `pipeline.yaml` | Recette complète reproductible | < 5 Ko |
| 8 | **data.yaml** | `.yaml` | Contrat de données (colonnes, types, ranges) | < 5 Ko |
| 9 | **Submission** | `submission.csv` | Soumission challenge | ~1 Mo |
| 10 | **SHAP values** | `.parquet` | Explicabilité par observation | ~50 Mo |
| 11 | **Graphiques** | `.png` | Rapport, documentation produit | ~2 Mo |

### 7.3 Procédure d'export pas à pas

```bash
# ── Depuis OctOpus ──

# 1. Télécharger les artefacts du run
#    OctOpus → onglet Model → Download all artifacts
#    ou via CLI :
octopus export --project SmartAgri92-SoilNowcast --output ./export/

# 2. Structure attendue dans ./export/
#    export/
#    ├── models/
#    │   ├── lgbm_y_plus_1d.pkl
#    │   ├── lgbm_y_plus_2d.pkl
#    │   ├── lgbm_y_plus_3d.pkl
#    │   ├── xgb_y_plus_1d.pkl
#    │   ├── ... (9 modèles individuels)
#    │   ├── stacking_y_plus_1d.pkl
#    │   ├── stacking_y_plus_2d.pkl
#    │   └── stacking_y_plus_3d.pkl
#    ├── onnx/
#    │   ├── best_y_plus_1d.onnx
#    │   ├── best_y_plus_2d.onnx
#    │   └── best_y_plus_3d.onnx
#    ├── config/
#    │   ├── pipeline.yaml
#    │   ├── data.yaml
#    │   ├── hyperparams.json
#    │   └── feature_importance.csv
#    ├── metrics/
#    │   ├── cv_results.json
#    │   ├── oof_predictions.parquet
#    │   └── shap_values.parquet
#    └── figures/
#        ├── feature_importance.png
#        ├── residuals.png
#        ├── learning_curves.png
#        └── shap_summary.png
```

### 7.4 Script d'inférence autonome SmartAgri

```python
"""
SmartAgri92 — Inférence Soil Nowcast autonome
Aucune dépendance OctOpus.
"""
import pickle
import pandas as pd
import numpy as np
import yaml

class SoilNowcastPredictor:
    """Prédicteur autonome pour SmartAgri."""

    def __init__(self, export_dir: str):
        with open(f'{export_dir}/config/pipeline.yaml') as f:
            self.config = yaml.safe_load(f)
        self.models = {}
        for target in self.config['targets']:
            model_path = f"{export_dir}/models/{self.config['best_algo']}_{target}.pkl"
            with open(model_path, 'rb') as f:
                self.models[target] = pickle.load(f)
        self.feature_cols = self.config['feature_cols']

    def predict(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prédiction sur nouvelles données."""
        X = data[self.feature_cols]
        results = pd.DataFrame(index=data.index)
        for target, model in self.models.items():
            results[target] = model.predict(X)
        return results

    def predict_single(self, row: dict) -> dict:
        """Prédiction pour une observation (API REST)."""
        df = pd.DataFrame([row])
        pred = self.predict(df)
        return pred.iloc[0].to_dict()


# Usage :
# predictor = SoilNowcastPredictor('./export')
# predictions = predictor.predict(new_data)
```

### 7.5 Inférence ONNX (embarqué, multi-langage)

```python
import onnxruntime as ort
import numpy as np

session = ort.InferenceSession('best_y_plus_1d.onnx')
input_name = session.get_inputs()[0].name

# Prédiction
X = np.array([[...]])  # 1 × 32 features, float32
pred = session.run(None, {input_name: X.astype(np.float32)})
print(f'Humidité J+1 : {pred[0][0]:.1f}%')
```

### 7.6 Fichier `pipeline.yaml` (contrat de reproductibilité)

```yaml
# pipeline.yaml — SmartAgri92 Soil Nowcast
version: '1.0'
project: SmartAgri92-SoilNowcast
created_in: OctOpus PAS Challenge 2026
seed: 42

data:
  train: train.parquet
  test: test.parquet
  train_rows: 258440
  test_rows: 25915
  n_features: 30

targets:
  - y_plus_1d_pct
  - y_plus_2d_pct
  - y_plus_3d_pct

feature_cols:
  - bulk_density_g_cm3
  - clay_pct
  - doy_cos
  - doy_sin
  - et0_pm_mean_7d_mm
  - et0_pm_mm
  - fc_ptf_pct
  - ph_h2o
  - pressure_hpa
  - rain_chirps_mm
  - rain_chirps_sum_14d_mm
  - rain_chirps_sum_3d_mm
  - rain_chirps_sum_7d_mm
  - rain_mm
  - rain_nasa_sum_14d_mm
  - rain_nasa_sum_3d_mm
  - rain_nasa_sum_7d_mm
  - rh_mean_pct
  - sand_pct
  - share_bare
  - share_built
  - share_crop
  - share_tree
  - soc_g_kg
  - solar_rad_mj_m2
  - t_max_c
  - t_mean_c
  - t_min_c
  - wind_2m_ms
  - wp_ptf_pct

group_col: power_cell_id
time_col: ts

validation:
  method: GroupKFold
  n_splits: 5
  group_col: power_cell_id

algorithms:
  - lightgbm
  - xgboost
  - catboost
  meta_learner: ridge

best_algo: lightgbm  # à remplir après entraînement

export_formats:
  - pickle
  - onnx
  - json_config

metrics:
  primary: rmse
  secondary: [mae, r2]
```

---
## 8. Analyse des risques

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| `soil_wetness_root_pct` absente du test | Vérifiée | Élevé | Ne pas l'utiliser comme feature, seulement comme cible auxiliaire |
| Overfitting spatial | Moyen | Élevé | GroupKFold strict sur `power_cell_id` |
| Drift temporel (train=passé, test=futur) | Moyen | Moyen | Ajouter une validation temporelle (purged time-series split) |
| Multicollinéarité (rain cumuls corrélés) | Confirmée | Faible | GBDT gère nativement ; SHAP pour interpréter |
| Pseudonymisation casse les jointures | Confirmée | Faible pour A1 | Features pré-assemblées, pas de jointure nécessaire |
| Budget dépassé | Très faible | Faible | Entraînement CPU < 2 $, budget 59,70 $ |

---
## 9. Dépendances SmartAgri

### 9.1 Dépendances amont

| Dépendance | Statut | Impact |
|---|---|---|
| `train.parquet` pré-assemblé | ✅ Disponible | Aucun assemblage nécessaire |
| `test.parquet` holdout | ✅ Disponible | Soumission challenge |
| NASA POWER API (production) | 🟡 Externe | Nécessaire pour inférence temps réel SmartAgri |
| CHIRPS API (production) | 🟡 Externe | Nécessaire pour inférence temps réel SmartAgri |
| iSDAsoil (constantes sol) | ✅ Statique | Chargé une fois, ne change pas |
| ESA WorldCover (constantes) | ✅ Statique | Chargé une fois, ne change pas |

### 9.2 Dépendances aval

| Consommateur | Utilise |
|---|---|
| **A8 RAG Agro** | Métriques et feature importance de A1 |
| **A9 Assistant Parcellaire** | Prédictions de A1 via API |
| **B6 Agent Monitoring** | Résidus de A1 pour détection d'anomalies |
| **Dashboard SmartAgri** | Visualisations des prédictions A1 |

---
## 10. Checklist pré-entraînement

- [ ] Confirmer la métrique du challenge (RMSE ?) via la page de soumission
- [ ] Vérifier si `soil_wetness_root_pct` est dans `test.parquet`
  → **Résultat** : ❌ NON, absente
- [ ] Décider si on entraîne 1 modèle multi-output ou 3 modèles séparés
  → **Recommandation** : 3 modèles séparés (meilleure performance, plus flexible)
- [ ] Fixer le nombre de folds (5 recommandé)
- [ ] Allouer le budget compute (< 2 $)
- [ ] Préparer `submission.csv` au format attendu par le challenge

### Format `test.parquet` — colonnes disponibles pour la soumission

```
  power_cell_id: string
  t_min_c: float64
  t_max_c: float64
  t_mean_c: float64
  rh_mean_pct: float64
  wind_2m_ms: float64
  solar_rad_mj_m2: float64
  pressure_hpa: float64
  rain_mm: float64
  rain_chirps_mm: float32
  et0_pm_mm: float64
  rain_nasa_sum_3d_mm: float64
  rain_nasa_sum_7d_mm: float64
  rain_nasa_sum_14d_mm: float64
  rain_chirps_sum_3d_mm: float64
  rain_chirps_sum_7d_mm: float64
  rain_chirps_sum_14d_mm: float64
  et0_pm_mean_7d_mm: float64
  doy_sin: float64
  doy_cos: float64
  sand_pct: float32
  clay_pct: float32
  soc_g_kg: float32
  ph_h2o: float32
  bulk_density_g_cm3: float32
  fc_ptf_pct: float32
  wp_ptf_pct: float32
  share_crop: float64
  share_tree: float64
  share_bare: float64
  share_built: float64
  ts: datetime64[ns]
```

**Colonnes à prédire (absentes du test)** : `soil_wetness_root_pct, y_plus_1d_pct, y_plus_2d_pct, y_plus_3d_pct`

---

*Document généré automatiquement par OctOpus — SmartAgri92*
*Date : 2026-11-16 | Seed : 42 | train : 258,440 × 36 | test : 25,915 × 32*