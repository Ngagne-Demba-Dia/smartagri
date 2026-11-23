# 84 — SmartAgri MLOps Architecture
## Système MLOps Complet SmartAgri92

**Version** : 1.0
**Date** : 2026-11-18
**Auteur** : SmartAgri92 — Agri-Moderne 5.0
**Statut** : Design de production

---

## Table des matières

1. Vue d'ensemble
2. Dataset Registry
3. Feature Store
4. Model Registry
5. Snapshots immuables
6. Validation Pipeline
7. Promotion Protocol
8. Challenger / Champion
9. Drift Detection
10. Monitoring
11. Retraining Strategy
12. Architecture technique

---

## 1. Vue d'ensemble

### 1.1 Portefeuille de modèles

| ID | Modèle | Type | Champion | Métrique clé | Données |
|----|--------|------|----------|-------------|---------|
| A1 | SoilNowcast | Régression | LightGBM | R² = 0.8375 | 258K lignes |
| A2 | ET0 Forecast | Régression | CatBoost | R² = 0.9997 | 329K lignes |
| A3 | Yield Forecast | Régression | CatBoost | R² = 0.9509 | 956 lignes |
| A4 | Rain Intelligence | Classification | CatBoost | AUC = 0.9650 | 258K lignes |
| A5 | Price Forecast | Régression | XGBoost | R² = 0.8995 | 55K lignes |
| A6 | Crop Calendar | Classification | CatBoost | F1 = 0.9799 | FAO-56 Kc |
| A7 | NDVI Anomaly | Classification | LightGBM | F1 = 0.9943 | 26K lignes |
| A8 | Anomaly Intelligence | Non supervisé | Ensemble | F1 = 0.85 | NASA+CHIRPS |
| A9 | Market Clustering | Clustering | KMeans k=2 | Sil = 0.345 | 79 marchés |

### 1.2 Principes MLOps

1. **Reproductibilité** : chaque entraînement est reproductible (seed=42, données versionnées)
2. **Immuabilité** : snapshots données + modèles ne sont jamais modifiés en place
3. **Traçabilité** : lineage complet données → features → modèle → prédiction
4. **Automatisation** : pipelines CI/CD pour validation, promotion, rollback
5. **Observabilité** : métriques temps réel, alertes drift, logs structurés

### 1.3 Architecture globale

```
┌─────────────────────────────────────────────────────────────────┐
│                    SmartAgri MLOps Platform                       │
├─────────────┬──────────────┬──────────────┬─────────────────────┤
│  Dataset    │  Feature     │  Model       │  Monitoring         │
│  Registry   │  Store       │  Registry    │  & Alerting         │
├─────────────┼──────────────┼──────────────┼─────────────────────┤
│ • Sources   │ • Offline    │ • Versions   │ • Data drift        │
│ • Versions  │ • Online     │ • Metadata   │ • Concept drift     │
│ • Schemas   │ • Validation │ • Lineage    │ • Performance       │
│ • Lineage   │ • Serving    │ • Promotion  │ • Latence           │
│ • Snapshots │ • Freshness  │ • Rollback   │ • Volume            │
└─────────────┴──────────────┴──────────────┴─────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Pipeline d'entraînement & Validation                 │
├─────────────────────────────────────────────────────────────────┤
│  Ingestion → Validation → Feature Eng → Train → Eval → Promote  │
└─────────────────────────────────────────────────────────────────┘
         │                                            │
         ▼                                            ▼
┌─────────────────────┐              ┌────────────────────────────┐
│  Challenger/Champion │              │  Retraining Orchestrator   │
│  A/B Protocol        │              │  Triggers + Scheduling     │
└─────────────────────┘              └────────────────────────────┘
```

---

## 2. Dataset Registry

### 2.1 Catalogue des sources

| Source | Type | Fréquence | Volume | Licence |
|--------|------|-----------|--------|---------|
| NASA POWER | Météo quotidienne | J+2 | 329K lignes/an | NASA Open Data |
| CHIRPS v3 | Pluie quotidienne | J+5 | 2,5M lignes/an | CC BY 4.0 |
| FAO-56 ET0 | Évapotranspiration | Calculée | 329K lignes/an | Dérivée |
| NASA Soil Wetness | Proxy humidité | J+2 | 329K lignes/an | NASA Open Data |
| iSDAsoil | Propriétés sol | Statique | 13 890 lignes | CC BY 4.0 |
| ESA WorldCover | Occupation sol | Annuelle | 6 945 lignes | CC BY 4.0 |
| Sentinel-2 NDVI | Végétation | Mensuelle | 26K lignes/an | Copernicus |
| WFP Food Prices | Prix marchés | Mensuelle | ~3K lignes/an | CC BY-IGO 3.0 |
| FAOSTAT | Rendements | Annuelle | ~15 lignes/an | CC BY 4.0 |
| FAO-56 Kc | Coefficients culture | Statique | 900 lignes | Référence |

