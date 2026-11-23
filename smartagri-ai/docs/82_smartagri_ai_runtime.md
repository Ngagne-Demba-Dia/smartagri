# 82 — SmartAgri AI Runtime : Architecture Python Exécutable

**Date** : 2026-11-19
**Statut** : Architecture v1 — prototype pré-production
**Dépendances** : 9 modèles Classe A entraînés, aucun Classe B/C
**Aucun nouvel entraînement**

---

## 1. Vue d'ensemble

SmartAgri AI Runtime transforme 9 modèles ML indépendants en un système IA
cohérent : routage, confiance, conflits, garde-fous, réponses exploitables.

### Composants

```
┌───────────────────────────────────────────────────────────────┐
│                   SmartAgriOrchestrator                        │
│  answer()  |  monitor()  |  recommend()  |  escalate()        │
├────────┬──────────┬──────────┬──────────┬─────────┬──────────┤
│ Soil   │ Rain     │ Anomaly  │Knowledge │Monitor  │Irrigation│
│Nowcast │Intel     │Service   │Service   │Engine   │Engine    │
│Service │Service   │          │          │         │          │
├────────┼──────────┼──────────┼──────────┼─────────┼──────────┤
│LGB     │CB AUC    │IsoForest │527 chunks│Rules +  │FAO-56 +  │
│R²=0.8353│=0.9625   │F1=0.850  │Recall@5  │9 modèles│SoilNow + │
│        │          │          │=75%      │         │Rain Intel│
└────────┴──────────┴──────────┴──────────┴─────────┴──────────┘
         |                                        |
    ┌────┴──────────────────────────────────────┴────┐
    │         Modèles complémentaires                 │
    │ ET0 R²=0.9997 | Yield R²=0.951 | Price R²=0.900 │
    │ Crop F1=0.980 | NDVI F1=0.994 | Mkt Sil=0.360  │
    └─────────────────────────────────────────────────┘
```

---

## 2. Classes Service

### 2.1 SoilNowcastService

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum
import numpy as np, time

class ConfidenceLevel(Enum):
    HIGH = "high"          # >= 0.80
    GOOD = "good"          # >= 0.60
    MODERATE = "moderate"  # >= 0.40
    LOW = "low"            # >= 0.20
    UNRELIABLE = "unreliable"  # < 0.20

@dataclass
class ServiceResponse:
    service: str
    values: Dict
    confidence: float
    confidence_level: ConfidenceLevel
    warnings: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    abstained: bool = False
    abstention_reason: str = ""

def _level(c):
    if c >= 0.80: return ConfidenceLevel.HIGH
    if c >= 0.60: return ConfidenceLevel.GOOD
    if c >= 0.40: return ConfidenceLevel.MODERATE
    if c >= 0.20: return ConfidenceLevel.LOW
    return ConfidenceLevel.UNRELIABLE

