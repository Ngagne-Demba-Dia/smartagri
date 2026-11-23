# 89 — SmartAgri Knowledge Graph

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Démonstrateur PAS Challenge

---

## 1. Vision

Le Knowledge Graph SmartAgri structure les relations entre tous les composants
du système : cultures, sols, climat, marchés, modèles IA et recommandations.
Il permet de naviguer dans l'espace de connaissance agricole du Sénégal de
manière relationnelle plutôt que documentaire.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│              SmartAgri Knowledge Graph                   │
│                                                         │
│  ┌─────────┐    produit_sur    ┌──────────┐             │
│  │ Culture ├───────────────────│  Région  │             │
│  └────┬────┘                   └────┬─────┘             │
│       │                             │                   │
│  nécessite                     contient                 │
│       │                             │                   │
│  ┌────┴────┐    influence     ┌─────┴─────┐             │
│  │  Sol    ├──────────────────│  Climat   │             │
│  └────┬────┘                  └─────┬─────┘             │
│       │                             │                   │
│  mesuré_par                    prédit_par               │
│       │                             │                   │
│  ┌────┴────────┐    alimente  ┌─────┴─────────┐         │
│  │ SoilNowcast ├─────────────│ Rain Intell.  │         │
│  │ R²=0.8375   │             │ AUC=0.9650    │         │
│  └─────────────┘             └───────────────┘         │
│                                                         │
│  ┌─────────┐   vendu_à    ┌─────────┐                  │
│  │ Récolte ├──────────────│ Marché  │                  │
│  └────┬────┘              └────┬────┘                  │
│       │                       │                        │
│  estimé_par               regroupé_par                 │
│       │                       │                        │
│  ┌────┴──────────┐   ┌───────┴──────────┐              │
│  │ Yield Forecast│   │ Market Clustering│              │
│  │ R²=0.9509     │   │ Sil.=0.345       │              │
│  └───────────────┘   └──────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Nœuds du graphe

### 3.1 Entités physiques

| Type de nœud | Instances | Source | Attributs clés |
|-------------|-----------|--------|----------------|
| **Région** | 14 | geoBoundaries ADM1 | nom, population, superficie |
| **Cellule grille** | 6 945 | senegal_grid_0p05 | lat, lon, cell_id, validation_zone |
| **Maille météo** | 76 | power_cells_0p5x0p625 | power_cell_id |
| **Marché** | 79 | WFP | nom, région, lat, lon, cluster |
| **Culture** | 17 | FAO-56 Kc | nom, Kc_ini, Kc_mid, Kc_end, cycle_jours |
| **Type de sol** | 6 945×2 | iSDAsoil | sand%, clay%, SOC, pH, bulk_density |
| **Occupation** | 6 945 | ESA WorldCover | share_crop, share_tree, share_bare |

### 3.2 Entités temporelles

| Type de nœud | Instances | Fréquence | Source |
|-------------|-----------|-----------|--------|
| **Jour météo** | 329 232 | Quotidien | NASA POWER |
| **Jour pluie** | 28,9 M | Quotidien × cellule | CHIRPS |
| **Relevé prix** | 55 283 | Mensuel × marché | WFP |
| **Composite NDVI** | 26 198 | Mensuel × cellule | Sentinel-2 |
| **Rendement annuel** | 956 | Annuel × culture | FAOSTAT |

### 3.3 Entités IA

| Type de nœud | Instances | Attributs |
|-------------|-----------|-----------|
| **Modèle IA** | 9 | nom, champion, métrique, R²/AUC/F1 |
| **Agent** | 2 | Monitoring, Irrigation |
| **Chunk Knowledge** | 527 | source, domaine, tokens |
| **Alerte** | 4 niveaux | NORMAL, WATCH, WARNING, CRITICAL |

---

## 4. Relations

### 4.1 Relations spatiales

| Relation | Source → Cible | Cardinalité | Clé |
|----------|---------------|-------------|-----|
| `contient` | Région → Cellule | 1:N | region → cell_id |
| `agrège` | Maille météo → Cellule | 1:N | power_cell_id → cell_id |
| `localise` | Marché → Région | N:1 | market → region |
| `couvre` | Occupation → Cellule | 1:1 | cell_id |
| `caractérise` | Sol → Cellule | 1:1 | cell_id × profondeur |

### 4.2 Relations temporelles