### 2.2 Schéma de versionnement

```python
class DatasetVersion:
    dataset_id: str          # ex: "chirps_v3_national_daily"
    version: str             # ex: "v2026.11.18"
    source_hash: str         # SHA-256 du fichier source
    schema_hash: str         # SHA-256 du schéma (colonnes + types)
    row_count: int
    date_range: Tuple[date, date]
    created_at: datetime
    created_by: str          # pipeline ID
    parent_version: Optional[str]
    status: Literal["draft", "validated", "active", "archived"]
```

### 2.3 Politique de rétention

| Catégorie | Rétention | Raison |
|-----------|-----------|--------|
| Sources brutes | 3 ans | Reproductibilité |
| Snapshots entraînement | Indéfinie | Audit modèle |
| Snapshots inférence | 90 jours | Debugging |
| Métriques | Indéfinie | Historique performance |

### 2.4 Validation de schéma

```python
DATASET_SCHEMAS = {
    "nasa_power_daily": {
        "required_columns": [
            "power_cell_id", "date", "t_min_c", "t_max_c", "t_mean_c",
            "rh_mean_pct", "wind_2m_ms", "solar_rad_mj_m2", "pressure_hpa"
        ],
        "types": {
            "power_cell_id": "string",
            "date": "date",
            "t_min_c": "float64",  # range: [-10, 55]
            "t_max_c": "float64",  # range: [-5, 60]
        },
        "constraints": {
            "t_max_c >= t_min_c": True,
            "rh_mean_pct": [0, 100],
            "solar_rad_mj_m2": [0, 40],
        }
    }
}
```

---

## 3. Feature Store

### 3.1 Architecture

```
┌───────────────────────────────────────────────┐
│              Feature Store SmartAgri            │
├───────────────────┬───────────────────────────┤
│   Offline Store   │     Online Store          │
│                   │                           │
│ • Parquet/Delta   │ • Redis/DuckDB            │
│ • Historique      │ • Dernières valeurs       │
│ • Batch training  │ • Inférence < 200ms       │
│ • Backfill        │ • TTL par feature         │
├───────────────────┴───────────────────────────┤
│            Feature Registry (catalogue)        │
│ • Métadonnées, types, propriétaire, version   │
│ • Lineage source → transformation → feature   │
│ • Monitoring freshness & distributions        │
└───────────────────────────────────────────────┘
```

### 3.2 Catalogue des features par modèle

#### A1 — SoilNowcast (30 features)

| Feature | Source | Type | Freshness | Importance LGB |
|---------|--------|------|-----------|---------------|
| rain_chirps_sum_14d_mm | CHIRPS | float64 | J+5 | 1.000 (top) |
| rain_nasa_sum_14d_mm | NASA POWER | float64 | J+2 | 0.85 |
| rain_chirps_sum_7d_mm | CHIRPS | float64 | J+5 | 0.78 |
| et0_pm_mm | FAO-56 | float64 | J+2 | 0.72 |
| rain_mm | NASA POWER | float64 | J+2 | 0.65 |
| clay_pct | iSDAsoil | float64 | Statique | 0.45 |
| sand_pct | iSDAsoil | float64 | Statique | 0.42 |
| fc_ptf_pct | Dérivée | float64 | Statique | 0.38 |
| doy_sin | Calculée | float64 | Temps réel | 0.35 |
| doy_cos | Calculée | float64 | Temps réel | 0.33 |

#### A4 — Rain Intelligence (30 features)

| Feature | Source | Importance CB |
|---------|--------|--------------|
| rain_chirps_sum_3d_mm | CHIRPS | Top 1 |
| rh_mean_pct | NASA POWER | Top 2 |
| rain_nasa_sum_7d_mm | NASA POWER | Top 3 |
| pressure_hpa | NASA POWER | Top 4 |
| solar_rad_mj_m2 | NASA POWER | Top 5 |

