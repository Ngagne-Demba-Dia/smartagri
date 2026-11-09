variable "name_prefix" {
  description = "Préfixe des rôles (ex. smartagri92-prod)."
  type        = string
}

variable "namespace" {
  description = "Namespace Kubernetes des ServiceAccounts."
  type        = string
  default     = "smartagri92"
}

variable "oidc_provider_arn" {
  description = "ARN du fournisseur OIDC du cluster EKS."
  type        = string
}

variable "oidc_provider" {
  description = "Émetteur OIDC du cluster, sans https://."
  type        = string
}

variable "bucket_arns" {
  description = "ARN des compartiments du lac par zone (raw, curated, models, images)."
  type        = map(string)

  validation {
    condition     = alltrue([for zone in ["raw", "curated", "models", "images"] : contains(keys(var.bucket_arns), zone)])
    error_message = "bucket_arns doit contenir les zones raw, curated, models et images."
  }
}

variable "datalake_kms_key_arn" {
  description = "Clé KMS du lac de données."
  type        = string
}

variable "ml_namespace" {
  description = "Namespace Kubernetes de la plateforme IA (inference, mlflow, tâches ML)."
  type        = string
  default     = "smartagri92-ml"
}

variable "ml_secret_arns" {
  description = "ARN des secrets lisibles par External Secrets dans le namespace ML (OCTOPUS_API_KEY, MLflow)."
  type        = list(string)
}

variable "secret_arns" {
  description = "ARN des secrets lisibles par External Secrets."
  type        = list(string)
}

variable "secrets_kms_key_arn" {
  description = "Clé KMS des secrets."
  type        = string
}

variable "github_repository" {
  description = "Dépôt GitHub « organisation/depot » autorisé à publier dans ECR ; null = pas de rôle GitHub."
  type        = string
  default     = null
}

variable "github_push_environment" {
  description = "Environnement GitHub du job de publication (restreint à la branche main dans GitHub)."
  type        = string
  default     = "ecr-push"
}

variable "create_github_oidc_provider" {
  description = "Crée le fournisseur OIDC GitHub (un seul par compte AWS)."
  type        = bool
  default     = true
}

variable "ecr_repository_arns" {
  description = "Dépôts ECR sur lesquels GitHub Actions peut publier."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
