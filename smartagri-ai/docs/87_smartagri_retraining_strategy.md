# 87 — SmartAgri Retraining Strategy
## Stratégie de Réentraînement des Modèles SmartAgri92

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Production-ready design
**Objectif** : Être prêt le jour où les premiers kits réels produiront des données

---

## Table des matières

1. Principes directeurs
2. Politique par modèle
3. Détail : SoilNowcast (A1)
4. Détail : Rain Intelligence (A4)
5. Détail : Anomaly Intelligence (A8)
6. Détail : Modèles secondaires (A2, A3, A5, A6, A7, A9)
7. Pipeline de réentraînement
8. Challenger / Champion Protocol
9. Rollback et récupération
10. Monitoring post-déploiement
11. Budget et planification
12. Transition données proxy → terrain

---

## 1. Principes directeurs

### 1.1 Règles fondamentales

1. **Jamais de réentraînement à l'aveugle** : chaque trigger est mesuré et documenté
2. **Challenger obligatoire** : aucun modèle ne remplace le champion sans shadow mode
3. **Données validées uniquement** : les données terrain passent les gates de qualité avant entraînement
4. **Reproductibilité totale** : seed fixe, snapshots immuables, code versionné
5. **Rollback instantané** : le champion précédent est toujours disponible en < 5 minutes
6. **Pas de dégradation silencieuse** : monitoring continu, alertes automatiques

### 1.2 Types de triggers

| Type | Description | Exemple |
|------|------------|---------|
| **Performance** | Métrique sous le seuil | R² SoilNowcast < 0.82 |
| **Drift** | Distribution features change | PSI rain_chirps > 0.15 |
| **Calendaire** | Fréquence fixe | Trimestriel pour A1 |
| **Données** | Nouvelles données disponibles | Nouveau dataset FAOSTAT |
| **Événement** | Changement structurel | Nouvelle source de données, nouveau capteur |

---

## 2. Politique par modèle — Vue d'ensemble

| ID | Modèle | Fréquence | Trigger performance | Trigger drift | Données min | Priorité |
|----|--------|-----------|-------------------|---------------|-------------|----------|
| A1 | SoilNowcast | Trimestrielle | R² < 0.82 | PSI > 0.15 | 90j × 71 cells | P0 |
| A2 | ET0 Forecast | Semestrielle | R² < 0.998 | PSI > 0.10 | 180j × 76 cells | P1 |
| A3 | Yield Forecast | Annuelle | R² < 0.90 | Nouvelle campagne | +1 an FAOSTAT | P2 |
| A4 | Rain Intelligence | Trimestrielle | AUC < 0.94 | PSI > 0.15 | 90j × 71 cells | P0 |
| A5 | Price Forecast | Mensuelle | R² < 0.87 | PSI > 0.10 | 30j × 79 marchés | P1 |
| A6 | Crop Calendar | Annuelle | F1 < 0.95 | Nouveau Kc FAO | Mise à jour FAO | P2 |
| A7 | NDVI Anomaly | Trimestrielle | F1 < 0.98 | Drift NDVI | 3 mois S2 | P1 |
| A8 | Anomaly Intel. | Semestrielle | Recall flood < 0.85 | PSI > 0.20 | 180j toutes sources | P0 |
| A9 | Market Clustering | Annuelle | Silhouette < 0.25 | Nouveau marché | Données complètes | P2 |

**Priorités** : P0 = critique (agriculteur dépend), P1 = important, P2 = opportuniste

---

## 3. Détail : SoilNowcast (A1)

### 3.1 Métriques de référence (champion v1.0.0)

| Cible | R² | RMSE | MAE |
|-------|-----|------|-----|
| y_plus_1d_pct | 0.8375 | 7.405 | 5.943 |
| y_plus_2d_pct | 0.8369 | 7.411 | 5.946 |
| y_plus_3d_pct | 0.8314 | 7.525 | 5.995 |

Groupes fiables (R² > 0.80) : 42/71 (59%)
Validation : GroupKFold k=5 sur power_cell_id

### 3.2 Triggers de réentraînement