#### A8 — Anomaly Intelligence (34 features)

Types d'anomalies détectées : flood (F1=0.307 IsoForest), drought, heat, water_stress, et0_extreme

### 3.3 Feature Groups

```python
FEATURE_GROUPS = {
    "meteo_daily": {
        "entity": "power_cell_id",
        "granularity": "daily",
        "source": "nasa_power_national_daily",
        "features": ["t_min_c", "t_max_c", "t_mean_c", "rh_mean_pct",
                     "wind_2m_ms", "solar_rad_mj_m2", "pressure_hpa"],
        "ttl_hours": 48,
    },
    "rain_daily": {
        "entity": "cell_id",
        "granularity": "daily",
        "source": "chirps_v3_national_daily",
        "features": ["rain_mm", "is_provisional"],
        "ttl_hours": 120,
    },
    "soil_static": {
        "entity": "cell_id",
        "granularity": "static",
        "source": "isdasoil_national_grid_0p05",
        "features": ["sand_pct", "clay_pct", "soc_g_kg", "ph_h2o",
                     "bulk_density_g_cm3", "fc_ptf_pct", "wp_ptf_pct"],
        "ttl_hours": None,  # static
    },
    "rolling_aggregates": {
        "entity": "power_cell_id",
        "granularity": "daily",
        "source": "computed",
        "features": ["rain_nasa_sum_3d_mm", "rain_nasa_sum_7d_mm",
                     "rain_nasa_sum_14d_mm", "rain_chirps_sum_3d_mm",
                     "rain_chirps_sum_7d_mm", "rain_chirps_sum_14d_mm",
                     "et0_pm_mean_7d_mm"],
        "ttl_hours": 48,
        "computation": "rolling window over raw sources"
    },
}
```

### 3.4 Freshness Monitoring

| Feature Group | SLA | Alerte jaune | Alerte rouge |
|---------------|-----|-------------|-------------|
| meteo_daily | J+2 | J+3 | J+5 |
| rain_daily | J+5 | J+7 | J+10 |
| soil_static | Annuelle | 18 mois | 24 mois |
| ndvi_monthly | M+1 | M+2 | M+3 |
| prices_monthly | M+1 | M+2 | M+4 |

---

## 4. Model Registry

### 4.1 Structure

```python
class ModelVersion:
    model_id: str            # ex: "A1_SoilNowcast"
    version: str             # ex: "v1.0.0"
    framework: str           # "lightgbm" | "xgboost" | "catboost" | "sklearn"
    algorithm: str           # ex: "LGBMRegressor"
    hyperparameters: dict    # paramètres exacts
    training_dataset: str    # dataset version ID
    feature_set: List[str]   # liste ordonnée des features
    metrics: dict            # métriques de validation
    artifact_path: str       # chemin vers le modèle sérialisé
    artifact_hash: str       # SHA-256
    onnx_path: Optional[str] # export ONNX si disponible
    status: Literal["candidate", "challenger", "champion", "archived", "rejected"]
    promoted_at: Optional[datetime]
    promoted_by: Optional[str]
    training_time_s: float
    inference_time_ms: float
```

### 4.2 Registre actuel

| ID | Version | Framework | Status | Promu le |
|----|---------|-----------|--------|----------|
| A1_SoilNowcast | v1.0.0 | LightGBM 4.x | champion | 2026-11-16 |
| A2_ET0Forecast | v1.0.0 | CatBoost 1.x | champion | 2026-11-17 |
| A3_YieldForecast | v1.0.0 | CatBoost 1.x | champion | 2026-11-17 |
| A4_RainIntelligence | v1.0.0 | CatBoost 1.x | champion | 2026-11-16 |
| A5_PriceForecast | v1.0.0 | XGBoost 3.x | champion | 2026-11-17 |
| A6_CropCalendar | v1.0.0 | CatBoost 1.x | champion | 2026-11-17 |
| A7_NDVIAnomaly | v1.0.0 | LightGBM 4.x | champion | 2026-11-17 |
| A8_AnomalyIntelligence | v1.0.0 | Ensemble | champion | 2026-11-17 |
| A9_MarketClustering | v1.0.0 | KMeans | champion | 2026-11-17 |

### 4.3 Politique de versionnement

- **Patch** (v1.0.x) : réentraînement même données, même hyperparamètres
- **Minor** (v1.x.0) : nouvelles features ou hyperparamètres ajustés
- **Major** (vx.0.0) : changement d'algorithme ou de schéma features

