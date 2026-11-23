# 88 — SmartAgri Demo App : Architecture & Démonstration PAS Challenge

**Date** : 2026-11-18
**Équipe** : Agri-Moderne 5.0 (Mouhamadou Diop, Moustapha Diallo)
**Objectif** : Application OctOpus de démonstration intégrant les 9 modèles IA,
SmartAgri Knowledge, les agents Monitoring et Irrigation.

---

## 1. Architecture de l'Application

```
┌─────────────────────────────────────────────────────┐
│              SmartAgri Demo App                      │
├─────────────────────────────────────────────────────┤
│  Navigation : 8 pages (sidebar)                     │
│                                                     │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐            │
│  │Dashboard│ │SoilNow-  │ │Rain      │            │
│  │Exécutif │ │cast      │ │Intelli-  │            │
│  │         │ │          │ │gence     │            │
│  └─────────┘ └──────────┘ └──────────┘            │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐            │
│  │Knowledge│ │Assistant │ │Monitoring│            │
│  │Explorer │ │IA        │ │          │            │
│  └─────────┘ └──────────┘ └──────────┘            │
│  ┌─────────┐ ┌──────────┐                          │
│  │Irrigation│ │Scenario │                          │
│  │          │ │Simulator│                          │
│  └─────────┘ └──────────┘                          │
│                                                     │
│  Backend : octopus.db (tables) + octopus.ask (RAG) │
│  Design  : Tailwind + shadcn/ui + Recharts         │
└─────────────────────────────────────────────────────┘
```

### Stack technique
- React + TypeScript + Tailwind CSS
- shadcn/ui (composants)
- Recharts (graphiques)
- Framer Motion (animations)
- octopus.db.query() pour les données des 9 modèles
- octopus.ask() pour SmartAgri Knowledge (527 chunks, 75.0% recall@5)

---

## 2. Pages détaillées

### Page 1 : Dashboard Exécutif
**Objectif** : Vue synthétique des 9 modèles pour le jury.

**KPIs affichés** :
| KPI | Valeur | Source |
|-----|--------|--------|
| Modèles entraînés | 9/9 Classe A | Portfolio |
| SoilNowcast R² | 0.8428 | LightGBM 5-fold |
| ET0 Forecast R² | 0.9997 | CatBoost 5-fold |
| Rain Intelligence AUC | 0.9625 | CatBoost 5-fold |
| Price Forecast R² | 0.8995 | XGBoost 5-fold |
| Crop Calendar F1 | 0.9799 | CatBoost 5-fold |
| NDVI Anomaly F1 | 0.9818 | LightGBM 5-fold |
| Data Lake | 30M lignes | 28 datasets réels |
| Couverture | 14/14 régions | Sénégal complet |

**Graphiques** :
1. Radar des performances des 9 modèles
2. Barres comparatives LightGBM / XGBoost / CatBoost
3. Timeline du projet (données → modèles → agents → app)

### Page 2 : SoilNowcast
**Modèle** : LightGBM, R² = 0.8428, RMSE = 7.3823

**Fonctionnalités** :
- Carte interactive des 76 power cells
- Prédiction humidité sol J+1, J+2, J+3
- Feature importance (30 variables)
- Erreurs par groupe (power_cell_id)

### Page 3 : Rain Intelligence
**Modèle** : CatBoost, AUC = 0.9625, F1 = 0.7642

**Fonctionnalités** :
- Probabilité de pluie par cell
- Seuils adaptatifs par région
- SHAP explanations
- Stabilité des folds

### Page 4 : Knowledge Explorer
**Base** : 527 chunks, 75.0% recall@5

**Fonctionnalités** :
- Recherche sémantique dans la base agronomique
- Affichage des sources et scores de pertinence
- Navigation par domaine (sol, météo, cultures, irrigation)

### Page 5 : Assistant IA
**Backend** : octopus.ask() connecté à SmartAgri Knowledge

**Fonctionnalités** :
- Chat conversationnel en français
- Réponses sourcées avec citations
- Questions pré-configurées pour le jury
- Historique de conversation

**Questions de démonstration pour le jury** :
1. "Quelle est l'humidité du sol prévue demain à Niayes ?"
2. "Va-t-il pleuvoir cette semaine à Thiès ?"
3. "Quand dois-je irriguer mes tomates ?"
4. "Quelle culture recommandez-vous pour la saison sèche ?"
5. "Expliquez le modèle SoilNowcast"

