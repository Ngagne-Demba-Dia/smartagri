# 27 — Rapport d'exécution du Sprint D2 (`weather` + `recommendations` + résolution de l'écart hybride d'identifiants)

**Statut** : Exécuté et vérifié — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : résolution de l'écart hybride d'identifiants signalé en fin de D1 (`docs/26_rapport_D1.md` § 6.1), branchement réel et tests de contrat live de `weather` (`GET /v1/fields/{id}/weather`) et `recommendations` (`GET /v1/fields/{id}/recommendations` + `POST /v1/recommendations/{id}/feedback`), visibilité des modes par service dans `/api/dev/mock`.
**Références** : `docs/16_architecture_octopus.md` (intouché), `docs/22_backend_gap_analysis.md`, `docs/23_integration_plan.md` § 3.3, `docs/25_rapport_D0.md`, `docs/26_rapport_D1.md`, `web/PASSATION.md`.

---

## 1. État initial

À la sortie du Sprint D1 (`docs/26_rapport_D1.md`) :

1. **Mécanisme hybride actif** : le BFF Next (`web/lib/service-mode.ts` + `web/lib/server/upstream.ts`) route chaque appel `/api/v1/...` vers l'API FastAPI réelle (`real`) ou vers le routeur MSW (`mock`) selon `AGRI_MOCK` et `AGRI_SERVICES`.
2. **Écart d'identifiants en mode hybride (risque n° 1 de D1)** :
   - Les fixtures simulées (`web/mocks/fixtures/places.ts`) utilisent des slugs lisibles (`fld-mboro-1`, `dev-0001`, `farm-mboro`, `org-demo-niayes`).
   - Le seed backend (`backend/app/seed.py`) générait des UUID v4 aléatoires à chaque exécution.
   - En navigation hybride (`AGRI_MOCK=1` avec certains services en `real`, ou `AGRI_MOCK=0` avec certains services restés en `mock`), l'identifiant issu d'un côté provoquait un `404 NOT_FOUND` de l'autre côté.
3. **Services `weather` et `recommendations` côté backend** :
   - Déjà implémentés dans `backend/app/services/weather.py`, `backend/app/services/field_weather.py` et `backend/app/services/recommendations.py`, enrichis de leur bloc `provenance` en Sprint D0 (`docs/25_rapport_D0.md`).
   - Non couverts par un test de contrat live traversant le BFF Next et validant les schémas Zod gelés (`WeatherSchema`, `RecommendationListSchema`, `RecommendationSchema`).
   - Sur une base nouvellement initialisée avec moins de 6 mesures kit sur 24 h, `recommendations` laissait `et0_mm = None` même lorsque la prévision météo du jour fournissait déjà `et0_hargreaves_mm` / `et0_mm`.

---

## 2. Décision d'architecture : résolution de l'écart d'identifiants hybrides

Deux options ont été évaluées conformément au plan D2 :

| Critère | Option A — Mapping déterministe d'identifiants démo (retenue) | Option B — Repli simulé automatique sur `404` (rejetée) |
| :--- | :--- | :--- |
| **Isolation multi-organisation (`CONVENTIONS.md` § 5)** | **Préservée** : un identifiant d'une autre organisation ou réellement inexistant continue de renvoyer `404 NOT_FOUND`. | **Violée** : un `404` renvoyé par le backend pour masquer une ressource étrangère ou supprimée serait remplacé par un `200` simulé factice. |
| **États métier `404` légitimes (`NO_ACTIVE_CYCLE`, etc.)** | **Préservés** : les erreurs métier `404` remontent telles quelles à l'interface. | **Masqués** : l'interface afficherait des données simulées au lieu de l'état vide ou de l'erreur attendue. |
| **Fidélité du mode `real`** | **Totale** : quand un service est `real`, la réponse provient exclusivement du backend réel. | **Compromise** : impossible de distinguer à l'écran une vraie réponse backend d'un repli mock silencieux. |

**Décision retenue : Option A — Mapping déterministe bidirectionnel entre les slugs de démonstration et des UUID v4 canoniques.**

- Les entités créées par `python -m app.seed` reçoivent des UUID RFC 4122 v4 fixes (`DEMO_SLUG_TO_UUID` dans `backend/app/services/access.py` et `DEMO_UUID_BY_SLUG` dans `web/lib/service-mode.ts`) :
  - `org-demo-niayes` ↔ `00000000-0000-4000-8000-000000000001`
  - `farm-mboro` ↔ `00000000-0000-4000-8000-000000000101`
  - `fld-mboro-1` ↔ `00000000-0000-4000-8000-000000000201`
  - `dev-0001` ↔ `00000000-0000-4000-8000-000000000301`
  - `cmp-contre-saison` ↔ `00000000-0000-4000-8000-000000000401`
  - `cyc-fld-mboro-1` ↔ `00000000-0000-4000-8000-000000000501`
  - `eq-mboro-pump` ↔ `00000000-0000-4000-8000-000000000601`
