#!/bin/bash
# Crée le rôle et la base « mlflow » (magasin de métadonnées MLflow), séparés de la base applicative.
# Exécuté une seule fois par l'entrypoint PostgreSQL, au premier démarrage sur un volume vide.
# Le script est « sourcé » par l'entrypoint : pas de « set -u » ni de « exit » ici.
# Le mot de passe passe par une variable psql (:'pw'), jamais interpolé dans le SQL par le shell.

if [ -z "${MLFLOW_DB_PASSWORD:-}" ]; then
  echo "00_mlflow_db.sh : MLFLOW_DB_PASSWORD absent, base mlflow non créée" >&2
  return 1 2>/dev/null || exit 1
fi

psql -v ON_ERROR_STOP=1 -v pw="${MLFLOW_DB_PASSWORD}" \
  --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<'SQL'
SELECT format('CREATE ROLE mlflow LOGIN PASSWORD %L', :'pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mlflow') \gexec
SELECT 'CREATE DATABASE mlflow OWNER mlflow'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mlflow') \gexec
SQL
