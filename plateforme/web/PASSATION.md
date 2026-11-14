# PASSATION — SmartAgri92 (Produit Web « Product Ready » + Backend Sprint D Intégré)

_Dernière mise à jour : 2026-11-14, à la clôture de la **Phase E (E1 → E6)**. Le produit Web (`plateforme/web`) est officiellement déclaré **« Product Ready »** après revue humaine intégrale des 24 écrans, validation multi-navigateurs (Chromium, Firefox, WebKit/Safari), audit d'accessibilité WCAG 2.1 AA, durcissement UX et validation complète sans régression._

---

## 1. État réel du projet

### 1.1 Produit Web (`plateforme/web`) — Déclaré « Product Ready » (Phases E1 → E6 achevées)
- **Couverture fonctionnelle** : 24 écrans complets couvrant 18/18 services de Doc 16 § 9.3 et 13/13 modules de Doc 10 § 3.2.
- **Livrables Phase E** :
  - **E1 — Revue humaine complète** : [`docs/34_revue_humaine.md`](../docs/34_revue_humaine.md) (contrôle visuel, responsive, orthographe, unités, alignements, boutons, icônes, états vides/chargements/erreurs sur les 24 écrans).
  - **E2 — Validation multi-navigateur** : [`docs/35_validation_navigateurs.md`](../docs/35_validation_navigateurs.md) (Chromium, Firefox 157, WebKit/Safari 27.2 testés via [`e2e/navigateurs.spec.ts`](./e2e/navigateurs.spec.ts) : Leaflet, upload image + Canvas, microphone, `localStorage`, cookies `httpOnly`, thème sombre, responsive `375 px`, animations `prefers-reduced-motion`).
  - **E3 — Accessibilité finale** : [`docs/36_accessibilite_finale.md`](../docs/36_accessibilite_finale.md) (WCAG 2.1 AA, 14/14 paires de contraste conformes en clair et en sombre via `npm run contrast`, navigation clavier, focus visibles, ARIA, formulaires, téléversement, `<dialog>` mobile, assistant IA via [`e2e/accessibilite.spec.ts`](./e2e/accessibilite.spec.ts)).
  - **E4 — Durcissement UX** : [`docs/37_ux_hardening.md`](../docs/37_ux_hardening.md) (suppression de `-0 %` sur les prix, traduction des saisons et des codes de règles d'alertes, noms de pompes lisibles et débits réalistes sur le planning d'arrosage, repère terrain `1 mm = 1 L/m² = 10 m³/ha` sur Irrigation, conseil prise de vue sur Maladies, 3 suggestions rapides cliquables sur Assistant IA).
  - **E5 — Validation complète** : [`docs/38_web_product_ready.md`](../docs/38_web_product_ready.md).
  - **E6 — Clôture Web complète** : [`docs/39_cloture_web_complete.md`](../docs/39_cloture_web_complete.md).
- **Qualité Frontend** :
  - `npm run lint` : **0 erreur, 0 avertissement**.
  - `npm run typecheck` : **0 erreur**.
  - `npm run i18n:check` : **100 % des clés synchronisées (`fr`, `wo`, `ff`)**.
  - `npm run contrast` : **14/14 couples conformes en thème clair et sombre**.
  - `npm test` (`vitest run`) : **31 fichiers / 630 tests unitaires passants**.
  - `npm run build` (`next build`) : **build de production compilé sans erreur**.
  - Contrats Zod (`lib/contracts/*.ts`) et Doc 16 (`docs/16_architecture_octopus.md`) **strictement intacts**.

### 1.2 Backend FastAPI & Base de données (`plateforme/backend`, `plateforme/db`) — Sprint D0 → D8 achevé
- **Migrations SQL** (`plateforme/db/migrations/`) :
  - `001_initial_schema.sql` (22 tables métier + TimescaleDB conditionnel),
  - `002_row_level_security.sql` (isolation multi-organisation PostgreSQL RLS),
  - `003_device_parameter_sets.sql` (jeux de paramètres conseillés aux kits et leur acquittement, avec RLS).
