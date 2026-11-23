# 91 — SmartAgri Scenario Simulator

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Démonstrateur PAS Challenge

---

## 1. Vision

Le Scenario Simulator permet de tester des hypothèses agricoles ("que se
passe-t-il si…") en exploitant les 9 modèles IA entraînés. L'utilisateur
modifie une variable (pluie, température, prix, culture) et le simulateur
propage l'impact à travers tout le système SmartAgri.

**Proposition de valeur** : transformer les modèles prédictifs en outil
de planification stratégique, permettant à un technicien ou décideur
d'évaluer des scénarios avant de conseiller un agriculteur.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────┐
│              SmartAgri Scenario Simulator                 │
│                                                          │
│  ┌──────────────┐                                        │
│  │  Interface    │  "Que se passe-t-il si…"              │
│  │  Scénario     │  Curseurs · Menus · Cartes            │
│  └──────┬───────┘                                        │
│         │                                                │
│  ┌──────┴───────┐                                        │
│  │  Moteur de   │  Propagation causale                   │
│  │  Simulation  │  Cascade inter-modèles                 │
│  └──────┬───────┘                                        │
│         │                                                │
│  ┌──────┴────────────────────────────────────────┐       │
│  │           Chaîne de propagation                │       │
│  │                                                │       │
│  │  Variable modifiée                             │       │
│  │       │                                        │       │
│  │       ├── Impact direct (modèle primaire)      │       │
│  │       ├── Impact indirect (modèles dépendants) │       │
│  │       └── Impact système (agents + alertes)    │       │
│  └───────────────────────────────────────────────┘       │
│                                                          │
│  ┌──────────────────────────────────────────────┐        │
│  │  9 Modèles + 2 Agents + Knowledge            │        │
│  │  (exécution complète, pas d'approximation)    │        │
│  └──────────────────────────────────────────────┘        │
│                                                          │
│  ┌──────────────────────────────────────────────┐        │
│  │  Résultats                                    │        │
│  │  Baseline vs Scénario · Delta · Confiance     │        │
│  │  Graphiques · Tableau comparatif · Export      │        │
│  └──────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Données utilisées

Le simulateur utilise les données réelles comme **baseline** et applique
les modifications de l'utilisateur comme **delta** :

| Variable | Source baseline | Plage modifiable |
|----------|----------------|-----------------|
| Pluie quotidienne | CHIRPS (28,9M lignes) | 0 – 200 mm/jour |
| Température min/max | NASA POWER (329K) | -5°C – +55°C |
| Humidité relative | NASA POWER | 0% – 100% |
| Vent | NASA POWER | 0 – 20 m/s |
| Rayonnement solaire | NASA POWER | 0 – 35 MJ/m² |
| ET0 | FAO-56 (329K) | Recalculé automatiquement |
| Prix marché | WFP (55K) | 0 – 2 000 FCFA/kg |
| Culture | FAO-56 Kc (17) | Sélection dans la liste |
| Type de sol | iSDAsoil (13K) | Lecture seule |
| Localisation | Grid 0.05° (6 945) | Sélection sur carte |

---

## 4. Modèles utilisés — Graphe de propagation

Quand une variable est modifiée, les modèles sont appelés dans l'ordre
de dépendance :

```
Variable modifiée : PLUIE
    │
    ├── Niveau 1 (impact direct)
    │   ├── A4 Rain Intelligence (AUC=0.965) : recalcul proba
    │   ├── A1 SoilNowcast (R²=0.837) : recalcul humidité
    │   └── A8 Anomaly Intelligence : recalcul anomalies
    │
    ├── Niveau 2 (impact indirect)
    │   ├── A2 ET0 Forecast (R²=0.999) : ajustement si T change
    │   ├── Agent Irrigation : nouvelle recommandation dose
    │   └── Agent Monitoring : nouveau score de risque
    │
    └── Niveau 3 (impact système)
        ├── A3 Yield Forecast (R²=0.951) : impact rendement
        ├── A7 NDVI Anomaly (F1=0.994) : projection NDVI
        └── A5 Price Forecast (R²=0.900) : impact prix marché
```

```
Variable modifiée : TEMPÉRATURE
    │
    ├── Niveau 1
    │   ├── A2 ET0 Forecast : recalcul ET0
    │   └── A8 Anomaly : détection canicule/gel
    │
    ├── Niveau 2
    │   ├── A1 SoilNowcast : impact évaporation
    │   ├── A6 Crop Calendar : ajustement phénologie
    │   └── Agent Monitoring : alerte thermique
    │
    └── Niveau 3
        ├── A3 Yield Forecast : impact rendement
        └── Agent Irrigation : ajustement dose
```

```
Variable modifiée : PRIX MARCHÉ
    │
    ├── Niveau 1
    │   └── A5 Price Forecast : nouveau baseline
    │
    ├── Niveau 2
    │   └── A9 Market Clustering : reclassification marchés
    │
    └── Niveau 3
        └── Knowledge : conseil de commercialisation
```

---

## 5. Flux d'interaction

### 5.1 Scénario sécheresse

```
Utilisateur : "Que se passe-t-il si pas de pluie pendant 30 jours
              à Potou pour mon oignon ?"

Simulation :
  1. Baseline : pluie moyenne Nov = 0.5 mm/j → forcée à 0 mm/j
  2. SoilNowcast : humidité passe de 42% → 18% en 15 jours
  3. Anomaly : détection sécheresse (drought) à J+12
  4. Agent Monitoring : CRITICAL à J+15 (risque = 0.88)
  5. Agent Irrigation : dose augmentée : 12 mm/j → 22 mm/j
  6. Yield Forecast : rendement estimé -35% si non irrigué
  7. Price Forecast : prix oignon +12% (raréfaction)

Résultat :
  ┌───────────────────────────────────────────┐
  │           BASELINE  vs  SCÉNARIO          │
  ├───────────────────────────────────────────┤
  │ Humidité sol J+15  │  42%   →   18%      │
  │ Alerte             │  NORMAL →  CRITICAL  │
  │ Dose irrigation    │  12 mm →   22 mm/j   │
  │ Rendement estimé   │  100%  →   65%       │
  │ Prix estimé        │  280   →   314 FCFA  │
  │ Confiance          │  82%   →   71%       │
  └───────────────────────────────────────────┘
```

### 5.2 Scénario inondation

```
Utilisateur : "Impact de 100 mm de pluie en 2 jours sur le riz à
              Richard-Toll ?"

Simulation :
  1. Baseline : pluie = 5 mm/j → forcée à 50 mm/j pendant 2 jours
  2. SoilNowcast : humidité = 35% → 92% (saturation)
  3. Anomaly : flood détecté, recall = 0.95
  4. Agent Monitoring : CRITICAL immédiat (risque = 0.94)
  5. Agent Irrigation : STOP irrigation (saturation)
  6. Knowledge : protocole post-inondation riz (drainage)

Résultat :
  ┌───────────────────────────────────────────┐
  │           BASELINE  vs  SCÉNARIO          │
  ├───────────────────────────────────────────┤
  │ Humidité sol       │  35%   →   92%      │
  │ Anomalie           │  aucune →  flood     │
  │ Alerte             │  NORMAL →  CRITICAL  │
  │ Irrigation         │  8 mm  →   STOP      │
  │ Action requise     │  aucune →  drainage  │
  │ Confiance          │  82%   →   88%       │
  └───────────────────────────────────────────┘
```

### 5.3 Scénario changement de culture

```
Utilisateur : "Si je remplace l'oignon par la tomate à Mboro,
              qu'est-ce qui change ?"

Simulation :
  1. Changement Kc : 1.05 (oignon) → 1.15 (tomate)
  2. ET0 stable : 4.8 mm/j
  3. Besoin en eau : 5.04 mm/j → 5.52 mm/j (+9.5%)
  4. Crop Calendar : cycle 120j → 130j
  5. Agent Irrigation : dose quotidienne augmentée
  6. Price Forecast : prix tomate vs oignon à la récolte
  7. Yield Forecast : rendement tomate Niayes estimé

Résultat :
  ┌───────────────────────────────────────────┐
  │           OIGNON  vs  TOMATE (Mboro)      │
  ├───────────────────────────────────────────┤
  │ Kc mid             │  1.05  →   1.15      │
  │ Besoin eau/jour    │  5.0   →   5.5 mm    │
  │ Cycle              │  120j  →   130j       │
  │ Prix récolte       │  280   →   350 FCFA   │
  │ Vulnérabilité      │  flood →   heat+disease│
  │ Confiance          │  79%   →   74%        │
  └───────────────────────────────────────────┘
```

### 5.4 Scénario prix de marché

```
Utilisateur : "Impact si le prix de l'oignon chute de 30% ?"

Simulation :
  1. Baseline prix : 280 FCFA/kg → forcé à 196 FCFA/kg
  2. Market Clustering : impact sur cluster 1 (urbain dense)
  3. Knowledge : stratégies alternatives (stockage, transformation)

Résultat :
  ┌───────────────────────────────────────────┐
  │           BASELINE  vs  SCÉNARIO          │
  ├───────────────────────────────────────────┤
  │ Prix oignon        │  280   →   196 FCFA  │
  │ Marge estimée      │  +40%  →   -2%       │
  │ Marchés affectés   │  0     →   45 (cl.1) │
  │ Recommandation     │  vente →   stockage   │
  │ Confiance          │  72%   →   65%        │
  └───────────────────────────────────────────┘
```

---

## 6. Interactions

### 6.1 Modes d'utilisation

| Mode | Description | Interface |
|------|------------|-----------|
| **Curseurs** | Modifier une variable avec un slider | Web |
| **Scénario texte** | Décrire en langage naturel | Chat Copilot |
| **Comparaison** | 2-3 scénarios côte à côte | Tableau |
| **Série temporelle** | Projeter sur 30/60/90 jours | Graphique |
| **Spatial** | Appliquer à une zone sur la carte | Carte |

### 6.2 Types de scénarios supportés

| Catégorie | Variables modifiables | Modèles impliqués |
|-----------|----------------------|-------------------|
| Climatique | Pluie, T, vent, RH, radiation | A1,A2,A4,A8 |
| Hydrique | Irrigation, sol, nappe | A1,Agent Irrig. |
| Agronomique | Culture, date semis, densité | A6,A3,Know |
| Économique | Prix, coûts, marché | A5,A9 |
| Combiné | Plusieurs variables simultanées | Chaîne complète |

---

## 7. Cas d'usage

| # | Scénario | Question type | Impact mesuré |
|---|----------|--------------|---------------|
| 1 | Sécheresse 30j | Risque parcellaire | Humidité, rendement |
| 2 | Inondation | Protocole urgence | Alerte, drainage |
| 3 | Canicule | Stress thermique | ET0, irrigation |
| 4 | Changement culture | Comparaison cultures | Eau, prix, cycle |
| 5 | Hausse prix | Opportunité commerciale | Marge, stratégie |
| 6 | Baisse prix | Risque économique | Marge, stockage |
| 7 | Retard semis | Impact calendrier | Rendement, risque |
| 8 | Nouvelle zone | Faisabilité | Sol, eau, climat |
| 9 | Changement climatique | Tendance long terme | Rendement, adaptation |
| 10 | Optimisation irrigation | Dose optimale | Eau, rendement, coût |

---

## 8. Démonstration devant jury

### Scénario recommandé (5 min)

1. **Interface** (30s) : montrer les curseurs et la carte du Sénégal

2. **Sécheresse** (90s) : sélectionner Potou, oignon, mettre pluie = 0 mm
   pendant 30 jours. Montrer la cascade :
   - SoilNowcast : humidité qui chute jour par jour
   - Anomaly : détection sécheresse à J+12
   - Monitoring : passage en CRITICAL à J+15
   - Irrigation : dose qui augmente
   - Rendement : impact estimé -35%

3. **Inondation** (60s) : basculer sur Richard-Toll, riz, injecter 100 mm/2j.
   Montrer : saturation, alerte CRITICAL instantanée, STOP irrigation.

4. **Comparaison cultures** (60s) : revenir à Mboro, comparer oignon vs tomate
   côte à côte. Montrer les différences : eau, prix, cycle, risques.

5. **Transparence** (30s) : chaque résultat montre le modèle, la confiance
   et les limites.

### Métriques de démonstration

| Indicateur | Valeur |
|-----------|--------|
| Variables simulables | 10 |
| Niveaux de propagation | 3 |
| Scénarios pré-construits | 10 |
| Cultures supportées | 17 |
| Cellules spatiales | 6 945 |
| Temps de simulation | < 5s |

---

## 9. Exportabilité hors OctOpus

### Architecture de déploiement

```
smartagri-scenario-simulator/
├── simulator/
│   ├── engine.py              # Moteur de simulation
│   ├── propagation.py         # Graphe de propagation
│   ├── baseline.py            # Chargement baseline réelle
│   ├── delta.py               # Application des modifications
│   └── comparator.py          # Comparaison baseline/scénario
├── scenarios/
│   ├── presets/               # 10 scénarios pré-construits
│   │   ├── drought_30d.json
│   │   ├── flood_extreme.json
│   │   ├── heatwave.json
│   │   └── ...
│   └── schema.json            # Format de scénario
├── orchestrator/               # Réutilisation doc 80
├── models/                     # 9 modèles ONNX/natifs
├── agents/                     # Monitoring + Irrigation
├── knowledge/                  # ChromaDB
├── api/
│   ├── main.py                # FastAPI
│   ├── simulate.py            # POST /simulate
│   └── compare.py             # POST /compare
├── docker-compose.yml
└── requirements.txt
```

### Exemple d'appel API

```python
import requests

scenario = {
    "location": {"cell_id": 42, "region": "Thiès", "zone": "Niayes"},
    "culture": "oignon",
    "duration_days": 30,
    "modifications": {
        "rain_mm": 0.0,       # Sécheresse totale
    },
    "baseline": "last_90_days"  # Baseline = 90 derniers jours réels
}

response = requests.post("http://localhost:8000/simulate", json=scenario)
result = response.json()

# result = {
#   "baseline": {"soil_moisture": 42, "alert": "NORMAL", ...},
#   "scenario": {"soil_moisture": 18, "alert": "CRITICAL", ...},
#   "delta": {"soil_moisture": -24, "alert_change": "NORMAL→CRITICAL"},
#   "confidence": 0.71,
#   "propagation_chain": ["A4", "A1", "A8", "Monitoring", "A3"],
#   "recommendations": ["Irriguer 22 mm/j", "Surveiller NDVI"],
#   "sources": ["NASA POWER", "CHIRPS", "iSDAsoil"]
# }
```

---

## 10. Limites connues

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| Simulation statique (pas de feedback) | Pas de boucle dynamique | Itération manuelle |
| Baseline = moyennes historiques | Pas temps réel sans API | Extension API DATA |
| Interactions non linéaires simplifiées | Cascade unidirectionnelle | Graphe DAG suffisant |
| Pas de Monte Carlo / incertitude | Point estimate seul | Extension planifiée |
| Résolution spatiale = 0.05° (5.5 km) | Pas de parcelle fine | Kits terrain Classe B |
| Pas d'impact social/logistique | Modèles agro-climatiques seuls | Extension future |
