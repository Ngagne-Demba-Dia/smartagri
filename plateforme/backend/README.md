# Backend SmartAgri92

> Confidentiel — réservé aux partenaires de travail.

API FastAPI (`/v1`) de la plateforme SmartAgri92 : comptes et organisations, exploitations et parcelles,
kits ESP32 et seuils d'irrigation, télémétrie, alertes, recommandations (FAO-56), météo, diagnostics,
campagnes, équipements, indicateurs, prévisions de rendement et assistant agronomique (Claude).
Le même paquet fournit le pont MQTT, la tâche de balayage des alertes, le jeu de démonstration et
l'exécuteur de migrations SQL.

## Contenu

| Chemin | Rôle |
|---|---|
| `app/main.py` | fabrique `create_app()` ; `uvicorn app.main:app` |
| `app/api/v1/` | routes `/v1/...` (enveloppe `{success, data, error, meta}`) |
| `app/api/health.py` | `/healthz`, `/readyz`, `/metrics` |
| `app/services/` | logique métier (agronomie, alertes, météo, rapports, assistant, inférence…) |
| `app/db/models/` | modèles SQLAlchemy 2.0, miroir de `../db/migrations` |
| `app/db/migrate.py` | exécuteur de migrations : `python -m app.db.migrate` |
| `app/ingestion/mqtt_bridge.py` | pont MQTT → base : `python -m app.ingestion.mqtt_bridge` |
| `app/jobs/alert_sweep.py` | balayage des kits muets : `python -m app.jobs.alert_sweep` |
| `app/seed.py` | données de démonstration : `python -m app.seed` (`scripts/seed.py` : ancien alias) |
| `tests/` | suite pytest (SQLite en mémoire, aucun service externe) |

## Démarrage local

Python 3.12 (image Docker) ; la suite locale a été exécutée avec Python 3.13.

```bash
cd plateforme/backend
python -m venv .venv && . .venv/bin/activate     # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                             # puis renseigner les secrets
```

Sans `DATABASE_URL`, l'API utilise SQLite (`./agri_dev.db`) et crée le schéma via l'ORM
(`AUTO_CREATE_SCHEMA` vrai par défaut sur SQLite). PostgreSQL + TimescaleDB + PostGIS sont requis
dès qu'on veut la RLS, les agrégats continus et la géométrie (voir `../db/README.md`).

```bash
python -m app.seed --create-schema               # organisation de démonstration (refusé si APP_ENV=prod)
uvicorn app.main:app --reload --port 8000        # documentation : http://localhost:8000/docs (hors prod)
python -m app.ingestion.mqtt_bridge              # pont MQTT (paho-mqtt requis)
python -m app.jobs.alert_sweep --once            # un passage ; sans --once : boucle (--interval secondes)
```

Le script de démonstration affiche une seule fois les mots de passe et la clé du kit générés.

## Migrations de la base

Les scripts SQL vivent dans `../db/migrations` (`001_init.sql`, `002_extensions.sql`, …).
Ils sont appliqués par :

```bash
python -m app.db.migrate --dry-run               # liste les fichiers en attente, n'applique rien
python -m app.db.migrate                         # applique
python -m app.db.migrate --dir ../db/migrations  # dossier explicite (sinon $MIGRATIONS_DIR, défaut /app/migrations)
```

- Connexion : `MIGRATION_DATABASE_URL` (rôle propriétaire du schéma) sinon `DATABASE_URL`.
  L'API, elle, ne doit jamais utiliser le rôle propriétaire (la RLS ne s'appliquerait pas).
- Fichiers appliqués dans l'ordre lexical et inscrits dans `schema_migrations(version, sha256, applied_at)`.
- `pg_advisory_lock` tenu pendant tout le passage : deux exécutions simultanées se sérialisent.
- Autocommit, une instruction à la fois : TimescaleDB refuse de créer un agrégat continu dans une transaction.
  Une migration interrompue n'est pas inscrite et sera rejouée : les scripts doivent rester rejouables
  (`IF NOT EXISTS`, `CREATE OR REPLACE`).
- Un fichier déjà appliqué dont l'empreinte SHA-256 a changé arrête tout. On ne modifie jamais un script
  appliqué : on ajoute `003_*.sql`.
- Codes de sortie : `0` succès (ou rien à faire), `1` échec (SQL, empreinte modifiée, connexion,
  psycopg absent), `2` configuration (dossier introuvable ou vide, URL absente).

### Image Docker et Kubernetes