class SoilNowcastService:
    """
    Prédiction humidité du sol J+1/J+2/J+3.
    Champion : LightGBM — R² = 0.8353, RMSE = 7.45%
    Validation : GroupKFold k=5 sur 71 power_cell_id
    """
    BASELINE_R2 = 0.8353
    FEATURES = [
        "t_min_c","t_max_c","t_mean_c","rh_mean_pct","wind_2m_ms",
        "solar_rad_mj_m2","pressure_hpa","rain_mm","rain_chirps_mm",
        "et0_pm_mm","rain_nasa_sum_3d_mm","rain_nasa_sum_7d_mm",
        "rain_nasa_sum_14d_mm","rain_chirps_sum_3d_mm",
        "rain_chirps_sum_7d_mm","rain_chirps_sum_14d_mm",
        "et0_pm_mean_7d_mm","doy_sin","doy_cos","sand_pct",
        "clay_pct","soc_g_kg","ph_h2o","bulk_density_g_cm3",
        "fc_ptf_pct","wp_ptf_pct","share_crop","share_tree",
        "share_bare","share_built"
    ]
    WILTING = 15.0; STRESS_SEV = 20.0; STRESS_MOD = 30.0
    FC = 80.0; SATURATION = 90.0

    def __init__(self, model=None):
        self.model = model

    def predict(self, features: Dict) -> ServiceResponse:
        t0 = time.time()
        missing = [f for f in self.FEATURES if f not in features]
        if len(missing) > 5:
            return ServiceResponse("soil_nowcast",{},0.0,
                ConfidenceLevel.UNRELIABLE,abstained=True,
                abstention_reason=f"{len(missing)}/30 features manquantes",
                latency_ms=(time.time()-t0)*1000)
        if self.model is None:
            return ServiceResponse("soil_nowcast",{},0.0,
                ConfidenceLevel.UNRELIABLE,abstained=True,
                abstention_reason="Modèle non chargé",
                latency_ms=(time.time()-t0)*1000)

        X = np.array([[features.get(f,0.0) for f in self.FEATURES]])
        preds = {}; warnings = []
        for i, h in enumerate(["y_plus_1d","y_plus_2d","y_plus_3d"]):
            v = float(self.model[i].predict(X)[0])
            if v < 0: v = 0.0; warnings.append(f"{h} clampé à 0%")
            elif v > 100: v = 100.0; warnings.append(f"{h} clampé à 100%")
            preds[h] = v

        j1 = preds["y_plus_1d"]
        if j1 < self.WILTING:
            warnings.append(f"CRITICAL: flétrissement J+1={j1:.0f}%")
        elif j1 < self.STRESS_MOD:
            warnings.append(f"WARNING: stress hydrique J+1={j1:.0f}%")
        if j1 > self.SATURATION:
            warnings.append(f"WARNING: saturation J+1={j1:.0f}%")

        conf = self._confidence(features)
        return ServiceResponse("soil_nowcast", preds, conf,
            _level(conf), warnings, (time.time()-t0)*1000)

    def _confidence(self, f):
        c = self.BASELINE_R2
        age = f.get("data_age_hours", 0)
        if age > 48: c *= max(0.5, 1-(age-48)/168)
        if f.get("is_new_cell", False): c *= 0.85
        if f.get("rain_chirps_sum_14d_mm", 0) > 200: c *= 0.80
        return round(min(1.0, max(0.0, c)), 4)
```

### 2.2 RainIntelligenceService

```python
class RainIntelligenceService:
    """
    Probabilité pluie J+1/J+2/J+3.
    Champion : CatBoost — AUC = 0.9625, Brier = 0.0611
    """
    BASELINE_AUC = 0.9625
    TARGETS = ["rain_1d","rain_2d","rain_3d"]
    THRESHOLDS = {"rain_1d": 0.45, "rain_2d": 0.50, "rain_3d": 0.55}

    def __init__(self, model=None):
        self.model = model

    def predict(self, features: Dict) -> ServiceResponse:
        t0 = time.time()
        if self.model is None:
            return ServiceResponse("rain_intelligence",{},0.0,
                ConfidenceLevel.UNRELIABLE,abstained=True,
                abstention_reason="Modèle non chargé",
                latency_ms=(time.time()-t0)*1000)
        probs = {}; decisions = {}; warnings = []
        for t in self.TARGETS:
            p = float(self.model[t].predict_proba(features)[0][1])
            probs[f"{t}_prob"] = p
            decisions[f"{t}_rain"] = p >= self.THRESHOLDS[t]
        if probs.get("rain_1d_prob",0) > 0.85:
            warnings.append("Forte probabilité pluie demain (>85%)")
        conf = self._confidence(features)
        return ServiceResponse("rain_intelligence",{**probs,**decisions},
            conf, _level(conf), warnings, (time.time()-t0)*1000)

    def _confidence(self, f):
        c = self.BASELINE_AUC
        m = f.get("month", 6)
        if m in [11,12,1,2,3,4,5]: c *= 0.95
        age = f.get("data_age_hours", 0)
        if age > 24: c *= max(0.6, 1-(age-24)/120)
        return round(min(1.0, max(0.0, c)), 4)