### 4.4 API de requête

```python
class ModelRegistryAPI:
    def get_champion(self, model_id: str) -> ModelVersion:
        """Retourne le modèle champion actif."""

    def get_version(self, model_id: str, version: str) -> ModelVersion:
        """Retourne une version spécifique."""

    def list_versions(self, model_id: str) -> List[ModelVersion]:
        """Liste toutes les versions avec statut."""

    def promote(self, model_id: str, version: str,
                reason: str, approved_by: str) -> bool:
        """Promeut un challenger en champion."""

    def rollback(self, model_id: str, reason: str) -> ModelVersion:
        """Rollback vers la version champion précédente."""
```

---

## 5. Snapshots immuables

### 5.1 Principe

Chaque entraînement produit un **snapshot immuable** :

```
snapshots/
└── A1_SoilNowcast/
    └── v1.0.0/
        ├── data/
        │   ├── train.parquet          # SHA-256 vérifié
        │   ├── val.parquet
        │   └── test.parquet
        ├── features/
        │   ├── feature_list.json
        │   └── feature_stats.json     # distributions de référence
        ├── model/
        │   ├── model.lgb              # modèle natif
        │   ├── model.onnx             # export ONNX
        │   └── hyperparameters.json
        ├── metrics/
        │   ├── fold_metrics.csv
        │   ├── group_errors.csv
        │   └── shap_summary.csv
        ├── metadata.json              # lineage complet
        └── snapshot.sha256            # hash de l'ensemble
```

### 5.2 Garanties

1. **Aucune modification** : un snapshot créé n'est jamais modifié
2. **Vérification d'intégrité** : hash SHA-256 de chaque fichier + hash global
3. **Reproductibilité** : seed + données + config = même modèle (± flottants)
4. **Audit** : qui a créé, quand, à partir de quoi, pourquoi

---

## 6. Validation Pipeline

### 6.1 Gates de validation

```
Données brutes
    │
    ▼
┌────────────────┐
│ Gate 1: Schema │  Colonnes, types, ranges, nulls
│ Validation     │  FAIL → rejet immédiat
└───────┬────────┘
        ▼
┌────────────────┐
│ Gate 2: Quality│  Distributions, outliers, freshness
│ Checks         │  WARN → log + continue | FAIL → rejet
└───────┬────────┘
        ▼
┌────────────────┐
│ Gate 3: Feature│  Features calculées, cohérence
│ Engineering    │  FAIL → debugging pipeline
└───────┬────────┘
        ▼
┌────────────────┐
│ Gate 4: Model  │  Métriques vs seuils, pas de régression
│ Quality        │  FAIL → rejet candidat
└───────┬────────┘
        ▼
┌────────────────┐
│ Gate 5: Bias & │  Équité régionale, groupes vulnérables
│ Fairness       │  WARN → revue humaine | FAIL → rejet
└───────┬────────┘
        ▼
    Candidat validé
```

### 6.2 Seuils de validation par modèle

| Modèle | Métrique | Seuil min | Champion actuel | Marge |
|--------|----------|-----------|-----------------|-------|
| A1 SoilNowcast | R² | 0.80 | 0.8375 | +4.7% |
| A2 ET0 Forecast | R² | 0.995 | 0.9997 | +0.47% |
| A3 Yield Forecast | R² | 0.90 | 0.9509 | +5.7% |
| A4 Rain Intelligence | AUC | 0.93 | 0.9650 | +3.8% |
| A5 Price Forecast | R² | 0.85 | 0.8995 | +5.8% |
| A6 Crop Calendar | F1 | 0.95 | 0.9799 | +3.1% |
| A7 NDVI Anomaly | F1 | 0.98 | 0.9943 | +1.5% |
| A8 Anomaly Intel. | F1 flood | 0.25 | 0.307 | +22.8% |

### 6.3 Règle anti-régression

```python
def validate_no_regression(candidate_metrics, champion_metrics, tolerance=0.02):
    for metric, value in candidate_metrics.items():
        champion_value = champion_metrics[metric]
        if metric in HIGHER_IS_BETTER:
            if value < champion_value * (1 - tolerance):
                return False, f"{metric} régression: {value:.4f} < {champion_value:.4f}"
        else:  # lower is better (RMSE, MAE)
            if value > champion_value * (1 + tolerance):
                return False, f"{metric} régression: {value:.4f} > {champion_value:.4f}"
    return True, "Pas de régression détectée"
```

