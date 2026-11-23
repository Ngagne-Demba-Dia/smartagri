# 83 — SmartAgri Runtime Scenarios : 30 Scénarios Réels

**Date** : 2026-11-19
**Base** : 9 modèles Classe A entraînés, métriques mesurées
**Aucun entraînement, aucun nouvel agent**

---

## Légende

- **Méthode** : `answer()`, `monitor()`, `recommend()`, `escalate()`
- **Composants** : SN (SoilNowcast), RI (Rain Intelligence), AN (Anomaly),
  KN (Knowledge), MO (MonitoringEngine), IR (IrrigationEngine)
- **Confiance** : HIGH >= 0.80, GOOD >= 0.60, MODERATE >= 0.40, LOW >= 0.20

---

## Catégorie 1 — Sol et humidité (6 scénarios)

### S01. État du sol — conditions normales

**Question** : "Quel est l'état de mon sol ?"
**Méthode** : `answer("Quel est l'état de mon sol ?", features)`
**Intent** : `soil_forecast`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | classify_intent() | `soil_forecast` |
| 2 | ROUTING | [SN, RI] |
| 3 | SN.predict() | J+1=52%, J+2=49%, J+3=47% |
| 4 | RI.predict() | rain_1d=0.12, rain_2d=0.08, rain_3d=0.15 |
| 5 | Confiance SN | 0.8353 (baseline, aucune pénalité) |
| 6 | Confiance RI | 0.9625 (baseline) |
| 7 | Composite | (0.8353 + 0.9625) / 2 = 0.8989 |

**Score final** : 0.90 — HIGH
**Réponse** : "Votre sol est en bon état. Humidité prévue : 52% demain, 49% après-demain. Aucune pluie significative attendue. Pas d'action urgente."

---

### S02. Sol en stress hydrique

**Question** : "Mon sol est-il trop sec ?"
**Méthode** : `answer("Mon sol est-il trop sec ?", features)`
**Intent** : `soil_forecast`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=22%, J+2=18%, J+3=15% |
| 2 | RI.predict() | rain_1d=0.05 |
| 3 | Warning SN | "WARNING: stress hydrique J+1=22%" |
| 4 | Warning SN | "CRITICAL: flétrissement J+3=15%" |
| 5 | Confiance | 0.8989 (données récentes, pas de pénalité) |

**Score final** : 0.90 — HIGH
**Réponse** : "ALERTE : votre sol est en stress hydrique sévère. Humidité J+1 = 22%, en dessous du seuil de stress (30%). Prévision J+3 = 15%, proche du point de flétrissement. Pas de pluie attendue. Irrigation recommandée."

---

### S03. Sol saturé après fortes pluies

**Question** : "Est-ce que mon terrain est trop humide ?"
**Méthode** : `answer()`
**Intent** : `soil_forecast`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=92%, J+2=85%, J+3=78% |
| 2 | Warning SN | "WARNING: saturation J+1=92%" |
| 3 | RI.predict() | rain_1d=0.65 |
| 4 | Confiance SN | 0.8353 × 0.80 = 0.6682 (pluie 14j > 200mm) |

**Score final** : 0.67 — GOOD (dégradée par extrême)
**Réponse** : "Oui, votre sol est saturé (92%). Il devrait redescendre à 78% en 3 jours. Reporter toute irrigation. Attention au drainage. Confiance modérée en raison des conditions extrêmes."

---

### S04. Données anciennes (> 48h)

**Question** : "Comment va mon sol ?"
**Méthode** : `answer()`
**Intent** : `soil_forecast`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=45% |
| 2 | Confiance | 0.8353 × 0.66 = 0.551 (données 96h) |
| 3 | Avertissement | "Données datant de 4 jours" |

**Score final** : 0.55 — MODERATE
**Réponse** : "Humidité estimée J+1 = 45%. ATTENTION : ces données datent de 4 jours, la confiance est modérée (55%). Vérifiez visuellement vos parcelles."

---

### S05. Nouvelle parcelle sans historique

**Question** : "J'ai un nouveau champ, quel est l'état du sol ?"
**Méthode** : `answer()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=48% |
| 2 | Pénalité | nouvelle parcelle : × 0.85 |
| 3 | Confiance | 0.8353 × 0.85 = 0.710 |

**Score final** : 0.71 — GOOD
**Réponse** : "Humidité estimée J+1 = 48% (bon état). Note : parcelle nouvelle, le modèle n'a pas d'historique local. Confiance réduite. Après quelques semaines de données, la précision s'améliorera."

---

### S06. Sol — données manquantes (> 5 features)

**Question** : "État du sol ?"
**Méthode** : `answer()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | ABSTENTION (12/30 features manquantes) |
| 2 | Fallback | KN.search("état sol général") |
| 3 | Knowledge | 2 chunks pertinents, score 0.28 |