Le `Dockerfile` copie les migrations depuis un **contexte de build nommé** `migrations`
(`COPY --from=migrations … ./migrations`), qui doit pointer vers `plateforme/db/migrations` :

```bash
docker build --build-context migrations=../db/migrations -t smartagri92-backend .
```

En CI c'est `build-contexts`, en compose `additional_contexts`. Le Job Kubernetes `migrate`
(hook ArgoCD `Sync`, vague `-1`, donc avant l'API) exécute, dans l'image du backend :

```bash
python -m app.db.migrate
```

avec `MIGRATION_DATABASE_URL` pointant vers le rôle propriétaire (`MIGRATIONS_DIR` vaut `/app/migrations`
par défaut).

## Variables d'environnement

Lues par `app/core/config.py` (sauf mention). Liste commentée et valeurs par défaut : `.env.example`.
En `staging`/`prod`, la configuration est stricte : l'application refuse de démarrer si une valeur est
dangereuse ou absente.

| Variable | Défaut | Remarque |
|---|---|---|
| `APP_ENV` | `local` | `local`, `test`, `staging`, `prod` ; `/docs` désactivé en `prod` |
| `DATABASE_URL` | SQLite local | obligatoire et PostgreSQL en staging/prod |
| `MIGRATION_DATABASE_URL` | — | lue par `app.db.migrate` seulement |
| `MIGRATIONS_DIR` | `/app/migrations` | lue par `app.db.migrate` seulement |
| `JWT_SECRET`, `DEVICE_KEY_PEPPER` | générés en local | ≥ 32 octets en staging/prod |
| `MQTT_URL`, `MQTT_USERNAME`, `MQTT_PASSWORD` | `mqtt://localhost:1883` | pont MQTT |
| `S3_ENDPOINT`, `S3_BUCKET_RAW` | —, `agri-raw` | lues mais pas encore utilisées par le code |
| `ANTHROPIC_API_KEY` | — | sans clé, l'assistant répond 503 |
| `ASSISTANT_MODEL`, `ASSISTANT_EFFORT`, `ASSISTANT_MAX_ITERATIONS`, `ASSISTANT_SERVER_FALLBACK` | `claude-opus-5-5`, `medium`, `6`, `true` | effort : `low`/`medium`/`high` |
| `WEATHER_BASE_URL`, `WEATHER_CACHE_MINUTES`, `WEATHER_TIMEOUT_S` | Open-Meteo, `180`, `10` | |
| `INFERENCE_BACKEND`, `MODEL_BUNDLE_DIR` | `local`, `./models` | `none`, `local` ou `octopus` |
| `OCTOPUS_BASE_URL`, `OCTOPUS_API_KEY`, `OCTOPUS_TIMEOUT_S` | —, —, `60` | HTTPS obligatoire en staging/prod |
| `CORS_ORIGINS` | `http://localhost:3000` | liste séparée par des virgules |
| `RATE_LIMIT_DEFAULT_PER_MIN`, `RATE_LIMIT_AUTH_PER_MIN`, `RATE_LIMIT_ASSISTANT_PER_MIN` | `120`, `10`, `20` | par client et par règle |
| `METRICS_ENABLED`, `AUTO_CREATE_SCHEMA` | `true`, vrai sur SQLite | |
| `DEVICE_SILENT_HOURS`, `DRY_SOIL_HOURS` | `24`, `2` | règles d'alerte |
| `DISEASE_CONSECUTIVE`, `DISEASE_MIN_CONFIDENCE`, `DISEASE_WINDOW_HOURS` | `3`, `0.7`, `48` | règles d'alerte |

`MLFLOW_TRACKING_URI` figure dans `.env.example` mais n'est lue que par `ml/`.

## Tests

```bash
python -m pytest -q
python -m flake8 --max-line-length 120 app tests scripts
```

Les tests utilisent SQLite et des doublures : météo factice, transport HTTP simulé (`httpx.MockTransport`)
pour Open-Meteo, client Anthropic simulé, base fictive pour l'exécuteur de migrations.
`tests/test_schema_drift.py` vérifie que l'ORM et `../db/migrations` concordent.

`pytest-cov` n'est pas installé dans l'environnement de développement actuel : la couverture n'est pas mesurée.

Non couvert par la suite locale (à valider en intégration) :

- PostgreSQL réel : RLS, agrégats continus, hypertable, PostGIS, exécution réelle de `app.db.migrate` ;
- boucle réseau `paho-mqtt` et broker ;
- SDK `anthropic` réel, OctOpus et Open-Meteo réels ;
- construction de l'image Docker avec le contexte nommé.
