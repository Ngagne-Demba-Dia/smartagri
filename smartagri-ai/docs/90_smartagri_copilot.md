# 90 — SmartAgri Copilot

**Version** : 1.0
**Date** : 2026-11-18
**Statut** : Démonstrateur PAS Challenge

---

## 1. Vision

Le SmartAgri Copilot est l'interface conversationnelle unifiée qui donne accès
à l'ensemble du système SmartAgri92. Contrairement à l'Assistant Parcellaire V2
(doc 76) qui orchestre les modèles en arrière-plan, le Copilot rend visible
le raisonnement IA et permet à l'utilisateur (agriculteur, technicien, décideur)
d'interagir directement avec chaque composant.

**Différenciation** : un copilote montre son travail. Chaque réponse affiche
les modèles appelés, les scores de confiance, les sources de données et les
hypothèses. L'agriculteur ne reçoit pas juste "irriguez 18 mm" : il voit
*pourquoi*, avec les chiffres.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  SmartAgri Copilot                        │
│                                                          │
│  ┌──────────────┐                                        │
│  │  Interface    │   Chat (texte/voix)                   │
│  │  Utilisateur  │   Wolof · Français · Anglais          │
│  └──────┬───────┘                                        │
│         │                                                │
│  ┌──────┴───────┐                                        │
│  │  Copilot     │   Intention → Plan → Exécution         │
│  │  Controller  │   → Synthèse → Explication             │
│  └──────┬───────┘                                        │
│         │                                                │
│  ┌──────┴────────────────────────────────────────┐       │
│  │           Orchestrateur SmartAgri              │       │
│  │  (doc 80 — routage, confiance, conflits)      │       │
│  └──────┬────────────────────────────────────────┘       │
│         │                                                │
│  ┌──────┴────────────────────────────────────────┐       │
│  │              Couche Exécution                  │       │
│  │                                                │       │
│  │  ┌─────────────┐  ┌──────────────┐            │       │
│  │  │ 9 Modèles   │  │ 2 Agents     │            │       │
│  │  │ Classe A    │  │ Monitoring   │            │       │
│  │  │             │  │ Irrigation   │            │       │
│  │  └─────────────┘  └──────────────┘            │       │
│  │                                                │       │
│  │  ┌─────────────┐  ┌──────────────┐            │       │
│  │  │ Knowledge   │  │ Knowledge    │            │       │
│  │  │ Base (527)  │  │ Graph        │            │       │
│  │  └─────────────┘  └──────────────┘            │       │
│  └───────────────────────────────────────────────┘       │
│                                                          │
│  ┌───────────────────────────────────────────────┐       │
│  │              Couche Transparence               │       │
│  │  Sources · Confiance · Hypothèses · Limites   │       │
│  └───────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Données utilisées

Le Copilot n'a pas de données propres. Il accède à l'intégralité du
Data Lake SmartAgri via l'Orchestrateur :

| Couche | Volume | Accès |
|--------|--------|-------|
| Météo (NASA POWER) | 329 232 lignes | Temps réel via API |
| Pluie (CHIRPS) | 28,9 M lignes | Quotidien |
| ET0 (FAO-56) | 329 232 lignes | Quotidien |
| Sol (iSDAsoil) | 13 890 lignes | Statique |
| NDVI (Sentinel-2) | 26 198 lignes | Mensuel |
| Prix (WFP) | 55 283 lignes | Mensuel |
| Rendements (FAO) | 956 lignes | Annuel |
| Knowledge | 527 chunks | Statique + enrichissement |

---

## 4. Modèles utilisés

Le Copilot appelle les modèles via l'Orchestrateur. Voici la matrice
d'utilisation par type de question :

| Type de question | Modèles appelés | Latence cible |
|------------------|-----------------|---------------|
| Irrigation | A1 + A4 + Agent Irrig. | < 1s |
| Diagnostic | A1 + A7 + A8 + Monit. | < 2s |
| Météo / Pluie | A4 + A2 + Monit. | < 1s |
| Planification | A6 + A5 + A3 + Know. | < 3s |
| Marché / Prix | A5 + A9 | < 1s |
| Culture / Pratiques | Know. + A6 | < 2s |
| Alerte | A8 + Monit. + A4 | < 1s |
| NDVI / Satellite | A7 | < 1s |

### Performances des modèles mobilisés