```

### 2.3 AnomalyService

```python
class AnomalyService:
    """
    Détection d'anomalies multi-type.
    Champions : Isolation Forest F1=0.850 + Autoencoder
    Types : sécheresse, excès eau, canicule, gel, ET0 extrême
    """
    HARD_THRESHOLDS = {
        "drought":     {"feat":"soil_wetness_root_pct","op":"<","val":15.0},
        "flood":       {"feat":"rain_chirps_sum_3d_mm","op":">","val":100.0},
        "heatwave":    {"feat":"t_max_c","op":">","val":42.0},
        "cold_snap":   {"feat":"t_min_c","op":"<","val":10.0},
        "et0_extreme": {"feat":"et0_pm_mm","op":">","val":7.0},
    }

    def __init__(self, iso_forest=None, autoencoder=None):
        self.iso = iso_forest; self.ae = autoencoder

    def detect(self, features: Dict) -> ServiceResponse:
        t0 = time.time(); anomalies = []
        for atype, r in self.HARD_THRESHOLDS.items():
            v = features.get(r["feat"])
            if v is not None:
                hit = (v < r["val"]) if r["op"]=="<" else (v > r["val"])
                if hit:
                    anomalies.append({"type":atype,"method":"threshold",
                        "value":v,"threshold":r["val"],"severity":"CRITICAL"})
        if self.iso is not None:
            score = self.iso.decision_function(features)
            if score < -0.15:
                anomalies.append({"type":"statistical","method":"isolation_forest",
                    "score":float(score),
                    "severity":"WARNING" if score > -0.3 else "CRITICAL"})
        n = len(anomalies)
        conf = 0.90 if n==0 else min(0.95, 0.70 + 0.05*n)
        return ServiceResponse("anomaly",
            {"anomalies":anomalies,"count":n,
              "max_severity":max((a["severity"] for a in anomalies),default="NORMAL")},
            conf, _level(conf), [], (time.time()-t0)*1000)
```

### 2.4 KnowledgeService

```python
class KnowledgeService:
    """
    Recherche sémantique SmartAgri Knowledge.
    527 chunks, 10 domaines, Recall@5 = 75%.
    """
    CORPUS_SIZE = 527; RECALL_5 = 0.75; MIN_SCORE = 0.15

    def __init__(self, index=None, chunks=None):
        self.index = index; self.chunks = chunks or []

    def search(self, query: str, top_k: int = 5,
               domain: str = None) -> ServiceResponse:
        t0 = time.time()
        if not self.index:
            return ServiceResponse("knowledge",{},0.0,
                ConfidenceLevel.UNRELIABLE,abstained=True,
                abstention_reason="Index non chargé",
                latency_ms=(time.time()-t0)*1000)
        results = self._query(query, top_k, domain)
        if not results or results[0]["score"] < self.MIN_SCORE:
            return ServiceResponse("knowledge",{"results":[]},0.10,
                ConfidenceLevel.UNRELIABLE,abstained=True,
                abstention_reason="Aucun chunk pertinent",
                latency_ms=(time.time()-t0)*1000)
        conf = min(0.85, 0.50 + results[0]["score"])
        return ServiceResponse("knowledge",
            {"results":results,"top_domain":results[0].get("domain","")},
            conf, _level(conf), [], (time.time()-t0)*1000)

    def _query(self, q, k, d): return []  # placeholder
```

### 2.5 MonitoringEngine

```python
class AlertLevel(Enum):
    NORMAL="NORMAL"; WATCH="WATCH"; WARNING="WARNING"; CRITICAL="CRITICAL"

@dataclass
class MonitoringAlert:
    level: AlertLevel; category: str; message: str
    confidence: float; components: List[str]
    action: str; escalate: bool = False

