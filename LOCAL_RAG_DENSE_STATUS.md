# LOCAL_RAG_DENSE_STATUS — État Local de KnowledgeService (`multilingual-e5-large` + `FAISS`)

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-06B — Étape 3  
**Statut** : ✅ **OPÉRATIONNEL EN LOCAL (`backend = e5_large+faiss`)**

---

## 1. Métriques mesurées en exécution réelle (`bench_06b.py` & `pytest`)

| Indicateur | Valeur observée | Détail |
|---|---|---|
| **Backend actif** | **`e5_large+faiss`** (`faiss_err=None`) | `intfloat/multilingual-e5-large` (`sentence-transformers 6.3.0`, `torch 2.15.0+cpu`) + `faiss.IndexFlatIP`. |
| **Temps de construction initial** | **732,22 s** (incluant téléchargement initial + encodage des 527 chunks) | Index persisté sur disque pour les démarrages suivants. |
| **Temps d'inférence (requête)** | **Moyenne = 445,00 ms** / **P95 = 753,02 ms** | Mesuré sur les 20 requêtes de `smartagri_knowledge_eval.csv` (CPU). |
| **Mémoire consommée (pic Python)** | **2 606,2 Mo** (pic `tracemalloc` incluant modèle `e5-large` + `SoilNowcast` + `FAISS`) | Modèle `intfloat/multilingual-e5-large` chargé en RAM. |
| **Taille des artefacts sur disque** | **`e5_large_chunks.npy` = 2,16 Mo** (+ `e5_large.faiss` dans `rag/embeddings/`) | Embeddings `float32` normalisés des 527 chunks (dimension 1024). |
| **Précision / Évaluation** | **`20/20` requêtes non vides** (`100%` au-dessus du seuil `0.65`) ; **`12/20` (60%) correspondance exacte `top_domain` dans top-5** | Évalué sur `rag/evaluation/smartagri_knowledge_eval.csv` (sans filtre domaine ; note : `smartagri_knowledge_eval.csv` reflétait les scores TF-IDF d'origine). |
| **Couverture du corpus** | **527 / 527 chunks (100 %)**, **10 / 10 domaines** | Chargés depuis `rag/chunks/smartagri_knowledge_chunks.csv`. |

---

## 2. Architecture mise en place

- **`smartagri-ai/rag/knowledge_service.py`** :
  - Préfixe `"passage: ..."` lors de l'indexation et `"query: ..."` lors de la recherche, conformément au protocole `intfloat/multilingual-e5-large`.
  - Persistance automatique dans `smartagri-ai/rag/embeddings/e5_large_chunks.npy` et `smartagri-ai/rag/embeddings/e5_large.faiss`.
  - Repli automatique sur produit scalaire `numpy` ou `tfidf+cosine` si un composant est absent.
- **Validation `pytest`** : `test_phase2_knowledge_service_and_eval` et l'ensemble des 8 tests (`test_runtime_services.py`) : **8 passed in 74.81s**.