| Modèle | Champion | Métrique clé |
|--------|----------|-------------|
| A1 SoilNowcast | LightGBM | R² = 0.8375 |
| A2 ET0 Forecast | CatBoost | R² = 0.9997 |
| A3 Yield Forecast | CatBoost | R² = 0.9509 |
| A4 Rain Intelligence | CatBoost | AUC = 0.9650 |
| A5 Price Forecast | XGBoost | R² = 0.8995 |
| A6 Crop Calendar | CatBoost | F1 = 0.9799 |
| A7 NDVI Anomaly | LightGBM | F1 = 0.9943 |
| A8 Anomaly Intel. | Iso Forest | Recall flood = 0.95 |
| A9 Market Cluster | KMeans | Sil. = 0.345 |

---

## 5. Flux d'interaction

### 5.1 Flux principal

```
Utilisateur → Message
    │
    ├─ 1. INTENTION : classification de l'intention (15 types)
    │     irrigation, diagnostic, météo, planification, prix,
    │     culture, alerte, satellite, rendement, comparaison,
    │     historique, explication, conseil_général, urgence, autre
    │
    ├─ 2. PLAN : sélection des composants nécessaires
    │     Orchestrateur → table de routage (doc 80)
    │     Timeouts : 200ms (modèle unitaire) → 2s (multi-modèle)
    │
    ├─ 3. EXÉCUTION : appel parallèle des modèles
    │     Chaque modèle retourne : {valeur, confiance, metadata}
    │
    ├─ 4. SYNTHÈSE : agrégation des résultats
    │     Confiance composite = Σ (wi × ci) avec :
    │       SoilNowcast: w=0.35  Rain: w=0.25
    │       Anomaly: w=0.25      ET0: w=0.15
    │
    ├─ 5. EXPLICATION : génération de la réponse
    │     Réponse + Sources + Confiance + Hypothèses + Limites
    │
    └─ 6. AFFICHAGE : présentation transparente
          ┌───────────────────────────────────┐
          │ Réponse : "Irriguez 18 mm demain" │
          ├───────────────────────────────────┤
          │ Confiance : 82% (HAUTE)           │
          │ Modèles : SoilNowcast, Rain, Irrig│
          │ Sources : NASA POWER, CHIRPS, FAO  │
          │ Hypothèses : sol sableux, Kc=1.05  │
          │ Limite : proxy NASA, pas capteur    │
          └───────────────────────────────────┘
```

### 5.2 Flux avec conflit entre modèles

```
Situation : SoilNowcast dit "sol sec" mais Rain dit "pluie probable"

    ├─ Détection du conflit par l'Orchestrateur
    ├─ Règle : précaution > optimisme (doc 80, §7)
    ├─ Résolution : recommander irrigation réduite (50% dose)
    │
    └─ Affichage transparent :
          "Recommandation prudente : irriguez 9 mm (dose réduite).
           Le sol est sec (28%), mais Rain Intelligence prédit 45%
           de probabilité de pluie demain. Si la pluie arrive,
           l'irrigation de 9 mm reste sans risque de saturation.
           Confiance : 65% (MODÉRÉE) — conflit entre modèles."
```

### 5.3 Flux avec abstention

```
Situation : données météo périmées (> 48h)

    ├─ Orchestrateur détecte le retard
    ├─ Confiance dégradée sous seuil minimal (< 0.30)
    ├─ Abstention partielle : pas de prédiction chiffrée
    │
    └─ Réponse :
          "Je ne peux pas donner de recommandation d'irrigation
           précise : les données météo datent de 52 heures.
           En attendant, basez-vous sur les règles FAO-56 :
           si le sol semble sec au toucher à 10 cm, irriguez
           la dose standard pour l'oignon (15-20 mm).
           Source : Guide FAO-56 Irrigation and Drainage Paper 56."
```

---

## 6. Interactions

### 6.1 Modes d'interaction

| Mode | Description | Public cible |
|------|------------|--------------|
| **Chat texte** | Question/réponse en français | Techniciens, décideurs |
| **Chat vocal** | Question vocale, réponse vocale | Agriculteurs terrain |
| **Rapport** | Rapport parcellaire automatique | Techniciens |
| **Tableau de bord** | KPIs temps réel | Décideurs |
| **Alertes push** | Notifications proactives | Tous |

### 6.2 Personnalisation par profil

| Profil | Niveau de détail | Explication | Langue |
|--------|-----------------|-------------|--------|
| Agriculteur | Simple | Action concrète + pourquoi | Wolof/Français |
| Technicien | Détaillé | Modèles + métriques + alternatives | Français |
| Décideur | Synthétique | KPIs + tendances + risques | Français/Anglais |
| Chercheur | Complet | Données brutes + intervalles de confiance | Français/Anglais |