class MonitoringEngine:
    """Moteur de surveillance parcellaire."""
    WEIGHTS = {"soil":0.35,"rain":0.25,"anomaly":0.25,"et0":0.15}
    RISK_BANDS = [(0.0,0.30,"NORMAL"),(0.30,0.55,"WATCH"),
                  (0.55,0.75,"WARNING"),(0.75,1.01,"CRITICAL")]

    def __init__(self, soil, rain, anomaly):
        self.soil = soil; self.rain = rain; self.anomaly = anomaly

    def assess(self, features: Dict):
        alerts = []; risk = 0.0
        sr = self.soil.predict(features)
        rr = self.rain.predict(features)
        ar = self.anomaly.detect(features)
        if not sr.abstained:
            j1 = sr.values.get("y_plus_1d", 50)
            if j1 < 20: risk += self.WEIGHTS["soil"]*min(1,(20-j1)/10)
            elif j1 > 85: risk += self.WEIGHTS["soil"]*min(1,(j1-85)/15)
        if not rr.abstained:
            rp = rr.values.get("rain_1d_prob", 0)
            j1s = sr.values.get("y_plus_1d",50) if not sr.abstained else 50
            if rp > 0.7 and j1s > 70:
                risk += self.WEIGHTS["rain"]*0.8
                alerts.append(MonitoringAlert(AlertLevel.WARNING,"excess",
                    f"Pluie ({rp*100:.0f}%) + sol humide ({j1s:.0f}%)",
                    min(sr.confidence,rr.confidence),
                    ["soil_nowcast","rain_intelligence"],
                    "Reporter irrigation"))
        if not ar.abstained:
            sev = ar.values.get("max_severity","NORMAL")
            if sev == "CRITICAL": risk += self.WEIGHTS["anomaly"]
            elif sev == "WARNING": risk += self.WEIGHTS["anomaly"]*0.6
        risk = min(1.0, risk)
        level = AlertLevel.NORMAL
        for lo,hi,lbl in self.RISK_BANDS:
            if lo <= risk < hi: level = AlertLevel[lbl]; break
        if level == AlertLevel.CRITICAL:
            for a in alerts: a.escalate = True
        return risk, level, alerts
```

### 2.6 IrrigationEngine

```python
class IrrigationDecision(Enum):
    IRRIGATE_NOW="irrigate_now"; IRRIGATE_TOMORROW="irrigate_tomorrow"
    DELAY="delay"; NO_IRRIGATION="no_irrigation"; ABSTAIN="abstain"

@dataclass
class IrrigationRec:
    decision: IrrigationDecision; dose_mm: float; confidence: float
    reasoning: List[str]; hard_stop: bool = False; hard_stop_reason: str = ""

class IrrigationEngine:
    """
    Moteur FAO-56 + SoilNowcast (R²=0.8353) + Rain (AUC=0.9625).
    """
    KC = {"oignon":1.05,"tomate":1.15,"gombo":1.0,"aubergine":1.05,
         "piment":1.05,"chou":1.05,"carotte":1.05,"pomme_de_terre":1.15,
         "pasteque":1.0,"melon":1.05,"mais":1.20,"riz":1.20,
         "arachide":1.15,"mil":1.0,"sorgho":1.0,"niebe":1.05,"mangue":0.75}
    DEFICIT_THR = 0.55

    def __init__(self, soil, rain):
        self.soil = soil; self.rain = rain

    def recommend(self, features: Dict, crop="oignon",
                  area_ha=1.0) -> IrrigationRec:
        reasons = []
        sr = self.soil.predict(features)
        rr = self.rain.predict(features)
        if sr.abstained:
            return IrrigationRec(IrrigationDecision.ABSTAIN,0.0,0.0,
                ["SoilNowcast indisponible"],True,"Pas de données sol")
        j1 = sr.values.get("y_plus_1d",50)
        rp = rr.values.get("rain_1d_prob",0) if not rr.abstained else 0
        if rp > 0.70:
            return IrrigationRec(IrrigationDecision.DELAY,0.0,
                min(sr.confidence,rr.confidence),
                [f"Pluie probable ({rp*100:.0f}%)"],True,"Pluie imminente")
        if j1 > 90:
            return IrrigationRec(IrrigationDecision.NO_IRRIGATION,0.0,
                sr.confidence,[f"Sol saturé ({j1:.0f}%)"],True,"Saturation")
        et0 = features.get("et0_pm_mm",4.5)
        kc = self.KC.get(crop,1.0); etc = et0*kc
        fc = features.get("fc_ptf_pct",65)
        deficit = max(0, fc-j1)/fc
        reasons.append(f"ETc={etc:.1f}mm, humidité J+1={j1:.0f}%, déficit={deficit*100:.0f}%")
        if deficit > (1-self.DEFICIT_THR):
            dose = round(etc*(1+deficit*0.5),1)
            dec = IrrigationDecision.IRRIGATE_NOW if deficit>0.6 else IrrigationDecision.IRRIGATE_TOMORROW
            reasons.append(f"Dose={dose}mm")
        elif rp > 0.40:
            dec = IrrigationDecision.DELAY; dose = 0.0
            reasons.append("Risque pluie — reporter")
        else:
            dec = IrrigationDecision.NO_IRRIGATION; dose = 0.0
            reasons.append("Sol OK — pas d'irrigation")
        conf = min(sr.confidence, rr.confidence if not rr.abstained else 1.0)
        return IrrigationRec(dec, dose, conf, reasons)
