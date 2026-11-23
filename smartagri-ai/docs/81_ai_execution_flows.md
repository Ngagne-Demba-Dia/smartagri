# 81 — SmartAgri AI Execution Flows

**Version** : 1.0 | **Date** : 2026-11-17 | **Auteur** : OctOpus x SmartAgri92

**30 scenarios complets** avec diagrammes, sequences, decisions automatiques.
Metriques reelles : SoilNowcast R2=0.835, Rain AUC=0.963, ET0 R2=0.9997,
Anomaly F1=0.85, Crop Calendar F1=0.980, NDVI Anomaly F1=0.994,
Yield R2=0.951, Price R2=0.900, Market Silhouette=0.345, RAG Recall@5=75%.

---

## S01 — Irrigation simple, saison seche

**Contexte** : Mboro (Niayes), tomate, decembre
**Requete** : "Dois-je irriguer aujourd'hui ?"

```
User -> Orchestrator [intent: irrigation_decision]
  |-> SoilNowcast     : soil=22% (stress leger), conf=0.86
  |-> Rain Intelligence: rain_1d=0.05, conf=0.91
  |-> ET0 Forecast     : et0=4.8mm/j, conf=0.99
  |-> Agent Irrigation : Kc=1.15, ETc=5.52mm, deficit=13%, dose=16mm
  => IRRIGUER, dose=16mm, confiance=0.88
```

**Reponse** : "Oui, irriguez. Sol a 22%, dose 16mm, pas de pluie demain. Confiance elevee (88%)."

---

## S02 — Pluie imminente, reporter

**Contexte** : Thies, oignon, octobre
**Requete** : "Je voulais irriguer demain ?"

```
User -> Orchestrator [intent: irrigation_decision]
  |-> SoilNowcast     : soil=28% (correct), conf=0.83
  |-> Rain Intelligence: rain_1d=0.78, conf=0.89
  |-> Agent Irrigation : sol OK + pluie probable
  => REPORTER 48h, confiance=0.84
```

**Reponse** : "Reportez. Sol a 28% (pas de stress), 78% pluie demain. Verifiez dans 48h."

---

## S03 — Alerte secheresse critique

**Contexte** : Louga, mil, novembre
**Requete** : "Etat des parcelles ?"

```
User -> Orchestrator [intent: monitoring_report]
  |-> [PARALLELE]
  |   SoilNowcast     : soil=12% (CRITIQUE < 15%)
  |   Rain Intelligence: rain_3d=0.08
  |   ET0 Forecast     : et0=6.2mm/j (eleve)
  |   Anomaly Intel    : is_anomaly=True (secheresse)
  |-> MonitoringEngine : risk=0.82 => CRITICAL
  => ALERTE CRITIQUE + escalade humaine
```

**Reponse** : "ALERTE CRITIQUE. Sol 12% sous fletissement (15%), 0 pluie 3j, ET0 6.2mm. Irrigation urgente."

---

## S04 — Question agronomique generale

**Contexte** : pas de parcelle
**Requete** : "Comment preparer le sol pour l'oignon ?"

```
User -> Orchestrator [intent: general_knowledge]
  |-> SmartAgri Knowledge: score=0.42, conf=0.70
  => Reponse RAG enrichie, confiance bonne (70%)
```

---

## S05 — Conflit SoilNowcast vs Rain

**Contexte** : Niayes, carotte, aout
**Requete** : "Sol sec mais il a plu hier ?"

```
User -> Orchestrator [intent: soil_status]
  |-> SoilNowcast     : soil=19% (bas), conf=0.72
  |-> Rain Intelligence: rain_hier=12mm (confirme CHIRPS)
  |-> ConflictResolver : sol sableux = drainage rapide < 24h
  => Pas de vrai conflit, conf=0.68
```

**Reponse** : "Normal : sols sableux Niayes drainent en < 24h. Irriguez si besoin."

---

## S06 — Exces d'eau, engorgement

**Contexte** : Richard-Toll, riz, septembre
**Requete** : "Il pleut beaucoup, je m'inquiete"

```
User -> Orchestrator [intent: anomaly_check]
  |-> SoilNowcast     : soil=88% (saturation)
  |-> Rain Intelligence: rain_3d=82mm
  |-> Anomaly Intel    : is_anomaly=True (flood_risk)
  |-> MonitoringEngine : risk=0.78 => CRITICAL
  => Ouvrir drains, alerte engorgement
```

