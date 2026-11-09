# Conventions et contrats techniques — Plateforme Smart Agri92

Document de référence partagé par toutes les équipes (backend, data/ML, IoT, mobile, web, DevOps).
Toute modification d'un contrat (API, MQTT, schéma) passe par une revue et une montée de version.
Ce document décrit **le code tel qu'il est** ; ce qui n'est pas encore codé est marqué « proposé ».

Confidentiel — réservé aux partenaires de travail.

## 1. Arborescence du monorepo

```
plateforme/
├── README.md                 Point d'entrée, démarrage rapide, état réel de chaque bloc
├── CONVENTIONS.md            Ce document
├── docs/                     Dossier d'étude : 00 à 12 (architecture, IA, OctOpus, web, déploiement, plan)
├── backend/                  API FastAPI (monolithe modulaire), worker d'ingestion MQTT, job d'alertes, migrations
├── db/migrations/            Schéma SQL de référence (PostgreSQL 16 + TimescaleDB + PostGIS)
├── ml/                       Package agriml : compétition + production (tabulaire, vision, séries), OctOpus, MLOps
├── web/                      Tableau de bord Next.js (BFF, pages des modules MVP)
├── mobile/                   Application Flutter (lecture locale du kit, relais hors ligne vers le cloud)
├── maquettes/                Maquettes HTML cliquables (locales, non publiées)
├── infra/                    Terraform (AWS), Kubernetes (kustomize), MLflow, observabilité, scripts GitOps
├── docker-compose.yml        Environnement local complet
├── Makefile                  Raccourcis (tests, lint, compose)
└── .github/workflows/        CI (ci.yml) et CD (cd.yml)
```

## 2. Langue et style

- Identifiants de code en anglais (bibliothèques, recrutement international) ; commentaires, docstrings et
  messages destinés aux utilisateurs en français.
- Python ≥ 3.11 (testé en 3.13), typage complet, `ruff` (lint + format), fonctions < 50 lignes, fichiers < 800 lignes.
- Objets immuables par défaut (`frozen=True` pour les dataclasses de configuration, pas de mutation des DataFrames
  reçus en argument : on retourne une copie).
- Aucun secret dans le code : variables d'environnement, injectées en production par External Secrets depuis
  AWS Secrets Manager.
- Les dépendances lourdes optionnelles (LightGBM, CatBoost, Optuna, MLflow, timm, ONNX, anthropic, paho-mqtt,
  psycopg) sont importées paresseusement : leur absence désactive la fonction concernée avec un message clair,
  sans casser le reste. Le client OctOpus n'utilise que `httpx`.
- **Interdit : le paquet PyPI `octopus-ml`.** Il porte le même nom que la plateforme mais n'a aucun lien avec elle
  (risque de confusion de dépendance). L'intégration passe par notre propre client
  (`ml/src/agriml/octopus/client.py`) et par l'API documentée du fournisseur.
- Interface : aucun nom de personne réelle dans les écrans, maquettes et données de démonstration (noms de rôle).

## 3. Contrat de télémétrie `telemetry.v1`

Format canonique de la plateforme. Le kit (firmware v1.1) expose ses propres clés sur `/data` ; le relais mobile
et le worker d'ingestion font la correspondance.

| Clé kit v1.1 (`/data`) | Clé plateforme      | Type            | Plage plausible |
|------------------------|---------------------|-----------------|-----------------|
| `sol`                  | `soil_moisture_pct` | float \| null   | 0 – 100         |
| `temp`                 | `air_temp_c`        | float \| null   | -10 – 60        |
| `hum`                  | `air_humidity_pct`  | float \| null   | 0 – 100         |
| `pres`                 | `pressure_hpa`      | float \| null   | 800 – 1100      |
| `n` / `p` / `k`        | `n_mgkg` / `p_mgkg` / `k_mgkg` | int \| null | 0 – 1999 |
| `pompe`                | `pump_on`           | bool            |                 |
| `defautPompe`          | `pump_fault`        | bool            |                 |
| `capteurSolOk`         | `soil_sensor_ok`    | bool            |                 |
| `bmeOk`                | `bme_ok`            | bool            |                 |
| `npkOk`                | `npk_ok`            | bool            |                 |
| `alerteEngrais`        | `alert_fertilizer`  | bool            |                 |
| `alertePlante`         | `alert_plant`       | bool            |                 |
| `seuilStart`           | `threshold_start_pct` | int           | 0 – 95          |
| `seuilStop`            | `threshold_stop_pct`  | int           | 5 – 100         |

