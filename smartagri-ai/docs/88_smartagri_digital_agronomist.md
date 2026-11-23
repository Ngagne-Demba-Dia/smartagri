# 88 — SmartAgri Digital Agronomist

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Démonstrateur PAS Challenge

---

## 1. Vision

Le Digital Agronomist est l'incarnation finale de SmartAgri92 : un agronome
numérique qui combine 9 modèles IA, une base de connaissances agricole et deux
agents spécialisés pour fournir un conseil parcellaire complet, en temps réel,
à tout exploitant sénégalais.

**Proposition de valeur** : remplacer la disponibilité limitée de l'encadrement
agricole (1 technicien pour 3 000 exploitants, source ANCAR) par un conseiller
numérique disponible 24/7, multilingue, fondé sur des données réelles.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│              SmartAgri Digital Agronomist            │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │  Interface   │  │  Orchestrat.│  │  Mémoire   │  │
│  │  Agriculteur │──│  Central    │──│  Parcelle  │  │
│  └─────────────┘  └──────┬──────┘  └────────────┘  │
│                          │                          │
│  ┌───────────────────────┼───────────────────────┐  │
│  │           Couche Modèles IA (9)               │  │
│  │                                               │  │
│  │  A1 SoilNowcast    │ LightGBM │ R² = 0.8375  │  │
│  │  A2 ET0 Forecast   │ CatBoost │ R² = 0.9997  │  │
│  │  A3 Yield Forecast │ CatBoost │ R² = 0.9509  │  │
│  │  A4 Rain Intell.   │ CatBoost │ AUC = 0.9650 │  │
│  │  A5 Price Forecast │ XGBoost  │ R² = 0.8995  │  │
│  │  A6 Crop Calendar  │ CatBoost │ F1 = 0.9799  │  │
│  │  A7 NDVI Anomaly   │ LightGBM │ F1 = 0.9943  │  │
│  │  A8 Anomaly Intel. │ IsoForest│ Recall = 0.95│  │
│  │  A9 Market Cluster │ KMeans   │ Sil. = 0.345 │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────┼───────────────────────┐  │
│  │          Couche Agents & Knowledge            │  │
│  │                                               │  │
│  │  Agent Monitoring  │ Risque composite pondéré │  │
│  │  Agent Irrigation  │ FAO-56 + Kc 17 cultures  │  │
│  │  Knowledge Base    │ 527 chunks, Recall@5=75% │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │             Data Lake National                │  │
│  │  28 datasets │ 30,4 M lignes │ 14 régions    │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 3. Données utilisées

| Source | Lignes | Couverture | Licence |
|--------|--------|------------|---------|
| NASA POWER | 329 232 | 2015-2026, 76 mailles | NASA Open Data |
| CHIRPS v3 | 28,9 M | 2015-2026, 6 945 cellules | CC BY 4.0 |
| FAO-56 ET0 | 329 232 | 2015-2026 | NASA Open Data |
| NASA Soil Wetness | 329 232 | 2015-2026 | NASA Open Data |
| iSDAsoil | 13 890 | National, 2 profondeurs | CC BY 4.0 |
| ESA WorldCover | 6 945 | National, 10 m résolution | CC BY 4.0 |
| Sentinel-2 NDVI | 26 198 | 2025, composites mensuels | Copernicus |
| WFP Food Prices | 55 283 | 2000-2026, 79 marchés | CC BY-IGO 3.0 |
| FAOSTAT | 956 | 1961-2024, rendements | CC BY 4.0 |
| FAO-56 Kc | 900 | 17 cultures maraîchères | Domaine public |
| SmartAgri Knowledge | 527 chunks | FAO, ISRA, CSP/CILSS | CC BY 4.0 |

**Total** : 30,4 millions de lignes, zéro donnée synthétique, 14/14 régions.

---

## 4. Modèles utilisés — Performances mesurées

### A1 — SoilNowcast (champion : LightGBM)

| Cible | RMSE | R² | Folds |
|-------|------|-----|-------|
| y_plus_1d_pct | 7.41 | 0.8375 | 5 |
| y_plus_2d_pct | 7.41 | 0.8369 | 5 |
| y_plus_3d_pct | 7.52 | 0.8315 | 5 |

### A2 — ET0 Forecast (champion : CatBoost)

| Cible | RMSE | R² | Folds |
|-------|------|-----|-------|
| et0_pm_mm | 0.0390 | 0.9997 | 5 |

