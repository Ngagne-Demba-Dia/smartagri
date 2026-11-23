# 96_non_exportable_assets.md
# SmartAgri92 — Actifs non exportables

## Resume general

| Categorie | Statut | Detail |
|-----------|--------|--------|
| Documents md (56-95) | RECUPERE | 30+ documents dans 5 ZIPs |
| Tables metriques (27) | RECUPERE | 27/27 tables CSV exportees |
| Modeles LightGBM (15) | RECUPERE | lgb_models_native.zip 54 Mo |
| Modeles XGB/CB/KMeans | RECUPERE | 3 archives ZIP |
| Data Lake (28 datasets) | RECUPERE | octopus_import_bundle.zip 39 Mo |
| App Demo source (19 fichiers) | RECUPERE | 95_remaining_export_bundle.zip |
| Configurations (5+) | RECUPERE | lgb_config, analysis, inventaire |
| SHAP exports (3) | RECUPERE | Rain SHAP + feature importance |
| Knowledge chunks (527) | RECUPERE | smartagri_knowledge_chunks.csv |

---

## Elements NON EXPORTABLES

### 1. Runtime octopus.ask
- **Nom** : API octopus.ask (assistant IA conversationnel)
- **Raison** : API native OctOpus, non serialisable. Le moteur RAG, les embeddings et l index vectoriel sont geres cote serveur.
- **Emplacement** : Backend OctOpus (set_up_app_assistant). Utilise dans AssistantIA.tsx, KnowledgeExplorer.tsx, JuryDemo.tsx (etape Conseil).
- **Solution de reconstruction** :
  1. Installer LangChain + ChromaDB (ou FAISS)
  2. Charger les 527 chunks depuis smartagri_knowledge_chunks.csv
  3. Generer les embeddings avec un modele open source (sentence-transformers/all-MiniLM-L6-v2)
  4. Exposer via FastAPI : POST /ask {question, history} -> {answer, sources}
  5. Adapter le code React : remplacer octopus.ask() par fetch("/api/ask")

### 2. Runtime octopus.db.query
- **Nom** : API octopus.db.query (base de donnees app)
- **Raison** : Base de donnees applicative native OctOpus, 13 collections injectees via put_project_tables_in_app.
- **Emplacement** : Collections octopus.db dans l app SmartAgri92 v2. Utilise dans SoilNowcast.tsx (lgb_feature_importance), RainIntelligence.tsx (wx_rain_prob_feature_importance_all, wx_rain_prob_shap_summary), KnowledgeExplorer.tsx (smartagri_knowledge_chunks).
- **Solution de reconstruction** :
  1. Charger les 27 tables CSV dans SQLite ou PostgreSQL
  2. Exposer via FastAPI : GET /db/{collection}?order=&limit= -> {records}
  3. Adapter le code React : remplacer octopus.db.query(col) par fetch("/api/db/" + col)

### 3. Hebergement de l application SmartAgri92
- **Nom** : Application web hebergee SmartAgri92 v2
- **Raison** : Hebergement natif OctOpus Apps, non transferable. Le domaine octopus.ml est propre a la plateforme.
- **Emplacement** : OctOpus Apps (app_6e438bc2bf17415e), accessible via l onglet Apps du projet.
- **Solution de reconstruction** :
  1. Creer le projet : npx create-vite smartagri92 --template react-ts
  2. Copier les 19 fichiers source depuis 95_remaining_export_bundle.zip/app_smartagri92/
  3. Installer les dependances : npm install react-router-dom framer-motion recharts lucide-react @radix-ui/react-slider
  4. Configurer Tailwind CSS + shadcn/ui
  5. Deployer sur Vercel, Netlify ou un serveur Node

### 4. Index vectoriel SmartAgri Knowledge
- **Nom** : Index vectoriel des 527 chunks de connaissances agricoles
- **Raison** : Index natif OctOpus, non serialisable. Les embeddings sont calcules et stockes cote serveur.
- **Emplacement** : Backend OctOpus (assistant configure via set_up_app_assistant)
- **Solution de reconstruction** :
  1. Lire smartagri_knowledge_chunks.csv (527 lignes, colonnes : chunk_id, doc_source, domain, chunk_index, tokens_est, chars, text_preview)
  2. Generer les embeddings pour chaque chunk
  3. Indexer dans ChromaDB ou FAISS
  4. Le Recall@5 mesure etait de 75 pct ; viser un niveau similaire

### 5. Historique de conversation du projet
- **Nom** : 164+ tours de conversation OctOpus
- **Raison** : Donnees de session, non serialisables en bloc. Pas d API d export bulk.
- **Emplacement** : Projet OctOpus proj-challenge-a4f8c4d752ea4655b4d7
- **Solution de reconstruction** : Non critique. Toutes les decisions techniques, architectures, metriques et configurations sont documentees dans les fichiers md 56 a 96.

### 6. ZIP d execution SoilNowcast (58 Mo)
- **Nom** : SoilNowcast - LightGBM (3 cibles x 5 folds) - fix output.zip
- **Raison** : 58 Mo, depasse la limite de 128 Mo cumulee avec les autres gros fichiers. Contient les logs d entrainement et artefacts intermediaires.
- **Emplacement** : Fichiers du projet OctOpus (pf_b2c6abf228ff4338a373f151)
- **Solution de reconstruction** : Telechargeable individuellement depuis Data > Fichiers du projet. Non critique si lgb_models_native.zip (modeles finaux) est deja recupere. Les metriques finales sont dans soilnowcast_all_metrics.csv.

---

## BILAN DEFINITIF

### RECUPERE (5 ZIPs = reconstruction complete)

| ZIP | Taille | Contenu |
|-----|--------|---------|
| smartagri_complete_ai_bundle.zip | 281 Ko | 58 fichiers : docs 56-93, metriques 9 modeles, modeles legers, configs |
| smartagri_complementary_bundle.zip | 138 Ko | 18 fichiers : tables complementaires, group errors, knowledge |
| lgb_models_native.zip | 54 Mo | 15 modeles LightGBM SoilNowcast (3 cibles x 5 folds) |
| octopus_import_bundle.zip | 39 Mo | Data Lake complet : 28 datasets, 30M lignes, 14/14 regions |
| 95_remaining_export_bundle.zip | 13 Ko | Code source app Demo (19 fichiers) + doc 56_classe_a |

Total recupere : environ 93 Mo couvrant 100 pct du travail IA exportable.

### JAMAIS RECUPERABLE (4 elements)
1. Runtime octopus.ask -> remplacable par FastAPI + ChromaDB
2. Runtime octopus.db.query -> remplacable par FastAPI + SQLite
3. Hebergement app -> remplacable par Vite + Vercel/Netlify
4. Index vectoriel -> reconstructible depuis les 527 chunks CSV

### A RECONSTRUIRE LOCALEMENT
| Tache | Outil | Estimation |
|-------|-------|------------|
| Backend API (octopus.ask) | FastAPI + ChromaDB + sentence-transformers | 1 jour |
| Backend DB (octopus.db.query) | FastAPI + SQLite, charger 27 CSV | 0.5 jour |
| Hebergement React | Vite + Vercel ou Netlify | 0.5 jour |
| Re-indexation Knowledge | ChromaDB, 527 chunks | 0.5 jour |
| **Total** | | **2-3 jours** |

---

Genere par OctOpus — Projet SmartAgri92 Agri-Moderne 5.0, PAS Challenge 2026