---

## 7. Promotion Protocol

### 7.1 Flux de promotion

```
Candidat entraîné
    │
    ▼
Validation Pipeline (Gates 1-5)
    │
    ├── FAIL → Rejet (archivé avec raison)
    │
    ▼ PASS
Challenger désigné
    │
    ▼
Shadow Mode (7 jours min)
    │  • Prédictions en parallèle du champion
    │  • Comparaison métriques en conditions réelles
    │  • Pas d'impact utilisateur
    │
    ▼
Challenger vs Champion
    │
    ├── Challenger < Champion → Rejet
    │
    ▼ Challenger ≥ Champion
Revue humaine
    │  • Data scientist valide
    │  • Product owner approuve
    │
    ▼ Approuvé
Promotion Champion
    │  • Ancien champion → archived
    │  • Snapshot immuable créé
    │  • Rollback automatique si dégradation < 24h
```

### 7.2 Critères de promotion

| Critère | Condition | Obligatoire |
|---------|-----------|-------------|
| Validation pipeline | 5/5 gates passées | Oui |
| Pas de régression | Toutes métriques ≥ champion - 2% | Oui |
| Shadow mode | ≥ 7 jours sans anomalie | Oui |
| Volume d'inférence shadow | ≥ 1000 prédictions | Oui |
| Latence | p95 < 200ms | Oui |
| Revue humaine | Approbation DS + PO | Oui |
| Tests unitaires | 100% passés | Oui |

---

## 8. Challenger / Champion

### 8.1 Protocole

Chaque modèle a au maximum **1 champion** et **1 challenger** actifs simultanément.

```python
class ChallengerChampionProtocol:
    def run_shadow(self, model_id: str, challenger_version: str,
                   duration_days: int = 7) -> ShadowResults:
        """
        Exécute le challenger en parallèle du champion.
        Les deux reçoivent les mêmes inputs.
        Seul le champion produit la réponse utilisateur.
        """

    def compare(self, shadow_results: ShadowResults) -> ComparisonReport:
        """
        Compare les métriques :
        - Accuracy/R²/AUC sur les mêmes données
        - Latence p50/p95/p99
        - Stabilité (std sur fenêtres glissantes)
        - Couverture (% de requêtes avec prédiction)
        """

    def promote_if_better(self, comparison: ComparisonReport,
                          approved_by: str) -> PromotionResult:
        """Promeut si le challenger est strictement meilleur."""
```

### 8.2 Rollback automatique

```python
ROLLBACK_CONDITIONS = {
    "performance_drop": {
        "metric": "primary_metric",
        "threshold": -0.05,  # -5% vs baseline 24h
        "window": "1h",
        "action": "immediate_rollback"
    },
    "error_rate_spike": {
        "metric": "error_rate",
        "threshold": 0.01,  # > 1%
        "window": "15min",
        "action": "immediate_rollback"
    },
    "latency_degradation": {
        "metric": "p95_latency_ms",
        "threshold": 500,
        "window": "30min",
        "action": "alert_then_rollback"
    }
}
```

---

## 9. Drift Detection

### 9.1 Types de drift

| Type | Description | Détection | Impact |
|------|------------|-----------|--------|
| **Data drift** | Distribution des features change | PSI, KS test | Features |
| **Concept drift** | Relation features→cible change | Performance decay | Modèle |
| **Schema drift** | Colonnes ou types changent | Validation schéma | Pipeline |
| **Label drift** | Distribution cible change | Chi², KL divergence | Entraînement |

### 9.2 Métriques de drift par modèle

#### A1 SoilNowcast — Features critiques à surveiller

| Feature | Méthode | Seuil alerte | Seuil critique |
|---------|---------|-------------|----------------|
| rain_chirps_sum_14d_mm | PSI | 0.10 | 0.25 |
| et0_pm_mm | KS test | p < 0.01 | p < 0.001 |
| clay_pct | PSI | 0.10 | 0.20 |
| soil_wetness_root_pct | KS test | p < 0.01 | p < 0.001 |

#### A4 Rain Intelligence — Features critiques

| Feature | Méthode | Seuil alerte |
|---------|---------|-------------|
| rh_mean_pct | PSI | 0.10 |
| pressure_hpa | PSI | 0.10 |
| rain_chirps_sum_3d_mm | KS test | p < 0.01 |