Point de mesure :

```json
{
  "schema": "telemetry.v1",
  "device_id": "SA92-000123",
  "fw": "1.1.0",
  "seq": 1234,
  "ts": "2026-10-26T10:00:00Z",
  "source": "relay",
  "m": { "soil_moisture_pct": 42.0, "air_temp_c": 31.5, "air_humidity_pct": 55.0, "pressure_hpa": 1009.2,
         "n_mgkg": 20, "p_mgkg": 10, "k_mgkg": 80, "pump_on": false, "pump_fault": false,
         "soil_sensor_ok": true, "bme_ok": true, "npk_ok": true,
         "alert_fertilizer": false, "alert_plant": false,
         "threshold_start_pct": 30, "threshold_stop_pct": 60 }
}
```

Règles :
- `device_id` suit le motif `^SA92-\d{6}$`.
- `ts` en UTC ISO 8601. Le kit n'a pas d'horloge : le relais mobile horodate avec l'heure du téléphone
  (synchronisée réseau) ; à partir du firmware v1.2 le kit horodate lui-même (heure reçue du téléphone ou SNTP).
- `source` ∈ `mqtt` (kit connecté), `relay` (application mobile), `http` (passerelle ou import).
- Valeur hors plage plausible ⇒ stockée à `null` + compteur de rejet (jamais de valeur absurde en base).
- Idempotence : clé unique `(device_id, ts)` ; un doublon est ignoré et compté, pas une erreur.
- Synchronisation des seuils : un changement fait par `PUT /v1/devices/{id}/thresholds` passe à `applied` dès que la
  télémétrie rapporte les mêmes `threshold_start_pct` / `threshold_stop_pct` (aucun accusé de réception séparé).

## 4. MQTT

| Sujet                                       | Sens               | QoS |
|---------------------------------------------|--------------------|-----|
| `agri92/v1/devices/{device_id}/telemetry`   | kit → plateforme   | 1   |
| `agri92/v1/devices/{device_id}/events`      | kit → plateforme   | 1   |
| `agri92/v1/devices/{device_id}/commands`    | plateforme → kit   | 1   |
| `agri92/v1/devices/{device_id}/commands/ack`| kit → plateforme   | 1   |

- Production : TLS 8883 uniquement, identifiant = `device_id`, mot de passe = secret du kit (haché côté serveur),
  ACL : un kit ne publie et ne s'abonne que sous son propre `device_id`.
- Commande de seuils : `{"cmd": "set_thresholds", "id": "<uuid>", "start": 30, "stop": 60}` ; le kit répond sur
  `commands/ack` avec `{"id": "<uuid>", "ok": true}`. Le firmware v1.1 n'a pas de client MQTT : ce sujet sert à
  partir de la v1.2 ; d'ici là, les seuils passent par l'application mobile et l'API locale du kit.

## 5. API REST v1

Base : `/v1`. OpenAPI généré par FastAPI sur `/docs` (désactivé en production) et `/openapi.json`.
Le code des routes est dans `backend/app/api/v1/*.py` ; cette table est vérifiée contre les décorateurs `@router`.

Enveloppe unique pour toutes les réponses :

```json
{ "success": true, "data": { }, "error": null, "meta": { "page": 1, "limit": 50, "total": 120 } }
{ "success": false, "data": null, "error": { "code": "THRESHOLDS_INVALID", "message": "...", "details": null }, "meta": null }
```

Pagination (`backend/app/api/deps.py`) : paramètres `page` (1 à 10 000) et `limit` (1 à 200, 50 par défaut) sur
`GET /v1/farms`, `/v1/farms/{farm_id}/fields`, `/v1/devices`, `/v1/alerts`, `/v1/campaigns` et `/v1/equipment` ;
`meta` renvoie `page`, `limit` et `total`. Les autres listes sont bornées par leur propre filtre (période, parcelle).

### 5.1 Routes codées

Rôles d'écriture (constantes de `backend/app/core/constants.py`) : F = `farmer`, C = `coop_manager`,
A = `agronomist`, D = `admin`. « JWT » seul = tout membre de l'organisation propriétaire.