- **Socle transversal Sprint D0–D2** :
  - Constructeur unique de provenance `app/services/provenance.py` conforme à Doc 16 § 9.2 (`model_name`, `model_version`, `source`, `confidence`, `fallback_step`, `computed_at`, `stale`).
  - Exécuteur de chaîne de repli à 3 paliers `app/services/inference/fallback.py` (`ml` → `rules` → `last`).
  - Grammaire hybride identique Backend / Frontend (`AGRI_MOCK=1|0` + `AGRI_SERVICES=service=real|mock`) et inspection dans `/api/dev/mock`.
  - Mapping déterministe entre les slugs de démonstration (`fld-mboro-1`, `dev-0001`, `farm-mboro`, etc.) et les UUID v4 canoniques créés par `python -m app.seed`.
- **Qualité Backend & Intégration Live** :
  - `pytest` (`plateforme/backend`) : **218 tests passants, 0 échec**.
  - `npm run test:live` (`plateforme/web` contre `scripts/live_stack.py`) : **4 fichiers / 16 tests de contrat live passants (16/16)**.

---

## 2. Matrice des 18 services de Doc 16 § 9.3 (Réel vs Préparé vs Simulé)

### A. Services branchés et vérifiés en mode `real` (prêts pour l'exploitation hybride)
Configuration recommandée :
```env
AGRI_MOCK=1
AGRI_SERVICES=irrigation_need=real,weather=real,recommendations=real,kit_parameters=real,device_health=real
```

| # | Service | Route(s) | État Backend | Rapport |
|---|---|---|---|---|
| 1 | `weather` | `GET /v1/fields/{id}/weather` | **Réel (`rules`)** — Open-Meteo + cache SQL par parcelle/jour (savepoint anti-course) + Hargreaves + repli `stale=true` | `docs/27_rapport_D2.md` |
| 3 | `irrigation_need` | `GET /v1/fields/{id}/irrigation-need` | **Réel (`rules`)** — Bilan hydrique FAO-56 (`irr_water_balance`) + télémétrie kit + pluie prévue | `docs/26_rapport_D1.md` |
| 5 | `recommendations` | `GET /v1/fields/{id}/recommendations`, `POST /v1/recommendations/{id}/feedback` | **Réel (`rules`)** — Recommandations irrigation (avec repli ET0 météo si < 6 points kit) et NPK + feedback audité | `docs/27_rapport_D2.md` |
| 7 | `kit_parameters` | `GET /v1/devices/{id}/parameters`, `POST /v1/devices/{id}/parameters/ack`, `GET/PUT /v1/devices/{id}/thresholds` | **Réel (`rules`)** — Table `device_parameter_sets`, seuils conseillés sans écraser les seuils agriculteur (Doc 16 § 6.1), acquittement audité | `docs/28_rapport_D3.md` |
| 13 | `device_health` | `GET /v1/devices/{id}/health`, `GET /v1/alerts`, `POST /v1/alerts/{id}/ack` | **Réel (`rules`)** — Santé des 6 capteurs (`soil`, `bme`, `npk`, `flow`, `pump`, `battery`) + provenance `anomaly_rules` | `docs/28_rapport_D3.md` |