```python
SOILNOWCAST_TRIGGERS = {
    "performance_degradation": {
        "metric": "r2",
        "target": "y_plus_1d_pct",
        "threshold": 0.82,
        "window_days": 30,
        "check_frequency": "daily",
        "action": "schedule_retraining"
    },
    "data_drift": {
        "features": ["rain_chirps_sum_14d_mm", "rain_nasa_sum_14d_mm",
                     "et0_pm_mm", "soil_wetness_root_pct"],
        "method": "PSI",
        "threshold": 0.15,
        "reference": "same_month_previous_year",
        "check_frequency": "weekly",
        "action": "alert_then_evaluate"
    },
    "scheduled": {
        "frequency": "quarterly",
        "months": [1, 4, 7, 10],
        "day": 15,
        "action": "automatic_retraining"
    },
    "new_real_data": {
        "condition": "capteurs_terrain_disponibles",
        "action": "immediate_retraining_with_review"
    }
}
```

### 3.3 Pipeline de réentraînement A1

```
Trigger
    │
    ▼
Collecte données (90 derniers jours)
    │  NASA POWER + CHIRPS + ET0 + soil_wetness
    │  Même pipeline feature engineering
    │
    ▼
Merge avec historique (cumul)
    │  Validation schéma (Gate 1)
    │  Validation qualité (Gate 2)
    │
    ▼
Entraînement 3 modèles
    │  LightGBM + XGBoost + CatBoost
    │  Mêmes hyperparamètres (ou Optuna si major)
    │  GroupKFold k=5, group=power_cell_id
    │
    ▼
Validation (Gate 4)
    │  R² ≥ 0.82 sur les 3 cibles
    │  Pas de régression > 2% vs champion
    │  ≥ 35 groupes fiables
    │
    ├── FAIL → Alerte + conserver champion
    │
    ▼ PASS
Shadow mode 7 jours
    │  Prédictions en parallèle
    │  Comparaison en conditions réelles
    │
    ▼
Promotion si meilleur
    │  Ancien champion → archived
    │  Snapshot immuable créé
```

### 3.4 Fenêtre d'entraînement

| Scénario | Données utilisées | Volume |
|----------|------------------|--------|
| Réentraînement normal | Tout l'historique + 90j nouveaux | ~300K+ lignes |
| Réentraînement avec données terrain | Proxy + terrain (pondéré 2:1 terrain) | Variable |
| Premier entraînement terrain pur | ≥ 30 jours × ≥ 10 cellules | ≥ 21 300 lignes |

---

## 4. Détail : Rain Intelligence (A4)

### 4.1 Métriques de référence (champion v1.0.0)

| Cible | AUC | F1 | Brier |
|-------|-----|-----|-------|
| rain_1d | 0.9650 | 0.773 | 0.059 |
| rain_2d | 0.9613 | 0.759 | 0.062 |
| rain_3d | 0.9612 | 0.760 | 0.062 |

Groupes fiables (AUC > 0.90) : 71/71 (100%)

### 4.2 Triggers

```python
RAIN_INTELLIGENCE_TRIGGERS = {
    "performance_degradation": {
        "metric": "auc",
        "target": "rain_1d",
        "threshold": 0.94,
        "window_days": 30,
        "action": "schedule_retraining"
    },
    "seasonal_transition": {
        "condition": "transition hivernage (juin) ou saison sèche (novembre)",
        "action": "evaluate_performance_then_decide",
        "note": "Le changement de régime pluviométrique est attendu, pas un drift"
    },
    "calibration_drift": {
        "metric": "brier",
        "threshold": 0.08,
        "action": "recalibration_only"
    },
    "scheduled": {
        "frequency": "quarterly",
        "months": [2, 5, 8, 11],
        "action": "automatic_retraining"
    }
}
```

### 4.3 Particularité saisonnière

Le Sénégal a deux régimes pluviométriques très distincts :
- **Saison sèche (Nov–Juin)** : rain ≈ 0, le modèle prédit "pas de pluie" avec AUC → 1.0
- **Hivernage (Juil–Oct)** : pluies fréquentes, le modèle est réellement testé

**Règle** : évaluer la performance sur l'hivernage uniquement pour les décisions de réentraînement. Ne pas déclencher d'alerte drift en transition saisonnière.

---

## 5. Détail : Anomaly Intelligence (A8)

### 5.1 Métriques de référence

| Modèle | Type | Precision | Recall | F1 |
|--------|------|-----------|--------|-----|
| Isolation Forest | flood | 0.183 | 0.948 | 0.307 |
| One-Class SVM | any_anomaly | 0.234 | 0.107 | 0.146 |
| AutoEncoder MLP | flood | 0.055 | 0.284 | 0.092 |

### 5.2 Triggers

