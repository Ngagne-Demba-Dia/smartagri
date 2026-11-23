# 80 — SmartAgri AI Orchestrator

**Version** : 1.0 | **Date** : 2026-11-17 | **Auteur** : OctOpus x SmartAgri92

---

## 1. Vue d'ensemble

L'orchestrateur SmartAgri est le composant central qui recoit toute requete utilisateur, identifie l'intention et les entites, route vers les composants pertinents, fusionne les reponses, controle la confiance, detecte les conflits et gere les abstentions.

### Inventaire des composants IA

| # | Composant | Type | Champion | Metrique cle |
|---|-----------|------|----------|-------------|
| A1 | SoilNowcast | Regression | LightGBM | R2 = 0.835 |
| A2 | ET0 Forecast | Regression | CatBoost | R2 = 0.9997 |
| A3 | Yield Forecast | Regression | CatBoost | R2 = 0.951 |
| A4 | Rain Intelligence | Classification | CatBoost | AUC = 0.962 |
| A5 | Price Forecast | Regression | XGBoost | R2 = 0.900 |
| A6 | Crop Calendar | Classification | CatBoost | F1 = nan |
| A7 | NDVI Anomaly | Classification | LightGBM | F1 = nan |
| A8 | Anomaly Intelligence | Detection | IsoForest+AE | F1 = 0.10 |
| A9 | Market Clustering | Clustering | KMeans k=2 | Silhouette = 0.345 |
| -- | SmartAgri Knowledge | RAG | TF-IDF+cosine | Recall@5 = 0.75 |
| -- | Agent Monitoring | Decision | MonitoringEngine | 20 scenarios valides |
| -- | Agent Irrigation | Decision | FAO-56 engine | 10 scenarios valides |

---

## 2. Architecture de routage

```
                    UTILISATEUR
                        |
                   INTENT CLASSIFIER
                        |
                   ORCHESTRATOR
          /    /    |    |    |    \    \
        A1   A2   A4   A8  RAG  MON  IRR
       Soil  ET0  Rain Anom Know  Mon  Irr
```

L'orchestrateur recoit une requete, classifie l'intention, extrait les entites (parcelle, culture, region, date), appelle les composants en parallele quand possible, fusionne les reponses et renvoie un resultat structure avec score de confiance.

---

## 3. Table de routage par intention

| Intent | Composants appeles | Timeout |
|--------|-------------------|---------|
| `soil_status` | SoilNowcast | 200ms |
| `soil_forecast` | SoilNowcast + Rain Intelligence | 400ms |
| `irrigation_decision` | Agent Irrigation (SoilNowcast+Rain+ET0) | 500ms |
| `rain_forecast` | Rain Intelligence | 200ms |
| `weather_status` | ET0 Forecast + Rain Intelligence | 400ms |
| `anomaly_check` | Anomaly Intelligence + MonitoringEngine | 500ms |
| `monitoring_report` | MonitoringEngine (tous modeles) | 800ms |
| `crop_phase` | Crop Calendar | 200ms |
| `ndvi_check` | NDVI Anomaly | 200ms |
| `yield_estimate` | Yield Forecast | 300ms |
| `price_check` | Price Forecast + Market Clustering | 400ms |
| `general_knowledge` | SmartAgri Knowledge | 300ms |
| `alert_explain` | MonitoringEngine + composant source | 500ms |
| `full_report` | Tous composants | 2000ms |
| `unknown` | SmartAgri Knowledge (fallback) | 300ms |

### Code de routage

```python
ROUTING = {
    'soil_status':        ['soilnowcast'],
    'rain_forecast':      ['rain_intelligence'],
    'crop_phase':         ['crop_calendar'],
    'ndvi_check':         ['ndvi_anomaly'],
    'yield_estimate':     ['yield_forecast'],
    'irrigation_decision': ['soilnowcast','rain_intelligence','et0_forecast','agent_irrigation'],
    'weather_status':      ['et0_forecast','rain_intelligence'],
    'anomaly_check':       ['anomaly_intelligence','monitoring_engine'],
    'price_check':         ['price_forecast','market_clustering'],
    'monitoring_report':   ['soilnowcast','rain_intelligence','et0_forecast','anomaly_intelligence','monitoring_engine'],
    'full_report':         ['ALL'],
    'general_knowledge':   ['smartagri_knowledge'],
    'unknown':             ['smartagri_knowledge'],
}
```

---

## 4. Quand appeler chaque composant

### 4.1 SoilNowcast (A1)

**Appeler** : etat du sol, stress hydrique, Agent Irrigation, MonitoringEngine, rapport parcellaire.
**Ne pas appeler** : question prix/marches, ravageurs, hors couverture spatiale.
**Performances** : R2 = 0.835, RMSE = 7.45%, 42/71 cellules avec R2 > 0.85. Latence < 50ms.

### 4.2 Rain Intelligence (A4)

