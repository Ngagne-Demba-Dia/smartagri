variable "account_id" {
  description = "Identifiant du compte AWS de production (12 chiffres)."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id doit comporter 12 chiffres."
  }
}

variable "region" {
  description = "Région AWS."
  type        = string
  default     = "eu-west-3"
}

variable "cluster_version" {
  description = "Version Kubernetes EKS (en support standard au moment du déploiement)."
  type        = string
  default     = "1.34"
}

variable "endpoint_public_access_cidrs" {
  description = "CIDR autorisés sur l'API Kubernetes."
  type        = list(string)
}

variable "admin_role_arns" {
  description = "Rôles IAM administrateurs du cluster."
  type        = list(string)
  default     = []
}

variable "ecr_pull_account_ids" {
  description = "Comptes autorisés à tirer les images (compte staging)."
  type        = list(string)
  default     = []
}

variable "github_repository" {
  description = "Dépôt GitHub « organisation/depot » autorisé à publier dans ECR."
  type        = string
  default     = null
}

variable "create_github_oidc_provider" {
  description = "Crée le fournisseur OIDC GitHub dans ce compte."
  type        = bool
  default     = true
}

variable "set_database_url_secret" {
  description = "Terraform écrit DATABASE_URL dans Secrets Manager."
  type        = bool
  default     = false
}

variable "database_url" {
  description = "URL PostgreSQL/TimescaleDB de production. Passer par TF_VAR_database_url, jamais dans un fichier versionné."
  type        = string
  default     = null
  sensitive   = true
}

variable "migration_database_url" {
  description = "URL PostgreSQL du rôle propriétaire du schéma (Job de migration, sensible). Passer par TF_VAR_migration_database_url."
  type        = string
  default     = null
  sensitive   = true
}

variable "monthly_budget_usd" {
  description = "Budget mensuel en USD."
  type        = number
  default     = 1500
}

variable "budget_alert_emails" {
  description = "Destinataires des alertes de budget."
  type        = list(string)
}