*(Les routes v1 existantes `yield_forecast`, `water_savings`, `assistant_chat` et `map_layers` (GeoJSON) fonctionnent également sur l'API réelle.)*

### B. Services techniquement préparés côté Backend (maintenus en `mock` par défaut jusqu'à levée d'un prérequis externe)

| # | Service | Route(s) | État technique Backend | Prérequis externe bloquant l'activation métier | Rapport |
|---|---|---|---|---|---|
| 6 | `fertilization` | `GET /v1/fields/{id}/fertilization` | **Implémenté & testé** (`FertilizationSchema` validé en live) | Tables d'exportation N-P-K (ISRA / CDH) et seuils d'interprétation par sol (aucune dose chiffrée inventée : `dose_kg_ha=0`) | `docs/29_rapport_D4.md` |
| 8 | `disease_diagnosis` (`diagnosis_analyze`) | `POST /v1/diagnoses/analyze` | **Implémenté & testé** (256 Kio → 413, scope → 404, abstention `< 0.7`, protocole `VisionAnalyzer`) | Poids ONNX `vis_disease` entraînés (`agriml`). Sans bundle, renvoie honnêtement `503 MODEL_UNAVAILABLE` | `docs/30_rapport_D5.md` |
| 9 | `pest_risk` | `GET /v1/fields/{id}/pest-risk` | **Implémenté & testé** (`PestRiskSchema` validé en live) | Grilles degrés-jours et seuils hygrométriques validés (ISRA / DPV) | `docs/29_rapport_D4.md` |
| 17 | `assistant_transcribe` | `POST /v1/assistant/transcribe` | **Implémenté & testé** (256 Kio → 413, `<= 60 s` → 422, `wo\|ff\|fr`, protocole `Transcriber`) | Clé API et adaptateur fournisseur ASR (comparatif Whisper / Azure / Google Cloud STT v2 établi). Sans clé, renvoie `503 MODEL_UNAVAILABLE` | `docs/31_rapport_D6.md` |

### C. Services V2/V3 maintenus en simulation (`mock`)
- `soil_forecast` (#2), `irrigation_plan` (#4), `trap_counts` (#10), `vegetation` (#11), `price_forecast` (#15) et calques raster V3 de `map_layers` (#18).

---

## 3. Commandes de vérification rapide

1. **Qualité statique, contrastes, i18n, tests unitaires et build Frontend (`plateforme/web`)** :
   ```powershell
   cd plateforme/web
   npm run lint
   npm run typecheck
   npm run i18n:check
   npm run contrast
   npm test
   npm run build
   ```
2. **Tests E2E Playwright et multi-navigateurs (`plateforme/web`)** :
   ```powershell
   cd plateforme/web
   npm run test:e2e
   # Validation multi-navigateur (Chromium + Firefox + WebKit) :
   $env:PLAYWRIGHT_MULTI="1"; npx playwright test e2e/navigateurs.spec.ts
   ```
3. **Tests Backend (`plateforme/backend`)** :
   ```powershell
   cd plateforme/backend
   python -m pytest -q
   ```
4. **Tests de contrat live BFF → FastAPI (`plateforme/backend` + `plateforme/web`)** :
   ```powershell
   # Terminal 1
   cd plateforme/backend
   python -m scripts.live_stack --stack-file ../web/.live-stack.json

   # Terminal 2
   cd plateforme/web
   npm run test:live
   ```

---

## 4. Frontières avec les phases ultérieures (IA, Données, Mobile, Langues)

Voir le rapport détaillé [`docs/39_cloture_web_complete.md`](../docs/39_cloture_web_complete.md) pour la répartition complète :
- **Ce qui dépend de l'IA (`agriml` / OctOpus)** : entraînement et export des bundles ONNX/LightGBM dans `ml/artifacts/` (`soil_nowcast`, `irr_need_24h`, `vis_disease`, `anomaly_ml`, etc.).
- **Ce qui dépend des données** : accumulation des relevés horaires des kits ESP32-S3, tables ISRA/CDH/DPV, séries de prix SIM/CSA, corpus photo terrain annoté, flux Sentinel-2.
- **Ce qui dépend du mobile** : le Web mobile est 100 % prêt dès `375 px` ; seule une future application native hors-ligne prolongé (file de synchronisation différée en écriture, notifications push OS, appairage BLE boîtier) relève d'un chantier mobile dédié.
- **Ce qui dépend des traductions** : validation humaine des fichiers `messages/traduction/{wo,ff}.csv`.
