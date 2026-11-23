# LOCAL_AI_END_TO_END_REPORT — Démonstrateur Complet 30 Scénarios

**Date** : 2026-11-17  
**Mission** : LOCAL-AI-07  
**Script exécuté** : `python -m runtime.demo_e2e_30` (résultats bruts dans `smartagri-ai/manifests/e2e_30_results.json`)  
**Contraintes respectées** : aucun modèle modifié, aucun nouveau modèle créé.

---

## 1. Synthèse globale

| Indicateur | Valeur observée |
|---|---|
| **Scénarios exécutés** | **30 / 30** (`S01` → `S30` de `81_ai_execution_flows.md`) |
| **Scénarios `PASSED` (complets)** | **15 / 30** (50,0 %) |
| **Scénarios `PARTIAL` (abstention contrôlée par poids absents)** | **15 / 30** (50,0 % : 9 `PARTIAL_RAIN_ABSTAINED`, 6 `PARTIAL_MISSING_MODEL`) |
| **Scénarios `FAILED` (erreurs / crashs)** | **0 / 30** (0 %) |
| **Temps d'initialisation (chargement LightGBM + E5-Large + FAISS)** | **104 708,5 ms** (~104,7 s) |
| **Temps d'inférence moyen par scénario** | **113,98 ms** (de `0,02 ms` sur S29 à `452,34 ms` sur S19 RAG dense) |
| **Mémoire consommée (pic `tracemalloc`)** | **2 690,24 Mo** (courante fin de run : **2 547,07 Mo**) |
| **Score de confiance moyen final** | **0,8297** (`high`) |

---

## 2. Vérification des 6 composants

| Composant | Statut local | Rôle vérifié dans les 30 scénarios |
|---|---|---|
| **SoilNowcastService (A1)** | ✅ **100 % réel** (`soil_ready=True`, 15 LightGBM `.txt`) | Prédictions `J+1`/`J+2`/`J+3`, pénalité de confiance J-4 (`S16` : `0.5966`), abstention sur features manquantes (`S11`). |
| **RainIntelligenceService (A4)** | ⚠️ **Abstention contrôlée** (`rain_ready=False`, poids CatBoost absents) | Chargeur local prêt ; s'abstient proprement sur `S01`, `S04`, `S05`, `S12`, `S16`, `S18`, `S19`, `S28`, `S30` sans bloquer l'orchestrateur. |
| **AnomalyService (A8)** | ✅ **Seuils métier actifs** (`5/5` règles critiques) | Détecte sécheresse (`S03`, `S23`), inondation (`S06`, `S26`), canicule (`S13`, `S20`, `S30`), gel (`S14`). Poids statistiques ML absents. |
| **KnowledgeService (RAG)** | ✅ **100 % réel** (`e5_large+faiss`, 527 chunks) | Recherche dense `intfloat/multilingual-e5-large` + `FAISS` sur `S04` (`AssistantService`), `S07`–`S11`, `S17`, `S19`, `S22`, `S24`, `S27`. |
| **MonitoringEngine** | ✅ **100 % réel** | Évalue le risque et les alertes sur `S03`, `S06`, `S09`, `S13`, `S14`, `S20`, `S21`, `S23`, `S26`. |
| **IrrigationEngine** | ✅ **100 % réel** | Décisions FAO-56 (`S01`, `S15`, `S25`, `S28`) et garde-fou pluie > 5 mm (`S02` → `delay`, `hard_stop=True`). |

---

## 3. Détail des 30 scénarios (`S01` → `S30`)

