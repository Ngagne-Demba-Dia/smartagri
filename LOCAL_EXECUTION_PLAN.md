# LOCAL_EXECUTION_PLAN — Plan d'Exécution de la Reconstruction Locale

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-04  
**Règle stricte** : aucun nouveau modèle, aucune modification de `plateforme/web` ni `plateforme/backend`. Tout s'exécute dans `smartagri-ai/`.

---

## 1. Dépendances exactes

### Dépendances système & Python
- **Python** : `>=3.10` (testé localement sur `3.13.14`).
- **Environnement virtuel dédié** : `smartagri-ai/.venv` (isolé du Python global et de `plateforme/`).

### Dépendances par couche (alignées sur `smartagri-ai/mlops/registry/requirements.txt`)

| Couche | Packages exacts requis | Usage |
|---|---|---|
| **Socle Data & Config** | `numpy>=1.24`, `pandas>=2.0`, `pyarrow`, `pyyaml`, `pydantic>=2.0` | Lecture des 27 Parquet (`datasets/`), CSV (`metrics/`, `rag/`), YAML (`mlops/architecture/`). |
| **SoilNowcast (A1)** | `lightgbm>=4.0` | Chargement natif des 15 fichiers `lgb_y_plus_{1d,2d,3d}_pct_fold{0..4}.txt` via `lightgbm.Booster(model_file=...)`. |
| **Knowledge (RAG)** | `scikit-learn>=1.3` *(mode TF-IDF léger)* **ou** `sentence-transformers>=2.2`, `faiss-cpu>=1.7`, `torch>=2.0` *(mode vectoriel dense)* | Indexation des 527 chunks (`smartagri_knowledge_chunks.csv`) et validation `Recall@5 >= 0.75` sur `smartagri_knowledge_eval.csv`. |
| **Agents & Runtime** | `fastapi>=0.100`, `uvicorn>=0.23` | Exposition locale de `SmartAgriOrchestrator`, `MonitoringEngine`, `IrrigationEngine`, `AssistantService` (sans toucher `plateforme/backend`). |
| **MLOps (optionnel si ré-entraînement A2–A9)** | `xgboost>=2.0`, `catboost>=1.2`, `shap>=0.42`, `matplotlib>=3.7` | Exécution des scripts `train_A2_et0.py`, `train_A3_yield_A5_price.py`, `train_A6_A7_A9.py` et validation contre `metrics/*.csv`. |

---

## 2. Ordre strict de reconstruction