| Méthode | Chemin | Auth / rôles | Rôle de la route |
|---|---|---|---|
| POST | `/v1/auth/token` | aucune | Connexion (téléphone ou e-mail + mot de passe) → jeton d'accès (15 min) et de rafraîchissement (30 j) |
| POST | `/v1/auth/refresh` | jeton de rafraîchissement | Rotation ; réutilisation d'un jeton déjà tourné → `401 REFRESH_TOKEN_REUSED` |
| POST | `/v1/auth/logout` | JWT | Révoque le jeton de rafraîchissement fourni |
| GET | `/v1/me` | JWT | Profil et appartenances |
| GET · POST | `/v1/farms` | JWT · écriture F C D | Exploitations de l'organisation |
| GET · POST | `/v1/farms/{farm_id}/fields` | JWT · écriture F C D | Parcelles (contour GeoJSON) |
| GET | `/v1/farms/{farm_id}/map` | JWT | Carte : parcelles et kits de l'exploitation (GeoJSON) |
| GET | `/v1/fields/{field_id}` | JWT | Détail d'une parcelle |
| GET · POST | `/v1/fields/{field_id}/crop-cycles` | JWT · écriture F C A D | Cycles de culture |
| PATCH | `/v1/crop-cycles/{cycle_id}` | F C A D | Mise à jour d'un cycle (récolte : date obligatoire) |
| GET | `/v1/fields/{field_id}/weather?days=` | JWT | Prévisions (Open-Meteo, cache `weather_cache`) |
| GET | `/v1/fields/{field_id}/recommendations` | JWT | Recommandations irrigation / fertilisation |
| GET | `/v1/fields/{field_id}/yield-forecast?refresh=` | JWT | Prévision de rendement p10 / p50 / p90 |
| POST | `/v1/recommendations/{recommendation_id}/feedback` | F C D | Suivi d'une recommandation (`followed`, `partially_followed`, `ignored`, `not_applicable`) |
| GET · POST | `/v1/campaigns` | JWT · écriture C D | Campagnes (saison sèche / pluvieuse) |
| GET · PATCH | `/v1/campaigns/{campaign_id}` | JWT · écriture C D | Détail, mise à jour |
| GET | `/v1/campaigns/{campaign_id}/summary` | JWT | Bilan de campagne |
| POST | `/v1/devices` | C D | Enregistrer un kit ; le secret n'est renvoyé qu'une fois |
| GET | `/v1/devices` · `/v1/devices/{device_id}` | JWT | Kits accessibles, dernier état |
| GET · PUT | `/v1/devices/{device_id}/thresholds` | JWT · écriture F C D | Seuils ; règle identique au firmware |
| GET | `/v1/devices/{device_id}/measurements?from=&to=&bucket=` | JWT | Séries ; `bucket` ∈ `raw`, `1h`, `1d`, `1w`, `1mo` |
| POST | `/v1/telemetry/batch` | `X-Device-Key` ou JWT (F C D) | Lot ≤ 1000 points (relais mobile, passerelle) |
| GET | `/v1/alerts?status=&device_id=` | JWT | Alertes (`open`, `acknowledged`, `resolved`) |
| POST | `/v1/alerts/{alert_id}/ack` | tout rôle | Acquittement |
| POST | `/v1/diagnoses` | tout rôle | Verdict du modèle de vision (image, classe, confiance) |
| GET · POST | `/v1/equipment` | JWT · écriture F C D | Équipements (pompe, cuve, panneau, batterie…) |
| PATCH | `/v1/equipment/{equipment_id}` | F C D | Mise à jour |
| GET · POST | `/v1/equipment/{equipment_id}/maintenance` | JWT · écriture tout rôle | Journal de maintenance |
| GET | `/v1/reports/kpis?scope=&id=&from=&to=` | JWT | Indicateurs ; `scope` ∈ `org`, `farm`, `campaign` |
| GET | `/v1/reports/export.csv?scope=&id=&from=&to=` | JWT | Export CSV (journalisé dans `audit_log`) |
| POST | `/v1/assistant/chat` | JWT | Assistant agronomique (Claude), outils limités aux données de l'utilisateur |
| GET | `/healthz` · `/readyz` | aucune | Sondes Kubernetes (`/readyz` → `503 NOT_READY` si la base est injoignable) |
| GET | `/metrics` | aucune (réseau interne) | Prometheus ; `404` si `METRICS_ENABLED=false` |

Règle des seuils (identique au firmware v1.1) : entiers, `0 ≤ start`, `start + 5 ≤ stop ≤ 100`,
sinon `400 THRESHOLDS_INVALID`.

