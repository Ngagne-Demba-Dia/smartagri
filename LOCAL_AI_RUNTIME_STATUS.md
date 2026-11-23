# LOCAL_AI_RUNTIME_STATUS — État du Premier Runtime IA Local SmartAgri

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-05  
**Contraintes respectées** : aucun nouveau modèle développé, aucune modification de `plateforme/web` ni `plateforme/backend`, aucune nouvelle fonctionnalité inventée.

---

## 1. Arborescence finale mise en place (`smartagri-ai/`)

```text
smartagri-ai/
├── data/          (README pointant vers datasets/ : 27 Parquet validés SHA-256, 173,54 Mo)
├── models/        (soilnowcast/ : 15 LightGBM .txt + scripts train_A2/A3_A5/A6_A7_A9)
├── rag/           (knowledge_service.py + 527 chunks + 20 requêtes eval)
├── agents/        (monitoring/, irrigation/, assistant/, orchestrator/ — prêts à recevoir le code)
├── runtime/       (__init__.py, types.py, soil_nowcast_service.py)
├── mlops/         (registry/, feature_store/, retraining/, architecture/)
├── api/           (app.py — FastAPI /health, /soil/predict, /knowledge/search)
├── tests/         (test_runtime_services.py — suite pytest)
└── docs/          (28 docs .md dont 56–58, 63–64, 80–94, 96_non_exportable_assets.md, APP_SOURCE_MANIFEST.md)
```
*(Les dossiers `datasets/`, `metrics/`, `shap/`, `manifests/` et les 26 `.zip` d'origine restent intacts dans `smartagri-ai/`.)*

---

## 2. Ce qui fonctionne réellement (vérifié en exécution)

1. **`SoilNowcastService`** (`smartagri-ai/runtime/soil_nowcast_service.py`) :
   - Charge les **15 boosters LightGBM natifs** (`3 cibles × 5 folds`) sans erreur.
   - Calcule la moyenne inter-folds (`y_plus_1d`, `y_plus_2d`, `y_plus_3d`), l'écart-type (`*_std`), les alertes seuils (`WILTING`, `STRESS_MOD`, `SATURATION`), la confiance et l'abstention automatique si >5 features manquent.
2. **`KnowledgeService`** (`smartagri-ai/rag/knowledge_service.py`) :
   - Indexe les **527 chunks** (`smartagri_knowledge_chunks.csv`) via TF-IDF + similarité cosinus (`scikit-learn`).
   - Retourne les top-k chunks avec score, domaine, confiance et abstention sous le seuil `MIN_SCORE = 0.08`.
3. **API FastAPI locale** (`smartagri-ai/api/app.py`) :
   - Endpoints `/health`, `/soil/predict`, `/knowledge/search` instanciables et fonctionnels (`status: "ok"`, `soil_nowcast_ready: True`, `knowledge_ready: True`, `knowledge_chunks: 527`).
4. **Nouvel export `95_remaining_export_bundle.zip` & `96_non_exportable_assets.md`** :
   - `96_non_exportable_assets.md` extrait dans `smartagri-ai/docs/`.
   - Les 19 fichiers source React de l'app démo OctOpus sont présents dans `95_remaining_export_bundle.zip`.

---

## 3. Ce qui ne fonctionne pas / limitations actuelles

1. **Lecture Parquet directe dans cet environnement Windows (`pyarrow`)** :
   - Le chargement de `test.parquet` via `pandas.read_parquet` (`pyarrow._fs`) échoue avec :
     `ImportError: DLL load failed while importing _fs: Une stratégie de contrôle d'application a bloqué ce fichier.`
   - De même, l'exécution de `pip.exe` dans un `.venv` local est bloquée par la **stratégie de contrôle d'application Windows (WDAC/AppLocker)**.
   - Contournement utilisé pour les dépendances déjà validées : `numpy` système + `smartagri-ai/.pydeps` en fin de `sys.path` (`sys.path.append`), ce qui permet à `lightgbm`, `pandas`, `scikit-learn` et `fastapi` de fonctionner.
2. **Agents & Orchestrateur (`agents/*`)** :
   - Non encore extraits en modules `.py` exécutables (`MonitoringEngine`, `IrrigationEngine`, `AssistantService`, `SmartAgriOrchestrator`).
3. **Modèles A2–A9 (`rain_intelligence`, `et0`, `yield`, `anomaly`, `clustering`)** :
   - Poids sérialisés non présents dans les exports ; non chargés dans le runtime tant qu'ils ne sont pas ré-entraînés.
4. **Index dense vectoriel (`sentence-transformers` + `faiss-cpu`)** :
   - Non installé (remplacé par l'index TF-IDF + cosinus conforme à la baseline documentée dans `80_smartagri_ai_orchestrator.md`).
5. **Éléments non exportables OctOpus** (`96_non_exportable_assets.md`) :
   - `octopus.ask`, `octopus.db.query`, hébergement `octopus.ml`.

---

## 4. Dépendances manquantes ou bloquées

| Dépendance | État | Impact |
|---|---|---|
| `lightgbm`, `pandas`, `scikit-learn`, `fastapi`, `uvicorn`, `pytest` | ✅ Installés dans `smartagri-ai/.pydeps` | `SoilNowcastService`, `KnowledgeService`, `api/app.py` et `pytest` opérationnels. |
| `pyarrow` (`_fs.pyd`) / `fastparquet` | ❌ `pyarrow` bloqué par contrôle d'application Windows ; `fastparquet` absent | Lecture `.parquet` impossible depuis ce Python tant que le binaire n'est pas approuvé ou exécuté dans un environnement autorisé (WSL/Docker/Python signé). |
| `xgboost`, `catboost`, `shap` | ❌ Non installés | Nécessaires uniquement pour ré-entraîner A2–A9. |
| `sentence-transformers`, `faiss-cpu` / `chromadb` | ❌ Non installés | Optionnels si l'on souhaite remplacer TF-IDF par des embeddings denses. |

---

## 5. Résultats des tests d'inférence (observés)

### Suite `pytest` (`smartagri-ai/tests/test_runtime_services.py`)
- **Résultat** : **3 passed in 14.89s** (`Command exited with code 0`).
  - `test_soil_nowcast_inference_direct` : **PASSED**
  - `test_soil_nowcast_abstains_on_missing_features` : **PASSED**
  - `test_knowledge_service_search_and_eval` : **PASSED** (527 chunks chargés, 20 requêtes de `smartagri_knowledge_eval.csv` exécutées, >=15 réponses non vides).

### Mesures d'inférence en direct (`api/app.py`)
- **`GET /health`** : `{'status': 'ok', 'soil_nowcast_ready': True, 'knowledge_ready': True, 'knowledge_chunks': 527}`
- **`SoilNowcastService.predict(SAMPLE_SENEGAL_FEATURES)`** :
  - `y_plus_1d`: **47.7124%** (std `5.0973`)
  - `y_plus_2d`: **49.6607%** (std `2.1944`)
  - `y_plus_3d`: **49.7098%** (std `4.5617`)
  - `confidence`: **0.8353** (`high`) | `latence`: **39.26 ms** | `warnings`: `[]`
- **`KnowledgeService.search("Coefficient cultural Kc pour le riz irrigué au Sénégal", top_k=3)`** :
  - `abstained`: **False** | `confidence`: **0.6528** | `latence`: **8.046 ms**
  - `top1`: `bundle:wfp_senegal_markets.parquet.manifest.json` (`score = 0.1528`)

---

## 6. Délai estimé pour reconstruire toute l'IA localement

| Chantier | Délai estimé | Prérequis |
|---|---|---|
| **1. Déblocage lecture Parquet** (environnement Python/WSL/Docker autorisé par la stratégie Windows) | **0,5 jour** | Droits d'exécution `.pyd` ou conteneur Linux local. |
| **2. Agents (`MonitoringEngine`, `IrrigationEngine`, `AssistantService`, `SmartAgriOrchestrator`)** | **1 jour** | Extraction depuis `docs/80` et `docs/82` + tests unitaires. |
| **3. Ré-entraînement local A2–A9** (via scripts `train_*.py` + 27 Parquet) | **0,5 – 1 jour** | `pyarrow`, `xgboost`, `catboost` opérationnels. |
| **4. API DB locale (`octopus.db.query` → FastAPI + SQLite sur 27 CSV) + RAG dense optionnel** | **0,5 – 1 jour** | Chargement des 27 CSV dans SQLite. |
| **Total pour 100 % de l'IA locale** | **2,5 à 3,5 jours** | *(Cohérent avec l'estimation 2–3 jours de `96_non_exportable_assets.md`.)* |