### A3 — Yield Forecast (champion : CatBoost)

| Cible | RMSE (t/ha) | R² | Folds |
|-------|-------------|-----|-------|
| yield_t_ha | 2.01 | 0.9509 | 5 |

### A4 — Rain Intelligence (champion : CatBoost)

| Cible | AUC | Brier | F1 | Folds |
|-------|-----|-------|-----|-------|
| rain_1d | 0.9650 | 0.0577 | 0.7734 | 5 |
| rain_2d | 0.9613 | 0.0621 | 0.7589 | 5 |
| rain_3d | 0.9612 | 0.0623 | 0.7602 | 5 |

### A5 — Price Forecast (champion : XGBoost)

| Cible | RMSE (FCFA/kg) | R² | Folds |
|-------|----------------|-----|-------|
| price | 66.67 | 0.8995 | 5 |

### A6 — Crop Calendar (champion : CatBoost)

| Métrique | Valeur |
|----------|--------|
| Accuracy | 0.9813 |
| F1 macro | 0.9799 |

### A7 — NDVI Anomaly (champion : LightGBM)

| Métrique | Valeur |
|----------|--------|
| Accuracy | 0.9976 |
| F1 macro | 0.9943 |

### A8 — Anomaly Intelligence (champion : Isolation Forest)

| Type anomalie | Precision | Recall | F1 |
|---------------|-----------|--------|-----|
| flood (inondation) | 0.183 | 0.948 | 0.307 |
| any_anomaly | 0.183 | 0.084 | 0.115 |

*Détection non supervisée : optimisé pour le rappel sur inondations
(alerte de sécurité). Le taux élevé de faux positifs est acceptable
en contexte d'alerte préventive.*

### A9 — Market Clustering (KMeans k=2)

| Métrique | Valeur |
|----------|--------|
| Silhouette | 0.345 |
| Clusters | 2 (urbain dense, rural/secondaire) |

---

## 5. Flux d'interaction

### 5.1 Question simple (< 2s)

```
Agriculteur : "Est-ce que je dois arroser mon oignon demain ?"
    │
    ├── Orchestrateur → intention : irrigation_decision
    ├── SoilNowcast → humidité prédite J+1 : 28%
    ├── Rain Intelligence → proba pluie J+1 : 12%
    ├── Agent Irrigation → dose recommandée : 18 mm
    ├── Confiance composite : 0.82 (HAUTE)
    │
    └── Réponse : "Oui, irriguez demain matin : 18 mm.
         Le sol sera à 28% d'humidité (sous le seuil de 35%
         pour l'oignon), et la probabilité de pluie est
         faible (12%). Confiance : élevée."
```

### 5.2 Diagnostic parcellaire (< 5s)

```
Agriculteur : "Mon champ de tomates va mal, que se passe-t-il ?"
    │
    ├── Orchestrateur → intention : diagnostic_parcelle
    ├── SoilNowcast → humidité sol : 22% (stress hydrique)
    ├── Anomaly Intelligence → anomalie détectée : sécheresse
    ├── NDVI Anomaly → NDVI en baisse (-0.15 vs mois précédent)
    ├── Agent Monitoring → alerte WARNING, risque = 0.68
    ├── Knowledge → recommandations ISRA pour tomate en stress
    ├── Confiance composite : 0.74 (BONNE)
    │
    └── Réponse : "Votre parcelle montre des signes de stress
         hydrique : humidité sol à 22% (seuil critique tomate :
         30%), NDVI en baisse. Recommandations : irrigation
         immédiate 25 mm, paillage, ombrage temporaire.
         Source : Guide ISRA cultures maraîchères."
```

### 5.3 Planification campagne (< 10s)

```
Agriculteur : "Je veux planter de la carotte à Mboro, quand ?"
    │
    ├── Orchestrateur → intention : conseil_campagne
    ├── Crop Calendar → fenêtre optimale : Nov-Fév
    ├── Rain Intelligence → prévisions saison sèche
    ├── ET0 Forecast → demande évaporative attendue
    ├── Price Forecast → prix carotte estimé à la récolte
    ├── Knowledge → itinéraire technique carotte Niayes
    ├── Confiance composite : 0.79 (BONNE)
    │
    └── Réponse : "La fenêtre optimale pour la carotte à Mboro
         est novembre à février. Cycle : 90 jours.
         Prix estimé à la récolte (mars) : 320 FCFA/kg.
         Irrigation : 4-5 mm/jour en saison sèche.
         Source : FAO-56 + calendrier cultural SmartAgri."
```

