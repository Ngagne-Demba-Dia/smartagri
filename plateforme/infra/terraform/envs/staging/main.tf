# Environnement de recette (eu-west-3, Paris), compte AWS distinct de la production.
# Dimensionnement réduit : 2 AZ, une seule passerelle NAT, pas de points de terminaison d'interface.
# Les images sont tirées du registre ECR du compte prod (create_ecr = false ici).
# Initialisation : terraform init -backend-config=backend.hcl (copier backend.hcl.example ; fichier non versionné).

terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.82"
    }
  }

  backend "s3" {
    key     = "smartagri92/staging/terraform.tfstate"
    region  = "eu-west-3"
    encrypt = true
  }
}

provider "aws" {
  region = var.region

  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      project             = "smartagri92"
      environment         = "staging"
      managed_by          = "terraform"
      data_classification = "confidentiel"
    }
  }
}

module "stack" {
  source = "../../stack"

  environment = "staging"

  vpc_cidr                   = "10.41.0.0/16"
  az_count                   = 2
  single_nat_gateway         = true
  enable_interface_endpoints = false

  cluster_version              = var.cluster_version
  endpoint_public_access_cidrs = var.endpoint_public_access_cidrs
  admin_role_arns              = var.admin_role_arns

  node_instance_types = ["t3.medium"]
  node_capacity_type  = var.node_capacity_type
  node_min_size       = 1
  node_max_size       = 3
  node_desired_size   = 2

  create_ecr = false

  set_database_url_secret = var.set_database_url_secret
  database_url            = var.database_url
  migration_database_url  = var.migration_database_url

  monthly_budget_usd  = var.monthly_budget_usd
  budget_alert_emails = var.budget_alert_emails
}
