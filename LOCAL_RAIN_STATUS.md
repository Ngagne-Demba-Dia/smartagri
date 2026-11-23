# LOCAL_RAIN_STATUS — État Local de RainIntelligenceService (A4)

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-06B  
**Contraintes respectées** : aucun nouveau modèle développé, aucun entraînement lancé, utilisation exclusive des artefacts existants.

---

## 1. Métriques mesurées et artefacts

| Indicateur | Valeur observée | Source / Détail |
|---|---|---|
| **Statut inférence CatBoost** | ⚠️ **Abstention contrôlée (`ready=False`)** | Poids sérialisés `.cbm`/`.pkl` absents de `smartagri-ai/models/rain_intelligence/`. |
| **Temps d'inférence (abstention)** | **0,012 ms** | Mesuré via `bench_06b.py` (`abstained=True`). |
| **Mémoire consommée** | **< 1 Mo** | Pas de poids CatBoost chargés en RAM. |
| **Taille des modèles sur disque** | **0 octet** | `rain_{1d,2d,3d}_champion.cbm`/`.pkl` non exportés par OctOpus. |
| **Précision de référence (OctOpus)** | **AUC = 0.9625**, **F1 = 0.7642**, **Brier = 0.0611** | `champions_summary.json` & `metrics/wx_rain_prob_all_metrics.csv` (15 lignes CatBoost chargées via `metrics_summary()`). |
| **Couverture** | **30 / 30 features** validées ; **3 horizons** (`rain_1d`, `rain_2d`, `rain_3d`) ; **5 top features SHAP** | `features_by_model.json`, `shap/wx_rain_prob_shap_summary.csv`. |

---

## 2. Ce qui est opérationnel

- `RainIntelligenceService` (`smartagri-ai/runtime/rain_intelligence_service.py`) :
  - Charge automatiquement `rain_{1d,2d,3d}_champion.pkl` ou `.cbm` dès qu'ils sont présents dans `models/rain_intelligence/`.
  - Expose `metrics_summary()` lisant `wx_rain_prob_all_metrics.csv` (45 lignes dont 15 CatBoost) et `wx_rain_prob_shap_summary.csv`.
  - Intégré dans `api/app.py` (`POST /rain/predict`), `MonitoringEngine`, `IrrigationEngine` et `SmartAgriOrchestrator`.
- **Tests `pytest`** : `test_rain_intelligence_service_and_api` **PASSED** (`8 passed in 74.81s`).