Rôles (`memberships.role`) : `farmer`, `coop_manager`, `agronomist`, `admin` (`partner_viewer` proposé en V2).
Toute ressource est filtrée par l'organisation de l'utilisateur ; une ressource d'une autre organisation répond
**404** (pas 403, pour ne pas révéler son existence). Un identifiant fourni par le client (ou par le modèle de
langage) n'est jamais utilisé sans contrôle d'appartenance.

### 5.2 Routes proposées (pas encore codées)

| Méthode | Chemin | Version | Rôle |
|---|---|---|---|
| POST | `/v1/auth/otp/request` · `/v1/auth/otp/verify` | V1.1 | Connexion par code SMS (remplace le mot de passe pour les agriculteurs) |
| GET | `/v1/firmware/latest?hw=` | firmware v1.2 | Dernière version signée du firmware, pour la mise à jour via le téléphone |
| GET | `/v1/app/min-version` | V1.1 | Version minimale de l'application mobile (forcer la mise à jour après un changement de contrat) |
| GET | `/v1/partners/...` | V2 | Accès en lecture agrégée pour `partner_viewer` |

### 5.3 Catalogue des codes d'erreur

Le `code` est stable (les clients s'en servent) ; le `message` est en français et peut changer.

| Famille | Codes (statut HTTP) |
|---|---|
| Génériques | `BAD_REQUEST` 400, `UNAUTHENTICATED` 401, `FORBIDDEN` 403, `NOT_FOUND` 404, `METHOD_NOT_ALLOWED` 405, `CONFLICT` 409, `PAYLOAD_TOO_LARGE` 413, `VALIDATION_ERROR` 422, `RATE_LIMITED` 429 (+ `Retry-After`), `INTERNAL_ERROR` 500 (+ `request_id`), `HTTP_ERROR` (autre statut), `NOT_READY` 503 |
| Authentification | `INVALID_CREDENTIALS` 401, `TOKEN_EXPIRED` 401, `TOKEN_INVALID` 401, `REFRESH_TOKEN_REUSED` 401, `ORGANIZATION_REQUIRED` 400 |
| Kits et télémétrie | `DEVICE_EXISTS` 409, `DEVICE_KEY_INVALID` 401, `DEVICE_MISMATCH` 403, `DEVICE_INACTIVE` 409, `BATCH_TOO_LARGE` 413, `DEVICE_NOT_ON_FARM` 400, `THRESHOLDS_INVALID` 400 |
| Paramètres | `INVALID_DATES` 400, `HARVEST_DATE_REQUIRED` 400, `INVALID_BUCKET` 400, `INVALID_RANGE` 400, `RANGE_TOO_LARGE` 400, `INVALID_SCOPE` 400, `SCOPE_ID_REQUIRED` 400, `LOCATION_REQUIRED` 400, `INVALID_DAYS` 400 |
| Météo et modèles | `WEATHER_UNAVAILABLE` 503, `MODEL_UNAVAILABLE` 503, `NO_ACTIVE_CYCLE` 404 |
| Assistant | `MESSAGE_INVALID` 400, `TOOL_INPUT_INVALID` 400 (renvoyé au modèle, pas au client), `ASSISTANT_RATE_LIMITED` 503, `ASSISTANT_OVERLOADED` 503, `ASSISTANT_UNAVAILABLE` 503, `ASSISTANT_UNREACHABLE` 503, `ASSISTANT_MODEL_NOT_FOUND` 502, `ASSISTANT_BAD_REQUEST` 502, `ASSISTANT_UPSTREAM_ERROR` 502 |

`MODEL_UNAVAILABLE` n'est renvoyé que lorsque toute la chaîne de repli a échoué : bundle local → lot OctOpus →
règles FAO-56 (voir `docs/09_octopus_ml.md`). Les erreurs 503 de l'assistant signifient « réessayer plus tard » ;
les 502 signalent une erreur de configuration ou du fournisseur, à corriger côté exploitation.

## 6. Base de données

PostgreSQL 16 + TimescaleDB + PostGIS. Schéma de référence : `db/migrations/*.sql`, appliqués dans l'ordre
lexical par `python -m app.db.migrate` (service compose `migrate` en local, Job Kubernetes `migrate` en
hook ArgoCD `Sync` sur les clusters, voir `docs/11_deploiement.md` §5).

| Migration | Tables |
|---|---|
| `001_init.sql` | `organizations`, `users`, `memberships`, `refresh_tokens`, `audit_log`, `farms`, `fields`, `crop_cycles`, `devices`, `device_thresholds`, `measurements` (hypertable), `alerts`, `images`, `diagnoses`, `recommendations`, `conversations`, `messages` ; agrégats continus `measurements_1h` et `measurements_1d` |
| `002_extensions.sql` | `campaigns`, `equipment`, `maintenance_events`, `weather_cache`, `yield_forecasts`, `model_registry` ; colonne `crop_cycles.campaign_id` |
| (lanceur) | `schema_migrations(version, sha256, applied_at)` : une ligne par fichier appliqué ; un fichier déjà appliqué dont l'empreinte change bloque le déploiement |

Règles :
- Une migration appliquée n'est jamais modifiée : on en ajoute une nouvelle (`003_...sql`).
- Chaque fichier s'exécute hors transaction globale (les agrégats continus TimescaleDB l'exigent) ; il doit donc
  être idempotent (`IF NOT EXISTS`) ou réversible à la main.
