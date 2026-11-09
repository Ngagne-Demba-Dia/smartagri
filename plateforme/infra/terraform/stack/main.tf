# Pile complète d'un environnement Smart Agri92 : réseau, EKS, lac de données, registre (prod seulement),
# secrets, rôles IAM et budget. Appelée par envs/staging et envs/prod avec des dimensionnements différents.

locals {
  name = "smartagri92-${var.environment}"
}

module "network" {
  source = "../modules/network"

  name                       = local.name
  vpc_cidr                   = var.vpc_cidr
  az_count                   = var.az_count
  single_nat_gateway         = var.single_nat_gateway
  enable_interface_endpoints = var.enable_interface_endpoints
  tags                       = var.tags
}

module "eks" {
  source = "../modules/eks"

  cluster_name                 = local.name
  cluster_version              = var.cluster_version
  vpc_id                       = module.network.vpc_id
  private_subnet_ids           = module.network.private_subnet_ids
  endpoint_public_access       = var.endpoint_public_access
  endpoint_public_access_cidrs = var.endpoint_public_access_cidrs
  admin_role_arns              = var.admin_role_arns
  node_instance_types          = var.node_instance_types
  node_capacity_type           = var.node_capacity_type
  node_min_size                = var.node_min_size
  node_max_size                = var.node_max_size
  node_desired_size            = var.node_desired_size
  tags                         = var.tags
}

module "datalake" {
  source = "../modules/datalake"

  name_prefix = local.name
  tags        = var.tags
}

module "ecr" {
  source = "../modules/ecr"
  count  = var.create_ecr ? 1 : 0

  pull_account_ids = var.ecr_pull_account_ids
  tags             = var.tags
}

module "secrets" {
  source = "../modules/secrets"

  name_prefix             = local.name
  set_database_url_secret = var.set_database_url_secret
  database_url            = var.database_url
  migration_database_url  = var.migration_database_url
  tags                    = var.tags
}

module "iam" {
  source = "../modules/iam"

  name_prefix                 = local.name
  namespace                   = var.k8s_namespace
  ml_namespace                = var.k8s_ml_namespace
  oidc_provider_arn           = module.eks.oidc_provider_arn
  oidc_provider               = module.eks.oidc_provider
  bucket_arns                 = module.datalake.bucket_arns
  datalake_kms_key_arn        = module.datalake.kms_key_arn
  secret_arns                 = [module.secrets.app_secret_arn, module.secrets.database_secret_arn]
  ml_secret_arns              = [module.secrets.ml_secret_arn]
  secrets_kms_key_arn         = module.secrets.kms_key_arn
  github_repository           = var.create_ecr ? var.github_repository : null
  create_github_oidc_provider = var.create_github_oidc_provider
  ecr_repository_arns         = var.create_ecr ? values(module.ecr[0].repository_arns) : []
  tags                        = var.tags
}

module "budget" {
  source = "../modules/budget"

  name_prefix       = local.name
  monthly_limit_usd = var.monthly_budget_usd
  alert_emails      = var.budget_alert_emails
  tags              = var.tags
}