```python
ANOMALY_TRIGGERS = {
    "recall_degradation": {
        "metric": "recall",
        "anomaly_type": "flood",
        "threshold": 0.85,
        "action": "immediate_investigation"
    },
    "false_positive_spike": {
        "metric": "daily_alerts_count",
        "threshold": "3x moyenne mobile 30j",
        "action": "recalibrate_thresholds"
    },
    "new_anomaly_type": {
        "condition": "événement non couvert détecté manuellement",
        "action": "extend_training_data_and_retrain"
    },
    "scheduled": {
        "frequency": "biannual",
        "months": [3, 9],
        "action": "automatic_retraining"
    }
}
```

### 5.3 Stratégie d'amélioration

L'Anomaly Intelligence a les performances les plus faibles du portefeuille. Plan d'amélioration :

1. **Court terme** : ajuster les seuils d'anomalie (percentiles → métier)
2. **Moyen terme** : enrichir avec données terrain (vrais positifs confirmés)
3. **Long terme** : passer de non supervisé à semi-supervisé quand ≥ 200 anomalies labelées

---

## 6. Modèles secondaires

### 6.1 A2 ET0 Forecast

- **Fréquence** : semestrielle
- **Trigger** : R² < 0.998 (marge très faible car le modèle est quasi parfait)
- **Données** : 180 jours NASA POWER
- **Risque** : très faible, la physique sous-jacente (Penman-Monteith) est stable
- **Alerte** : changement de station météo NASA ou mise à jour du modèle GEOS

### 6.2 A3 Yield Forecast

- **Fréquence** : annuelle (après publication FAOSTAT)
- **Trigger** : nouvelle campagne disponible ou R² < 0.90
- **Données** : +1 an de données FAOSTAT
- **Risque** : volume faible (956 lignes), sensible au surapprentissage
- **Stratégie** : conserver la régularisation forte, augmenter les données progressivement

### 6.3 A5 Price Forecast

- **Fréquence** : mensuelle (données WFP mises à jour mensuellement)
- **Trigger** : R² < 0.87 ou nouveau marché ajouté
- **Données** : 30 derniers jours de prix + historique
- **Risque moyen** : les prix sont volatils, sensibles à des chocs exogènes
- **Stratégie** : fenêtre glissante 3 ans, décroissance exponentielle des poids

### 6.4 A6 Crop Calendar

- **Fréquence** : annuelle
- **Trigger** : mise à jour FAO-56 ou ajout de nouvelle culture
- **Données** : mise à jour des Kc FAO
- **Risque** : très faible (données de référence stables)

### 6.5 A7 NDVI Anomaly

- **Fréquence** : trimestrielle (nouveaux composites Sentinel-2)
- **Trigger** : F1 < 0.98 ou nouvelles scènes disponibles
- **Données** : 3 mois de composites NDVI Sentinel-2
- **Risque** : changement de capteur (Sentinel-2A/2B → Sentinel-2C) pourrait causer un drift

### 6.6 A9 Market Clustering

- **Fréquence** : annuelle
- **Trigger** : nouveau marché WFP ou changement structurel des prix
- **Données** : données marchés complètes
- **Risque** : très faible (segmentation structurelle)

---

## 7. Pipeline de réentraînement générique

### 7.1 Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Retraining Orchestrator (Prefect)             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌────────┐ │
│  │ Trigger │──▶│ Collect  │──▶│ Validate│──▶│ Train  │ │
│  │ Monitor │   │ Data     │   │ Data    │   │ Models │ │
│  └─────────┘   └──────────┘   └─────────┘   └───┬────┘ │
│                                                   │      │
│  ┌─────────┐   ┌──────────┐   ┌─────────┐       │      │
│  │ Deploy  │◀──│ Promote  │◀──│ Shadow  │◀──────┘      │
│  │         │   │          │   │ Mode    │               │
│  └─────────┘   └──────────┘   └─────────┘               │
│                                                           │
│  ┌─────────┐                                              │
│  │ Monitor │  Post-deployment monitoring continu          │
│  │ Post    │                                              │
│  └─────────┘                                              │
└──────────────────────────────────────────────────────────┘
```

### 7.2 DAG Prefect

```python
from prefect import flow, task
from prefect.schedules import CronSchedule

@task
def check_triggers(model_id: str) -> Optional[str]:
    """Vérifie si un réentraînement est nécessaire."""

@task
def collect_data(model_id: str, window_days: int) -> DataSnapshot:
    """Collecte et snapshot les données d'entraînement."""

