# Base de données SmartAgri92

> Confidentiel — réservé aux partenaires de travail.

PostgreSQL 16 avec TimescaleDB 2.x (≥ 2.11 recommandé), PostGIS 3.x, `pgcrypto` et `citext`.
Les modèles SQLAlchemy de `backend/app/db/models` sont le miroir de ces scripts. Le test
`backend/tests/test_schema_drift.py` vérifie que les tables, colonnes, nullabilités, contraintes
CHECK et index nommés de l'ORM existent tous dans les migrations.

## Migrations

| Fichier | Contenu |
|---|---|
| `migrations/001_init.sql` | extensions, rôles, identité (organisations, utilisateurs, adhésions, jetons de rafraîchissement), journal d'audit, exploitations, parcelles (SIG), cycles culturaux, kits et seuils, hypertable `measurements` et agrégats continus, alertes, images, diagnostics, recommandations, conversations, RLS |
| `migrations/002_extensions.sql` | campagnes (+ `crop_cycles.campaign_id`), équipements, journal de maintenance, cache météo, prévisions de rendement, registre des modèles |

Exécution, dans l'ordre, avec le compte propriétaire (superutilisateur pour les extensions et le rôle `BYPASSRLS`).
Ne pas envelopper les scripts dans une transaction, car TimescaleDB refuse de créer un agrégat continu dans un bloc
`BEGIN … COMMIT`.

```bash
psql "$DATABASE_URL_ADMIN" -v ON_ERROR_STOP=1 -f migrations/001_init.sql
psql "$DATABASE_URL_ADMIN" -v ON_ERROR_STOP=1 -f migrations/002_extensions.sql
```

Les scripts sont ré-exécutables (`IF NOT EXISTS`, `CREATE OR REPLACE`, `if_not_exists => TRUE`).
Un futur changement de schéma passera par un nouveau fichier `003_*.sql`. On ne modifie jamais un script déjà
appliqué en production.

## Rôles et connexions

Les deux rôles créés sont `NOLOGIN`. On crée ensuite des comptes de connexion qui en héritent :

```sql
CREATE ROLE agri_api    LOGIN PASSWORD '…' IN ROLE agri_app;     -- API FastAPI
CREATE ROLE agri_bridge LOGIN PASSWORD '…' IN ROLE agri_worker;  -- pont MQTT, tâche d'alertes
```

`BYPASSRLS` ne s'hérite pas par appartenance à un rôle. Pour le pont MQTT, on donne donc l'attribut
directement au compte de connexion : `ALTER ROLE agri_bridge BYPASSRLS;`.

| Rôle | Usage | RLS |
|---|---|---|
| propriétaire (migration) | migrations, alimentation de `model_registry` | non soumis (RLS `ENABLE`, pas `FORCE`) |
| `agri_app` | API | soumis |
| `agri_worker` | pont MQTT, `app.jobs.alert_sweep` | contourne (`BYPASSRLS`) |

L'API ne doit **jamais** se connecter avec le compte propriétaire, sinon la RLS ne s'applique pas.

## Cloisonnement par organisation (RLS)

À chaque transaction, l'API exécute `set_config('app.org_id', '<uuid>[,<uuid>…]', true)`
(voir `backend/app/db/session.py`). La politique `tenant_isolation` laisse passer une ligne dans les deux cas
suivants :

```sql
organization_id = ANY (app_current_org_ids())   -- USING et WITH CHECK
```

Sans réglage, aucune ligne n'est visible. C'est une seconde barrière : l'API filtre déjà chaque requête par
organisation et renvoie 404 sur une ressource d'une autre organisation.

- **Tables protégées :** `farms`, `fields`, `crop_cycles`, `devices`, `device_thresholds`, `alerts`, `images`,
  `diagnoses`, `recommendations`, `conversations`, `campaigns`, `equipment`, `maintenance_events` et
  `yield_forecasts`.
- **Tables sans RLS :**
  - Tables d'identité : `organizations`, `users`, `memberships`, `refresh_tokens`. Elles sont filtrées par le code.
  - Données publiques : `weather_cache`.
  - Registre global : `model_registry`.
  - `audit_log`, en ajout seul.
  - `messages`, jointe à `conversations`.
  - L'hypertable `measurements` : la RLS y est incompatible avec la compression et les agrégats continus. L'API
    ne lit les mesures que pour un kit dont l'organisation a été vérifiée.

L'authentification d'un kit par `X-Device-Key` passe par `app_device_org_by_key(key_hash)`. Cette fonction est en
`SECURITY DEFINER`, avec un `search_path` fixé. Elle renvoie seulement l'organisation d'un kit actif, ce qui permet
ensuite de positionner `app.org_id`.

## Séries temporelles

- `measurements` est une hypertable découpée en tronçons de 7 jours. Sa clé primaire `(device_id, ts)` rend
  l'ingestion idempotente : un doublon est ignoré et compté.
- **Compression :** elle s'applique après 7 jours, avec `segmentby = device_id` et `orderby = ts DESC`.
  L'insertion tardive par le relais mobile dans un tronçon compressé suppose TimescaleDB ≥ 2.11 (à vérifier sur
  l'instance cible).
- **Rétention :** elle est commentée. La durée de conservation reste à décider avec les partenaires.
- **Agrégats continus :** `measurements_1h` et `measurements_1d` contiennent :
  - `n_points` et `pump_on_ratio` ;
  - pour l'humidité du sol et la température de l'air, la moyenne, le minimum et le maximum ;
  - pour l'humidité de l'air, la pression et N/P/K, la moyenne seulement.

  Les fenêtres de rafraîchissement sont de 10 et 40 jours, pour absorber la synchronisation différée du relais.
- Les vues hebdomadaires et mensuelles sont calculées à la volée à partir de `measurements_1d`, en pondérant par
  `n_points` (`backend/app/services/measurements.py`).

## SIG

- `fields.geometry` (jsonb) stocke le polygone GeoJSON validé par l'API : anneau fermé, coordonnées lon/lat dans
  leurs bornes, au plus 1000 sommets.
- `fields.geom` est une colonne générée en `geometry(Polygon, 4326)`, indexée en GiST.
- `farms.location` est le point généré à partir de `latitude` et `longitude`.
- Ces deux colonnes n'existent qu'en SQL. Elles sont absentes de l'ORM et des tests SQLite.

## Journal d'audit

`audit_log` fonctionne en ajout seul. Un déclencheur refuse `UPDATE` et `DELETE`, et les droits correspondants sont
retirés à `agri_app` et `agri_worker`. Une seule modification est tolérée : la mise à NULL de `actor_user_id` ou
`organization_id` quand un compte ou une organisation est supprimé (`ON DELETE SET NULL`). Le journal ne contient
jamais le contenu des messages de l'assistant ni de secrets.

## Non vérifié

Ces scripts n'ont **pas** été exécutés contre un PostgreSQL/TimescaleDB réel dans cet environnement : aucune
instance n'est disponible et rien ne doit être installé. La suite de tests tourne sur SQLite et ne couvre ni la RLS,
ni les agrégats continus, ni PostGIS. Avant toute mise en service, il faut les exécuter sur une base de recette
(`docker compose`, propriété du lot infra).