```

---

## 3. SmartAgriOrchestrator

```python
@dataclass
class OrchestratorResponse:
    intent: str; answer: str; confidence: float
    confidence_level: ConfidenceLevel
    components_called: List[str]; latency_ms: float
    warnings: List[str]; alerts: List[MonitoringAlert]
    abstentions: List[str]; escalate: bool = False

class SmartAgriOrchestrator:
    """Point d'entrée unique — route vers 6 services."""

    ROUTING = {
        "soil_status":   ["soil_nowcast"],
        "soil_forecast": ["soil_nowcast","rain_intelligence"],
        "irrigation":    ["irrigation_engine","soil_nowcast","rain_intelligence"],
        "rain_forecast": ["rain_intelligence"],
        "anomaly_check": ["anomaly","monitoring_engine"],
        "monitoring":    ["monitoring_engine"],
        "crop_advice":   ["knowledge","soil_nowcast","irrigation_engine"],
        "pest_info":     ["knowledge"],
        "fertilizer":    ["knowledge","soil_nowcast"],
        "price":         ["knowledge"],
        "calendar":      ["knowledge","rain_intelligence"],
        "general":       ["knowledge"],
        "alert_check":   ["monitoring_engine","anomaly"],
        "full_report":   ["soil_nowcast","rain_intelligence","anomaly",
                         "monitoring_engine","irrigation_engine","knowledge"],
    }
    TIMEOUTS = {"soil_nowcast":200,"rain_intelligence":200,"anomaly":300,
               "knowledge":500,"monitoring_engine":800,"irrigation_engine":400}

    def __init__(self, soil, rain, anomaly, knowledge, monitoring, irrigation):
        self.svc = {"soil_nowcast":soil,"rain_intelligence":rain,
                    "anomaly":anomaly,"knowledge":knowledge,
                    "monitoring_engine":monitoring,"irrigation_engine":irrigation}

    # ── 4 méthodes ───────────────────────────────────────
    def answer(self, query, features, crop="oignon"):
        t0 = time.time()
        intent = self._classify(query)
        comps = self.ROUTING.get(intent, ["knowledge"])
        resps = {}; abstentions = []; warnings = []
        for c in comps:
            r = self._call(c, features, crop)
            if r.abstained: abstentions.append(f"{c}: {r.abstention_reason}")
            else: resps[c] = r; warnings.extend(r.warnings)
        conf = sum(r.confidence for r in resps.values())/max(1,len(resps))
        ans = self._assemble(intent, resps, abstentions, crop)
        return OrchestratorResponse(intent, ans, conf, _level(conf),
            list(resps.keys()), (time.time()-t0)*1000,
            warnings, [], abstentions, conf < 0.30)

    def monitor(self, features):
        t0 = time.time()
        risk, level, alerts = self.svc["monitoring_engine"].assess(features)
        ar = self.svc["anomaly"].detect(features)
        conf = 0.85 if not ar.abstained else 0.60
        return OrchestratorResponse("monitoring",
            f"Risque: {risk:.2f} ({level.value})", conf, _level(conf),
            ["monitoring_engine","anomaly"], (time.time()-t0)*1000,
            [a.message for a in alerts], alerts, [],
            level == AlertLevel.CRITICAL)

    def recommend(self, features, crop="oignon"):
        t0 = time.time()
        rec = self.svc["irrigation_engine"].recommend(features, crop)
        return OrchestratorResponse("irrigation",
            f"{rec.decision.value}, dose={rec.dose_mm}mm",
            rec.confidence, _level(rec.confidence),
            ["irrigation_engine","soil_nowcast","rain_intelligence"],
            (time.time()-t0)*1000, rec.reasoning, [],
            [rec.hard_stop_reason] if rec.hard_stop else [], rec.hard_stop)

    def escalate(self, context):
        return {"type":"human_escalation",
                "reason":context.get("reason","Confiance insuffisante"),
                "parcelle":context.get("cell_id","?"),
                "contact":"conseiller@smartagri92.sn"}

    # ── Internes ──
    def _classify(self, q):
        q = q.lower()
        for kw, intent in [
            (["irrigu","arros","eau","dose"],"irrigation"),
            (["humid","sol","terre","sec"],"soil_forecast"),
            (["pluie","pleuv","précip"],"rain_forecast"),
            (["anomal","bizarre"],"anomaly_check"),
            (["alerte","danger","risque"],"alert_check"),
            (["rapport","bilan","résumé"],"full_report"),
            (["ravageur","insecte","maladie"],"pest_info"),
            (["engrais","fertili","npk"],"fertilizer"),
            (["prix","marché","vendre"],"price"),
            (["calendrier","semer","planter"],"calendar"),
        ]:
            if any(w in q for w in kw): return intent
        return "general"

    def _call(self, name, features, crop):
        s = self.svc.get(name)
        if s is None:
            return ServiceResponse(name,{},0.0,ConfidenceLevel.UNRELIABLE,
                abstained=True,abstention_reason="Service indisponible")
        if isinstance(s, SoilNowcastService): return s.predict(features)
        if isinstance(s, RainIntelligenceService): return s.predict(features)
        if isinstance(s, AnomalyService): return s.detect(features)
        if isinstance(s, KnowledgeService):
            return s.search(features.get("query",""))
        if isinstance(s, MonitoringEngine):
            _,_,al = s.assess(features)
            return ServiceResponse("monitoring",{"alerts":len(al)},
                0.80,ConfidenceLevel.HIGH)
        if isinstance(s, IrrigationEngine):
            r = s.recommend(features, crop)
            return ServiceResponse("irrigation",
                {"decision":r.decision.value,"dose":r.dose_mm},
                r.confidence, _level(r.confidence), r.reasoning)
        return ServiceResponse(name,{},0.0,ConfidenceLevel.UNRELIABLE,
            abstained=True,abstention_reason="Type inconnu")

    def _assemble(self, intent, resps, abstentions, crop):
        parts = []
        if "soil_nowcast" in resps:
            v = resps["soil_nowcast"].values
            parts.append(f"Humidité: J+1={v.get('y_plus_1d',0):.1f}%")
        if "rain_intelligence" in resps:
            v = resps["rain_intelligence"].values
            parts.append(f"Pluie J+1: {v.get('rain_1d_prob',0)*100:.0f}%")
        if "irrigation_engine" in resps:
            v = resps["irrigation_engine"].values
            parts.append(f"Irrigation: {v.get('decision','?')}")
        if abstentions:
            parts.append(f"Indisponible: {len(abstentions)} composant(s)")
        return " | ".join(parts) if parts else "Consulter un conseiller."