@task
def validate_data(snapshot: DataSnapshot) -> ValidationResult:
    """Valide schéma, qualité, fraîcheur."""

@task
def train_models(snapshot: DataSnapshot, model_id: str) -> List[ModelCandidate]:
    """Entraîne LGB + XGB + CB, retourne les candidats."""

@task
def evaluate_candidates(candidates: List[ModelCandidate],
                        champion: ModelVersion) -> EvaluationResult:
    """Compare candidats vs champion actuel."""

@task
def start_shadow_mode(best_candidate: ModelCandidate,
                      duration_days: int = 7) -> ShadowJob:
    """Lance le shadow mode."""

@task
def evaluate_shadow(shadow_job: ShadowJob) -> ShadowResult:
    """Évalue la performance en shadow après N jours."""

@task
def promote_or_reject(shadow_result: ShadowResult) -> PromotionResult:
    """Promeut si meilleur, rejette sinon."""

@flow(schedule=CronSchedule(cron="0 2 15 1,4,7,10 *"))  # 15 du mois, 2h
def retrain_soilnowcast():
    trigger = check_triggers("A1_SoilNowcast")
    if trigger is None:
        return "No retraining needed"

    snapshot = collect_data("A1_SoilNowcast", window_days=90)
    validation = validate_data(snapshot)
    if not validation.passed:
        return f"Data validation failed: {validation.reason}"

    candidates = train_models(snapshot, "A1_SoilNowcast")
    evaluation = evaluate_candidates(candidates, get_champion("A1_SoilNowcast"))
    if not evaluation.has_better_candidate:
        return "No candidate better than champion"

    shadow = start_shadow_mode(evaluation.best_candidate)
    # Shadow evaluation runs as a separate scheduled task after 7 days
```

### 7.3 Configuration par modèle

```python
RETRAINING_CONFIG = {
    "A1_SoilNowcast": {
        "schedule": "0 2 15 1,4,7,10 *",  # Trimestriel
        "window_days": 90,
        "algorithms": ["LightGBM", "XGBoost", "CatBoost"],
        "validation": "GroupKFold_k5",
        "group_col": "power_cell_id",
        "shadow_days": 7,
        "min_improvement": 0.005,  # +0.5% R²
        "auto_promote": False,  # Revue humaine requise
    },
    "A4_RainIntelligence": {
        "schedule": "0 2 15 2,5,8,11 *",
        "window_days": 90,
        "algorithms": ["LightGBM", "XGBoost", "CatBoost"],
        "validation": "GroupKFold_k5",
        "group_col": "power_cell_id",
        "shadow_days": 7,
        "min_improvement": 0.003,  # +0.3% AUC
        "auto_promote": False,
    },
    "A5_PriceForecast": {
        "schedule": "0 2 1 * *",  # Mensuel
        "window_days": 30,
        "algorithms": ["LightGBM", "XGBoost", "CatBoost"],
        "validation": "TimeSeriesSplit_k5",
        "shadow_days": 14,
        "min_improvement": 0.01,
        "auto_promote": True,  # Prix = données fréquentes
    },
}
```

---

## 8. Challenger / Champion Protocol

### 8.1 Règles

1. **Un seul challenger** par modèle à la fois
2. **Shadow mode obligatoire** : 7-14 jours selon le modèle
3. **Même inputs** : challenger et champion reçoivent exactement les mêmes requêtes
4. **Isolation** : le challenger ne produit pas de réponse utilisateur
5. **Métriques comparées** : performance, latence, stabilité, couverture

### 8.2 Critères de décision

```python
def should_promote(shadow_results: ShadowResult, config: dict) -> bool:
    checks = [
        # Performance meilleure
        shadow_results.challenger_metric >= shadow_results.champion_metric
            + config["min_improvement"],
        # Pas de dégradation sur aucune métrique secondaire
        all(
            shadow_results.challenger_secondary[m] >=
            shadow_results.champion_secondary[m] * 0.98
            for m in shadow_results.champion_secondary
        ),
        # Latence acceptable
        shadow_results.challenger_p95_ms <= 200,
        # Stabilité (std sur fenêtres glissantes)
        shadow_results.challenger_std <= shadow_results.champion_std * 1.2,
        # Volume suffisant
        shadow_results.total_predictions >= 1000,
    ]
    return all(checks)
