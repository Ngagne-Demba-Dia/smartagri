# 85 — SmartAgri Model Registry
## Registre Complet des Modèles IA SmartAgri92

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Production-ready design

---

## 1. Vue d'ensemble

Le Model Registry SmartAgri centralise les 9 modèles Classe A entraînés, leurs versions, métadonnées, lineage et politiques de promotion.

### 1.1 Registre actuel

| ID | Modèle | Framework | Algo | Version | Status | Métrique clé |
|----|--------|-----------|------|---------|--------|-------------|
| A1 | SoilNowcast | LightGBM 4.x | LGBMRegressor | v1.0.0 | champion | R² = 0.8375 |
| A2 | ET0 Forecast | CatBoost 1.x | CatBoostRegressor | v1.0.0 | champion | R² = 0.9997 |
| A3 | Yield Forecast | CatBoost 1.x | CatBoostRegressor | v1.0.0 | champion | R² = 0.9509 |
| A4 | Rain Intelligence | CatBoost 1.x | CatBoostClassifier | v1.0.0 | champion | AUC = 0.9650 |
| A5 | Price Forecast | XGBoost 3.x | XGBRegressor | v1.0.0 | champion | R² = 0.8995 |
| A6 | Crop Calendar | CatBoost 1.x | CatBoostClassifier | v1.0.0 | champion | F1 = 0.9799 |
| A7 | NDVI Anomaly | LightGBM 4.x | LGBMClassifier | v1.0.0 | champion | F1 = 0.9943 |
| A8 | Anomaly Intel. | scikit-learn | IsolationForest + AE | v1.0.0 | champion | F1 = 0.307 (flood) |
| A9 | Market Clustering | scikit-learn | KMeans | v1.0.0 | champion | Silhouette = 0.345 |

---

## 2. Schéma de métadonnées

### 2.1 ModelCard

```python
@dataclass
class ModelCard:
    # Identité
    model_id: str                    # "A1_SoilNowcast"
    display_name: str                # "SoilNowcast v1"
    description: str                 # Description métier
    owner: str                       # "SmartAgri92"
    team: str                        # "Agri-Moderne 5.0"

    # Version
    version: str                     # "v1.0.0" (semver)
    parent_version: Optional[str]    # None pour v1.0.0
    created_at: datetime
    promoted_at: Optional[datetime]
    status: Literal["candidate", "challenger", "champion", "archived", "rejected"]

    # Technique
    framework: str                   # "lightgbm"
    framework_version: str           # "4.5.0"
    algorithm: str                   # "LGBMRegressor"
    task_type: Literal["regression", "classification", "anomaly_detection", "clustering"]
    hyperparameters: dict            # Paramètres exacts
    feature_count: int               # Nombre de features
    feature_names: List[str]         # Liste ordonnée
    training_rows: int               # Lignes d'entraînement
    training_seed: int               # 42

    # Validation
    validation_method: str           # "GroupKFold_k5"
    validation_group: Optional[str]  # "power_cell_id"
    metrics: dict                    # {"r2": 0.8375, "rmse": 7.405, ...}
    fold_metrics: List[dict]         # Métriques par fold
    group_metrics: Optional[dict]    # Métriques par groupe spatial

    # Artifacts
    artifact_path: str               # Chemin relatif
    artifact_hash: str               # SHA-256
    artifact_size_bytes: int
    onnx_path: Optional[str]
    onnx_hash: Optional[str]

    # Lineage
    training_dataset_version: str    # ID dataset
    feature_store_version: str       # ID feature set
    training_pipeline_hash: str      # SHA-256 du code
    training_duration_s: float
    inference_latency_ms: float      # p50

    # Governance
    approved_by: Optional[str]
    approval_reason: Optional[str]
    risk_level: Literal["low", "medium", "high"]
    regulatory_notes: Optional[str]
```

### 2.2 Statuts du cycle de vie

```
    ┌──────────┐
    │ candidate│ ← entraînement terminé, pas encore validé
    └────┬─────┘
         │ validation pipeline passée
         ▼
    ┌──────────┐
    │challenger│ ← en shadow mode vs champion actuel
    └────┬─────┘
         │ shadow > 7j + meilleur que champion
         ▼
    ┌──────────┐
    │ champion │ ← modèle actif en production
    └────┬─────┘
         │ nouveau champion promu
         ▼
    ┌──────────┐
    │ archived │ ← conservé pour audit/rollback
    └──────────┘

    ┌──────────┐
    │ rejected │ ← validation échouée, conservé pour analyse
    └──────────┘
```