---

## 6. Cas d'usage

| # | Cas d'usage | Modèles impliqués | Confiance |
|---|-------------|-------------------|-----------|
| 1 | Conseil irrigation quotidien | A1, A4, Irrig. | HAUTE |
| 2 | Diagnostic stress parcellaire | A1, A7, A8, Monit. | BONNE |
| 3 | Alerte météo anticipée | A4, A2, Monit. | HAUTE |
| 4 | Planification campagne | A6, A5, A4, Know. | BONNE |
| 5 | Estimation rendement attendu | A3, A1, A4 | MODÉRÉE |
| 6 | Alerte prix de marché | A5, A9 | MODÉRÉE |
| 7 | Suivi NDVI satellite | A7, Monit. | HAUTE |
| 8 | Conseil fertilisation | Know., A1 | BONNE |
| 9 | Détection anomalie climatique | A8, A4, A2, Monit. | BONNE |
| 10 | Choix variétal adapté | Know., A6, A3 | MODÉRÉE |

---

## 7. Démonstration devant jury

### Scénario recommandé (5 min)

1. **Introduction** (30s) : présenter le Data Lake (30,4 M lignes, 14 régions)
2. **Question irrigation** (60s) : poser une question en temps réel, montrer
   le flux complet et la réponse avec sources
3. **Diagnostic parcelle** (60s) : simuler un stress hydrique, montrer
   l'activation de Monitoring + Anomaly + NDVI
4. **Planification** (60s) : planifier une campagne carotte à Mboro
5. **Architecture** (60s) : montrer le diagramme des 9 modèles, les métriques
6. **Exportabilité** (30s) : montrer que tout fonctionne hors OctOpus

### Métriques à présenter au jury

| Indicateur | Valeur |
|-----------|--------|
| Modèles entraînés | 9/9 Classe A |
| Données réelles | 30,4 M lignes |
| Couverture nationale | 14/14 régions |
| Données synthétiques | 0 |
| Dépendance cloud | 0 (exportable) |
| Temps de réponse cible | < 2s (question simple) |

---

## 8. Exportabilité hors OctOpus

### Stack de déploiement local

```
smartagri-digital-agronomist/
├── models/
│   ├── soilnowcast/          # LightGBM .txt + ONNX
│   ├── et0_forecast/          # CatBoost .cbm + ONNX
│   ├── yield_forecast/        # CatBoost .cbm + ONNX
│   ├── rain_intelligence/     # CatBoost .cbm + ONNX
│   ├── price_forecast/        # XGBoost .json + ONNX
│   ├── crop_calendar/         # CatBoost .cbm + ONNX
│   ├── ndvi_anomaly/          # LightGBM .txt + ONNX
│   ├── anomaly_intelligence/  # Isolation Forest .pkl
│   └── market_clustering/     # KMeans .pkl
├── knowledge/
│   ├── chunks/                # 527 chunks JSON
│   ├── embeddings/            # multilingual-e5-large
│   └── index/                 # ChromaDB
├── agents/
│   ├── monitoring_engine.py
│   ├── irrigation_engine.py
│   └── orchestrator.py
├── api/
│   ├── main.py                # FastAPI
│   └── schemas.py             # Pydantic
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Dépendances Python

```
lightgbm==4.5.0
xgboost==2.1.0
catboost==1.2.7
scikit-learn==1.5.2
onnxruntime==1.19.0
fastapi==0.115.0
chromadb==0.5.0
sentence-transformers==3.3.0
numpy==1.26.4
pandas==2.2.3
```

### Commandes de déploiement

```bash
docker compose up -d
# API disponible sur http://localhost:8000
# Docs : http://localhost:8000/docs
```

---

## 9. Limites connues

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| SoilNowcast = proxy NASA, pas capteurs | Biais possible vs terrain | Calibration B6 planifiée |
| Anomaly = non supervisé, F1 faible | Faux positifs fréquents | Seuils adaptatifs + escalade |
| Knowledge = 527 chunks | Couverture partielle | Extension avec nouvelles sources |
| Yield = données FAOSTAT nationales | Pas de granularité locale | Extension avec données parcellaires |
| Price = WFP mensuel | Pas de prix journaliers | Extension avec relevés terrain |
| Pas de données capteurs réels | Validation terrain absente | Pilote Mboro/Potou planifié |