**Appeler** : prevision pluie 1-3j, Agent Irrigation, MonitoringEngine, risque inondation/secheresse.
**Ne pas appeler** : prix/marches, NDVI, donnees CHIRPS > 7 jours.
**Performances** : AUC = 0.962, Brier = 0.061, 71/71 cellules AUC > 0.80. Latence < 50ms.

### 4.3 ET0 Forecast (A2)

**Appeler** : evapotranspiration, bilan hydrique FAO-56, Agent Irrigation.
**Ne pas appeler** : questions sans rapport climat/eau.
**Performances** : R2 = 0.9997, RMSE = 0.039 mm/j. Quasi parfait.

### 4.4 Anomaly Intelligence (A8)

**Appeler** : detection anomalies, MonitoringEngine risk > 0.55, rapport parcellaire, mots "bizarre"/"anormal".
**Ne pas appeler** : conditions normales, prix, zone sans historique < 30j.
**Performances** : F1 = 0.10. 5 types : secheresse, canicule, exces eau, gel Niayes, ET0 extreme.

### 4.5 SmartAgri Knowledge (RAG)

**Appeler** : intent general_knowledge/unknown, questions agronomiques, enrichissement contextuel, "comment"/"pourquoi".
**Ne pas appeler** : intent resolu par modele predictif seul, requete numerique pure.
**Performances** : Recall@5 = 75%, 527 chunks, 10 domaines. Latence < 200ms.

### 4.6 MonitoringEngine

**Appeler** : monitoring_report, anomaly_check, alert_explain, bilan parcellaire, alertes.
**Ne pas appeler** : question simple, question economique, pas de parcelle.
**Flux interne** : SoilNowcast (35%) + Rain (25%) + Anomaly (25%) + ET0 (15%) -> score composite -> niveau alerte.

### 4.7 Agent Irrigation

**Appeler** : irrigation_decision, "faut-il irriguer ?", stress hydrique detecte.
**Ne pas appeler** : pas de culture identifiee, pas de SoilNowcast, sol sature en hivernage.
**Flux** : SoilNowcast -> Rain -> ET0 -> FAO-56 Kc -> bilan hydrique -> decision + dose.

### 4.8 Yield Forecast (A3)

**Appeler** : estimation rendement, bilan campagne. **R2 = 0.951**, donnees nationales (956 lignes).

### 4.9 Price Forecast (A5)

**Appeler** : prix, tendance, marches. **R2 = 0.900**, RMSE = 66.7 FCFA/kg, 39 marches.

### 4.10 Crop Calendar (A6) et NDVI Anomaly (A7)

| Composant | Appeler quand | F1 |
|-----------|--------------|-----|
| Crop Calendar | phase culturale, Kc dynamique | nan |
| NDVI Anomaly | sante vegetation, stress culture | nan |

### 4.11 Market Clustering (A9)

**Appeler** : segmentation marches, comparaison prix inter-clusters. Silhouette = 0.345 (2 clusters).

---

## 5. Gestion de la confiance

### 5.1 Score de confiance par composant

Chaque composant retourne un score [0,1] base sur sa performance mesuree et des penalites contextuelles.

```python
COMPONENT_BASELINES = {
    'soilnowcast':         {'metric': 0.835, 'threshold': 0.70},
    'rain_intelligence':   {'metric': 0.962, 'threshold': 0.80},
    'et0_forecast':        {'metric': 0.9997, 'threshold': 0.95},
    'anomaly_intelligence':{'metric': 0.10,  'threshold': 0.60},
    'yield_forecast':      {'metric': 0.951, 'threshold': 0.80},
    'price_forecast':      {'metric': 0.900, 'threshold': 0.75},
    'crop_calendar':       {'metric': nan, 'threshold': 0.90},
    'ndvi_anomaly':        {'metric': nan, 'threshold': 0.90},
}

PENALTIES = {
    'data_delay_hours':  lambda h: max(0, 1 - h/168),   # 7j max
    'new_cell':          0.60,   # -40%
    'extrapolation':     0.50,   # -50%
    'single_source':     0.80,   # -20%
    'season_mismatch':   0.70,   # -30%
}
```

### 5.2 Niveaux de confiance

| Niveau | Score | Action |
|--------|-------|--------|
| HAUTE | 0.80-1.00 | Reponse directe, decision automatique |
| BONNE | 0.60-0.79 | Reponse avec avertissement |
| MODEREE | 0.40-0.59 | Reponse prudente, verification terrain |
| FAIBLE | 0.00-0.39 | ABSTENTION, escalade humaine |

### 5.3 Confiance composite

```python
WEIGHTS = {
    'soilnowcast': 0.30, 'rain_intelligence': 0.25,
    'et0_forecast': 0.15, 'anomaly_intelligence': 0.15,
    'crop_calendar': 0.10, 'ndvi_anomaly': 0.05,
}
def composite_confidence(responses):
    tw, tc = 0, 0
    for r in responses:
        w = WEIGHTS.get(r['component'], 0.10)
        tw += w; tc += w * r['confidence']
    return tc / tw if tw > 0 else 0
```

---

