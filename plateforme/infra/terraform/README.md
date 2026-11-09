# Infrastructure AWS — Terraform

> **Statut : non validé.** Ce code n'a été passé ni par `terraform validate`, ni par `tflint`, ni par
> `checkov` : Terraform n'est pas installé sur le poste où il a été écrit et aucun téléchargement n'a
> été autorisé. Exécuter les commandes ci-dessous avant tout `plan`.

## Organisation

```
infra/terraform/
├── .tflint.hcl
├── modules/
│   ├── network/    VPC 2 ou 3 AZ, NAT, journaux de flux, points de terminaison S3/ECR/STS/Secrets Manager
│   ├── eks/        EKS (mode d'authentification API, IRSA, journaux d'audit, IMDSv2, disques chiffrés)
│   ├── datalake/   S3 raw / curated / models / images, KMS, TLS obligatoire, cycle de vie
│   ├── ecr/        registre partagé (tags immuables, scan à la publication, tirage inter-comptes)
│   ├── secrets/    Secrets Manager : <prefix>/app, <prefix>/database, <prefix>/ml (valeurs hors Terraform)
│   ├── iam/        rôles IRSA par ServiceAccount + rôle OIDC GitHub de publication ECR
│   └── budget/     budget mensuel avec alertes 80 % / 100 % prévu / 100 % réel
├── stack/          composition de tous les modules pour un environnement
└── envs/
    ├── staging/    compte de recette : 2 AZ, 1 NAT, t3.medium SPOT 1→3, pas de registre
    └── prod/       compte de production : 3 AZ, 1 NAT par AZ, t3.large 3→6, registre ECR partagé
```

Les deux environnements sont dans des **comptes AWS distincts** (`allowed_account_ids` empêche
d'appliquer un environnement avec les identifiants de l'autre).

## Rôles IRSA produits

| Rôle (`<prefix>-…`) | ServiceAccount | Droits |
|---|---|---|
| `api` | `smartagri92/agri-api` | lecture/écriture `images/*` |
| `ingestor` | `smartagri92/agri-ingestor` | écriture `raw/telemetry/*` |
| `external-secrets` | `smartagri92/external-secrets-reader` | lecture `<prefix>/app`, `<prefix>/database` |
| `ml-jobs` | `smartagri92-ml/agri-ml-jobs` | lecture lac, écriture `curated/*`, `models/*` |
| `inference` | `smartagri92-ml/agri-inference` | lecture `models/bundles/*` |
| `mlflow` | `smartagri92-ml/agri-mlflow` | lecture/écriture `models/mlflow/*` |
| `external-secrets-ml` | `smartagri92-ml/external-secrets-reader` | lecture `<prefix>/ml` uniquement |

Les ARN sont dans la sortie `irsa_role_arns` ; les reporter dans les correctifs
`infra/k8s/overlays/*/patches/irsa.yaml`.

## Commandes

Prérequis : Terraform ≥ 1.6, TFLint, Checkov, identifiants AWS du bon compte (SSO de préférence).

```bash
cd infra/terraform

# 1. Format et validation statique (sans état distant)
terraform fmt -check -recursive
for d in envs/staging envs/prod; do
  terraform -chdir="$d" init -backend=false
  terraform -chdir="$d" validate
done

# 2. Lint et analyse de sécurité
tflint --init --config "$(pwd)/.tflint.hcl"
tflint --recursive --config "$(pwd)/.tflint.hcl"
checkov -d . --framework terraform --quiet

# 3. Plan d'un environnement (état distant)
cd envs/staging
cp backend.hcl.example backend.hcl            # adapter : compartiment d'état du compte
cp terraform.tfvars.example terraform.tfvars  # adapter
terraform init -backend-config=backend.hcl
terraform plan -out=tfplan
terraform apply tfplan
```

Après le premier `terraform init`, **commiter `.terraform.lock.hcl`** de chaque environnement
(sommes de contrôle des providers). Il n'est pas fourni ici car il ne peut être produit sans
télécharger les providers.

## Secrets : valeurs posées hors bande

Terraform crée les secrets vides (sauf le secret `database` si `set_database_url_secret = true` : valeurs
passées par `TF_VAR_database_url` et `TF_VAR_migration_database_url`, toutes deux exigées). Les valeurs
ne transitent ainsi ni par l'état Terraform ni par un fichier versionné :

```bash
aws secretsmanager put-secret-value --secret-id smartagri92-prod/app \
  --secret-string file://app-secret.json   # JWT_SECRET, DEVICE_KEY_PEPPER, MQTT_*, ANTHROPIC_API_KEY
aws secretsmanager put-secret-value --secret-id smartagri92-prod/database \
  --secret-string file://db-secret.json    # DATABASE_URL (rôle API), MIGRATION_DATABASE_URL (rôle propriétaire)
aws secretsmanager put-secret-value --secret-id smartagri92-prod/ml \
  --secret-string file://ml-secret.json    # OCTOPUS_API_KEY, MLFLOW_BACKEND_STORE_URI, AGRIML_PSEUDO_SALT(_ID)
shred -u app-secret.json db-secret.json ml-secret.json
```

`MIGRATION_DATABASE_URL` n'est recopiée que dans le Secret `agri-database-migrate`, monté par le seul Job
de migration (`infra/k8s/base/app/migrate-job.yaml`) ; l'API n'a que `DATABASE_URL`.

External Secrets Operator les recopie ensuite dans les Secrets Kubernetes (voir `infra/k8s`).

## Base de données

Amazon RDS **ne propose pas l'extension TimescaleDB**. Options, par ordre de préférence :

1. Timescale Cloud (région AWS eu-west-3), connecté par VPC peering ou PrivateLink ;
2. PostgreSQL + TimescaleDB autogéré sur EKS (opérateur CloudNativePG, image TimescaleDB, sauvegardes
   S3) — plus de travail d'exploitation, mais portable ;
3. RDS PostgreSQL sans Timescale (hypertables remplacées par du partitionnement natif) — à éviter, la
   migration `001_init.sql` suppose TimescaleDB.

Aucune de ces options n'est créée ici : `DATABASE_URL` est fourni par secret.

## Souveraineté des données

- Les mesures des champs, les photos de cultures et les données des exploitants sont des **données à
  caractère personnel** au sens de la loi sénégalaise n° 2008-12 du 25 janvier 2008 dès qu'elles sont
  rattachées à un exploitant identifiable. Le transfert hors du Sénégal est encadré par la **CDP**
  (Commission de protection des données personnelles) : déclaration ou autorisation préalable selon
  les traitements.
- eu-west-3 (Paris) est retenu pour la latence et l'offre de services managés ; ce choix **doit être
  validé par un juriste** au regard de la loi 2008-12 et des exigences contractuelles des partenaires
  (coopératives, bailleurs).
- Portabilité : tout ce qui tourne sur EKS est décrit en manifestes Kubernetes standard
  (`infra/k8s`). Une migration vers un centre de données local (Sénégal) ou un fournisseur souverain
  ne demande de réécrire que cette couche Terraform (réseau, stockage objet compatible S3, secrets).
- Les journaux de flux, sauvegardes et compartiments d'état restent dans la même région.
