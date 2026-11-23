# LOCAL_RECONSTRUCTION_STATUS — État de la Reconstruction Exécutable SmartAgri AI

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-04  
**Contraintes respectées** : aucun nouveau modèle développé, `plateforme/web` et `plateforme/backend` non modifiés.

---

## 1. Vue d'ensemble par brique cible

| Brique | État actuel | Ce qui tourne déjà | Ce qui manque pour exécution locale |
|---|---|---|---|
| **SoilNowcast (A1)** | 🟡 **Artefacts prêts, runtime Python absent** | 15 modèles natifs LightGBM (`.txt`), `lgb_config.json`, `train.parquet`/`test.parquet`, métriques de référence (`soilnowcast_all_metrics.csv`). | Package `lightgbm` (non installé dans Python global), `pandas`/`pyarrow`, et module Python chargeant les 5 folds × 3 cibles (`J+1`, `J+2`, `J+3`). |
| **Knowledge (RAG)** | 🟡 **Corpus/éval prêts, index absent** | `smartagri_knowledge_chunks.csv` (527 chunks, 10 domaines) et `smartagri_knowledge_eval.csv` (20 requêtes). | Index vectoriel (`rag/embeddings/`), `sentence-transformers` + `faiss-cpu` (ou TF-IDF `scikit-learn`), et script d'indexation/requête. |
| **Agents** | 🔴 **Spécifications uniquement** | Spécifications & règles dans `docs/80_smartagri_ai_orchestrator.md`, `docs/82_smartagri_ai_runtime.md`, `docs/90_smartagri_copilot.md`, `docs/93_smartagri_full_project_export_manifest.md`. | Code `.py` exécutable dans `agents/{monitoring,irrigation,assistant,orchestrator}/` (et docs `65`–`79` absents des exports). |
| **Runtime** | 🔴 **Prototype documenté, non extrait en `.py`** | Architecture Python complète documentée dans `docs/82_smartagri_ai_runtime.md` (6 services + `SmartAgriOrchestrator`, gestion confiance/conflits/abstentions). | Extraction & adaptation en package Python exécutable + serveur `fastapi`/`uvicorn` (non installés). |
| **MLOps** | 🟡 **Configs & schémas prêts, pipelines absents** | `champions_summary.json`, `features_by_model.json`, `datasets_inventory.json`, `knowledge_stats.json`, `requirements.txt`, schémas YAML (`datasets.yaml`, `models.yaml`, `sources.yaml`), docs `84`–`87`, `SHA256SUMS.txt`. | Scripts exécutables de registre/validation/retraining (`mlops/retraining/`), et environnement virtuel Python dédié. |

---

## 2. Diagnostic de l'environnement Python local

Vérification effectuée sur **Python 3.13.14** (aucun virtualenv détecté à la racine ni dans `plateforme/`) :

- **Déjà installés** : `numpy` (`2.4.4`), `pydantic` (`2.13.4`), `pyyaml` (`6.0.3`), `matplotlib` (`3.11.0`).
- **Manquants (requis par `smartagri-ai/mlops/registry/requirements.txt`)** :
  - `lightgbm>=4.0` (inférence SoilNowcast)
  - `pandas>=2.0`, `pyarrow` (lecture Parquet Data Lake & CSV)
  - `scikit-learn>=1.3`, `scipy` (baseline TF-IDF / clustering / métriques)
  - `sentence-transformers>=2.2`, `faiss-cpu>=1.7`, `torch>=2.0` (Knowledge RAG vectoriel)
  - `fastapi>=0.100`, `uvicorn>=0.23` (Runtime API locale)
  - `xgboost>=2.0`, `catboost>=1.2`, `shap>=0.42` (uniquement si ré-entraînement A2–A9 / SHAP)

---

## 3. Ce qui tourne déjà vs ce qui manque

### Ce qui est immédiatement exploitable (données & artefacts validés)
- **Data Lake** : 27/27 fichiers `.parquet` (173,54 Mo) validés (`PAR1` + 23/23 SHA-256).
- **SoilNowcast** : 15/15 fichiers `.txt` LightGBM valides.
- **Vérité terrain & tests** : 24 tables `metrics/*.csv` et `rag/evaluation/smartagri_knowledge_eval.csv` pour valider toute reconstruction sans régression.

### Ce qui manque pour exécuter localement
1. **Un virtualenv Python isolé** (`smartagri-ai/.venv`) avec les dépendances exactes.
2. **Le code Python exécutable** pour :
   - `SoilNowcastService` (chargement des 15 `.txt` + ensemble 5 folds),
   - `KnowledgeService` (indexation des 527 chunks + recherche),
   - `MonitoringEngine`, `IrrigationEngine`, `AssistantService`, `SmartAgriOrchestrator`,
   - le point d'entrée **Runtime FastAPI** (`82_smartagri_ai_runtime.md`),
   - les scripts **MLOps** de vérification de registre et de non-régression (`metrics/*.csv`).
3. **Les poids sérialisés A2–A9** : absents des exports (les modèles A2–A9 doivent soit être ré-entraînés via les scripts `train_*.py` existants, soit être stubbés/chargés avec repli documenté dans le Runtime sans développer de nouveaux modèles).