```

### 8.3 Journal de promotion

```json
{
  "model_id": "A1_SoilNowcast",
  "old_version": "v1.0.0",
  "new_version": "v1.1.0",
  "promoted_at": "2027-01-16T02:30:00Z",
  "reason": "Quarterly retraining, R² improved 0.8375 → 0.8412",
  "shadow_days": 7,
  "shadow_predictions": 4970,
  "approved_by": "auto" | "mouhamadou.diop",
  "rollback_available": true
}
```

---

## 9. Rollback et récupération

### 9.1 Rollback automatique

| Condition | Fenêtre | Action |
|-----------|---------|--------|
| Performance primaire -5% | 1h | Rollback immédiat |
| Taux d'erreur > 1% | 15min | Rollback immédiat |
| Latence p95 > 500ms | 30min | Alerte puis rollback |
| Nombre d'abstentions > 20% | 4h | Investigation + rollback si confirmé |

### 9.2 Procédure de rollback

```
Condition détectée
    │
    ▼
Notification CRITICAL (Slack + SMS)
    │
    ▼
Restauration champion précédent (< 5 min)
    │  1. Charger model.lgb depuis archived
    │  2. Vérifier hash SHA-256
    │  3. Remplacer le modèle en serving
    │  4. Invalider cache Redis
    │
    ▼
Validation post-rollback
    │  Comparer métriques sur 100 dernières prédictions
    │
    ▼
Post-mortem obligatoire
    │  Analyse root cause
    │  Action corrective
    │  Documentation