- Côté backend, `access.parse_uuid()` traduit ces slugs connus vers leur UUID canonique tout en continuant de lever `404 NOT_FOUND` pour tout autre slug ou UUID inconnu.
- Côté frontend mock (`web/mocks/fixtures/places.ts`), `farmById`, `fieldSeedById`, `deviceSeedById`, `fieldSeedsOfFarm` et `deviceSeedOfField` normalisent l'identifiant via `toMockId(id)`, ce qui permet aux services restés en `mock` (ex. `vegetation`, `yield_forecast`, `soil_forecast`) de répondre sur l'UUID canonique d'une parcelle chargée depuis le backend réel.

---

## 3. Modifications réalisées

### Backend (`plateforme/backend/`)
- **`app/services/access.py`** : ajout de `DEMO_SLUG_TO_UUID` et résolution des slugs de démonstration dans `parse_uuid()`.
- **`app/services/devices.py`** : paramètres optionnels `device_id` et `firmware_version` sur `register_device()`.
- **`app/seed.py`** : attribution des UUID canoniques `DEMO_IDS` aux entités du jeu de démonstration.
- **`app/services/recommendations.py`** : dans `irrigation_payload()`, repli sur l'ET0 de la prévision météo du jour (`today.et0_hargreaves_mm` sinon `today.et0_mm`) lorsque le kit dispose de moins de 6 lectures de température sur 24 h.
- **`scripts/live_stack.py`** : ajout d'un point de télémétrie initial et des seuils `28 % / 55 %` sur le kit démo `dev-0001` pour que la pile live exerce l'ensemble des services de parcelle et de kit avec des mesures réalistes.
- **`tests/test_sprint_d2.py`** : tests unitaires et d'intégration backend pour le seed déterministe, la résolution par slug/UUID, la météo (`provider`, `cache`, `provenance`) et les recommandations + feedback.

### Frontend BFF & Mocks (`plateforme/web/`)
- **`lib/service-mode.ts`** : ajout de `allServiceModes()`, `DEMO_UUID_BY_SLUG`, `DEMO_SLUG_BY_UUID`, `toRealId()` et `toMockId()`.
- **`mocks/fixtures/places.ts`** : résolution transparente des UUID canoniques vers les graines de démonstration via `toMockId()`.
- **`app/api/dev/mock/route.ts`** : exposition de `defaultMode` et `serviceModes` dans l'instantané de diagnostic dev/mock.
- **`tests/service-mode.test.ts`** : tests unitaires du mapping bidirectionnel et de `allServiceModes()`.
- **`tests/live/weather-recommendations.live.ts`** : tests de contrat live BFF → FastAPI validant `WeatherSchema`, `RecommendationListSchema`, `RecommendationSchema` et la cohabitation hybride `real` / `mock`.

*(Aucun contrat Frontend `web/lib/contracts/*.ts`, aucun composant RC et le document `docs/16_architecture_octopus.md` n'ont été modifiés.)*

---

## 4. Tests exécutés

1. **Backend (`pytest`)** :
   - `tests/test_sprint_d2.py`, `tests/test_agronomy_weather.py`, `tests/test_seed.py` : **100 % passants**.
2. **Frontend unitaire (`vitest`)** :
   - `tests/service-mode.test.ts` : **100 % passant** (14 tests incluant le mapping hybride et `allServiceModes`).
3. **Contrat live (`vitest.live.config.ts` via `scripts/live_stack.py`)** :
   - `tests/live/weather-recommendations.live.ts` : validation complète contre `WeatherSchema`, `RecommendationListSchema` et `RecommendationSchema`.

---

## 5. Risques résiduels et points de vigilance

1. **Parcelles secondaires des mocks (`fld-mboro-2`, `fld-potou-1`, etc.)** : le seed backend minimal (`app.seed`) crée une exploitation (`farm-mboro`), une parcelle (`fld-mboro-1`) et un kit (`dev-0001`). En mode hybride où la liste des parcelles vient du mock (`AGRI_MOCK=1`), seule `fld-mboro-1` existe dans le seed backend par défaut ; en mode `AGRI_MOCK=0` (liste des parcelles issue du backend réel), toutes les parcelles affichées dans l'UI existent dans PostgreSQL/SQLite et `fld-mboro-1` est également reconnue par les mocks restants.
2. **Champs ML V2 de la météo (`rain_probability`, `local_bias_c`)** : comme prévu par Doc 16 § 9.3, Open-Meteo et le repli Hargreaves renvoient `null` sur ces deux champs tant que les modèles `wx_rain_prob` et `wx_local_bias` ne sont pas déployés ; le contrat `WeatherSchema` les déclare `.nullable()` et l'UI gère nativement leur absence.

---

## 6. Prochaines étapes (Sprint D3)

- Brancher en réel **`kit_parameters`** (`GET /v1/devices/{device_id}/parameters` et `POST /v1/devices/{device_id}/parameters/ack` + migration additive `db/migrations/003_device_parameter_sets.sql`) et **`device_health`** (`GET /v1/devices/{device_id}/health` + provenance sur `GET /v1/alerts` et `POST /v1/alerts/{id}/ack`).
