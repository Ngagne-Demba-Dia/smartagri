#!/usr/bin/env bash
# Fixe étiquette et condensat des quatre images dans un overlay kustomize, à partir des fiches
# images/image-*.txt produites par le job build-push de .github/workflows/cd.yml, et écrit le corps
# de la PR GitOps dans pr-body.md.
# Usage : SOURCE_SHA=<sha> gitops-bump.sh <overlay>/kustomization.yaml <application ArgoCD>
set -euo pipefail

overlay="${1:?overlay manquant}"
app="${2:?application ArgoCD manquante}"
: "${SOURCE_SHA:?SOURCE_SHA manquant}"
allowed=" smartagri92/api smartagri92/ml smartagri92/mlflow smartagri92/web "
expected=4

{
  echo "Images construites depuis \`${SOURCE_SHA}\`, analysées (trivy), signées et attestées (cosign)."
  echo
  echo "| Image | Étiquette | Condensat |"
  echo "| --- | --- | --- |"
} > pr-body.md

count=0
for file in images/image-*.txt; do
  read -r name ref tag digest < "$file"
  [[ "$allowed" == *" $name "* ]] || { echo "::error::image inattendue : $name"; exit 1; }
  [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "::error::condensat invalide pour $name"; exit 1; }
  [[ "$tag" =~ ^sha-[0-9a-f]{40}$ ]] || { echo "::error::étiquette invalide pour $name"; exit 1; }
  export NAME="$name" REF="$ref" TAG="$tag" DIGEST="$digest"
  yq -e '.images[] | select(.name == strenv(NAME))' "$overlay" > /dev/null \
    || { echo "::error::$name absent de $overlay"; exit 1; }
  # yq conserve les commentaires de l'overlay.
  yq -i '(.images[] | select(.name == strenv(NAME))) |= (.newName = strenv(REF) | .newTag = strenv(TAG) | .digest = strenv(DIGEST))' "$overlay"
  echo "| \`$name\` | \`$tag\` | \`$digest\` |" >> pr-body.md
  count=$((count + 1))
done
[[ "$count" -eq "$expected" ]] || { echo "::error::$expected images attendues, $count reçues"; exit 1; }

{
  echo
  echo "Vérifier avant fusion : \`cosign verify <image>@<condensat>\` (identité du workflow cd.yml)."
  echo "La fusion déclenche la synchronisation ArgoCD de \`$app\`."
} >> pr-body.md