### Phase 0 — Environnement & Socle MLOps (`mlops/`)
1. Créer `smartagri-ai/.venv` et installer le socle :
   ```powershell
   python -m venv smartagri-ai\.venv
   smartagri-ai\.venv\Scripts\python -m pip install --upgrade pip
   smartagri-ai\.venv\Scripts\pip install numpy pandas pyarrow pyyaml pydantic lightgbm scikit-learn fastapi uvicorn
   ```
   *(Ajouter `sentence-transformers faiss-cpu torch` si vous activez l'index dense FAISS ; `xgboost catboost shap` uniquement pour ré-entraîner A2–A9.)*
2. Vérifier l'intégrité des artefacts via `smartagri-ai/manifests/SHA256SUMS.txt`.
3. Mettre en place le chargeur de registre MLOps (`mlops/registry/`) lisant `champions_summary.json`, `features_by_model.json` et `mlops/architecture/models.yaml`.
   - **Critère de validation** : lecture sans erreur des 9 entrées modèles et des 30 features de `A1_SoilNowcast`.

### Phase 1 — SoilNowcast (`models/soilnowcast/`)
1. Implémenter `SoilNowcastService` (spécifié dans `docs/82_smartagri_ai_runtime.md` §2.1 et `docs/64_soilnowcast_productization.md`) :
   - Charger les 15 `Booster` LightGBM (`3 cibles × 5 folds`).
   - Moyenne des 5 folds par horizon (`J+1`, `J+2`, `J+3`) + calcul d'incertitude (écart-type inter-folds) et niveau de confiance.
2. Valider sur un échantillon de `datasets/curated/soil_nowcast_proxy_national/v=20261114-natl01/test.parquet`.
   - **Critère de validation** : inférence sans erreur et métriques cohérentes avec `metrics/soilnowcast_all_metrics.csv` (`R² ≈ 0.8353`, `RMSE ≈ 7.447`).

### Phase 2 — Knowledge / RAG (`rag/`)
1. Implémenter l'indexation de `rag/chunks/smartagri_knowledge_chunks.csv` (527 chunks) :
   - **Option rapide (sans GPU / sans téléchargement HuggingFace)** : TF-IDF + cosine (`scikit-learn`), conforme à `docs/80_smartagri_ai_orchestrator.md` (ligne 24 : `TF-IDF+cosine | Recall@5 = 0.75`).
   - **Option dense** : `sentence-transformers` + `faiss-cpu`, sauvegarde de l'index dans `rag/embeddings/`.
2. Implémenter `KnowledgeService.search(query, top_k=5)`.
   - **Critère de validation** : exécution de `rag/evaluation/smartagri_knowledge_eval.csv` (20 requêtes) avec `Recall@5 >= 0.75`.

### Phase 3 — Agents (`agents/`)
Construire les 4 modules Python à partir des spécifications exactes déjà présentes :
1. **`agents/monitoring/`** (`MonitoringEngine`) : 8 seuils configurables (sol, pluie, ET0, NDVI), 4 niveaux d'alerte (`NORMAL → WATCH → WARNING → CRITICAL`), d'après `docs/82_smartagri_ai_runtime.md` §2.5 et `docs/93` §10.
2. **`agents/irrigation/`** (`IrrigationEngine`) : bilan hydrique FAO-56 (`ETc = Kc × ET0`), 17 cultures avec courbes `Kc` (`datasets/raw/crops_senegal/fao56_crop_coefficients_daily.parquet`), règle garde-fou *ne pas irriguer si pluie > 5 mm dans 24h* (`docs/82_smartagri_ai_runtime.md` §2.6 et `docs/93` §10).
3. **`agents/assistant/`** (`AssistantService`) : prompt système français + assemblage contexte (`SoilNowcast` + `KnowledgeService` + `IrrigationEngine`), d'après `docs/90_smartagri_copilot.md` et `docs/93` §10.
4. **`agents/orchestrator/`** (`SmartAgriOrchestrator`) : routage des 15 intentions, timeouts (`200ms–2s`), gestion des conflits (`confiance > précaution > terrain > spécialiste > abstention`), d'après `docs/80_smartagri_ai_orchestrator.md` et `docs/82_smartagri_ai_runtime.md` §3–7.
   - **Critère de validation** : exécution des scénarios types documentés dans `docs/81_ai_execution_flows.md` et `docs/83_runtime_scenarios.md`.

### Phase 4 — Runtime Exécutable (`smartagri-ai/runtime/`)
1. Extraire le runtime complet de `docs/82_smartagri_ai_runtime.md` en package Python exécutable (`answer()`, `monitor()`, `recommend()`, `escalate()`).
2. Exposer une API FastAPI locale autonome (ex. port `8010`, distincte de `plateforme/backend`) avec `/health`, `/predict/soil`, `/knowledge/search`, `/agents/monitor`, `/agents/irrigate`, `/orchestrator/ask`.
   - **Critère de validation** : `uvicorn` démarre en local et tous les endpoints répondent avec le schéma `ServiceResponse` (`confidence`, `confidence_level`, `warnings`, `abstained`, `latency_ms`).

### Phase 5 — Boucle MLOps & Ré-entraînement optionnel (`mlops/retraining/`)
1. Script de contrôle de dérive / non-régression comparant les sorties locales aux 24 CSV de `metrics/`.
2. *(Optionnel, sans créer de nouveaux modèles)* : si besoin des binaires locaux A2–A9, exécuter les scripts existants `models/et0/train_A2_et0.py`, `models/yield/train_A3_yield_A5_price.py`, `models/clustering/train_A6_A7_A9.py` sur `datasets/raw/`.

---

## 3. Matrice de dépendances entre phases

```text
Phase 0 (venv + MLOps Registry)
   ├──▶ Phase 1 (SoilNowcast A1) ──┐
   └──▶ Phase 2 (Knowledge RAG)  ──┼──▶ Phase 3 (Agents: Monitoring, Irrigation, Assistant, Orchestrator)
                                   │         │
                                   └─────────┴──▶ Phase 4 (Runtime FastAPI local)
                                                       │
                                                       ▼
                                                  Phase 5 (MLOps validation / ré-entraînement A2–A9)
```