**Score final** : 0.10 — UNRELIABLE (abstention)
**Réponse** : "Je ne peux pas estimer l'humidité de votre sol : 12 données sur 30 sont manquantes. En général, en cette saison au Sénégal... [réponse RAG]. Contactez votre conseiller pour un diagnostic terrain."

---

## Catégorie 2 — Irrigation (6 scénarios)

### S07. Irrigation standard — déficit modéré

**Question** : "Dois-je irriguer mes oignons demain ?"
**Méthode** : `recommend(features, crop="oignon")`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=35% |
| 2 | RI.predict() | rain_1d=0.15 |
| 3 | Hard stops | Aucun déclenché |
| 4 | ETc | ET0=5.2 × Kc_oignon=1.05 = 5.46 mm/j |
| 5 | Déficit | FC=65%, j1=35%, déficit=46% |
| 6 | Seuil | 46% > 45% (1-0.55) → IRRIGATE_TOMORROW |
| 7 | Dose | 5.46 × (1 + 0.46×0.5) = 6.7 mm |

**Score final** : 0.84 — HIGH
**Réponse** : "Oui, irriguez demain matin. Dose recommandée : 6.7 mm pour vos oignons (ETc = 5.5 mm/j). Le sol est à 35%, en dessous du seuil optimal."

---

### S08. Irrigation bloquée — pluie imminente

**Question** : "Je veux irriguer aujourd'hui"
**Méthode** : `recommend()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=40% |
| 2 | RI.predict() | rain_1d=0.82 |
| 3 | Hard stop | rain_1d > 0.70 → DELAY |

**Score final** : 0.83 — HIGH
**Réponse** : "REPORTER. Forte probabilité de pluie demain (82%). Attendre 24h pour évaluer les apports naturels. Si la pluie ne vient pas, irriguer après-demain."

---

### S09. Irrigation bloquée — sol saturé

**Question** : "Quelle dose pour mes tomates ?"
**Méthode** : `recommend(features, crop="tomate")`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=93% |
| 2 | Hard stop | Sol > 90% → NO_IRRIGATION |

**Score final** : 0.84 — HIGH
**Réponse** : "NE PAS IRRIGUER. Le sol est saturé (93%). Risque d'asphyxie racinaire pour vos tomates. Vérifiez le drainage. Prochaine évaluation dans 48h."

---

### S10. Irrigation — stress critique

**Question** : "Mes piments sèchent, que faire ?"
**Méthode** : `recommend(features, crop="piment")`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=12% |
| 2 | RI.predict() | rain_1d=0.03 |
| 3 | Déficit | 81% → IRRIGATE_NOW |
| 4 | ETc | 5.0 × 1.05 = 5.25 mm |
| 5 | Dose | 5.25 × (1 + 0.81×0.5) = 7.4 mm |

**Score final** : 0.84 — HIGH
**Réponse** : "URGENCE. Sol à 12%, en dessous du point de flétrissement (15%). Irriguer MAINTENANT : 7.4 mm. Vos piments sont en danger immédiat."

---

### S11. Irrigation — modèle indisponible

**Question** : "Dois-je irriguer ?"
**Méthode** : `recommend()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | ABSTENTION (modèle non chargé) |
| 2 | Fallback | ABSTAIN |

**Score final** : 0.00 — UNRELIABLE
**Réponse** : "Je ne peux pas calculer de recommandation : le modèle SoilNowcast n'est pas disponible. En attendant, vérifiez visuellement l'humidité du sol. Contactez votre conseiller."

---

### S12. Irrigation — culture inconnue

**Question** : "Combien d'eau pour mon bissap ?"
**Méthode** : `recommend(features, crop="bissap")`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | Kc lookup | "bissap" absent → Kc par défaut = 1.0 |
| 2 | Warning | "Culture non référencée, Kc générique" |
| 3 | Calcul normal | ETc = 4.8 × 1.0 = 4.8 mm |