---

## S07 — Prevision rendement national

**Contexte** : DRDR, bilan campagne
**Requete** : "Rendement mil cette annee ?"

```
User -> Orchestrator [intent: yield_estimate]
  |-> Yield Forecast: mil, pred=0.82t/ha, conf=0.78
  => Estimation nationale, R2=0.951, conf bonne
```

---

## S08 — Prix marche et tendance

**Contexte** : Dakar, commercant
**Requete** : "Prix oignon va monter ?"

```
User -> Orchestrator [intent: price_check]
  |-> Price Forecast   : actuel=450, pred_30j=520 FCFA/kg (+16%)
  |-> Market Clustering: cluster_0 (urbain), hausse saisonniere
  => Tendance haussiere, conf=0.74, RMSE=67 FCFA/kg
```

---

## S09 — NDVI anormal, stress vegetatif

**Contexte** : Kaolack, arachide
**Requete** : "Satellite montre anomalie ?"

```
User -> Orchestrator [intent: ndvi_check]
  |-> NDVI Anomaly     : ndvi=0.28 (attendu>0.45), anomaly=True, conf=0.92
  |-> SmartAgri Knowledge: "NDVI bas = stress hydrique ou attaque"
  => Anomalie confirmee (F1=0.994), verification terrain
```

---

## S10 — Phase culturale et Kc

**Contexte** : tomate, semaine 6
**Requete** : "Ma tomate est a quelle phase ?"

```
User -> Orchestrator [intent: crop_phase]
  |-> Crop Calendar: jour=42, phase=developpement, Kc=0.82, conf=0.95
  => Phase developpement, Kc 0.82, mi-saison dans ~3 semaines
```

---

## S11 — Abstention, manque de donnees

**Contexte** : nouvelle parcelle hors couverture
**Requete** : "Etat de mon sol ?"

```
User -> Orchestrator [intent: soil_status]
  |-> SoilNowcast: cell_id=8901, conf=0.32 (< 0.40)
  => ABSTENTION
  |-> Fallback: SmartAgri Knowledge (conseils generaux)
  => "Pas assez de donnees. Verification terrain recommandee."
```

---

## S12 — Rapport complet parcellaire

**Contexte** : Mboro, parcelle suivie
**Requete** : "Rapport complet parcelle 4521"

```
User -> Orchestrator [intent: full_report]
  |-> [PARALLELE, 8 composants]
  |   SoilNowcast:      22%, stress leger
  |   Rain Intel:        prob_1d=0.15, prob_3d=0.42
  |   ET0 Forecast:      4.1mm/j
  |   Anomaly Intel:     NORMAL
  |   Crop Calendar:     mi-saison, Kc=1.15
  |   NDVI Anomaly:      0.52, NORMAL
  |   MonitoringEngine:  risk=0.38, WATCH
  |   Knowledge:         enrichissement
  => Rapport structure, conf_composite=0.84, latence=1.2s
```

---

## S13 — Canicule Niayes

**Contexte** : T_max > 42C, declenchement auto
**Requete** : (automatique MonitoringEngine)

```
MonitoringEngine -> Orchestrator [alerte auto]
  |-> ET0 Forecast: et0=7.8mm/j (extreme)
  |-> Anomaly Intel: heatwave=True
  => CRITICAL, irrigation urgence, notification push, escalade
```

---

## S14 — Gel Niayes (T_min < 10C)

**Contexte** : decembre-janvier, maraichage cotier
```
MonitoringEngine -> Alerte gel
  T_min=8.5C, cultures sensibles: tomate, poivron
  => WARNING, protection recommandee (paillage, voiles)
```

---

## S15 — Multi-cultures, meme parcelle

**Contexte** : tomate + oignon
**Requete** : "Eau pour mes deux cultures ?"

```
User -> Orchestrator [intent: irrigation_decision]
  |-> Crop Calendar(tomate): Kc=1.15
  |-> Crop Calendar(oignon): Kc=0.95
  |-> ET0: 4.5mm/j
  |-> Agent Irrigation:
  |   ETc_tomate=5.18, ETc_oignon=4.28
  => Dose=max(5.18,4.28)=5.2mm/j, irriguer pour la tomate
```

