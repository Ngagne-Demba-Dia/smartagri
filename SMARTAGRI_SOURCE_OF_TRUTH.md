# SMARTAGRI_SOURCE_OF_TRUTH — Référentiel Définitif SmartAgri AI

**Date** : 2026-11-17  
**Périmètre** : `smartagri-ai/` (indépendant de `plateforme/web` et `plateforme/backend`, qui restent intacts).

---

## 1. Ce qui vient directement d'OctOpus (actifs sources immuables)

1. **Modèle A1 SoilNowcast** :
   - 15 boosters natifs LightGBM (`smartagri-ai/models/soilnowcast/lgb_y_plus_{1d,2d,3d}_pct_fold{0..4}.txt`) + `lgb_config.json`.
2. **Data Lake Sénégal complet** :
   - 25 fichiers Parquet bruts (`smartagri-ai/datasets/raw/`) + 2 fichiers curés `train.parquet` / `test.parquet` (`smartagri-ai/datasets/curated/`), 173,54 Mo sur disque, validés `PAR1` et `23/23` SHA-256.
3. **Tables de vérité, métriques & SHAP** :
   - 27/27 tables CSV (`smartagri-ai/metrics/`, `smartagri-ai/rag/`, `smartagri-ai/shap/wx_rain_prob_shap_summary.csv`) + `lgb_feature_importance.png`.
4. **Corpus RAG** :
   - `smartagri-ai/rag/chunks/smartagri_knowledge_chunks.csv` (527 chunks, 10 domaines) et `smartagri-ai/rag/evaluation/smartagri_knowledge_eval.csv` (20 requêtes).
5. **Documentation, schémas & manifests** :
   - 25 documents `.md` (`56`–`58`, `63`–`64`, `80`–`94`, `96`, `rapport_analyse_bundle_smartagri92.md`), 9 docs `octopus_import/`, 10 schémas `*_SCHEMA.md`, configs JSON/YAML (`mlops/`) et 26 archives `.zip` originales conservées.
   - 3 scripts d'entraînement (`train_A2_et0.py`, `train_A3_yield_A5_price.py`, `train_A6_A7_A9.py`).

---

## 2. Ce qui a été reconstruit localement (exécutable & testé)

1. **Services d'inférence** (`smartagri-ai/runtime/`) :
   - `SoilNowcastService` : inférence réelle sur les 15 LightGBM `.txt` (~19–39 ms).
   - `RainIntelligenceService` : chargeur local CatBoost + métriques/SHAP + abstention contrôlée tant que les poids `.cbm`/`.pkl` manquent.
   - `AnomalyService` : chargeur local `IsolationForest`/`One-Class SVM`/`AutoEncoder` + **5 seuils métier critiques actifs** (`drought`, `flood`, `heatwave`, `cold_snap`, `et0_extreme`).
2. **RAG dense vectoriel** (`smartagri-ai/rag/`) :
   - `KnowledgeService` reconstruit avec **`intfloat/multilingual-e5-large` + `FAISS` (`IndexFlatIP`)** sur les 527 chunks, persisté dans `rag/embeddings/e5_large_chunks.npy` (2,16 Mo) et `e5_large.faiss` (repli TF-IDF conservé).
3. **Agents & Orchestrateur** (`smartagri-ai/agents/`) :
   - `MonitoringEngine`, `IrrigationEngine` (FAO-56 + garde-fou pluie > 5 mm), `AssistantService`, `SmartAgriOrchestrator` (routage multi-intentions, abstentions, escalade).
4. **API & MLOps locaux** (`smartagri-ai/api/`, `smartagri-ai/mlops/`) :
   - API FastAPI autonome (`api/app.py`) : `/health`, `/mlops/registry`, `/soil/predict`, `/rain/predict`, `/anomaly/detect`, `/knowledge/search`, `/agents/monitor`, `/agents/irrigate`, `/agents/assistant`, `/orchestrator/ask`.
   - `LocalModelRegistry` (`mlops/registry/registry.py`) et `validate_metrics.py` (`mlops/retraining/validate_metrics.py`).
5. **Validation automatisée** :
   - Suite `pytest` (`tests/test_runtime_services.py`) : **8 / 8 PASSED**.
   - Démonstrateur 30 scénarios (`runtime/demo_e2e_30.py`) : **30 / 30 exécutés** (**15 `PASSED`**, **15 `PARTIAL`** par absence de poids A4/A3/A5/A6/A7/A9, **0 `FAILED`**).

---

## 3. Ce qui reste à reconstruire

1. **Poids sérialisés des 8 modèles A2–A9** :
   - Ré-entraîner `A2_ET0`, `A3_Yield`, `A4_Rain`, `A5_Price`, `A6_Crop_Calendar`, `A7_NDVI_Anomaly`, `A8_Anomaly` (`IsolationForest`/`AutoEncoder`/`OCSVM`) et `A9_Market_Clustering` à partir des 27 Parquet de `datasets/` et des hyperparamètres de `docs/93`, dans un environnement où `pyarrow`, `catboost` et `xgboost` ne sont pas bloqués par la stratégie de contrôle d'application Windows (ex. WSL, Docker Linux, ou Python approuvé).
2. **Couche DB locale (`octopus.db.query`)** :
   - Charger les 27 tables CSV de `metrics/` et `rag/` dans SQLite/PostgreSQL et exposer `GET /db/{collection}` si l'on souhaite reproduire l'API `octopus.db.query`.
3. **Intégration applicative (hors périmètre actuel)** :
   - Brancher le runtime local `smartagri-ai/` sur `plateforme/backend/` et `plateforme/web/` lorsque l'intégration produit démarrera.