### 9.3 Pipeline de drift

```python
class DriftDetector:
    def compute_psi(self, reference: pd.Series, current: pd.Series,
                    n_bins: int = 10) -> float:
        """Population Stability Index."""

    def ks_test(self, reference: pd.Series, current: pd.Series) -> float:
        """Kolmogorov-Smirnov test p-value."""

    def detect_concept_drift(self, model_id: str,
                             window_days: int = 30) -> DriftReport:
        """
        Compare performance sur fenêtre glissante vs baseline.
        Si R² drop > 5% ou AUC drop > 3% → alerte.
        """

    def daily_check(self) -> List[DriftAlert]:
        """Vérification quotidienne de tous les modèles actifs."""
```

### 9.4 Saisonnalité Sénégal

| Saison | Période | Impact attendu |
|--------|---------|----------------|
| Saison sèche (Noor) | Nov–Juin | rain_mm ≈ 0, distribution normale |
| Hivernage (Nawet) | Juil–Oct | rain_mm >> 0, forte variabilité |
| Transition | Juin, Nov | Changement rapide, drift attendu |

**Règle** : ne pas déclencher d'alerte drift pour les transitions saisonnières connues. Utiliser des **fenêtres de référence saisonnières** (même mois de l'année précédente).

---

## 10. Monitoring

### 10.1 Stack de monitoring

```
┌──────────────────────────────────────────┐
│          Dashboard SmartAgri MLOps        │
├──────────┬──────────┬──────────┬─────────┤
│ Santé    │ Perfor-  │ Données  │ Infra   │
│ modèles  │ mance    │          │         │
│          │          │          │         │
│ • Status │ • R²/AUC │ • Volume │ • CPU   │
│ • Drift  │ • RMSE   │ • Fresh  │ • RAM   │
│ • Errors │ • Latence│ • Drift  │ • Disk  │
└──────────┴──────────┴──────────┴─────────┘
```

### 10.2 Métriques clés (KPIs)

| KPI | Calcul | Seuil vert | Seuil jaune | Seuil rouge |
|-----|--------|-----------|-------------|-------------|
| Model Health Score | (perf + freshness + drift) / 3 | > 0.90 | 0.70–0.90 | < 0.70 |
| Prédictions/jour | count(inferences) | > 100 | 10–100 | < 10 |
| Latence p95 | percentile(95, latency_ms) | < 200ms | 200–500ms | > 500ms |
| Taux d'erreur | errors / total | < 0.1% | 0.1–1% | > 1% |
| Fraîcheur données | max(age_hours) | < SLA | SLA–2×SLA | > 2×SLA |
| Drift score | max(PSI features) | < 0.10 | 0.10–0.25 | > 0.25 |

### 10.3 Alertes

| Niveau | Canal | Temps de réaction | Exemple |
|--------|-------|-------------------|---------|
| INFO | Log | Aucun | "A2 ET0 réentraîné avec succès" |
| WARNING | Slack + email | 4h | "PSI > 0.10 sur rain_chirps_sum_14d" |
| CRITICAL | Slack + SMS + PagerDuty | 30min | "R² SoilNowcast < 0.80" |
| EMERGENCY | Rollback auto + notification | Immédiat | "Taux erreur > 5%" |

---

## 11. Retraining Strategy

### 11.1 Politique par modèle

| Modèle | Trigger | Fréquence min | Données requises |
|--------|---------|---------------|-----------------|
| A1 SoilNowcast | Drift PSI > 0.15 ou R² < 0.82 | Trimestrielle | 90 jours NASA + CHIRPS |
| A2 ET0 Forecast | Performance R² < 0.998 | Semestrielle | 180 jours NASA POWER |
| A3 Yield Forecast | Nouvelle campagne FAOSTAT | Annuelle | +1 an FAOSTAT |
| A4 Rain Intelligence | AUC < 0.94 ou saison | Trimestrielle | 90 jours NASA + CHIRPS |
| A5 Price Forecast | R² < 0.87 ou nouveau marché | Mensuelle | 30 jours WFP |
| A6 Crop Calendar | Nouveau Kc FAO | Annuelle | Mise à jour FAO |
| A7 NDVI Anomaly | Nouvelles scènes S2 | Trimestrielle | 3 mois S2 NDVI |
| A8 Anomaly Intelligence | Drift features | Semestrielle | 180 jours toutes sources |
| A9 Market Clustering | Nouveau marché WFP | Annuelle | Données marchés complètes |

