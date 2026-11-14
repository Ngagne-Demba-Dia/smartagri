# 32 — Validation globale du Sprint D (D0 → D8)

**Statut** : Exécuté et vérifié — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : synthèse et validation globale des Sprints D0 à D8 (socle transversal, branchement progressif des services réels `irrigation_need`, `weather`, `recommendations`, `kit_parameters`, `device_health`, et préparation technique complète des services conditionnés par des prérequis externes `fertilization`, `pest_risk`, `diagnosis_analyze`, `assistant_transcribe`).
**Références** : `docs/16_architecture_octopus.md` (gelé), `docs/22_backend_gap_analysis.md`, `docs/23_integration_plan.md`, `docs/24_backend_readiness_report.md`, `docs/25_rapport_D0.md` à `docs/31_rapport_D6.md`, `docs/33_readiness_ia_reelle.md`.

---

## 1. Bilan par sous-sprint (D0 → D8)

| Sprint | Périmètre | Statut | Rapport |
|---|---|---|---|
| **D0** | Socle transversal : `build_provenance` (Doc 16 § 9.2), chaîne de repli à 3 paliers (`ml` → `rules` → `last`), modes hybrides par service (`AGRI_MOCK` + `AGRI_SERVICES`) | **Terminé (100 %)** | `docs/25_rapport_D0.md` |
| **D1** | Service pilote **`irrigation_need`** (`GET /v1/fields/{id}/irrigation-need`), routage BFF sélectif par service, pile de test de contrat live | **Terminé (100 %)** | `docs/26_rapport_D1.md` |
| **D2** | **`weather`** + **`recommendations`** (+ feedback), correspondance déterministe UUID v4 canoniques ↔ slugs de démonstration (`fld-mboro-1`, `dev-0001`, etc.), repli ET0 météo | **Terminé (100 %)** | `docs/27_rapport_D2.md` |
| **D3** | **`kit_parameters`** (`GET /v1/devices/{id}/parameters` + `POST .../ack`, migration `003_device_parameter_sets.sql`) + **`device_health`** (`GET /v1/devices/{id}/health` + provenance sur `GET /v1/alerts`) | **Terminé (100 %)** | `docs/28_rapport_D3.md` |
| **D4** | **`fertilization`** + **`pest_risk`** : blocage agronomique documenté (tables N-P-K ISRA/CDH et seuils degrés-jours non intégrés) + préparation technique complète (services, routes, contrats, 0 dose chiffrée inventée) | **Préparé & testé (mode par défaut : `mock`)** | `docs/29_rapport_D4.md` |
| **D5** | **`diagnosis_analyze`** (`POST /v1/diagnoses/analyze`) : blocage modèle documenté (aucun poids ONNX `vis_disease`) + préparation technique complète (garde-fous 256 Kio, scope organisation, seuil d'abstention `< 0.7`, `503 MODEL_UNAVAILABLE` honnête) | **Préparé & testé (mode par défaut : `mock`)** | `docs/30_rapport_D5.md` |
| **D6** | **`assistant_transcribe`** (`POST /v1/assistant/transcribe`) : comparatif ASR (OpenAI Whisper / Azure Speech / Google Cloud STT v2) + préparation technique complète (256 Kio, `<= 60 s`, `wo|ff|fr`, `503 MODEL_UNAVAILABLE` sans clé ASR) | **Préparé & testé (mode par défaut : `mock`)** | `docs/31_rapport_D6.md` |
| **D7** | Validation globale (backend, frontend, contrats live, non-régression, respect des gels) | **Terminé (100 %)** | `docs/32_validation_globale_sprint_D.md` |
| **D8** | Analyse de préparation à l'IA réelle (`agriml` → bundles versionnés → `BundleRegistry`) | **Terminé (100 %)** | `docs/33_readiness_ia_reelle.md` |

---

## 2. État des 18 services de Doc 16 § 9.3 à l'issue du Sprint D

### 2.1 Services prêts et vérifiés en mode `real` (recommandés pour l'activation hybride immédiate)

```env
AGRI_MOCK=1
AGRI_SERVICES=irrigation_need=real,weather=real,recommendations=real,kit_parameters=real,device_health=real
```

| # | Service (`ServiceId`) | Route(s) réelle(s) vérifiée(s) | Contrat Zod validé en live | Source active |
|---|---|---|---|---|
| 1 | `weather` | `GET /v1/fields/{id}/weather` | `WeatherSchema` | `rules` (`open_meteo`, cache SQL + repli `stale=true`) |
| 3 | `irrigation_need` | `GET /v1/fields/{id}/irrigation-need` | `IrrigationNeedSchema` | `rules` (`irr_water_balance` FAO-56) |
| 5 | `recommendations` | `GET /v1/fields/{id}/recommendations`, `POST /v1/recommendations/{id}/feedback` | `RecommendationListSchema`, `RecommendationSchema` | `rules` (`irrigation_fao56`, `fertility_rules`) |
| 7 | `kit_parameters` | `GET /v1/devices/{id}/parameters`, `POST /v1/devices/{id}/parameters/ack`, `GET/PUT /v1/devices/{id}/thresholds` | `KitParametersSchema` | `rules` (`irr_water_balance`, `fert_reco`, `sm_calibration`, `phenology_stage`) |
| 13 | `device_health` | `GET /v1/devices/{id}/health`, `GET /v1/alerts`, `POST /v1/alerts/{id}/ack` | `DeviceHealthSchema`, `AlertListSchema` | `rules` (`anomaly_rules`) |

*(Les services existants `yield_forecast`, `water_savings`, `assistant_chat` et `map_layers` de base disposent également de leurs routes backend v1 ; leurs enrichissements V2/V3 restent pilotés par `AGRI_SERVICES`.)*

### 2.2 Services techniquement câblés et testés en backend, maintenus en `mock` par défaut en attendant un prérequis externe

| # | Service (`ServiceId`) | Route backend prête | Prérequis externe manquant | Comportement actuel en `real` |
|---|---|---|---|---|
| 6 | `fertilization` | `GET /v1/fields/{id}/fertilization` | Tables N-P-K par culture × stade × sol (ISRA/CDH) | Renvoie le déficit mesuré par le kit avec `dose_kg_ha=0` et consigne explicite (conforme `FertilizationSchema`) |
| 8 | `disease_diagnosis` (`diagnosis_analyze`) | `POST /v1/diagnoses/analyze` | Bundle ONNX `vis_disease` entraîné | Valide le scope et la taille (256 Kio), puis renvoie `503 MODEL_UNAVAILABLE` tant qu'aucun `VisionAnalyzer` n'est injecté |
| 9 | `pest_risk` | `GET /v1/fields/{id}/pest-risk` | Seuils thermiques et hygrométriques validés (ISRA/DPV) | Renvoie `level="low"` (`score=0.1`) à partir de la météo réelle et du cycle cultural (conforme `PestRiskSchema`) |
| 17 | `assistant_transcribe` | `POST /v1/assistant/transcribe` | Clé et fournisseur ASR (`wo`/`ff`/`fr`) | Valide 256 Kio, `<= 60 s` et langue, puis renvoie `503 MODEL_UNAVAILABLE` tant qu'aucun `Transcriber` n'est injecté |

### 2.3 Services V2/V3 maintenus en simulation (`mock`)

- `soil_forecast` (#2), `irrigation_plan` (#4), `trap_counts` (#10), `vegetation` (#11), `price_forecast` (#15) et les calques raster V3 de `map_layers` (#18).

---

## 3. Résultats des campagnes de vérification

### 3.1 Suite Backend (`pytest`)
- Commande : `python -m pytest -q` (dans `plateforme/backend`)
- Résultat : **218 tests passés, 0 échec**
- Couvre :
  - `tests/test_migrate.py` et `tests/test_schema_drift.py` (validation de `001_initial_schema.sql`, `002_row_level_security.sql` et `003_device_parameter_sets.sql` contre les modèles SQLAlchemy).
  - `tests/test_sprint_d0.py` (provenance, chaîne de repli, parsing `AGRI_SERVICES`).
  - `tests/test_irrigation_need.py` (service pilote D1).
  - `tests/test_sprint_d2.py` (UUID v4 déterministes du seed, résolution hybride des slugs démo, météo, recommandations, feedback, isolation multi-tenant).
  - `tests/test_sprint_d3.py` (publication et acquittement de `kit_parameters`, `device_health` 6 capteurs, provenance des alertes).
  - `tests/test_sprint_d4_d5_d6.py` (`fertilization`, `pest_risk`, `diagnoses/analyze` 200/404/413/503 + abstention `< 0.7`, `assistant/transcribe` 200/413/422/503).

### 3.2 Suite de contrats live BFF → FastAPI (`npm run test:live`)
- Pile locale : `python -m scripts.live_stack --stack-file ../web/.live-stack.json`
- Commande : `npm run test:live` (`vitest run --config vitest.live.config.ts`)
- Résultat : **4 fichiers de test passés, 16/16 tests passés**
  - `tests/live/irrigation-need.live.ts` (7/7)
  - `tests/live/weather-recommendations.live.ts` (4/4)
  - `tests/live/kit-device-health.live.ts` (2/2)
  - `tests/live/prepared-services.live.ts` (3/3)

### 3.3 Suite unitaire Frontend, Typage et Lint (`plateforme/web`)
- `npm test` (`vitest run`) : **31 fichiers passés, 630/630 tests passés**
- `npm run typecheck` (`tsc --noEmit`) : **0 erreur**
- `npm run lint` (`eslint . --max-warnings 0`) : **0 erreur, 0 avertissement**

---

## 4. Vérification du respect strict des contraintes

1. **`docs/16_architecture_octopus.md` non modifié** : vérifié par `git status` (aucune modification sur Doc 16).
2. **Contrats Frontend (`web/lib/contracts/*.ts`) non modifiés** : vérifié par `git status` (aucun fichier de `web/lib/contracts/` touché).
3. **Écrans et composants du Frontend RC non modifiés** : aucun fichier dans `web/features/*`, `web/components/*` ou `web/app/[locale]/*` n'a été touché ; seules les couches d'intégration BFF/mocks (`web/lib/service-mode.ts`, `web/app/api/dev/mock/route.ts`, `web/mocks/fixtures/places.ts`, `web/mocks/handlers/ai.ts`) et les tests (`web/tests/*`) ont été adaptés.
4. **Aucun repli silencieux vers la simulation en cas d'erreur API réelle** : un identifiant inconnu ou hors organisation renvoie un vrai `404 NOT_FOUND` ; un modèle indisponible sans repli de règles renvoie un vrai `503 MODEL_UNAVAILABLE`.