**Score final** : 0.71 — GOOD (pénalité Kc inconnu)
**Réponse** : "Dose estimée : 5.2 mm. Note : le bissap n'est pas dans notre base FAO-56, j'utilise un coefficient générique. Pour plus de précision, consultez votre conseiller ISRA."

---

## Catégorie 3 — Météo et pluie (4 scénarios)

### S13. Prévision pluie standard

**Question** : "Il va pleuvoir cette semaine ?"
**Méthode** : `answer()`
**Intent** : `rain_forecast`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | RI.predict() | rain_1d=0.72, rain_2d=0.65, rain_3d=0.45 |

**Score final** : 0.96 — HIGH
**Réponse** : "Oui, forte probabilité de pluie demain (72%) et après-demain (65%). J+3 plus incertain (45%). Préparez vos parcelles."

---

### S14. Pluie — saison sèche

**Question** : "Il va pleuvoir en janvier ?"
**Méthode** : `answer()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | RI.predict() | rain_1d=0.02, rain_2d=0.01, rain_3d=0.01 |
| 2 | Pénalité saison | × 0.95 |

**Score final** : 0.91 — HIGH
**Réponse** : "Non, probabilité de pluie quasi nulle (2%). Nous sommes en saison sèche. Prévoyez l'irrigation pour les 3 prochains jours."

---

### S15. Épisode pluvieux prolongé

**Question** : "Il pleut depuis 3 jours, ça va continuer ?"

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | RI.predict() | rain_1d=0.88, rain_2d=0.75, rain_3d=0.62 |
| 2 | Warning | "Épisode pluvieux prolongé (3 jours)" |
| 3 | AN.detect() | flood threshold proche |

**Score final** : 0.93 — HIGH
**Réponse** : "Oui, la pluie devrait continuer (88% demain, 75% J+2). Risque de saturation. Vérifiez le drainage, arrêtez toute irrigation, surveillez les zones basses."

---

### S16. Pluie + température extrême

**Question** : "Il fait très chaud et il pourrait pleuvoir ?"

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | RI.predict() | rain_1d=0.55 |
| 2 | AN.detect() | heatwave: t_max=44°C → CRITICAL |
| 3 | Conflit | Pluie possible + canicule |
| 4 | Résolution | Les deux alertes coexistent |

**Score final** : 0.82 — HIGH
**Réponse** : "ALERTE CANICULE (44°C). Pluie possible demain (55%) mais la chaleur reste le risque principal. Protégez les cultures sensibles, irriguez tôt le matin, évitez l'irrigation par aspersion en plein jour."

---

## Catégorie 4 — Anomalies (4 scénarios)

### S17. Sécheresse critique détectée

**Question** : "Y a-t-il un problème avec mes parcelles ?"
**Méthode** : `answer()`
**Intent** : `anomaly_check`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | AN.detect() | drought: soil=12% < 15% → CRITICAL |
| 2 | MO.assess() | risque = 0.82 → CRITICAL |
| 3 | Escalade | Oui (CRITICAL) |

**Score final** : 0.92 — HIGH
**Réponse** : "ANOMALIE CRITIQUE : sécheresse détectée. Humidité du sol = 12%, en dessous du point de flétrissement. Action immédiate requise. Un conseiller a été alerté."

---

### S18. Gel Niayes (zone côtière)

**Question** : "Mon monitoring montre un problème ?"
**Méthode** : `monitor(features)`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | AN.detect() | cold_snap: t_min=8°C < 10°C |
| 2 | MO.assess() | risque = 0.45 → WATCH |
| 3 | Alert | "Gel possible zone Niayes" |

**Score final** : 0.88 — HIGH
**Réponse** : "SURVEILLANCE : température minimale basse (8°C) dans la zone Niayes. Risque de gel pour les cultures sensibles (tomates, piments). Couvrir les plants si T° descend sous 5°C."

---

### S19. ET0 extrême

**Question** : "Mes plantes transpirent beaucoup, c'est normal ?"

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | AN.detect() | et0_extreme: ET0=7.8 > 7.0 |
| 2 | MO.assess() | risque = 0.55 → WARNING |

**Score final** : 0.85 — HIGH
**Réponse** : "Oui, l'évapotranspiration est exceptionnelle aujourd'hui (7.8 mm/j, seuil 7.0). Vos plantes perdent plus d'eau que d'habitude. Augmentez l'irrigation de 15% et irriguez tôt le matin."

---

### S20. Aucune anomalie

**Question** : "Tout va bien sur ma parcelle ?"
**Méthode** : `answer()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | AN.detect() | 0 anomalie |
| 2 | MO.assess() | risque = 0.12 → NORMAL |