### 11.2 Pipeline de réentraînement

```
Trigger détecté
    │
    ▼
Snapshot données (T-N jours → T)
    │
    ▼
Feature engineering (même pipeline)
    │
    ▼
Entraînement 3 modèles (LGB, XGB, CB)
    │
    ▼
Validation Pipeline (5 gates)
    │
    ├── FAIL → Alerte + conserver champion
    │
    ▼ PASS
Shadow mode (7 jours)
    │
    ▼
Promotion si meilleur
    │
    ▼
Archivage ancien champion
```

### 11.3 Budget compute

| Modèle | Temps entraînement | CPU/GPU | Coût estimé |
|--------|-------------------|---------|-------------|
| A1 SoilNowcast | ~15 min | 4 CPU | ~0.10 USD |
| A2 ET0 Forecast | ~10 min | 4 CPU | ~0.07 USD |
| A4 Rain Intelligence | ~15 min | 4 CPU | ~0.10 USD |
| A5 Price Forecast | ~5 min | 2 CPU | ~0.03 USD |
| Total trimestriel | ~1h | — | ~0.50 USD |

---

## 12. Architecture technique

### 12.1 Stack recommandée

| Composant | Technologie | Raison |
|-----------|-------------|--------|
| Feature Store offline | DuckDB / Parquet | Léger, SQL, pas de serveur |
| Feature Store online | Redis | Latence < 1ms |
| Model Registry | MLflow / fichiers versionné | Standard, léger |
| Orchestration | Prefect / Airflow Lite | DAGs, retry, monitoring |
| Monitoring | Prometheus + Grafana | Métriques temps réel |
| Alertes | Grafana Alerting | Intégration Slack/SMS |
| CI/CD | GitHub Actions | Automatisation complète |
| Stockage | S3-compatible (MinIO) | Immutabilité, versionnement |

### 12.2 Structure de déploiement

```
smartagri-mlops/
├── feature_store/
│   ├── offline/          # Parquet partitionnés
│   ├── online/           # Redis config
│   └── registry.yaml     # Catalogue features
├── model_registry/
│   ├── models/           # Artifacts par modèle
│   ├── metadata/         # Versions, métriques
│   └── registry.yaml     # Catalogue modèles
├── dataset_registry/
│   ├── schemas/          # Contrats par source
│   ├── versions/         # Métadonnées versions
│   └── registry.yaml
├── pipelines/
│   ├── ingestion/        # DAGs d'ingestion
│   ├── training/         # DAGs d'entraînement
│   ├── validation/       # Gates de validation
│   └── promotion/        # Protocole promotion
├── monitoring/
│   ├── drift/            # Détecteurs drift
│   ├── dashboards/       # Grafana JSON
│   └── alerts/           # Règles d'alertes
├── docker-compose.yml
└── Makefile
```

### 12.3 Docker Compose

```yaml
version: "3.9"
services:
  feature-store:
    build: ./feature_store
    volumes:
      - feature-data:/data
    ports:
      - "8001:8001"

  model-registry:
    build: ./model_registry
    volumes:
      - model-data:/data
    ports:
      - "8002:8002"

  api-gateway:
    build: ./api
    depends_on:
      - feature-store
      - model-registry
    ports:
      - "8000:8000"

  monitoring:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./monitoring/dashboards:/var/lib/grafana/dashboards
    ports:
      - "3000:3000"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Résumé

| Composant | Statut | Couverture |
|-----------|--------|-----------|
| Dataset Registry | Design complet | 10 sources, 4 politiques rétention |
| Feature Store | Design complet | 4 feature groups, SLAs définis |
| Model Registry | Design complet | 9 modèles, versionnement sémantique |
| Snapshots | Design complet | Structure immuable avec SHA-256 |
| Validation | Design complet | 5 gates, seuils par modèle |
| Promotion | Design complet | Shadow mode 7j, rollback auto |
| Challenger/Champion | Design complet | Protocole parallèle |
| Drift Detection | Design complet | PSI, KS, saisonnalité Sénégal |
| Monitoring | Design complet | 6 KPIs, 4 niveaux alertes |
| Retraining | Design complet | Triggers, fréquences, budget |

**Indépendant d'OctOpus. Déployable sur n'importe quelle infrastructure Docker.**
