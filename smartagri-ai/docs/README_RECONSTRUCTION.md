# SmartAgri92 — Complete AI Bundle
## README de Reconstruction

**Équipe** : Agri-Moderne 5.0 (Mouhamadou Diop, Moustapha Diallo)
**Challenge** : PAS Challenge 2026 — Thème Agriculture
**Plateforme** : OctOpus ML

---

## Contenu du bundle

Ce ZIP contient l'intégralité du travail IA SmartAgri92 exportable :

### 1_documentation/ (11 + 4 fichiers)
Tous les documents techniques clés (56-93), incluant portfolio, architecture,
plans d'entraînement, rapports, agents, MLOps et démonstrateurs.

### 2_models/ (3 archives)
Modèles entraînés légers (ET0, Yield/Price, CropCal/NDVI/Clustering).
**Note** : lgb_models_native.zip (54 Mo) est à télécharger séparément.

### 3_metrics/ (15+ tables CSV)
Métriques de tous les 9 modèles : R², RMSE, MAE, AUC, F1, accuracy par fold.

### 4_shap/ (SHAP + figures)
Résumé SHAP Rain Intelligence + figure feature importance SoilNowcast.

### 5_features/ (7 tables)
Feature importance pour les 9 modèles (LightGBM, XGBoost, CatBoost).

### 6_knowledge/ (2 tables)
527 chunks de connaissances + 20 évaluations de retrieval.

### 7_agents/ (specs dans documentation)
Monitoring Engine, Irrigation Engine, Assistant Parcellaire, Orchestrator.

### 8_mlops/ (3 docs)
Model Registry, Feature Store, Retraining Strategy.

### 8_configs/ (fichiers JSON)
Configuration LightGBM, inventaire datasets, quality checks.

### 9_app_demo/ (4 docs)
App démo PAS Challenge (88), Copilot (90), Simulator (91).

### 10_manifest/ (2 fichiers)
92_export_manifest.md + 93_full_project_export_manifest.md.

---

## Fichiers volumineux (téléchargements séparés)

Ces fichiers dépassent la limite du bundle et doivent être téléchargés
individuellement depuis OctOpus > Data > Fichiers du projet :

| Fichier | Taille | Contenu |
|---------|--------|---------|
| lgb_models_native.zip | ~54 Mo | 15 modèles LightGBM SoilNowcast |
| octopus_import_bundle.zip | ~39 Mo | Data Lake complet (28 datasets, 30M lignes) |

---

## Reconstruction SmartAgri IA

### Prérequis

```bash
pip install lightgbm xgboost catboost scikit-learn pandas numpy flask
```

### Ordre de lecture recommandé

1. **Ce README** — vue d'ensemble
2. **93_smartagri_full_project_export_manifest.md** — inventaire complet
3. **56_real_ai_portfolio.md** — portfolio des 9 modèles
4. **84_smartagri_mlops_architecture.md** — architecture de production
5. **82_*.md** — runtime IA exécutable
6. **80_smartagri_ai_orchestrator.md** — routage intelligent
7. **88_smartagri_demo_app.md** — architecture de l'app démo

### Étapes de reconstruction

1. Installer les dépendances Python.
2. Extraire octopus_import_bundle.zip → Data Lake (28 datasets).
3. Extraire lgb_models_native.zip → 15 modèles LightGBM.
4. Extraire les modèles légers de ce bundle (2_models/).
5. Charger les 27 tables CSV de métriques (3_metrics/ + 5_features/).
6. Reconstruire l'index Knowledge à partir de 6_knowledge/chunks.csv.
7. Implémenter les agents depuis les specs (7_agents/).
8. Déployer avec FastAPI selon 84_smartagri_mlops_architecture.md.

---

## Modèles champions — Résumé

| Modèle | Champion | Métrique principale |
|--------|----------|---------------------|
| SoilNowcast | LightGBM | r2=0.8353, rmse=7.45 |
| ET0 Forecast | CatBoost | r2=0.9997, rmse=0.0390 |
| Rain Intelligence | CatBoost | auc=0.9625, f1=0.764 |
| Yield Forecast | CatBoost | r2=0.9509, rmse=2.01 |
| Price Forecast | XGBoost | r2=0.8995, rmse=66.67 |
| Anomaly Intelligence | One-Class SVM + Autoencoder |  |
| Market Clustering | KMeans | k=2, silhouette=0.3446 |

---

## Licences

Toutes les données incluses sont sous licence ouverte (CC BY 4.0, NASA Open Data,
CC BY-IGO 3.0). Voir octopus_import_bundle.zip/OCTOPUS_IMPORT_README.md pour le
détail par source.

---

*SmartAgri92 — PAS Challenge 2026 — Équipe Agri-Moderne 5.0*