---

## 3. Fiches détaillées

### 3.1 A1 — SoilNowcast

**Mission** : Prédire l'humidité du sol à J+1, J+2, J+3

| Propriété | Valeur |
|-----------|--------|
| Framework | LightGBM 4.x |
| Algorithme | LGBMRegressor |
| Features | 30 |
| Training rows | 258 440 |
| Validation | GroupKFold k=5, group=power_cell_id |
| R² (y_plus_1d) | 0.8375 |
| RMSE (y_plus_1d) | 7.405 % |
| MAE (y_plus_1d) | 5.943 % |
| R² (y_plus_2d) | 0.8369 |
| R² (y_plus_3d) | 0.8314 |
| Top features | rain_chirps_sum_14d, rain_nasa_sum_14d, rain_chirps_sum_7d |
| Groupes fiables (R² > 0.80) | 42/71 (59%) |
| Inference latency | < 5ms |
| Export | LGB natif + ONNX |

**Hyperparamètres** :
```json
{
  "n_estimators": 800,
  "learning_rate": 0.05,
  "max_depth": 8,
  "num_leaves": 127,
  "min_child_samples": 50,
  "subsample": 0.8,
  "colsample_bytree": 0.8,
  "reg_alpha": 0.1,
  "reg_lambda": 1.0
}
```

### 3.2 A2 — ET0 Forecast

**Mission** : Prédire l'évapotranspiration de référence Penman-Monteith

| Propriété | Valeur |
|-----------|--------|
| Framework | CatBoost 1.x |
| R² | 0.9997 |
| RMSE | 0.039 mm/jour |
| Training rows | 329 232 |
| Top features | solar_rad_mj_m2, t_max_c, wind_2m_ms |

### 3.3 A3 — Yield Forecast

**Mission** : Prédire les rendements agricoles nationaux

| Propriété | Valeur |
|-----------|--------|
| Framework | CatBoost 1.x |
| R² | 0.9509 |
| RMSE | 2.008 t/ha |
| Training rows | 956 |
| Attention | Volume faible, risque de surapprentissage |

### 3.4 A4 — Rain Intelligence

**Mission** : Prédire la probabilité de pluie à J+1, J+2, J+3

| Propriété | Valeur |
|-----------|--------|
| Framework | CatBoost 1.x |
| AUC (rain_1d) | 0.9650 |
| F1 (rain_1d) | 0.773 |
| Brier (rain_1d) | 0.059 |
| AUC (rain_2d) | 0.9613 |
| AUC (rain_3d) | 0.9612 |
| Training rows | 258 440 |
| Top features | rain_chirps_sum_3d, rh_mean_pct, rain_nasa_sum_7d |
| Groupes fiables (AUC > 0.90) | 71/71 (100%) |

### 3.5 A5 — Price Forecast

**Mission** : Prédire les prix alimentaires sur les marchés sénégalais

| Propriété | Valeur |
|-----------|--------|
| Framework | XGBoost 3.x |
| R² | 0.8995 |
| RMSE | 66.67 FCFA/kg |
| Training rows | 55 283 |

### 3.6 A6 — Crop Calendar

**Mission** : Classifier la phase de croissance des cultures

| Propriété | Valeur |
|-----------|--------|
| Framework | CatBoost 1.x |
| F1 macro | 0.9799 |
| Accuracy | 0.9811 |

### 3.7 A7 — NDVI Anomaly

**Mission** : Détecter les anomalies de végétation par satellite

| Propriété | Valeur |
|-----------|--------|
| Framework | LightGBM 4.x |
| F1 | 0.9943 |
| Accuracy | 0.9976 |
| Anomaly rate | ~12% |

### 3.8 A8 — Anomaly Intelligence

**Mission** : Détecter les anomalies agro-climatiques multimodales

| Propriété | Valeur |
|-----------|--------|
| Modèles | Isolation Forest + AutoEncoder MLP |
| Meilleur F1 (flood) | IsoForest: 0.307, Recall: 0.948 |
| Meilleur F1 (any) | OC-SVM: 0.146 |
| Approche | Ensemble non supervisé |

### 3.9 A9 — Market Clustering

**Mission** : Segmenter les marchés sénégalais

| Propriété | Valeur |
|-----------|--------|
| Algorithme | KMeans k=2 |
| Silhouette | 0.345 |
| Marchés | 67 classifiés sur 79 |

