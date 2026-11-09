#!/bin/sh
# Initialisation ponctuelle de MinIO (service « minio-init ») :
#  - compartiments du lac de données et d'MLflow, sans accès anonyme ;
#  - versionnage sur les données brutes (protection contre l'écrasement accidentel) ;
#  - utilisateur applicatif distinct du compte root, avec la politique « readwrite ».
# Idempotent : peut être relancé sans effet de bord.
set -eu

BUCKETS="agri-raw agri-curated agri-models agri-images mlflow"

mc alias set local http://minio:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null

for bucket in ${BUCKETS}; do
  mc mb --ignore-existing "local/${bucket}"
  mc anonymous set none "local/${bucket}"
done

mc version enable local/agri-raw

if mc admin user info local "${S3_ACCESS_KEY}" >/dev/null 2>&1; then
  echo "minio-init : utilisateur applicatif déjà présent"
else
  mc admin user add local "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}"
fi

if ! mc admin policy attach local readwrite --user "${S3_ACCESS_KEY}" 2>/tmp/attach.err; then
  # Une politique déjà attachée renvoie une erreur : on la journalise au lieu de l'ignorer.
  echo "minio-init : attache de politique non appliquée : $(cat /tmp/attach.err)" >&2
fi

echo "minio-init : terminé"