| ID | Scénario | Statut | Intent | Composants utilisés | Confiance | Latence (ms) |
|---|---|---|---|---|---:|---:|
| **S01** | Irrigation simple, saison sèche | `PARTIAL_RAIN_ABSTAINED` | `irrigation` | `irrigation_engine`, `soil_nowcast` | 0.8353 | 65.23 |
| **S02** | Pluie imminente, reporter | `PASSED` | `irrigation` | `irrigation_engine`, `soil_nowcast`, `rain_intelligence` | 0.8353 | 25.69 |
| **S03** | Alerte sécheresse critique | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 25.97 |
| **S04** | Question agronomique générale | `PARTIAL_RAIN_ABSTAINED` | `soil_forecast` | `soil_nowcast` *(+ `AssistantService`)* | 0.8353 | 25.07 |
| **S05** | Conflit SoilNowcast vs Rain | `PARTIAL_RAIN_ABSTAINED` | `soil_forecast` | `soil_nowcast` | 0.8353 | 30.41 |
| **S06** | Excès d'eau, engorgement | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 27.64 |
| **S07** | Prévision rendement national (A3 absent) | `PARTIAL_MISSING_MODEL` | `general` | `knowledge` | 0.9106 | 322.44 |
| **S08** | Prix marché et tendance (A5/A9 absents) | `PARTIAL_MISSING_MODEL` | `price` | `knowledge` | 0.9169 | 366.56 |
| **S09** | NDVI anormal, stress végétatif (A7 absent) | `PARTIAL_MISSING_MODEL` | `anomaly_check` | `anomaly`, `monitoring_engine` | 0.8500 | 31.70 |
| **S10** | Phase culturale et Kc (A6 absent) | `PARTIAL_MISSING_MODEL` | `calendar` | `knowledge` | 0.9146 | 303.06 |
| **S11** | Abstention, manque de données | `PASSED` | `soil_forecast` | `knowledge` *(fallback après abstention sol)* | 0.9187 | 289.68 |
| **S12** | Rapport complet parcellaire | `PARTIAL_RAIN_ABSTAINED` | `soil_forecast` | `soil_nowcast` | 0.8353 | 26.55 |
| **S13** | Canicule Niayes (`T_max > 42C`) | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 27.71 |
| **S14** | Gel Niayes (`T_min < 10C`) | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 26.69 |
| **S15** | Multi-cultures, même parcelle | `PASSED` | `irrigation` | `irrigation_engine`, `soil_nowcast`, `rain_intelligence` | 0.8353 | 24.98 |
| **S16** | Données météo retardées (J-4) | `PARTIAL_RAIN_ABSTAINED` | `soil_forecast` | `soil_nowcast` | 0.5966 | 29.41 |
| **S17** | Comparaison inter-marchés (A5/A9 absents) | `PARTIAL_MISSING_MODEL` | `price` | `knowledge` | 0.9149 | 373.78 |
| **S18** | Stress hydrique progressif | `PARTIAL_RAIN_ABSTAINED` | `soil_forecast` | `soil_nowcast` | 0.8353 | 46.86 |
| **S19** | Fin hivernage, transition irrigation | `PARTIAL_RAIN_ABSTAINED` | `rain_forecast` | `knowledge` *(fallback)* | 0.9270 | 452.34 |
| **S20** | Anomalie, cause inconnue | `PASSED` | `anomaly_check` | `anomaly`, `monitoring_engine` | 0.7750 | 35.09 |
| **S21** | Bilan hebdomadaire automatique | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 29.98 |
| **S22** | Agriculteur hors zone couverte | `PASSED` | `general` | `knowledge` | 0.9041 | 338.72 |
| **S23** | ET0 extrême + sol sec | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 30.01 |
| **S24** | Conflit prix vs rendement (A3/A5 absents) | `PARTIAL_MISSING_MODEL` | `price` | `knowledge` | 0.9098 | 320.18 |
| **S25** | Dose précise goutte-à-goutte | `PASSED` | `irrigation` | `irrigation_engine`, `soil_nowcast`, `rain_intelligence` | 0.8353 | 32.68 |
| **S26** | Pluie extrême (`>100mm/3j`) | `PASSED` | `monitoring` | `monitoring_engine`, `anomaly` | 0.8500 | 28.45 |
| **S27** | Première connexion, onboarding | `PASSED` | `onboarding` | `knowledge` | 0.8000 | 0.03 |
| **S28** | Vérification post-irrigation | `PARTIAL_RAIN_ABSTAINED` | `irrigation` | `irrigation_engine`, `soil_nowcast` | 0.8353 | 55.53 |
| **S29** | Requête ambiguë, clarification | `PASSED` | `ambiguous` | `—` *(pas de ML)* | 0.2500 | 0.02 |
| **S30** | Escalade humaine après conflit | `PARTIAL_RAIN_ABSTAINED` | `soil_forecast` | `soil_nowcast` | 0.8353 | 26.83 |

---

## 4. Analyse des scénarios partiels et échecs

- **0 scénario échoué techniquement (`failed = 0`)**.
- **9 scénarios `PARTIAL_RAIN_ABSTAINED`** (`S01`, `S04`, `S05`, `S12`, `S16`, `S18`, `S19`, `S28`, `S30`) : dus uniquement à l'absence des poids CatBoost `A4_Rain_Intelligence` dans `models/rain_intelligence/`.
- **6 scénarios `PARTIAL_MISSING_MODEL`** (`S07`, `S08`, `S09`, `S10`, `S17`, `S24`) : dus à l'absence des poids locaux pour `A3_Yield`, `A5_Price`, `A6_Crop_Calendar`, `A7_NDVI_Anomaly` et `A9_Market_Clustering`, avec repli propre sur `KnowledgeService` (`e5_large+faiss`) ou `MonitoringEngine`.