---

## 4. API du Model Registry

### 4.1 Endpoints

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="SmartAgri Model Registry", version="1.0")

@app.get("/models")
def list_models(status: Optional[str] = None) -> List[ModelSummary]:
    """Liste tous les modèles, filtrable par statut."""

@app.get("/models/{model_id}")
def get_model(model_id: str) -> ModelCard:
    """Retourne la carte complète du modèle champion."""

@app.get("/models/{model_id}/versions")
def list_versions(model_id: str) -> List[ModelVersionSummary]:
    """Liste toutes les versions d'un modèle."""

@app.get("/models/{model_id}/versions/{version}")
def get_version(model_id: str, version: str) -> ModelCard:
    """Retourne une version spécifique."""

@app.post("/models/{model_id}/register")
def register_candidate(model_id: str, card: ModelCard) -> RegistrationResult:
    """Enregistre un nouveau candidat (status=candidate)."""

@app.post("/models/{model_id}/promote/{version}")
def promote(model_id: str, version: str,
            request: PromotionRequest) -> PromotionResult:
    """Promeut un challenger en champion."""

@app.post("/models/{model_id}/rollback")
def rollback(model_id: str, reason: str) -> RollbackResult:
    """Rollback vers le champion précédent."""

@app.get("/models/{model_id}/lineage")
def get_lineage(model_id: str) -> LineageGraph:
    """Graphe de lineage complet : données → features → modèle."""

@app.get("/models/{model_id}/compare")
def compare_versions(model_id: str,
                     v1: str, v2: str) -> ComparisonReport:
    """Compare deux versions sur toutes les métriques."""
```

### 4.2 Schéma de stockage

```
model_registry/
├── A1_SoilNowcast/
│   ├── champion.json          # Pointe vers la version active
│   ├── versions/
│   │   └── v1.0.0/
│   │       ├── card.json      # ModelCard complète
│   │       ├── model.lgb      # Artifact natif
│   │       ├── model.onnx     # Export ONNX
│   │       ├── hyperparams.json
│   │       ├── feature_list.json
│   │       ├── feature_stats.json
│   │       ├── fold_metrics.csv
│   │       ├── group_errors.csv
│   │       ├── shap_summary.csv
│   │       └── training_log.json
│   └── history/
│       └── promotions.jsonl   # Journal de promotions
├── A2_ET0Forecast/
│   └── ...
└── registry.yaml              # Index global
```

---

## 5. Politique de rétention

| Statut | Rétention | Artifacts | Métriques |
|--------|-----------|-----------|-----------|
| champion | Indéfinie | Complets | Complètes |
| archived | 2 ans | Complets | Complètes |
| rejected | 90 jours | Supprimés | Conservées |
| candidate | 30 jours si non promu | Supprimés | Conservées |

---

## 6. Promotion Gates

### 6.1 Checklist de promotion

```python
PROMOTION_GATES = {
    "A1_SoilNowcast": {
        "min_r2": 0.80,
        "max_rmse": 9.0,
        "min_groups_reliable": 35,  # sur 71
        "max_regression_pct": 2.0,
        "min_shadow_days": 7,
        "min_shadow_predictions": 1000,
        "max_latency_p95_ms": 200,
        "requires_human_approval": True,
    },
    "A4_RainIntelligence": {
        "min_auc": 0.93,
        "max_brier": 0.08,
        "min_groups_reliable": 60,  # sur 71
        "max_regression_pct": 2.0,
        "min_shadow_days": 7,
        "requires_human_approval": True,
    },
}
```

### 6.2 Rollback

Rollback automatique si dans les 24h suivant la promotion :
- Performance primaire chute > 5% vs baseline
- Taux d'erreur > 1%
- Latence p95 > 500ms

Le champion précédent est toujours disponible (status=archived).

---

## 7. Matrice de dépendances

```
A8 Anomaly ──┐
A1 Soil ─────┤
A4 Rain ─────┼── MonitoringEngine ── SmartAgriOrchestrator
A2 ET0 ──────┤                              │
A6 CropCal ──┘                              │
                                            ▼
A3 Yield ────┐                     IrrigationEngine
A5 Price ────┤                              │
A9 Market ───┘                              ▼
                                  Assistant Parcellaire V2
```

Si un modèle est rollbacké, tous les composants en aval doivent être notifiés et ajuster leurs scores de confiance.