**Score final** : 0.90 — HIGH
**Réponse** : "Tout est normal. Aucune anomalie détectée, risque faible (0.12). Conditions favorables pour vos cultures."

---

## Catégorie 5 — Cultures et conseil (4 scénarios)

### S21. Conseil calendrier cultural

**Question** : "Quand semer mes oignons ?"
**Méthode** : `answer()`
**Intent** : `calendar`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | KN.search() | 3 chunks (calendrier oignon Niayes) |
| 2 | RI.predict() | Prévisions pluie 3j |

**Score final** : 0.72 — GOOD
**Réponse** : "Dans la zone des Niayes, le semis d'oignon se fait d'octobre à décembre (saison fraîche). Assurez-vous que le sol est bien drainé. La pluie est peu probable cette semaine (< 10%)."

---

### S22. Ravageurs (Knowledge only)

**Question** : "Comment lutter contre la mouche de l'oignon ?"
**Méthode** : `answer()`
**Intent** : `pest_info`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | KN.search() | 2 chunks (lutte intégrée oignon) |
| 2 | Garde-fou | Pas de dose pesticide (hard stop) |

**Score final** : 0.65 — GOOD
**Réponse** : "La mouche de l'oignon (Delia antiqua) se combat par rotation culturale et pièges jaunes. Pour les traitements phytosanitaires, consultez impérativement votre conseiller ANCAR. SmartAgri ne recommande pas de doses de pesticides."

---

### S23. Fertilisation

**Question** : "Combien de NPK pour mes tomates ?"
**Intent** : `fertilizer`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | KN.search() | 1 chunk (fertilisation tomate) |
| 2 | SN.predict() | Sol: soc_g_kg connu |
| 3 | Garde-fou | Source FAO requise → OK |

**Score final** : 0.60 — GOOD
**Réponse** : "Selon les recommandations FAO pour la tomate : NPK 15-15-15 à 300 kg/ha en fond, puis 46-0-0 (urée) à 100 kg/ha en couverture. Adaptez selon votre analyse de sol (SOC = X g/kg)."

---

### S24. Question prix marché

**Question** : "Quel est le prix de l'oignon à Dakar ?"
**Intent** : `price`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | KN.search() | Données WFP marchés |

**Score final** : 0.55 — MODERATE
**Réponse** : "D'après les derniers relevés WFP, le prix de l'oignon à Dakar est d'environ 350-450 FCFA/kg (données historiques). Pour le prix du jour, consultez le marché de Thiaroye."

---

## Catégorie 6 — Alertes et conflits (4 scénarios)

### S25. Conflit : sol sec + pluie prévue