### Page 6 : Monitoring
**Composants** : MonitoringEngine (12 seuils, 4 niveaux d'alerte)

**Fonctionnalités** :
- Score de risque composite en temps réel
- 4 niveaux : NORMAL / WATCH / WARNING / CRITICAL
- Tableau des alertes actives
- Historique des événements

### Page 7 : Irrigation
**Composants** : IrrigationEngine (FAO-56, 17 cultures Kc)

**Fonctionnalités** :
- Calcul besoin hydrique par culture
- Recommandation irrigation (mm/jour)
- Calendrier d'irrigation hebdomadaire
- Comparaison irrigation traditionnelle vs SmartAgri

### Page 8 : Scenario Simulator
**Modèles utilisés** : SoilNowcast + Rain + ET0 + Yield + Price

**Fonctionnalités** :
- Curseurs : température, pluie, ET0, prix marché
- Propagation en cascade (météo → sol → rendement → revenu)
- 4 scénarios pré-configurés (sécheresse, inondation, optimal, changement culture)
- Résultat : impact sur rendement et revenu estimé

---

## 3. KPIs globaux de l'application

| Catégorie | KPI | Valeur |
|-----------|-----|--------|
| **Data** | Lignes data lake | 30,073,395 |
| **Data** | Datasets réels | 28 |
| **Data** | Couverture régionale | 14/14 |
| **Modèles** | Classe A entraînés | 9/9 |
| **Modèles** | Classe B prêts | 6/6 spécifications |
| **Knowledge** | Chunks indexés | 527 |
| **Knowledge** | Recall@5 | 75.0% |
| **Monitoring** | Règles actives | 12 seuils |
| **Monitoring** | Niveaux d'alerte | 4 |
| **Irrigation** | Cultures Kc | 17 |

---

## 4. Flux utilisateur

### Parcours Jury (5 minutes)
1. **Dashboard** (30s) : Vue d'ensemble, 9 KPIs verts
2. **SoilNowcast** (45s) : Prédiction live, feature importance
3. **Rain Intelligence** (30s) : Probabilités, SHAP
4. **Assistant** (60s) : 3 questions jury, réponses sourcées
5. **Monitoring** (30s) : Alertes en cours, score de risque
6. **Scenario Simulator** (45s) : Scénario sécheresse, impact rendement
7. **Dashboard** (30s) : Retour synthèse

### Parcours Agriculteur (3 minutes)
1. Assistant → "Dois-je irriguer aujourd'hui ?"
2. Irrigation → Voir la recommandation détaillée
3. Monitoring → Vérifier les alertes
4. Knowledge → Approfondir une question technique

---

## 5. Éléments impressionnants pour les jurés

1. **9 modèles réels entraînés** sur données ouvertes du Sénégal (pas de mock)
2. **30 millions de lignes** de données réelles (NASA, CHIRPS, WFP, FAOSTAT, Sentinel-2)
3. **Assistant IA conversationnel** qui répond en français avec sources
4. **Couverture nationale** : 14/14 régions, 6 945 cellules, 76 power cells
5. **Orchestrateur IA** : routage intelligent, gestion des conflits, abstentions
6. **MLOps complet** : Feature Store, Model Registry, stratégie de retraining
7. **Scenario Simulator** : propagation en cascade multi-modèles
8. **Classe B prête** : 6 modèles spécifiés, prêts dès données terrain
9. **100% données ouvertes**, 100% reproductible, 100% documenté

---

## 6. Design

- **Palette** : vert agricole (#22c55e) + bleu données (#3b82f6) + fond sombre (#0f172a)
- **Typographie** : Inter (titres), JetBrains Mono (métriques)
- **Animations** : Framer Motion sur les KPIs et transitions de page
- **Responsive** : desktop-first, adapté tablette pour démo
- **Logo** : SmartAgri92 + PAS Challenge 2026

---

## 7. Exportabilité hors OctOpus

| Composant | Export possible | Format |
|-----------|----------------|--------|
| Modèles | Oui | ONNX, LightGBM .txt, XGBoost .json |
| Knowledge | Oui | JSON chunks + embeddings |
| Monitoring | Oui | Python standalone |
| Irrigation | Oui | Python standalone |
| Dashboard | Oui | Capture PDF / lien partagé |
| App | Oui | URL partageable OctOpus |