---

## 7. Cas d'usage

| # | Cas d'usage | Intention | Modèles | Confiance |
|---|-------------|-----------|---------|-----------|
| 1 | "Dois-je arroser ?" | irrigation | A1,A4,Irrig | HAUTE |
| 2 | "Mon champ va mal" | diagnostic | A1,A7,A8,Monit | BONNE |
| 3 | "Va-t-il pleuvoir ?" | météo | A4,A2 | HAUTE |
| 4 | "Quand planter ?" | planification | A6,A5,Know | BONNE |
| 5 | "Prix oignon demain ?" | prix | A5,A9 | MODÉRÉE |
| 6 | "Quel engrais ?" | culture | Know,A1 | BONNE |
| 7 | "Alerte dans mon champ" | alerte | A8,Monit,A4 | HAUTE |
| 8 | "NDVI en baisse" | satellite | A7,Know | HAUTE |
| 9 | "Rendement espéré ?" | rendement | A3,A1,A4 | MODÉRÉE |
| 10 | "Comparer Mboro/Potou" | comparaison | A1,A4,A5 | BONNE |
| 11 | "Pluie des 7 derniers jours" | historique | CHIRPS direct | HAUTE |
| 12 | "Pourquoi cette recommandation ?" | explication | Traçabilité | HAUTE |

---

## 8. Démonstration devant jury

### Scénario recommandé (5 min)

1. **Entrée en matière** (30s) : l'agriculteur ouvre le Copilot, pose une
   question simple : "Est-ce que je dois arroser mon oignon à Mboro ?"

2. **Réponse transparente** (60s) : montrer la réponse avec le panneau
   de transparence : modèles appelés (SoilNowcast R²=0.8375, Rain AUC=0.9650),
   confiance composite (82%), sources (NASA POWER, CHIRPS), hypothèses.

3. **Gestion de conflit** (60s) : injecter un scénario où SoilNowcast et
   Rain divergent. Montrer la résolution prudente et l'explication.

4. **Abstention honnête** (60s) : données périmées → le Copilot refuse de
   prédire et propose un fallback FAO-56.

5. **Multi-profil** (60s) : montrer la même question en mode agriculteur
   (simple) vs technicien (détaillé).

6. **Bilan** (30s) : 9 modèles, transparence complète, zéro hallucination.

### KPIs de démonstration

| KPI | Valeur |
|-----|--------|
| Modèles IA accessibles | 9 |
| Agents spécialisés | 2 |
| Chunks Knowledge | 527 |
| Intentions reconnues | 15 |
| Profils utilisateur | 4 |
| Niveaux de confiance | 5 (HAUTE → BLOQUÉE) |
| Temps de réponse cible | < 2s |

---

## 9. Exportabilité hors OctOpus

### Architecture de déploiement

```
smartagri-copilot/
├── copilot/
│   ├── controller.py          # Copilot Controller
│   ├── intent_classifier.py   # Classification d'intention
│   ├── response_builder.py    # Construction de réponse
│   ├── transparency.py        # Panneau de transparence
│   └── profiles.py            # Gestion des profils
├── orchestrator/               # (doc 80)
│   └── orchestrator.py
├── models/                     # 9 modèles ONNX/natifs
├── agents/                     # Monitoring + Irrigation
├── knowledge/                  # ChromaDB + embeddings
├── api/
│   ├── main.py                # FastAPI
│   ├── chat.py                # Endpoint chat
│   └── report.py              # Endpoint rapport
├── frontend/                   # (séparé, non inclus ici)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Dépendances supplémentaires (vs Digital Agronomist)

```
# En plus des dépendances doc 88 :
langdetect==1.0.9       # Détection de langue
```

---

## 10. Limites connues

| Limite | Impact | Mitigation |
|--------|--------|-----------|
| Pas de voix Wolof native | Exclusion de certains agriculteurs | Partenariat prévu |
| Pas de mode hors-ligne | Nécessite connectivité | Mode dégradé SMS planifié |
| Pas d'apprentissage du profil | Pas de personnalisation dynamique | Profils statiques |
| Latence multi-modèle | Jusqu'à 3s pour planification | Parallélisation |
| Pas de mémoire conversationnelle longue | Contexte limité | Fenêtre 10 tours |
