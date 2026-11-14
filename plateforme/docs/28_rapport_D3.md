# 28 — Rapport d'exécution du Sprint D3 (`kit_parameters` + `device_health`)

**Statut** : Exécuté et vérifié — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : branchement réel et tests de contrat live de `kit_parameters` (`GET /v1/devices/{device_id}/parameters` + `POST /v1/devices/{device_id}/parameters/ack`) et de `device_health` (`GET /v1/devices/{device_id}/health` + `GET /v1/alerts` + `POST /v1/alerts/{id}/ack`).
**Références** : `docs/16_architecture_octopus.md` § 6.1 et § 9.3 (intouché), `docs/22_backend_gap_analysis.md`, `docs/23_integration_plan.md` § 3.4, `docs/27_rapport_D2.md`.

---

## 1. État initial

À l'entrée du Sprint D3 :

1. **`kit_parameters` (service 7 de Doc 16 § 9.3)** :
   - Le backend gérait déjà `GET/PUT /v1/devices/{device_id}/thresholds` (seuils d'irrigation choisis par l'agriculteur), mais n'exposait ni `GET /v1/devices/{device_id}/parameters` ni `POST /v1/devices/{device_id}/parameters/ack`, et ne disposait pas de table dédiée `device_parameter_sets`.
   - Le contrat Frontend (`KitParametersSchema` dans `web/lib/contracts/device.ts`) exige 4 blocs indépendants (`seuils`, `npk`, `etalonnage`, `agro`) avec un bloc `provenance` par sous-ensemble (`irr_water_balance`, `fert_reco`, `sm_calibration`, `phenology_stage`).
2. **`device_health` (service 13 de Doc 16 § 9.3)** :
   - Le moteur d'alertes (`backend/app/services/alerting.py`) évaluait déjà `soil_sensor_failure`, `pump_fault`, `dry_soil_persistent`, `device_silent` et `disease_suspected` lors de l'ingestion, mais la route `GET /v1/devices/{device_id}/health` n'existait pas côté backend et `alert_view()` ne renvoyait pas le champ `provenance` attendu par `AlertSchema`.

---

## 2. Modifications réalisées

### Base de données (`plateforme/db/migrations/`)
- **`003_device_parameter_sets.sql`** : migration additive et idempotente créant la table `device_parameter_sets` (`id`, `created_at`, `organization_id`, `device_id`, `version`, `issued_at`, `payload`, `applied`, `applied_at`), index `(device_id, version DESC)`, contrainte d'unicité `(device_id, version)`, politique RLS `tenant_isolation` et droits `agri_app` / `agri_worker`.

### Backend (`plateforme/backend/`)
- **`app/db/models/device.py` & `app/db/models/__init__.py`** : ajout du modèle ORM `DeviceParameterSet`.
- **`app/schemas/devices.py`** : ajout de `ParametersAckIn(version: int | None = None, applied: bool = True)`.
- **`app/services/kit_parameters.py`** :
  - Calcul des seuils conseillés par texture de sol (`sableux`/`dior`/`loamy_sand` → `28/55`, `deck` → `32/62`, `argileux`/`hollaldé` → `38/70`, défaut `30/60`) sans jamais écraser `device_thresholds` (respect strict de Doc 16 § 6.1 : *« Les seuils conseillés ne remplacent jamais automatiquement les seuils choisis par l'agriculteur »*).
  - Construction du bloc `agro` (`culture`, `stade`, `date_semis`, `kc`) à partir du cycle cultural actif et des courbes FAO-56 (`agronomy.py`).
  - Courbe d'étalonnage usine (`{"adc_sec": 3200, "adc_eau": 1350}`, fallback documenté dans `ml/catalog/models.yaml` pour `sm_calibration`) fournie tant qu'aucune courbe gravimétrique propre au kit n'est enregistrée, conformément à `KitParametersSchema`.
  - Acquittement (`acknowledge_parameters`) mettant à jour `applied` et `applied_at` avec journalisation d'audit (`device.parameters_ack`).
- **`app/services/device_health.py`** :
  - Agrégation de l'état des 6 capteurs (`soil`, `bme`, `npk`, `flow`, `pump`, `battery`) à partir du dernier point de télémétrie, des équipements rattachés (`flow_m3h`) et des alertes ouvertes/acquittées (`since`).
  - `pump_failure_48h: None` tant que le modèle V2 `pump_health` n'est pas chargé (honnêteté de l'absence de modèle prédictif).
  - Provenance `anomaly_rules` (`source="rules"`, `fallback_step=2`, `stale` calculé selon `device_silent_hours`).
- **`app/services/alerting.py`** : enrichissement de `alert_view()` avec `provenance` (`anomaly_rules`, `source="rules"`).
- **`app/api/v1/devices.py`** : ajout des routes `GET /v1/devices/{device_id}/parameters`, `POST /v1/devices/{device_id}/parameters/ack` et `GET /v1/devices/{device_id}/health`.

### Frontend Mocks, Routage Hybride & Tests (`plateforme/web/`)
- **`lib/service-mode.ts`** : rattachement explicite de `/v1/devices/{id}/parameters/ack` au service `kit_parameters` (`EXTRA_SERVICE_ROUTES`), sans modifier `lib/contracts/registry.ts` (gelé).
- **`mocks/handlers/ai.ts`** : ajout du handler `POST /v1/devices/:id/parameters/ack` pour la symétrie complète du routeur MSW.
- **`tests/live/kit-device-health.live.ts`** : tests de contrat live BFF → FastAPI validant `KitParametersSchema`, `DeviceHealthSchema` et `AlertListSchema`.
- **`backend/tests/test_sprint_d3.py`** : tests unitaires et d'intégration backend (publication, acquittement, 404 version inconnue, isolation multi-organisation, états de santé capteurs `ok`/`fault`/`absent`, provenance des alertes).

---

## 3. Tests exécutés

1. **Backend (`pytest`)** :
   - `tests/test_sprint_d3.py`, `tests/test_migrate.py`, `tests/test_schema_drift.py`, `tests/test_alerting.py` : **100 % passants** (la migration `003_device_parameter_sets.sql` est automatiquement découverte et validée par `test_split_real_migrations_yields_single_statements` et `test_schema_drift.py`).
2. **Contrat live (`vitest.live.config.ts`)** :
   - `tests/live/kit-device-health.live.ts` : validation stricte de `KitParametersSchema`, `DeviceHealthSchema` et `AlertListSchema` (**2/2 passants**).

---

## 4. Risques résiduels et points de vigilance

1. **Étalonnage sonde capacitive (`sm_calibration`)** : en l'absence de mesures gravimétriques de terrain propres au kit, `etalonnage` utilise la courbe usine documentée dans `ml/catalog/models.yaml` (`adc_sec=3200`, `adc_eau=1350`, `source="rules"`, `fallback_step=2`).
2. **Prédiction de panne pompe à 48 h (`pump_health`)** : exige un débitmètre et une mesure de puissance électrique (V1.1/V2, `ml/catalog/models.yaml` l. 896-919). Le backend renvoie honnêtement `pump_failure_48h: null` sans inventer de probabilité.

---

## 5. Prochaines étapes (Sprint D4)

- Examiner les prérequis agronomiques de **`fertilization`** et **`pest_risk`**, documenter le blocage de référentiels terrain le cas échéant, et livrer la préparation technique complète (routes, services, contrats, tests unitaires et live).