| Relation | Source → Cible | Fréquence |
|----------|---------------|-----------|
| `mesure_météo` | Maille → Jour | Quotidien |
| `mesure_pluie` | Cellule → Jour | Quotidien |
| `mesure_ndvi` | Cellule → Mois | Mensuel |
| `mesure_prix` | Marché → Mois | Mensuel |
| `mesure_rendement` | Culture → Année | Annuel |

### 4.3 Relations agronomiques

| Relation | Description | Exemple |
|----------|------------|---------|
| `produit_sur` | Culture → Région | Oignon → Niayes |
| `nécessite_sol` | Culture → Type de sol | Carotte → sableux (sand>60%) |
| `nécessite_eau` | Culture → ET0 × Kc | Tomate → 5.2 mm/j × Kc_mid=1.15 |
| `sensible_à` | Culture → Type anomalie | Riz → inondation |
| `vendu_à` | Culture → Marché | Oignon → Diaobé, Touba |
| `concurrent_de` | Marché → Marché | Même cluster, même culture |

### 4.4 Relations IA

| Relation | Description | Exemple |
|----------|------------|---------|
| `prédit` | Modèle → Variable | SoilNowcast → humidité J+1 |
| `utilise_feature` | Modèle → Variable | Rain → rain_chirps_sum_7d |
| `alimente` | Modèle → Agent | SoilNowcast → Irrigation Engine |
| `déclenche` | Agent → Alerte | Monitoring → WARNING |
| `documente` | Chunk → Culture | ISRA_guide → tomate |

---

## 5. Données utilisées

| Couche | Tables | Lignes | Rôle dans le graphe |
|--------|--------|--------|---------------------|
| Spatiale | senegal_grid, power_cells, worldcover, isdasoil | 27 856 | Structure des nœuds |
| Climatique | nasa_power, chirps (×12), et0 | 29,6 M | Relations temporelles |
| Agricole | faostat, fao56_kc | 1 856 | Relations culture-sol |
| Marché | wfp_prices, wfp_markets | 55 362 | Relations prix-marché |
| Satellite | s2_ndvi, deafrica_catalog | 46 920 | Relations NDVI |
| Knowledge | 527 chunks | 527 | Relations documentaires |

---

## 6. Modèles utilisés

Chaque modèle IA est un **nœud du graphe** relié à ses entrées, ses sorties et
ses performances mesurées :

| Modèle | Entrées (relations) | Sorties (relations) | Performance |
|--------|---------------------|---------------------|-------------|
| A1 SoilNowcast | météo, pluie, sol | humidité J+1/2/3 | R² = 0.8375 |
| A2 ET0 Forecast | météo | ET0 mm/j | R² = 0.9997 |
| A3 Yield Forecast | météo, pluie, culture | rendement t/ha | R² = 0.9509 |
| A4 Rain Intell. | météo, pluie historique | proba pluie J+1/2/3 | AUC = 0.9650 |
| A5 Price Forecast | prix historiques, météo | prix FCFA/kg | R² = 0.8995 |
| A6 Crop Calendar | météo, culture, Kc | phase culturale | F1 = 0.9799 |
| A7 NDVI Anomaly | NDVI, météo | anomalie NDVI | F1 = 0.9943 |
| A8 Anomaly Intel. | toutes variables | type anomalie | Recall flood = 0.95 |
| A9 Market Cluster | prix, marchés | cluster marché | Sil. = 0.345 |

---

## 7. Flux et interactions

### 7.1 Requête par navigation relationnelle

```
Agriculteur : "Quel est le meilleur moment pour planter des carottes
              dans la zone de Mboro ?"

Graphe traversé :
  Mboro → cell_id (validation_zone = mboro)
       → Sol (sand_pct = 78%, clay_pct = 8%)
       → Climat (via power_cell_id)
       → Crop Calendar → fenêtre : Nov-Fév
       → ET0 Forecast → ET0 moyen saison sèche : 4.8 mm/j
       → Rain Intelligence → proba pluie Nov : 3%
       → Price Forecast → prix carotte Mars : 320 FCFA/kg
       → Knowledge → itinéraire technique carotte Niayes
```

### 7.2 Détection de risque par propagation