---

## S16 — Donnees meteo retardees

**Contexte** : panne NASA POWER, donnees J-4

```
User -> Orchestrator [intent: soil_status]
  |-> SoilNowcast: derniere=J-4, penalite=0.77
  |   conf_ajustee = 0.86 x 0.77 = 0.66
  => Reponse avec avertissement "donnees retardees 4j", conf BONNE
```

---

## S17 — Comparaison inter-marches

**Contexte** : grossiste, achats multi-marches
**Requete** : "Ou acheter oignon moins cher ?"

```
User -> Orchestrator [intent: market_info]
  |-> Price Forecast: prix tous marches oignon
  |-> Market Clustering: 2 clusters (urbain/rural)
  => Top 3 marches moins chers, cluster rural souvent moins cher
```

---

## S18 — Stress hydrique progressif

**Contexte** : Potou, suivi 5 jours
**Requete** : "Sol se degrade depuis lundi"

```
User -> Orchestrator [intent: soil_forecast]
  |-> SoilNowcast (serie):
  |   Lun:35% Mar:30% Mer:26% Jeu:22% Ven:19% (-3.2%/j)
  |-> Rain Intelligence: rain_3d=0.12 (sec)
  |-> MonitoringEngine: risk=0.65 => WARNING
  => "Irrigation recommandee avant dimanche"
```

---

## S19 — Fin hivernage, transition irrigation

**Contexte** : octobre, Thies
**Requete** : "Pluies finies ? Reprendre irrigation ?"

```
User -> Orchestrator [intent: irrigation_decision + rain_forecast]
  |-> Rain Intelligence: prob_7d=[0.35,0.28,0.15,0.10,0.08,0.05,0.03]
  |-> SoilNowcast: soil=42% (confortable)
  |-> Agent Irrigation: sol OK ~5j, pluies en declin
  => "Surveiller, reprendre irrigation dans ~7 jours"
```

---

## S20 — Anomalie, cause inconnue

**Contexte** : zone rurale, pas de satellite recent
**Requete** : "Anomalie detectee, c'est quoi ?"

```
User -> Orchestrator [intent: alert_explain]
  |-> Anomaly Intel: multi_variable, conf=0.58
  |-> NDVI Anomaly: pas de donnees recentes => ABSTENTION
  |-> ConflictResolver: anomalie sans satellite
  => Conf MODEREE, verification terrain, escalade si > 48h
```

---

## S21 — Bilan hebdomadaire automatique

**Contexte** : cron job, toutes parcelles

```
Scheduler -> Orchestrator [batch]
  |-> MonitoringEngine (par parcelle):
  |   NORMAL: 45 | WATCH: 12 | WARNING: 3 | CRITICAL: 1
  => Notification groupee, detail WARNING/CRITICAL uniquement
```

---

## S22 — Agriculteur hors zone couverte

**Contexte** : Casamance, peu de donnees
**Requete** : "Que me conseillez-vous ?"

```
User -> Orchestrator [intent: general_knowledge]
  |-> SoilNowcast: ABSTENTION (pas de donnees locales)
  |-> SmartAgri Knowledge: chunks Casamance/riz
  => Reponse RAG + disclaimer "pas de donnees specifiques"
```

---

## S23 — ET0 extreme + sol deja sec

**Contexte** : mars, Ferlo, zone pastorale

```
MonitoringEngine -> detection simultanee:
  et0=7.5mm/j (extreme) + soil=14% (critique) + rain_3d=0.02
  risk=0.89 => CRITICAL
  => Double alerte secheresse+evaporation, escalade immediate
```

---

## S24 — Conflit prix vs rendement

**Contexte** : planification campagne
**Requete** : "Oignon rentable cette annee ?"

```
User -> Orchestrator [intent: price_check + yield_estimate]
  |-> Yield Forecast: 12.5t/ha (bon)
  |-> Price Forecast: 380 FCFA/kg (baisse)
  |-> ConflictResolver: bonne recolte = offre abondante = prix bas
  => Coherence economique, pas de conflit reel
  => "Bon rendement mais prix en baisse. Rentabilite selon couts."
```

---

## S25 — Dose precise goutte-a-goutte