## 6. Gestion des conflits entre modeles

### 6.1 Types de conflits

| Type | Exemple | Frequence |
|------|---------|-----------|
| Contradiction directe | SoilNowcast "sol sec" vs Rain "pluie hier" | ~5% |
| Incoherence temporelle | ET0 elevee mais sol sature | ~3% |
| Divergence de risque | Monitoring WARNING vs Anomaly NORMAL | ~8% |
| Conflit economique | Price hausse vs Yield bonne recolte | ~2% |

### 6.2 Regles de resolution

```python
RESOLUTION_RULES = [
    # R1: composant le plus fiable gagne si ecart confiance > 0.20
    {'condition': 'confidence_gap > 0.20', 'action': 'trust_higher'},
    # R2: securite d'abord (principe precaution)
    {'condition': 'one_says_critical', 'action': 'escalate_critical'},
    # R3: observation terrain > modele
    {'condition': 'terrain_data', 'action': 'trust_observation'},
    # R4: specialiste > generaliste
    {'condition': 'specialist_available', 'action': 'trust_specialist'},
    # R5: abstention si non resolu
    {'condition': 'unresolved', 'action': 'abstain_escalate'},
]

SPECIALIST_MAP = {
    'soil': 'soilnowcast', 'rain': 'rain_intelligence',
    'et0': 'et0_forecast', 'anomaly': 'anomaly_intelligence',
    'irrigation': 'agent_irrigation', 'price': 'price_forecast',
    'ndvi': 'ndvi_anomaly', 'phase': 'crop_calendar',
}
```

### 6.3 Exemples

**Conflit SoilNowcast vs Rain** : sol 19% (sec) mais pluie 12mm hier. Resolution : sols sableux Niayes drainent < 24h. Pas de contradiction reelle.

**Conflit Monitoring vs Anomaly** : Monitoring WARNING (risk 0.62) vs Anomaly NORMAL. Resolution : Monitoring est specialiste evaluation risque -> maintenir WARNING.

---

## 7. Gestion des abstentions

### 7.1 Quand s'abstenir

| Condition | Action |
|-----------|--------|
| Confiance < 0.40 | Abstention, pas de recommandation |
| Donnees > 7 jours | Avertissement + RAG fallback |
| Nouvelle parcelle | Confiance degradee -40%, mentionner limite |
| Hors distribution | Abstention, recommandation capteur terrain |
| Conflit non resolu | Escalade humaine |

### 7.2 Hierarchie de fallback

```
1. Modele specialise (confiance > 0.40)
   -> si abstention ->
2. SmartAgri Knowledge (Recall@5 = 75%)
   -> si pas de chunk ->
3. Regles FAO-56 statiques
   -> si hors couverture ->
4. Message d'abstention + escalade humaine
```

---

## 8. API de l'orchestrateur

### 8.1 Endpoint principal

```python
@app.post("/api/v1/orchestrate")
async def orchestrate(req: OrchestrateRequest) -> OrchestrateResponse: ...

class OrchestrateRequest(BaseModel):
    query: str
    cell_id: Optional[int] = None
    power_cell_id: Optional[str] = None
    culture: Optional[str] = None
    region: Optional[str] = None
    date: Optional[str] = None

class OrchestrateResponse(BaseModel):
    intent: str
    components_called: list[str]
    answer: str
    data: dict
    confidence: float
    confidence_level: str       # HAUTE/BONNE/MODEREE/FAIBLE
    alerts: list[dict]
    conflicts: list[dict]
    abstentions: list[dict]
    sources: list[str]
    latency_ms: float
```

### 8.2 Endpoints secondaires

| Endpoint | Methode | Description |
|----------|---------|-------------|
| `/api/v1/health` | GET | Sante de tous les composants |
| `/api/v1/components` | GET | Liste et metriques |
| `/api/v1/explain/{id}` | GET | Explication detaillee |
| `/api/v1/feedback` | POST | Retour utilisateur |
| `/api/v1/monitoring/report` | POST | Rapport complet parcellaire |

---

## 9. Latence et parallelisation

| Scenario | Composants | Latence cible |
|----------|-----------|---------------|
| Question simple | 1 | < 200ms |
| Question composite | 2-3 paralleles | < 500ms |
| Rapport complet | tous | < 2000ms |

```
Requete "Comment va ma parcelle ?"
  t=0     [PARALLELE] Soil(50ms) Rain(50ms) ET0(30ms) Anomaly(80ms)
  t=80ms  [SEQ] MonitoringEngine (20ms)
  t=100ms [SEQ] Orchestrateur fusion (10ms)
  t=110ms [OPT] LLM generation (1500ms)
  Total: ~1600ms
```

---

## 10. Observabilite

| Metrique | Alerte si |
|----------|-----------|
| Latence P95 | > 500ms |
| Taux abstention/jour | > 15% |
| Taux conflits/jour | > 10% |
| Confiance moyenne | < 0.60 |
| Taux escalade/semaine | > 5% |
| Feedback positif/semaine | < 70% |