**Question** : "Mon sol est sec mais il va pleuvoir ?"
**Méthode** : `answer()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=25% (stress) |
| 2 | RI.predict() | rain_1d=0.75 |
| 3 | Conflit | Sol sec → irriguer vs pluie → attendre |
| 4 | Résolution | Rain AUC (0.9625) > seuil → ATTENDRE |

**Score final** : 0.85 — HIGH
**Réponse** : "Votre sol est stressé (25%) mais une pluie est très probable demain (75%). Recommandation : attendre 24h. Si la pluie ne vient pas, irriguer 6 mm en urgence."

---

### S26. Conflit : irrigation recommandée + anomalie saturation

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | IR.recommend() | IRRIGATE_NOW (déficit J+2) |
| 2 | AN.detect() | flood: rain_3d=110mm > 100mm |
| 3 | Conflit | Irriguer vs excès d'eau |
| 4 | Hard stop | Anomalie bloque → NO_IRRIGATION |

**Score final** : 0.88 — HIGH
**Réponse** : "Malgré un déficit prévu, les pluies cumulées des 3 derniers jours (110 mm) indiquent un risque d'excès d'eau. NE PAS IRRIGUER. Surveiller le drainage."

---

### S27. Alerte multi-composants (full report)

**Question** : "Donne-moi un bilan complet de ma parcelle"
**Méthode** : `answer()`
**Intent** : `full_report`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | J+1=38%, J+2=35%, J+3=32% |
| 2 | RI.predict() | rain_1d=0.20 |
| 3 | AN.detect() | 0 anomalie |
| 4 | MO.assess() | risque=0.25, NORMAL |
| 5 | IR.recommend() | IRRIGATE_TOMORROW, 5.8mm |
| 6 | KN.search() | 2 chunks pertinents |

**Score final** : 0.87 — HIGH (6 composants, confiance moyenne)
**Réponse** : "BILAN PARCELLE — Sol : 38% (correct, tendance baisse). Pluie : peu probable (20%). Anomalies : aucune. Risque : faible (0.25). Irrigation : prévoir 5.8 mm demain matin. Calendrier : période favorable pour les semis d'oignon."

---

### S28. Escalade humaine — confiance trop basse

**Question** : "Que faire avec ma parcelle ?"
**Méthode** : `answer()` → `escalate()`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | SN.predict() | ABSTENTION (données 5 jours) |
| 2 | RI.predict() | Confiance 0.60 (dégradée) |
| 3 | Composite | 0.18 < 0.20 → ESCALADE |
| 4 | escalate() | Transfert conseiller |

**Score final** : 0.18 — UNRELIABLE → ESCALADE
**Réponse** : "Je n'ai pas assez de données fiables pour vous conseiller (confiance 18%). Vos données datent de 5 jours. Un conseiller SmartAgri va vous contacter. En attendant, inspectez visuellement vos parcelles."

---

## Catégorie 7 — Cas limites et erreurs (2 scénarios)

### S29. Question hors domaine

**Question** : "Quel est le score du match Sénégal-Mali ?"
**Méthode** : `answer()`
**Intent** : `general`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | classify_intent() | `general` |
| 2 | KN.search() | ABSTENTION (score < 0.15) |
| 3 | Garde-fou | Question hors domaine |

**Score final** : 0.10 — UNRELIABLE (abstention)
**Réponse** : "Je suis SmartAgri, votre assistant agricole. Je ne peux pas répondre à cette question. Posez-moi des questions sur votre sol, l'irrigation, la météo ou vos cultures."

---

### S30. Garde-fou pesticides

**Question** : "Quelle dose de Roundup pour désherber ?"
**Intent** : `pest_info`

| Étape | Action | Résultat |
|-------|--------|---------|
| 1 | KN.search() | 1 chunk (désherbage) |
| 2 | Garde-fou | HARD STOP — dose pesticide |
| 3 | Blocage | Réponse filtrée |

**Score final** : 0.00 — BLOCKED
**Réponse** : "SmartAgri ne recommande JAMAIS de doses de pesticides ou d'herbicides. Pour un conseil de traitement phytosanitaire, contactez votre conseiller ANCAR ou la Direction de la Protection des Végétaux (DPV). Je peux vous conseiller sur les méthodes de lutte intégrée alternatives."

---

## Matrice de couverture

| Catégorie | Scénarios | SN | RI | AN | KN | MO | IR |
|-----------|-----------|----|----|----|----|----|----|
| Sol | S01-S06 | 6/6 | 4/6 | — | 1/6 | — | — |
| Irrigation | S07-S12 | 6/6 | 5/6 | — | — | — | 6/6 |
| Météo | S13-S16 | — | 4/4 | 2/4 | — | — | — |
| Anomalies | S17-S20 | — | — | 4/4 | — | 3/4 | — |
| Cultures | S21-S24 | 1/4 | 1/4 | — | 4/4 | — | — |
| Conflits | S25-S28 | 3/4 | 3/4 | 2/4 | 1/4 | 1/4 | 2/4 |
| Erreurs | S29-S30 | — | — | — | 2/2 | — | — |
| **Total** | **30** | **16** | **17** | **8** | **8** | **4** | **8** |

## Distribution des niveaux

| Niveau | Count | Scénarios |
|--------|-------|-----------|
| HIGH (>= 0.80) | 17 | S01-03, S07-10, S13-20, S25-27 |
| GOOD (>= 0.60) | 6 | S03, S05, S12, S21-23 |
| MODERATE (>= 0.40) | 3 | S04, S14, S24 |
| LOW/UNRELIABLE | 3 | S06, S11, S29 |
| BLOCKED | 1 | S30 |
| ESCALADE | 1 | S28 |

## Distribution des méthodes

| Méthode | Count |
|---------|-------|
| answer() | 22 |
| recommend() | 6 |
| monitor() | 1 |
| escalate() | 1 |

---

*30 scénarios construits à partir des métriques mesurées des 9 modèles.
Aucun entraînement, aucun nouvel agent, aucune donnée inventée pour l'entraînement.*
