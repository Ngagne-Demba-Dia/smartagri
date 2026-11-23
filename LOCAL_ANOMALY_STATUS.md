# LOCAL_ANOMALY_STATUS — État Local de AnomalyService (A8)

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-06B  
**Contraintes respectées** : aucun nouveau modèle développé, aucun entraînement lancé, utilisation exclusive des artefacts existants.

---

## 1. Métriques mesurées et artefacts

| Indicateur | Valeur observée | Source / Détail |
|---|---|---|
| **Statut détection** | ✅ **Seuils métier actifs** (`5/5` règles) ; ⚠️ **Poids ML absents** (`stat_loaded=False`) | `models/anomaly/` ne contient ni `isolation_forest_champion.pkl`, ni `ocsvm_champion.pkl`, ni `autoencoder_champion.pkl`. |
| **Temps d'inférence** | **0,098 ms** | Mesuré via `bench_06b.py` sur cas critique multi-anomalies (`count=3`). |
| **Mémoire consommée** | **< 1 Mo** | Mode seuils métier léger sans poids ML en RAM. |
| **Taille des modèles sur disque** | **0 octet** | Poids `IsolationForest` / `AutoEncoder` / `One-Class SVM` non exportés par OctOpus. |
| **Précision de référence (OctOpus)** | **One-Class SVM F1 = 0.0969** (`Prec=0.09`, `Rec=0.1981`) ; **IsoForest `flood` F1 = 0.3065** (`Rec=0.9475`) | `metrics/anomaly_intelligence_metrics.csv` (30 lignes) & `anomaly_intelligence_feature_importance.csv`. |
| **Couverture** | **5 / 5 types d'anomalies critiques** (`drought`, `flood`, `heatwave`, `cold_snap`, `et0_extreme`) | `AnomalyService.HARD_THRESHOLDS`. |

---

## 2. Ce qui est opérationnel

- `AnomalyService` (`smartagri-ai/runtime/anomaly_service.py`) :
  - Supporte le chargement de `isolation_forest_champion.pkl`, `ocsvm_champion.pkl` et `autoencoder_champion.pkl` depuis `models/anomaly/`.
  - Exécute en temps réel les 5 détecteurs déterministes à seuils critiques.
  - Expose `metrics_summary()` lisant `anomaly_intelligence_metrics.csv`.
  - Intégré dans `api/app.py` (`POST /anomaly/detect`), `MonitoringEngine.assess()` et `SmartAgriOrchestrator.monitor()`.
- **Tests `pytest`** : `test_anomaly_service_thresholds_api_and_orchestrator` **PASSED** (`8 passed in 74.81s`).