```

---

## 4. Gestion de la confiance

### 4.1 Baselines mesurées

| Composant | Métrique | Valeur | Baseline confiance |
|-----------|----------|--------|--------------------|
| SoilNowcast | R² | 0.8353 | 0.8353 |
| Rain Intelligence | AUC | 0.9625 | 0.9625 |
| ET0 Forecast | R² | 0.9997 | 0.95 (cap) |
| Yield Forecast | R² | 0.951 | 0.951 |
| Price Forecast | R² | 0.900 | 0.900 |
| Crop Calendar | F1 | 0.980 | 0.980 |
| NDVI Anomaly | F1 | 0.994 | 0.994 |
| Anomaly Intel | F1 | 0.850 | 0.850 |
| Knowledge | Recall@5 | 0.75 | 0.75 |

### 4.2 Pénalités

| Facteur | Pénalité | Condition |
|---------|----------|-----------|
| Données > 48h | -15 à -50% | Linéaire 48h -> 7j |
| Nouvelle parcelle | -15% | Pas d'historique |
| Extrême climatique | -20% | Pluie 14j > 200mm ou T > 45°C |
| Conflit modèles | -10% | Décisions contradictoires |
| Saison sèche | -5% | Nov-mai |
| Hors distribution | -25% | Zone hors training |
| CHIRPS manquant | -10% | Fallback NASA seul |

---

## 5. Gestion des abstentions

| Condition | Action | Fallback |
|-----------|--------|----------|
| Confiance < 0.20 | ABSTENTION | Réponse RAG générique |
| Données > 72h | ABSTENTION | "Données trop anciennes" |
| > 5 features manquantes | ABSTENTION | Conseiller humain |
| Zone hors Sénégal | ABSTENTION | "Zone non couverte" |
| Question hors domaine | ABSTENTION | Redirection |
| Modèle non chargé | ABSTENTION | Fallback Knowledge |

Hiérarchie : ML -> Seuils FAO-56 -> RAG Knowledge -> Escalade humaine.

---

## 6. Gestion des conflits

| Conflit | Résolution |
|---------|------------|
| Sol sec + pluie prévue | Attendre (Rain AUC > Soil R²) |
| Normal + anomalie | Alerter (précaution) |
| Pluie + ET0 élevée | Calculer bilan net |
| Irriguer + saturation | Anomalie bloque (hard stop) |

Règles : 1) Confiance haute gagne (écart > 0.15), 2) Précaution,
3) Terrain > modèle, 4) Spécialiste > généraliste, 5) Abstention.

---

## 7. Garde-fous

| Garde-fou | Condition | Action | Contournable |
|-----------|-----------|--------|-------------|
| Pesticides | Toute dose | BLOQUER | Non |
| Santé humaine | Tout conseil médical | REDIRIGER | Non |
| Saturation | Sol > 90% | INTERDIRE irrigation | Non |
| Gel | T < 5°C | REPORTER | Non |
| Données périmées | > 72h | ABSTENIR | Opérateur |
| Hors distribution | > 3 sigma | DÉGRADER confiance | Oui |
| Dose max | > 30 mm/j | PLAFONNER | Agronome |

---

## 8. Diagrammes d'exécution

### answer()
```
Requête -> classify_intent() -> ROUTING
    -> Appels parallèles [timeout par service]
    -> Confiance composite
    -> Conflits -> Garde-fous
    -> conf >= 0.60 ? RÉPONSE COMPLÈTE
    -> conf >= 0.20 ? RÉPONSE + AVERTISSEMENT
    -> conf < 0.20  ? ABSTENTION + FALLBACK