```

### 9.3 Capacité de rollback

| Modèle | Versions conservées | Délai rollback |
|--------|-------------------|---------------|
| A1 SoilNowcast | 4 dernières | < 5 min |
| A4 Rain Intelligence | 4 dernières | < 5 min |
| A8 Anomaly Intelligence | 2 dernières | < 5 min |
| Autres | 2 dernières | < 10 min |

---

## 10. Monitoring post-déploiement

### 10.1 Métriques surveillées

```python
POST_DEPLOYMENT_METRICS = {
    "performance": {
        "r2_rolling_7d": {"frequency": "daily", "alert": "< baseline - 0.03"},
        "rmse_rolling_7d": {"frequency": "daily", "alert": "> baseline + 1.0"},
        "auc_rolling_7d": {"frequency": "daily", "alert": "< baseline - 0.02"},
    },
    "operational": {
        "predictions_per_day": {"frequency": "hourly", "alert": "< 10 or > 10000"},
        "latency_p95_ms": {"frequency": "every_5min", "alert": "> 200"},
        "error_rate": {"frequency": "every_5min", "alert": "> 0.001"},
        "abstention_rate": {"frequency": "hourly", "alert": "> 0.15"},
    },
    "data_quality": {
        "null_rate": {"frequency": "daily", "alert": "> 0.01"},
        "feature_drift_psi": {"frequency": "weekly", "alert": "> 0.10"},
        "data_freshness_hours": {"frequency": "hourly", "alert": "> SLA * 1.5"},
    }
}
```

### 10.2 Dashboard Grafana

Panneaux recommandés :
1. **Santé globale** : score 0-100 par modèle (vert/jaune/rouge)
2. **Performance** : R²/AUC rolling 7j par modèle
3. **Latence** : p50/p95/p99 en temps réel
4. **Volume** : prédictions/heure par modèle
5. **Drift** : PSI top features, rolling 30j
6. **Alertes** : timeline des événements
7. **Challenger** : comparaison shadow en cours
8. **Fraîcheur** : statut de chaque source de données

---

## 11. Budget et planification

### 11.1 Coût compute par cycle

| Modèle | Fréquence | Durée | CPU | Coût/cycle | Coût/an |
|--------|-----------|-------|-----|-----------|---------|
| A1 SoilNowcast | Trimestriel | 15 min | 4 | 0.10 USD | 0.40 USD |
| A2 ET0 Forecast | Semestriel | 10 min | 4 | 0.07 USD | 0.14 USD |
| A3 Yield Forecast | Annuel | 2 min | 2 | 0.01 USD | 0.01 USD |
| A4 Rain Intelligence | Trimestriel | 15 min | 4 | 0.10 USD | 0.40 USD |
| A5 Price Forecast | Mensuel | 5 min | 2 | 0.03 USD | 0.36 USD |
| A6 Crop Calendar | Annuel | 3 min | 2 | 0.02 USD | 0.02 USD |
| A7 NDVI Anomaly | Trimestriel | 5 min | 2 | 0.03 USD | 0.12 USD |
| A8 Anomaly Intel. | Semestriel | 10 min | 4 | 0.07 USD | 0.14 USD |
| A9 Market Clustering | Annuel | 2 min | 2 | 0.01 USD | 0.01 USD |
| **Total** | | | | | **1.60 USD/an** |

### 11.2 Calendrier annuel

```
Jan : A1 réentraînement trimestriel
Fév : A4 réentraînement trimestriel
Mar : A8 réentraînement semestriel, A3 évaluation annuelle
Avr : A1 réentraînement trimestriel
Mai : A4 réentraînement trimestriel, A5 mensuel
Jun : Évaluation pré-hivernage (tous les modèles)
Jul : A1 réentraînement trimestriel (début hivernage)
Aoû : A4 réentraînement trimestriel, A7 trimestriel
Sep : A8 réentraînement semestriel
Oct : A1 réentraînement trimestriel (fin hivernage)
Nov : A4 réentraînement trimestriel, évaluation post-hivernage
Déc : Revue annuelle complète, A6/A9 annuels
```

---

## 12. Transition données proxy → terrain

### 12.1 Scénarios de montée en puissance

Le portefeuille actuel est entraîné sur des **données proxy** (NASA GEOS GWETROOT pour l'humidité du sol). Quand les premiers kits SmartAgri produiront des **données terrain réelles**, la stratégie de transition est :

#### Phase 0 : Proxy uniquement (actuel)
- Modèles entraînés sur NASA GEOS + CHIRPS + iSDAsoil
- R² = 0.8375 (SoilNowcast)
- Confiance : MODÉRÉE

#### Phase 1 : Premiers capteurs (≥ 1 kit, ≥ 30 jours)
- **Action** : enrichir le dataset d'entraînement
- **Méthode** : données terrain pondérées 2× vs proxy
- **Validation** : comparer prédictions vs mesures terrain
- **Objectif** : calibrer le biais proxy vs terrain
- **R² attendu** : 0.85–0.90

#### Phase 2 : Réseau de capteurs (≥ 10 kits, ≥ 90 jours)
- **Action** : réentraîner avec données mixtes proxy + terrain
- **Méthode** : features terrain comme variables principales, proxy en backup
- **Validation** : GroupKFold sur les kits réels
- **Objectif** : modèle calibré sur la réalité du terrain
- **R² attendu** : 0.88–0.93

#### Phase 3 : Déploiement à l'échelle (≥ 50 kits, ≥ 180 jours)
- **Action** : modèle terrain-first avec proxy en enrichissement
- **Méthode** : features terrain prioritaires, proxy pour combler les gaps
- **Objectif** : précision niveau parcellaire
- **R² attendu** : 0.90–0.95

### 12.2 Critères de transition

```python
TRANSITION_CRITERIA = {
    "phase_0_to_1": {
        "min_kits": 1,
        "min_days": 30,
        "min_valid_readings": 500,
        "action": "add_terrain_features_and_retrain"
    },
    "phase_1_to_2": {
        "min_kits": 10,
        "min_days": 90,
        "min_valid_readings": 10000,
        "terrain_coverage_regions": 3,
        "action": "retrain_mixed_model"
    },
    "phase_2_to_3": {
        "min_kits": 50,
        "min_days": 180,
        "min_valid_readings": 100000,
        "terrain_coverage_regions": 7,
        "action": "retrain_terrain_first_model"
    }
}
```

### 12.3 Compatibilité ascendante

Chaque transition de phase doit :
1. **Conserver le champion actuel** comme fallback
2. **Maintenir l'API identique** (mêmes endpoints, mêmes formats)
3. **Ne pas dégrader** les performances sur les zones sans capteur
4. **Documenter** chaque changement dans le Model Registry

---

## Résumé

| Aspect | Statut |
|--------|--------|
| Politique de réentraînement | 9/9 modèles couverts |
| Triggers définis | Performance, drift, calendaire, événement |
| Pipeline automatisé | DAG Prefect, 7 étapes |
| Challenger/Champion | Shadow mode 7-14j, critères stricts |
| Rollback | Automatique < 5 min, 4 dernières versions |
| Monitoring post-déploiement | 12 métriques, 4 niveaux alertes |
| Budget annuel | ~1.60 USD/an (compute CPU) |
| Transition terrain | 4 phases, critères mesurables |

**Prêt pour les premiers kits réels. Indépendant d'OctOpus.**