- Le lanceur prend un verrou `pg_advisory_lock` : deux déploiements simultanés ne migrent pas en même temps.
- Les tests backend utilisent SQLite via l'ORM (colonnes géographiques stockées en GeoJSON texte dans ce cas).

## 7. Variables d'environnement

Backend (lues par `backend/app/core/config.py` ; en `staging`/`prod`, l'API refuse de démarrer si un secret
obligatoire manque ou fait moins de 32 octets) :

| Variable | Défaut / exemple local | Usage |
|---|---|---|
| `APP_ENV` | `local` | `local`, `test`, `staging`, `prod` |
| `DATABASE_URL` | `postgresql+psycopg://agri:agri@db:5432/agri` (SQLite si vide hors prod) | Base, rôle de l'API (sans DDL) ; les migrations utilisent `MIGRATION_DATABASE_URL` |
| `JWT_SECRET` | (générer : `openssl rand -hex 32`) | Signature des jetons, ≥ 32 octets (obligatoire en staging/prod) |
| `DEVICE_KEY_PEPPER` | (générer) | Poivre du hachage des secrets de kit, ≥ 32 octets (obligatoire en staging/prod) |
| `MQTT_URL` · `MQTT_USERNAME` · `MQTT_PASSWORD` | `mqtt://mqtt:1883` | Broker (worker d'ingestion) |
| `S3_ENDPOINT` · `S3_BUCKET_RAW` | `http://minio:9000` · `agri-raw` | Lues mais **pas encore utilisées** (stockage des images prévu en V1.1) |
| `ANTHROPIC_API_KEY` | (secret) | Assistant |
| `ASSISTANT_MODEL` | `claude-opus-5-5` | Modèle de l'assistant |
| `ASSISTANT_EFFORT` | `medium` | `low`, `medium`, `high` |
| `ASSISTANT_MAX_ITERATIONS` | `6` | Tours d'outils maximum par question |
| `ASSISTANT_SERVER_FALLBACK` | `true` | Repli serveur sur un autre modèle en cas de surcharge (bêta) |
| `WEATHER_BASE_URL` · `WEATHER_CACHE_MINUTES` · `WEATHER_TIMEOUT_S` | Open-Meteo · `180` · `10` | Météo |
| `INFERENCE_BACKEND` | `local` | `none`, `local`, `octopus` |
| `MODEL_BUNDLE_DIR` | `./models` | Bundles de modèles exportés par `agriml` |
| `OCTOPUS_BASE_URL` · `OCTOPUS_API_KEY` · `OCTOPUS_TIMEOUT_S` | `https://octopus.ml` · (secret) · `60` | Client OctOpus (HTTPS obligatoire en staging/prod) |
| `CORS_ORIGINS` | `http://localhost:3000` | Liste séparée par des virgules |
| `RATE_LIMIT_DEFAULT_PER_MIN` · `RATE_LIMIT_AUTH_PER_MIN` · `RATE_LIMIT_ASSISTANT_PER_MIN` | `120` · `10` · `20` | Limites par client |
| `AUTO_CREATE_SCHEMA` | `true` avec SQLite, sinon `false` (forcé à `false` en staging/prod) | Création des tables par l'ORM (développement) |
| `METRICS_ENABLED` | `true` | Expose `/metrics` |
| `DEVICE_SILENT_HOURS` · `DRY_SOIL_HOURS` | `24` · `2` | Règles d'alerte (kit muet, sol sec) |
| `DISEASE_CONSECUTIVE` · `DISEASE_MIN_CONFIDENCE` · `DISEASE_WINDOW_HOURS` | `3` · `0.7` · `48` | Règle d'alerte maladie |
| `MIGRATION_DATABASE_URL` | `postgresql://agri:…@db:5432/agri` (service compose `migrate`) | Rôle propriétaire du schéma (DDL), lu par `python -m app.db.migrate` seulement ; à défaut, le lanceur prend `DATABASE_URL`. Sur les clusters : Secret `agri-database-migrate`, jamais monté dans l'API |
| `MIGRATIONS_DIR` | `/app/migrations` | Dossier lu par `python -m app.db.migrate` |

ML (`ml/`) :

| Variable | Usage |
|---|---|
| `MLFLOW_TRACKING_URI` | Serveur MLflow (lu par la bibliothèque MLflow), registre de référence des modèles |
| `OCTOPUS_BASE_URL` · `OCTOPUS_API_KEY` | Client OctOpus de `agriml.octopus` |
| `AGRIML_PSEUDO_SALT` · `AGRIML_PSEUDO_SALT_ID` | Sel de pseudonymisation des exports vers OctOpus (jamais écrit ni journalisé ; seul l'identifiant est gardé). Sur les clusters : `<prefix>/ml` → Secret `agri-ml` → CronJob `retrain` |
| `AGRIML_NOTIFY_WEBHOOK` | Webhook de notification du flux de réentraînement (vide = pas de notification) |
| `LOKY_MAX_CPU_COUNT` | Fixé à la moitié des cœurs à l'import d'`agriml` s'il est absent (évite un avertissement joblib sous Windows) |

Web et mobile :

| Variable | Usage |
|---|---|
| `API_BASE_URL` | URL de l'API, lue côté serveur par le BFF Next.js ; passée au mobile par `--dart-define=API_BASE_URL=...` |
| `NEXT_TELEMETRY_DISABLED` · `NODE_ENV` | Next.js |

Compose et infrastructure (`.env.example`) : `POSTGRES_*`, `MLFLOW_DB_PASSWORD`, `MQTT_INGESTOR_*`, `MQTT_API_*`,
`MQTT_HEALTH_PASSWORD`, `MINIO_ROOT_*`, `AWS_REGION`, `GRAFANA_ADMIN_PASSWORD`.

## 8. Ports locaux

API 8000 · Web 3000 · PostgreSQL 5432 · MQTT 1883 · MinIO 9000/9001 · MLflow 5000 · Grafana 3001 · Prometheus 9090 ·
collecteur OpenTelemetry 4317 (gRPC) / 4318 (HTTP). Tous liés à `127.0.0.1` uniquement.

## 9. Package ML `agriml`

- Emplacement : `ml/src/agriml`, CLI : `python -m agriml.train --config configs/<exp>.yaml`.
- Chaque expérience écrit dans `ml/artifacts/<exp_name>/` : `oof.parquet` (ou `.csv`), `test_pred.*`,
  `cv_scores.json`, modèles par pli, `config_resolved.yaml`.
- Toute transformation apprise (encodage cible, normalisation, imputation apprise) est ajustée **dans** le pli
  d'entraînement uniquement.
- Le même code de features sert à la compétition et à l'inférence de production (`agriml.predict`).
- Sous-paquets : `features/`, `models/`, `forecast/`, `vision/`, `monitoring/` (dérive), `octopus/` (client HTTP,
  export pseudonymisé, programmes, synchronisation du registre), `mlops/` (registre, promotion, flux de
  réentraînement).
- OctOpus est le hub d'expérimentation ; PostgreSQL + S3 restent la source de vérité des données et MLflow le
  registre de référence. Seuls des instantanés pseudonymisés partent vers OctOpus ; le jeu de test final (holdout)
  n'y est jamais envoyé. Détails : `docs/09_octopus_ml.md`.
- Les bundles exportés (`ml/bundles/`) ne sont pas versionnés dans git.

## 10. Qualité

- Tests : `pytest`, couverture visée ≥ 80 % sur `backend/app` et `ml/src/agriml`.
- Commits : Conventional Commits (`feat:`, `fix:`, `docs:` …).
- Rien n'est publié en ligne : dépôt privé, documents confidentiels.