```
Événement : pluie extrême détectée (CHIRPS > 50 mm/3j)

Propagation dans le graphe :
  Cellule affectée
       → Anomaly Intelligence → type : flood, recall = 0.95
       → SoilNowcast → humidité prédite : 89% (saturation)
       → Cultures sur cellule → riz (tolérant), oignon (vulnérable)
       → Agent Monitoring → CRITICAL pour oignon, WATCH pour riz
       → Marchés connectés → alerte approvisionnement
       → Knowledge → guide gestion post-inondation
```

---

## 8. Cas d'usage

| # | Cas | Traversée du graphe | Nœuds touchés |
|---|-----|---------------------|---------------|
| 1 | Diagnostic parcellaire | Cellule → Sol → Climat → Modèles | 8-12 |
| 2 | Planification campagne | Culture → Région → Calendrier → Prix | 6-10 |
| 3 | Alerte chaîne de valeur | Anomalie → Cultures → Marchés | 5-8 |
| 4 | Comparaison inter-régionale | Régions → Cellules → Moyennes | 15-30 |
| 5 | Traçabilité prédiction | Réponse → Modèle → Features → Source | 4-6 |
| 6 | Impact climatique | Climat → Sol → Culture → Rendement | 6-8 |

---

## 9. Démonstration devant jury

### Scénario recommandé (5 min)

1. **Vue d'ensemble** (60s) : afficher le graphe complet, 7 types de nœuds,
   30,4 M relations temporelles
2. **Navigation** (90s) : partir d'une parcelle à Mboro, traverser le graphe
   jusqu'à une recommandation d'irrigation
3. **Propagation d'alerte** (60s) : injecter un événement pluie extrême,
   montrer la cascade dans le graphe
4. **Traçabilité** (60s) : cliquer sur une prédiction, remonter jusqu'à
   la source de données originale (NASA/CHIRPS/WFP)
5. **Chiffres** (30s) : 9 modèles, 6 945 cellules, 28 datasets, 527 chunks

### Statistiques du graphe

| Indicateur | Valeur |
|-----------|--------|
| Types de nœuds | 7 physiques + 4 IA = 11 |
| Nœuds physiques | ~7 200 (cellules + marchés + cultures + régions) |
| Relations spatiales | ~14 000 |
| Relations temporelles | ~30,4 M |
| Relations agronomiques | ~1 200 |
| Relations IA | ~100 |

---

## 10. Exportabilité hors OctOpus

### Implémentation recommandée

```python
# Option 1 : NetworkX (léger, en mémoire)
import networkx as nx

G = nx.DiGraph()
# Nœuds
G.add_node("mboro_cell_42", type="cellule", lat=15.17, lon=-16.96)
G.add_node("oignon", type="culture", Kc_mid=1.05, cycle=120)
G.add_node("SoilNowcast", type="model", r2=0.8375, champion="LightGBM")
# Relations
G.add_edge("oignon", "mboro_cell_42", relation="produit_sur")
G.add_edge("SoilNowcast", "mboro_cell_42", relation="prédit")

# Option 2 : Neo4j (scalable, production)
# CREATE (m:Cellule {id: 'mboro_42', lat: 15.17, lon: -16.96})
# CREATE (o:Culture {nom: 'oignon', Kc_mid: 1.05})
# CREATE (o)-[:PRODUIT_SUR]->(m)
```

### Stack recommandé

| Composant | Prototype | Production |
|-----------|-----------|-----------|
| Graphe | NetworkX | Neo4j Community |
| Requêtes | Python | Cypher |
| Visualisation | Pyvis | Neo4j Browser |
| API | FastAPI | FastAPI + Neo4j Driver |

### Structure exportable

```
smartagri-knowledge-graph/
├── graph/
│   ├── nodes/               # CSV par type de nœud
│   ├── edges/               # CSV par type de relation
│   └── schema.json          # Schéma du graphe
├── loaders/
│   ├── load_networkx.py
│   └── load_neo4j.cypher
├── api/
│   ├── main.py
│   └── traversal.py
├── visualization/
│   └── dashboard.py         # Pyvis
└── requirements.txt
```

---

## 11. Limites connues

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| Relations temporelles volumineuses | Mémoire NetworkX > 4 Go | Fenêtre glissante 90 jours |
| Pas de graphe dynamique temps réel | Latence de mise à jour | Batch quotidien |
| Relations causales non validées | Corrélation ≠ causalité | Documentation explicite |
| Granularité FAOSTAT = nationale | Pas de rendement local | Extension données parcellaires |
