# 22 — Écart backend : contrat (Doc 16) / FastAPI / Frontend / IA

> Sprint D, phases 1 à 3. Document de travail interne, confidentiel (partenaires uniquement).
> Date : 2026-11-09. Aucun fichier de code, aucun contrat ni le Doc 16 n'ont été modifiés pour l'écrire.

## 1. Objet et méthode

Ce document répond à une question : **pour chacun des 18 services du Doc 16 § 9, que fournit déjà FastAPI, qu'attend le Frontend gelé en RC, et que manque-t-il ?**

Sources relues dans le code (pas d'hypothèse) :

| Domaine | Fichiers |
|---|---|
| Contrat | `docs/16_architecture_octopus.md` § 9.2 à 9.5 (tableaux 9.3 et 9.4) |
| Backend | `backend/app/api/v1/*.py`, `api/health.py`, `core/constants.py`, `core/config.py`, `services/*` (dont `inference/`, `assistant/`), `tests/*.py` |
| Frontend | `web/lib/contracts/*.ts` (Zod), `web/lib/{modules,service-screens,mock-config}.ts`, `web/app/api/v1/[...path]/route.ts`, `web/mocks/*` |
| IA | `ml/catalog/models.yaml`, `ml/RESULTS_SMOKE.md`, `ml/bundles/`, `ml/artifacts/`, `ml/src/agriml/` |

Légende : **Oui** = vérifié dans le code ; **Non** = absent du code ; **Partiel** = présent mais écart précisé. Les durées sont des **estimations** (jours-ingénieur, une personne) et non des mesures.

### Chiffres clés

| Mesure | Valeur |
|---|---|
| Routes `/v1` codées | **40** (+ 3 d'infrastructure : `/healthz`, `/readyz`, `/metrics`) |
| Services Doc 16 dont la route existe | **5 sur 18** (1 weather, 5 recommendations, 12 yield_forecast, 14 water_savings, 16 assistant_chat) |
| Services dont la route n'existe qu'en partie | **3** (7 kit_parameters : seuils seulement ; 13 device_health : alertes seulement ; 18 map_layers : contours seulement) |
| Services sans aucune route | **10** (2, 3, 4, 6, 8, 9, 10, 11, 15, 17) |
| Routes proposées à créer par le Doc 16 | 13 (`soil-forecast`, `irrigation-need`, `irrigation-plan`, `fertilization`, `parameters`, `diagnoses/analyze`, `pest-risk`, `trap-counts`, `vegetation`, `devices/{id}/health`, `markets/prices`, `assistant/transcribe`, `?layers=` sur la carte) |
| Tests backend | 123 fonctions de test, 13 fichiers ; **aucun** test d'inférence ni de provenance |
| Routes qui renvoient le bloc `provenance` | **0** |

## 2. Phase 2 — Inventaire des routes FastAPI

Tout passe par le préfixe `/v1`, l'enveloppe `{success, data, error{code,message,details}, meta}` et un JWT Bearer, sauf `auth/token`, `auth/refresh`, les routes d'infrastructure et `telemetry/batch` (accepte aussi la clé d'appareil). L'isolement par organisation renvoie **404** hors organisation (testé : `test_cross_org.py`). Limites par minute (config) : 120 par défaut, 10 pour `auth`, 20 pour l'assistant.

Rôles d'écriture (`core/constants.py`) : `FARM_WRITERS` = farmer, coop_manager, admin ; `DEVICE_WRITERS` = coop_manager, admin ; `CROP_CYCLE_WRITERS` = + agronomist ; `ALERT_ACKERS`, `DIAGNOSIS_WRITERS`, `MAINTENANCE_WRITERS` = tous les rôles. Les lectures sont ouvertes à tout rôle de l'organisation.

« Test » : la route est exercée dans `backend/tests/` (appel direct ou test d'isolement).

| # | Méthode et URI | Entrée | Sortie (`data`) | Auth / rôle | Test |
|---|---|---|---|---|---|
| 1 | `POST /v1/auth/token` | `LoginIn` | jetons access et refresh | public, 10/min | Oui |
| 2 | `POST /v1/auth/refresh` | `RefreshIn` | nouveaux jetons | public | Oui |
| 3 | `POST /v1/auth/logout` | `RefreshIn` | acquittement | JWT | Oui |
| 4 | `GET /v1/me` | — | profil, rôle, organisation | JWT | Oui |
| 5 | `GET /v1/farms` | — | liste des exploitations | JWT | Oui |
| 6 | `POST /v1/farms` | `FarmIn` | exploitation créée (201) | FARM_WRITERS | Oui |
| 7 | `GET /v1/farms/{farm_id}/fields` | — | liste des parcelles | JWT | Oui |
| 8 | `POST /v1/farms/{farm_id}/fields` | `FieldIn` | parcelle créée (201) | FARM_WRITERS | Oui (via conftest) |
| 9 | `GET /v1/farms/{farm_id}/map` | — | GeoJSON des parcelles (sans couches IA) | JWT | Oui (isolement) |
| 10 | `GET /v1/fields/{field_id}` | — | parcelle | JWT | Oui (isolement) |
| 11 | `GET /v1/fields/{field_id}/recommendations` | — | irrigation et fertilisation (règles) | JWT | Oui |
| 12 | `GET /v1/fields/{field_id}/weather` | `days` (défaut 7, max 16) | prévision par jour, fournisseur Open-Meteo, cache | JWT | Oui |
| 13 | `GET /v1/fields/{field_id}/yield-forecast` | `refresh` | `forecast`, `crop_cycle`, `actual_t_ha`, `caveat` ; 404 `NO_ACTIVE_CYCLE` | JWT | Isolement seulement |
| 14 | `GET /v1/fields/{field_id}/crop-cycles` | — | cycles | JWT | Oui |
| 15 | `POST /v1/fields/{field_id}/crop-cycles` | `CropCycleIn` | cycle créé (201) | CROP_CYCLE_WRITERS | Oui |
| 16 | `PATCH /v1/crop-cycles/{cycle_id}` | `CropCyclePatch` | cycle mis à jour | CROP_CYCLE_WRITERS | Oui |
| 17 | `POST /v1/devices` | `DeviceIn` | kit enregistré (201) | DEVICE_WRITERS | Oui |
| 18 | `GET /v1/devices` | `status` | liste des kits | JWT | Oui |
| 19 | `GET /v1/devices/{device_id}` | — | kit | JWT | Oui |
| 20 | `GET /v1/devices/{device_id}/thresholds` | — | seuils start/stop | JWT | Oui |
| 21 | `PUT /v1/devices/{device_id}/thresholds` | `ThresholdsIn` | seuils appliqués ; 400 `THRESHOLDS_INVALID` | THRESHOLD_WRITERS | Oui |
| 22 | `GET /v1/devices/{device_id}/measurements` | `bucket`, `from`, `to` | mesures brutes ou agrégées | JWT | Oui (isolement) |
| 23 | `POST /v1/telemetry/batch` | `TelemetryBatch` | `IngestResultOut` | JWT (TELEMETRY_WRITERS) ou clé d'appareil | Oui (6 fichiers) |
| 24 | `GET /v1/alerts` | `status`, `device_id` | alertes | JWT | Oui |
| 25 | `POST /v1/alerts/{alert_id}/ack` | — | alerte acquittée | ALERT_ACKERS | Oui |
| 26 | `POST /v1/diagnoses` | `DiagnosisIn` (verdict calculé ailleurs, `image` = clé de stockage) | diagnostic enregistré (201) | DIAGNOSIS_WRITERS | Oui |
| 27 | `POST /v1/recommendations/{id}/feedback` | `FeedbackIn` | retour enregistré | FEEDBACK_WRITERS | Oui |
| 28 | `GET /v1/campaigns` | `status` | campagnes | JWT | Oui |
| 29 | `POST /v1/campaigns` | `CampaignIn` | campagne (201) | CAMPAIGN_WRITERS | Oui |
| 30 | `GET /v1/campaigns/{campaign_id}` | — | campagne | JWT | Oui |
| 31 | `PATCH /v1/campaigns/{campaign_id}` | `CampaignPatch` | campagne | CAMPAIGN_WRITERS | Oui |
| 32 | `GET /v1/campaigns/{campaign_id}/summary` | — | synthèse | JWT | Oui |
| 33 | `GET /v1/equipment` | `farm_id`, `kind`, `status` | équipements | JWT | Oui |
| 34 | `POST /v1/equipment` | `EquipmentIn` | équipement (201) | EQUIPMENT_WRITERS | Oui |
| 35 | `PATCH /v1/equipment/{equipment_id}` | `EquipmentPatch` | équipement | EQUIPMENT_WRITERS | Oui |
| 36 | `GET /v1/equipment/{equipment_id}/maintenance` | — | historique | JWT | Oui |
| 37 | `POST /v1/equipment/{equipment_id}/maintenance` | `MaintenanceIn` | entrée (201) | MAINTENANCE_WRITERS | Oui |
| 38 | `GET /v1/reports/kpis` | `scope`, `id`, `from`, `to` | `scope, scope_id, from, to, kpis{…}` | JWT | Oui |
| 39 | `GET /v1/reports/export.csv` | idem | CSV | JWT | Oui |
| 40 | `POST /v1/assistant/chat` | `ChatIn` (garde-fou 10 000 caractères, limite métier 2 000) | un seul JSON : `conversation_id, reply, stop_reason, tools_used, truncated, limit_reached, model, fallback_used, refusal_category, language_quality_notice` ; erreurs `ASSISTANT_*` | JWT, 20/min | Oui (17 tests) |
| i1 | `GET /healthz` | — | vivacité | public | Oui |
| i2 | `GET /readyz` | — | disponibilité (`NOT_READY`) | public | Oui |
| i3 | `GET /metrics` | — | Prometheus | public, hors schéma, hors enveloppe | Non vérifié |

### Comparaison systématique au Doc 16 (routes existantes)

| Route | Contrat Doc 16 | Constat |
|---|---|---|
| `GET …/weather` | 9.3 n° 1 ; 9.4 : températures, pluie, P(pluie), ET0, biais local | **Conforme au Zod** pour `date, t_max_c, t_min_c, precipitation_mm, et0_mm, et0_hargreaves_mm` ; les trois champs IA (`rain_probability`, `rain_threshold_mm`, `local_bias_c`) sont absents et le Zod les met à `null` par défaut. Pas de `provenance`. |
| `GET …/yield-forecast` | 9.3 n° 12 | **Conforme au Zod** (`forecast{model_name, model_version, predicted_t_ha, p10, p90, created_at}`, `crop_cycle`, `actual_t_ha`, `caveat`). Pas de `provenance`. Pas de repli par règles (R12). |
| `GET …/recommendations` | 9.3 n° 5 | Deux types seulement (`irrigation`, `fertilization`). **Non conforme sur un point** : voir écart E1. |
| `POST …/feedback` | 9.3 n° 5 | Conforme (quatre valeurs `followed, partially_followed, ignored, not_applicable`). |
| `GET /alerts`, `POST /alerts/{id}/ack` | 9.3 n° 13 | Conforme pour la partie règles ; pas de `provenance`. |
| `GET /reports/kpis` | 9.3 n° 14 | Renvoie les clés `devices, fields, water_m3, devices_without_flow, pump_hours, irrigation_events, measurements, kit_uptime_pct, alerts_by_rule, diagnoses_by_label, recommendations_feedback, recommendations_followed_pct`. **Aucune** économie d'eau en m³ ni en % ni méthode « parcelles témoins » : le service `water_savings` n'est pas implémenté, seul le cadre KPI existe. |
| `POST /assistant/chat` | 9.3 n° 16 | Passerelle, garde-fous et erreurs existent (`ASSISTANT_*`, `RATE_LIMITED`). **Écarts mineurs** : la réponse est un JSON unique (le Doc 16 prévoit un flux) ; `citations` et `refusal` n'existent pas côté API (le Zod les met à `[]` et `null`), l'API envoie à la place `refusal_category`. |
| `GET …/map` | 9.3 n° 18 | Contours uniquement ; le paramètre `?layers=` n'existe pas. |
| `PUT …/thresholds` | 9.3 n° 7 | Conforme (`THRESHOLDS_INVALID`) ; aucune version de jeu de paramètres. |

## 3. Phase 1 — Les 18 services

Colonnes demandées. « Route Front » = écran et route BFF (le proxy `web/app/api/v1/[...path]` transmet l'URI inchangée). « Conforme » compare la réponse FastAPI au schéma Zod du Frontend (qui reflète le Doc 16 § 9.4). Priorité : P1 à P7 = ordre imposé du sprint pour les routes manquantes ; P0 = défaut sur route existante ; — = hors périmètre du sprint (V2, V3).

| # | Service | Écran | Contrat Doc 16 | Route Front (BFF) | Route API réelle | Existe ? | Conforme ? | Écart identifié | Priorité |
|---|---|---|---|---|---|---|---|---|---|
| 1 | weather | `/meteo` | 9.3 n° 1, MVP et V2 | `/api/v1/fields/{id}/weather?days=` | `GET /v1/fields/{field_id}/weather` | **Oui** | Partiel | Pas de `provenance` ; P(pluie), seuil et biais local absents (modèles `wx_*` non codés) | P0 |
| 2 | soil_forecast | `/previsions` | n° 2, V2 | `/api/v1/fields/{id}/soil-forecast` | — | **Non** | — | Route absente ; modèle `soil_moisture_forecast` entraîné (synthétique), pas de bundle vérifié | V2 |
| 3 | irrigation_need | `/irrigation` | n° 3, MVP et V2 | `/api/v1/fields/{id}/irrigation-need` | — (le calcul FAO-56 existe dans `recommendations`) | **Non** | — | Route absente ; `rain_expected_mm` jamais calculé | **P1** |
| 4 | irrigation_plan | `/planning` | n° 4, V3 | `/api/v1/farms/{id}/irrigation-plan` | — | **Non** | — | Route et ordonnanceur absents | V3 |
| 5 | recommendations | `/recommandations` | n° 5, MVP | `/api/v1/fields/{id}/recommendations` | `GET /v1/fields/{field_id}/recommendations`, `POST /v1/recommendations/{id}/feedback` | **Oui** | **Non** (E1) | `payload.crop` est un objet, le Zod attend une chaîne ; pas de `provenance` | P0 |
| 6 | fertilization | `/fertilisation` | n° 6, V1.1 et V2 | `/api/v1/fields/{id}/fertilization` | — (un niveau bas/moyen/élevé existe dans `recommendations`) | **Non** | — | Route absente ; pas de doses N, P, K en kg/ha | **P3** |
| 7 | kit_parameters | `/kit` | n° 7, V1.1 | `/api/v1/devices/{id}/parameters` | `GET` et `PUT …/thresholds` seulement | **Non** (seuils : oui) | — | Pas de jeu versionné (`version`, `emis_a`, `npk`, `etalonnage`, `agro`) ni d'accusé de réception | **P2** |
| 8 | disease_diagnosis | `/maladies` | n° 8, V2 | `/api/v1/diagnoses/analyze` | `POST /v1/diagnoses` (enregistrement seul) | **Non** (analyse) | — | Pas d'inférence côté serveur ; pas de dépôt d'image ; 413 non géré | **P7** |
| 9 | pest_risk | `/risques` | n° 9, V1.1 et V2 | `/api/v1/fields/{id}/pest-risk` | — | **Non** | — | Route absente ; aucune règle de ravageur codée | **P4** |
| 10 | trap_counts | `/pieges` | n° 10, V3 | `/api/v1/devices/{id}/trap-counts` | — | **Non** | — | Route et modèle `vis_pest_count` absents | V3 |
| 11 | vegetation | `/vegetation` | n° 11, V2 | `/api/v1/fields/{id}/vegetation` | — | **Non** | — | Aucune source satellite ingérée | V2 |
| 12 | yield_forecast | `/rendement` | n° 12, V3 | `/api/v1/fields/{id}/yield-forecast` | `GET /v1/fields/{field_id}/yield-forecast` | **Oui** | Oui (forme) | Pas de `provenance` ; modèle entraîné sur données synthétiques ; pas de repli par règles | P0 |
| 13 | device_health | `/alertes`, tableau | n° 13, MVP et V2 | `/api/v1/alerts`, `/api/v1/devices/{id}/health` | `GET /v1/alerts`, `POST /v1/alerts/{id}/ack` | Alertes **oui**, santé **non** | Alertes oui | Route `…/health` absente (états des capteurs, `pump_failure_48h`) | **P5** |
| 14 | water_savings | `/rapports` | n° 14, V1.1 | `/api/v1/reports/kpis` | `GET /v1/reports/kpis` | **Oui** (KPI) | Partiel | Pas d'économie d'eau en m³ ni en %, pas de méthode | P0 |
| 15 | price_forecast | `/marches` | n° 15, V3 | `/api/v1/markets/prices` | — | **Non** | — | Route, données de prix et modèle absents | V3 |
| 16 | assistant_chat | `/assistant` | n° 16, MVP | `/api/v1/assistant/chat` | `POST /v1/assistant/chat` | **Oui** | Oui (erreurs) | Pas de `provenance` ; fournisseur LLM réel à confirmer en intégration | P0 |
| 17 | assistant_transcribe | `/assistant` | n° 17, V2 | `/api/v1/assistant/transcribe` | — | **Non** | — | Route absente ; aucun modèle ASR pour `wo` et `ff` | **P6** |
| 18 | map_layers | `/carte` | n° 18, V3 | `/api/v1/farms/{id}/map?layers=` | `GET /v1/farms/{farm_id}/map` | **Oui** (contours) | Partiel | `?layers=` non géré ; aucune couche culture, salinité ou contour proposé | V3 |

Lecture : sur 18 services, **5 ont leur route** (1, 5, 12, 14, 16), **3 l'ont en partie** (7, 13, 18) et **10 n'en ont aucune** (2, 3, 4, 6, 8, 9, 10, 11, 15, 17). **Sept services sont dans le périmètre du sprint** : 3, 6, 7, 8, 9, 13 (route santé) et 17. Les six autres (2, 4, 10, 11, 15, 18) sont V2 ou V3 au Doc 16 et le sprint D n'y touche pas.

## 4. Écarts transverses

| # | Écart | Preuve | Effet |
|---|---|---|---|
| **E1** | `recommendations.irrigation_payload` renvoie `crop` = `crop_state(...)` (un **dict**) ; le Zod `IrrigationPayloadSchema` attend `crop: z.string().nullable()` | `services/recommendations.py` ; `web/lib/contracts/field.ts` l. 61–75 | En mode réel, la validation `parseContract` échouera : le BFF renverra `BAD_RESPONSE` 502 sur `/recommandations`. Invisible tant que `AGRI_MOCK=1`. **Correction de bug** admise dans le Frontend (ou côté API, au choix : voir plan D0). |
| **E2** | `IrrigationInput.rain_forecast_mm` existe mais n'est jamais renseigné | `services/agronomy.py`, `recommendations.irrigation_payload` | Le conseil d'irrigation ignore la pluie annoncée alors que la météo est disponible. Prérequis de `irrigation_need` (`defer`, `rain_expected_mm`). |
| **E3** | Aucune route n'envoie le bloc `provenance` (Doc 16 § 9.2) | recherche dans `app/` : aucune occurrence de `fallback_step` | Le Frontend l'accepte `null` sur les routes existantes (`OptionalProvenance`) mais **exige** `ProvenanceSchema` sur les routes proposées. |
| **E4** | La chaîne de repli n'est pas codée (R12) ; `predict_or_503` n'essaie qu'un seul backend | `services/inference/factory.py`, `base.py` | Un modèle absent donne `MODEL_UNAVAILABLE` 503 sans passer par les règles. |
| **E5** | Bascule de simulation **globale** : `AGRI_MOCK=1` (MSW, hôte `api.mock.invalid`) ou `API_BASE_URL` | `web/lib/mock-config.ts`, `web/mocks/index.ts` | Impossible de brancher un seul service réel : un service réel exige un mode hybride. Les mocks ne répondent que pour les ids des fixtures. |
| **E6** | Aucun test d'inférence ni de provenance ; `yield-forecast` n'a qu'un test d'isolement | `backend/tests/` | Toute route IA nouvelle part sans filet. |
| **E7** | Contrat OctOpus non confirmé ; client httpx interne marqué « à vérifier » | `ml/src/agriml/octopus/client.py` | L'étape 1 de la chaîne de repli (lot OctOpus) n'est pas utilisable. |

## 5. Phase 3 — Routes manquantes prioritaires

Pour chaque route : contrat attendu = schéma Zod du Frontend (identique au Doc 16 § 9.4), donc **non modifiable**. Toutes renvoient `provenance` (obligatoire).

### P1 — `irrigation_need` : `GET /v1/fields/{field_id}/irrigation-need`

| Rubrique | Contenu |
|---|---|
| Contrat | `{field_id, window_hours: 24, need_mm ≥ 0, volume_m3 \| null, defer, defer_reason \| null, rain_expected_mm \| null, provenance}` ; p95 < 300 ms ; confiance `none` (bilan MVP) |
| Dépendances | `agronomy.recommend_irrigation` (FAO-56, Hargreaves, Kc par stade, 7 cultures), `weather.forecast_with_cache` (pluie à 24 h), dernière mesure d'humidité, seuils du kit, cycle de culture actif, `RAIN_SKIP_MM`, `IRRIGATION_EFFICIENCY`, surface de la parcelle (m³) |
| Modèle IA | `irr_water_balance` du catalogue = **règles FAO-56 déjà codées** ; `irr_need_24h` (ML) reporté V2 faute de données réelles |
| Source des données | Télémétrie du kit + météo Open-Meteo + cycle de culture : toutes déjà en base |
| Erreurs | `NO_ACTIVE_CYCLE` 404, `WEATHER_UNAVAILABLE` 503 (repli : climatologie, si défini), `LOCATION_REQUIRED` 400 |
| Effort (estimation) | 3 à 4 j : service + route + schéma + tests ; inclut E2 |

### P2 — `kit_parameters` : `GET /v1/devices/{device_id}/parameters` (+ accusé `POST …/parameters/ack` proposé au § 6.2)

| Rubrique | Contenu |
|---|---|
| Contrat | `{device_id, version ≥ 1, emis_a, seuils{start,stop}, npk{n,p,k}, etalonnage{adc_sec,adc_eau}, agro{culture,stade,date_semis,kc}, applied, provenance{seuils,npk,etalonnage,agro}}` ; bornes : `start + 5 ≤ stop ≤ 100`, NPK 0–2 000 mg/kg, ADC 0–4 095, Kc 0,1–1,5 |
| Dépendances | Table des seuils actuelle (`GET/PUT thresholds`), cycle actif, `fertility_status`, nouvelle table `device_parameter_sets` (version strictement croissante) + migration |
| Modèle IA | `irr_water_balance` (règles), `sm_calibration`, `fert_reco` : tous en règles ou valeurs d'usine au départ ; provenance par bloc |
| Source des données | Seuils déjà stockés ; NPK et étalonnage : valeurs d'usine du firmware (NPK codés en dur N < 20, P < 10, K < 80) |
| Limite connue | Le bloc `agro` dépend du backlog firmware E1 (doc 12) : l'API peut l'émettre, le kit ne l'applique pas encore |
| Effort (estimation) | 4 à 6 j (migration, service, route, ack, tests) |

### P3 — `fertilization` : `GET /v1/fields/{field_id}/fertilization`

| Rubrique | Contenu |
|---|---|
| Contrat | `{field_id, crop, stage, n_kg_ha, p_kg_ha, k_kg_ha, npk_class, indicative, caveat, provenance}` ; `indicative = true` tant que l'étalonnage n'est pas validé |
| Dépendances | `fertilization_payload` et `fertility_status` (niveaux bas/moyen/élevé), dernière mesure NPK (`npk_ok`), cycle actif |
| Modèle IA | `fert_reco` : règles. **Les doses en kg/ha n'existent pas dans le code** : il faut un barème par culture et par stade (source agronomique à valider avec l'agronome) |
| Source des données | Mesures NPK du kit (indicatives) ; barème à saisir |
| Effort (estimation) | 3 j si le barème est fourni ; sinon bloqué par la donnée |

### P4 — `pest_risk` : `GET /v1/fields/{field_id}/pest-risk`

| Rubrique | Contenu |
|---|---|
| Contrat | `{field_id, pests[{pest_code, level low\|medium\|high, p_outbreak_7d \| null, p_outbreak_14d \| null, factors[]}], provenance}` |
| Dépendances | Météo (température, humidité), phénologie du cycle, table de règles par culture |
| Modèle IA | `risk_rules` (règles) au départ ; `pest_phenology` et `pest_risk_ml` en V2. Un artefact `disease_risk_binary` existe dans `ml/artifacts` (synthétique, non vérifié) et ne doit pas être exposé |
| Source des données | Météo existante ; règles agronomiques à rédiger et à faire valider |
| Effort (estimation) | 4 j (règles, route, tests), probabilités `null` en règles |

### P5 — `device_health` : `GET /v1/devices/{device_id}/health`

| Rubrique | Contenu |
|---|---|
| Contrat | `{device_id, checked_at, sensors[{sensor soil\|bme\|npk\|flow\|pump\|battery, state, since}], pump_failure_48h \| null, provenance}` |
| Dépendances | Dernière mesure et drapeaux de validité (`npk_ok`…), moteur d'alertes `alerting` (règles existantes), `kit_uptime_pct` |
| Modèle IA | `anomaly_rules` (règles, déjà là sous forme d'alertes) ; `anomaly_ml` et `pump_health` V2 |
| Source des données | Télémétrie et alertes déjà en base |
| Effort (estimation) | 3 j |

### P6 — `assistant_transcribe` : `POST /v1/assistant/transcribe`

| Rubrique | Contenu |
|---|---|
| Contrat | Audio ≤ 60 s (hyp.), langue `wo\|ff\|fr` ; sortie texte modifiable + langue détectée ; < 3 s pour 10 s d'audio ; erreurs `PAYLOAD_TOO_LARGE`, `MODEL_UNAVAILABLE` |
| Dépendances | Corps JSON `{audio_base64, content_type, duration_s ≤ 60, language_hint}` (forme du Zod `TranscribeInputSchema`), limite de taille, limiteur assistant (20/min), modèle ASR |
| Modèle IA | `asst_asr` : **aucun modèle exploitable** ; le wolof et le peul n'ont pas de données d'entraînement dans le dépôt |
| Source des données | À constituer |
| Effort (estimation) | 5 j pour une intégration avec un fournisseur externe ; indéterminé pour un modèle propre. Réponse honnête en attendant : `MODEL_UNAVAILABLE` 503 |

### P7 — `diagnosis_analyze` : `POST /v1/diagnoses/analyze`

| Rubrique | Contenu |
|---|---|
| Contrat | Entrée : image (413 au-delà de la taille maximale), `device_id` ou `field_id`, `captured_at` ; sortie : `label healthy\|suspect\|sick`, `disease_code`, 3 classes les plus probables, `abstained` (seuil 0,7, `DISEASE_MIN_CONFIDENCE`) ; p95 < 1,5 s |
| Dépendances | Dépôt d'image (`storage_key` existe déjà côté `ImageRef`, stockage objet à confirmer), `POST /diagnoses` (enregistrement), runtime d'inférence image |
| Modèle IA | `vis_disease` : un artefact `vision_disease` existe dans `ml/artifacts`, entraîné sur données synthétiques ; **aucun bundle vérifié**, dépendances optionnelles (onnx…) absentes |
| Source des données | Aucune photo réelle étiquetée dans le dépôt |
| Effort (estimation) | 5 à 8 j pour la route et le runtime ; la valeur dépend d'un jeu d'images réelles |

## 6. Synthèse

- **Ce qui existe** : 40 routes testées (hors inférence), enveloppe, JWT, RLS, rôles, météo, moteur FAO-56, alertes, KPI, assistant, enregistrement des diagnostics.
- **Ce qui manque** : 13 routes ou paramètres de service (10 services sans route, 3 incomplets), le bloc `provenance` partout, la chaîne de repli, un mode de simulation par service.
- **Un bug latent** (E1) sur une route existante, invisible tant que les mocks tournent.
- **Aucun modèle ML n'est prêt pour la production** (voir doc 24) : tous les sept services manquants du sprint peuvent d'abord être servis par des **règles**, avec `source: rules` et `fallback_step: 2`, ce qui est conforme au contrat.
