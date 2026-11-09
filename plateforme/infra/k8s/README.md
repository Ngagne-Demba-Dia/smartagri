# Manifestes Kubernetes (kustomize)

```text
infra/k8s/
├── base/
│   ├── app/   namespace smartagri92 : api, ingestor, web, Job migrate, Ingress Traefik, ExternalSecrets, NetworkPolicies
│   └── ml/    namespace smartagri92-ml : inference, MLflow, CronJobs retrain et drift, ExternalSecret OctOpus
├── components/
│   └── egress-fqdn-cilium/   filtrage de la sortie par nom DNS (octopus.ml, S3, Anthropic…)
└── overlays/
    ├── dev/   cluster de recette (compte AWS staging, APP_ENV=staging)
    └── prod/  cluster de production
```

Rendu local (vérifié avec kubectl v1.34.1 / kustomize v5.7.1) :

```bash
kubectl kustomize infra/k8s/overlays/dev
kubectl kustomize infra/k8s/overlays/prod
```

Déploiement : ArgoCD (`infra/argocd/`), jamais `kubectl apply` à la main en production.

## Prérequis dans le cluster

| Composant | Rôle |
| --- | --- |
| Traefik v3 (namespace `traefik`) | Ingress, Middlewares `ratelimit`, `security-headers`, `body-limit` |
| cert-manager + ClusterIssuers `letsencrypt-staging` / `letsencrypt-prod` | certificats TLS |
| External Secrets Operator ≥ 0.16 (API `external-secrets.io/v1`) | secrets depuis AWS Secrets Manager |
| kube-prometheus-stack (namespace `monitoring`) + Pushgateway | ServiceMonitors, règles d'alerte |
| VPC CNI avec `enableNetworkPolicy` (Terraform) ou Cilium | application des NetworkPolicies |
| metrics-server | HPA |

## Sécurité appliquée

- Pod Security Standards `restricted` sur les deux namespaces ; tous les conteneurs : non root (UID
  10001), `readOnlyRootFilesystem`, `capabilities: drop ALL`, seccomp `RuntimeDefault`.
- Un ServiceAccount et un rôle IRSA par charge de travail ; jeton monté seulement là où AWS est appelé.
- NetworkPolicies : refus par défaut, DNS, puis flux explicites. `/metrics`, `/docs`, `/healthz` ne sont
  pas routés par l'Ingress (seul `/v1` l'est).
- Secrets : uniquement via External Secrets ; aucun secret dans ce dépôt.

## Sortie vers OctOpus (`octopus.ml:443`)

Une NetworkPolicy Kubernetes standard filtre par IP et port, **pas par nom DNS**. Sans Cilium, la
garantie est donc « seuls les pods étiquetés `smartagri92.io/egress-https` ont le 443 sortant » — ce
qui inclut l'API (Anthropic, météo, S3). Pour restreindre réellement OctOpus au ré-entraînement du
namespace ML :

- **Cilium** (CNI ou chaînage avec le VPC CNI) : activer `components/egress-fqdn-cilium` dans l'overlay.
  Il supprime les politiques `egress-https` et les remplace par des règles `toFQDNs` : `octopus.ml`
  pour les pods `smartagri92.io/octopus=true` (CronJob `retrain`), S3/STS pour les autres pods ML,
  S3/STS/Anthropic/Open-Meteo pour l'API. Rendu vérifié : `kubectl kustomize` d'un overlay prod
  incluant le composant produit 3 `CiliumNetworkPolicy` et aucune `egress-https`.
- **Sans Cilium** : proxy de sortie (Squid, Envoy) avec liste blanche de domaines, et 443 sortant
  autorisé seulement vers le proxy.

## Migrations de schéma

`base/app/migrate-job.yaml` : Job `migrate`, même image que l'API (le digest épinglé par l'overlay
s'applique aussi au Job), commande `python -m app.db.migrate`. Il lit `MIGRATION_DATABASE_URL` (rôle
propriétaire du schéma) dans le Secret `agri-database-migrate`, que l'API ne monte pas. Pas d'IRSA,
aucune entrée réseau, sortie vers PostgreSQL seulement (NetworkPolicy `migrate`).

Ordre ArgoCD : vague -3 namespace et ServiceAccounts, -2 `SecretStore` et `ExternalSecret`, -1 Job
(hook `Sync`, `BeforeHookCreation`), 0 Deployments. Un hook `PreSync` passerait avant le namespace et
le Secret au premier déploiement et resterait bloqué. Un échec du Job arrête la synchronisation avant
les Deployments. Détails : `docs/11_deploiement.md` §5.

## Inférence

- Paquet de modèles : `MODEL_BUNDLE_URI` + `MODEL_BUNDLE_SHA256` (ConfigMap `inference-bundle`).
  L'init `fetch-bundle` télécharge et vérifie l'empreinte ; `extract-bundle` extrait (tarfile, filtre
  `data`) ; la sonde de disponibilité recalcule l'empreinte toutes les 60 s.
- Promotion d'un modèle = PR changeant ces deux valeurs (relue). Aucune promotion automatique.
- **À fournir par le lot ML** :
  - service HTTP `python -m agriml.predict serve --bundle-dir … --port 8080` : `agriml.predict`
    existe mais n'offre qu'une prédiction par lot, sans sous-commande `serve` ;
  - CLI de dérive `--window-days 7 --push` : `agriml.monitoring.drift` calcule PSI et KS mais n'a pas
    de point d'entrée (CronJob `drift` suspendu en attendant) ;
  - ré-entraînement planifié : `agriml.mlops.retrain_flow` existe avec des fichiers locaux en entrée ;
    il manque l'extraction des données, la source OctOpus et l'envoi au Pushgateway (CronJob
    `retrain` suspendu) ;
  - le `Dockerfile` de `ml/` (UID 10001 ; Python ≥ 3.11.4 pour le filtre tarfile `data`).
- **À fournir par le lot backend** : l'API ne connaît que `INFERENCE_BACKEND` ∈ `none|local|octopus`.
  Pour appeler ce service, ajouter un mode `remote` (URL `http://inference.smartagri92-ml.svc:8080`) ;
  en attendant, les overlays fixent `INFERENCE_BACKEND=none` (la NetworkPolicy api → inference:8080
  est déjà en place). Le mode `local` resterait possible en ajoutant à l'API les mêmes conteneurs
  d'initialisation et un droit IRSA de lecture `models/bundles/*`.

## Points ouverts

- Job `migrate` : jamais exécuté sur un cluster. Le tester en recette sur une copie de la base
  contenant des segments compressés avant la première mise en production.
- L'ingestor n'a pas de sonde : le pont MQTT n'expose pas de point HTTP de santé.
- `ingestor` reste à 1 réplique tant que le backend n'utilise pas d'abonnement partagé MQTT.
- Le CronJob `retrain` est suspendu (`suspend: true`) jusqu'à la livraison du pipeline.
- Comptes AWS fictifs (111111111111 prod, 222222222222 staging) et domaines `smartagri92.example` à
  remplacer.
