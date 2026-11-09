# Environnement de production (eu-west-3, Paris).
# Initialisation : terraform init -backend-config=backend.hcl (copier backend.hcl.example ; fichier non versionné).
# Le fichier .terraform.lock.hcl produit par « terraform init » DOIT être commité (sommes de contrôle des providers).

terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.82"
    }
  }

  # Configuration partielle : bucket et dynamodb_table viennent de backend.hcl.
  backend "s3" {
    key     = "smartagri92/prod/terraform.tfstate"
    region  = "eu-west-3"
    encrypt = true
  }
}

provider "aws" {
  region = var.region

  # Garde-fou : refuse de s'exécuter avec des identifiants d'un autre compte.
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      project             = "smartagri92"
      environment         = "prod"
      managed_by          = "terraform"
      data_classification = "confidentiel"
    }
  }
}

module "stack" {
  source = "../../stack"

  environment = "prod"

  vpc_cidr                   = "10.40.0.0/16"
  az_count                   = 3
  single_nat_gateway         = false
  enable_interface_endpoints = true

  cluster_version              = var.cluster_version
  endpoint_public_access_cidrs = var.endpoint_public_access_cidrs
  admin_role_arns              = var.admin_role_arns

  node_instance_types = ["t3.large"]
  node_capacity_type  = "ON_DEMAND"
  node_min_size       = 3
  node_max_size       = 6
  node_desired_size   = 3

  create_ecr                  = true
  ecr_pull_account_ids        = var.ecr_pull_account_ids
  github_repository           = var.github_repository
  create_github_oidc_provider = var.create_github_oidc_provider

  set_database_url_secret = var.set_database_url_secret
  database_url            = var.database_url
  migration_database_url  = var.migration_database_url

  monthly_budget_usd  = var.monthly_budget_usd
  budget_alert_emails = var.budget_alert_emails
}