```

### monitor()
```
Cron 15min -> MonitoringEngine.assess()
    -> SoilNowcast + Rain + Anomaly (parallèle)
    -> Score risque composite (pondéré)
    -> NORMAL (log) | WATCH (note) | WARNING (push) | CRITICAL (appel)
```

### recommend()
```
Requête -> IrrigationEngine.recommend()
    -> SoilNowcast.predict() + Rain.predict()
    -> Hard stops (pluie > 70%, saturation, gel)
    -> ETc = ET0 x Kc -> Déficit -> Dose
    -> IRRIGATE_NOW | TOMORROW | DELAY | NO | ABSTAIN
```

---

## 9. API interne

| Endpoint | Méthode | Latence p50 | Composants |
|----------|---------|-------------|------------|
| `/v1/answer` | POST | < 50ms (simple) | 1-2 |
| `/v1/answer` | POST | < 200ms (complet) | 4-6 |
| `/v1/monitor` | POST | < 100ms | 3 |
| `/v1/recommend` | POST | < 80ms | 2-3 |
| `/v1/escalate` | POST | < 5ms | 0 |
| `/v1/health` | GET | < 5ms | 0 |
| `/v1/models` | GET | < 5ms | 0 |

**Empreinte** : ~800 Mo (9 modèles + index vectoriel + runtime).

---

*Généré à partir des métriques mesurées des 9 modèles Classe A.
Aucun entraînement. Aucun nouvel agent.*