**Contexte** : technicien irrigation
**Requete** : "Litres par plant de tomate ?"

```
User -> Orchestrator [intent: irrigation_decision]
  |-> Agent Irrigation:
  |   ETc=5.2mm/j, espacement 50x50cm, surface=0.25m2
  |   dose/plant = 5.2 x 0.25 = 1.3 L/plant/jour
  => "1.3L par plant, Kc=1.15, conf=0.85"
```

---

## S26 — Pluie extreme (>50mm/3j)

**Contexte** : hivernage, Kedougou

```
MonitoringEngine -> rain_3d=78mm, soil=92%
  => CRITICAL: flood_risk
  => Couper irrigation, ouvrir drains, alerte glissement
```

---

## S27 — Premiere connexion, onboarding

**Contexte** : nouvel agriculteur
**Requete** : "Bonjour, je commence"

```
User -> Orchestrator [intent: unknown -> onboarding]
  |-> SmartAgri Knowledge: bienvenue
  => Pas de ML. "Indiquez region + cultures pour commencer."
```

---

## S28 — Verification post-irrigation

**Contexte** : agriculteur a irrigue hier
**Requete** : "J'ai irrigue, c'est mieux ?"

```
User -> Orchestrator [intent: soil_status]
  |-> SoilNowcast: avant=19% -> apres=38%, delta=+19%
  => "Sol remonte a 38%. Prochain arrosage ~3 jours."
```

---

## S29 — Requete ambigue, clarification

**Contexte** : message vague
**Requete** : "Ca va pas"

```
User -> Orchestrator [intent: AMBIGUOUS]
  => Clarification:
     "Precisez : sol ? cultures ? meteo ? prix ?"
  => Pas de ML appele
```

---

## S30 — Escalade humaine apres echec

**Contexte** : 3 composants en desaccord
**Requete** : "Que faire pour ma parcelle ?"

```
User -> Orchestrator [intent: monitoring_report]
  |-> SoilNowcast: 25% (OK)
  |-> Anomaly Intel: anomalie, conf=0.48
  |-> NDVI Anomaly: anomalie, conf=0.51
  |-> ConflictResolver: sol OK mais anomalies faibles
  |   conf_composite=0.42 => MODEREE
  => ABSTENTION partielle
  => "Sol correct mais signaux faibles. Visite terrain recommandee."
  => Escalade humaine declenchee
```

---

## Matrice de couverture

| Composant | Scenarios | % |
|-----------|-----------|---|
| SoilNowcast | 1,2,3,5,6,11,12,16,18,19,23,28,30 | 43% |
| Rain Intelligence | 1,2,3,6,12,18,19,26 | 27% |
| MonitoringEngine | 3,6,12,13,14,18,21,23,26 | 30% |
| ET0 Forecast | 1,3,12,13,15,23 | 20% |
| Anomaly Intelligence | 3,6,12,20,23,30 | 20% |
| Agent Irrigation | 1,2,15,19,25 | 17% |
| SmartAgri Knowledge | 4,9,11,22,27 | 17% |
| NDVI Anomaly | 9,12,20,30 | 13% |
| ConflictResolver | 5,20,24,30 | 13% |
| Crop Calendar | 10,12,15 | 10% |
| Price Forecast | 8,17,24 | 10% |
| Yield Forecast | 7,24 | 7% |
| Market Clustering | 8,17 | 7% |

## Distribution par type de decision

| Type | Count | Scenarios |
|------|-------|-----------|
| Decision automatique | 12 | 1,2,5,7,8,9,10,15,17,19,25,28 |
| Alerte automatique | 6 | 3,6,13,14,23,26 |
| Reponse RAG | 4 | 4,11,22,27 |
| Abstention/escalade | 4 | 11,20,29,30 |
| Rapport complet | 3 | 12,18,21 |
| Conflit resolu | 2 | 5,24 |

## Distribution par niveau d'alerte

| Niveau | Count | Scenarios |
|--------|-------|-----------|
| NORMAL | 10 | 1,2,4,7,8,9,10,17,25,27 |
| WATCH | 5 | 12,16,18,19,28 |
| WARNING | 6 | 5,14,15,20,24,30 |
| CRITICAL | 6 | 3,6,13,23,26,29 |
| ABSTENTION | 3 | 11,22,29 |
