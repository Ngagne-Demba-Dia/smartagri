#!/bin/sh
# Premier conteneur d'initialisation de l'inférence (image aws-cli) : télécharge le paquet de modèles
# depuis S3 et vérifie son empreinte SHA-256. Toute erreur arrête le pod : aucun modèle non vérifié
# n'est servi. L'extraction est faite ensuite par extract-bundle.py (image ML).
set -eu

: "${MODEL_BUNDLE_URI:?MODEL_BUNDLE_URI manquant}"
: "${MODEL_BUNDLE_SHA256:?MODEL_BUNDLE_SHA256 manquant}"

case "$MODEL_BUNDLE_SHA256" in
  *[!0-9a-f]*) echo "MODEL_BUNDLE_SHA256 invalide (hexadécimal minuscule attendu)" >&2; exit 1 ;;
esac
if [ "${#MODEL_BUNDLE_SHA256}" -ne 64 ]; then
  echo "MODEL_BUNDLE_SHA256 doit comporter 64 caractères" >&2
  exit 1
fi

aws s3 cp --only-show-errors "$MODEL_BUNDLE_URI" /models/bundle.tar.gz
echo "$MODEL_BUNDLE_SHA256  /models/bundle.tar.gz" | sha256sum -c -
echo "Paquet de modèles téléchargé et vérifié : $MODEL_BUNDLE_SHA256"
