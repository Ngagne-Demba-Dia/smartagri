variable "environment" {
  description = "Nom de l'environnement (staging ou prod)."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment doit valoir staging ou prod."
  }
}

variable "vpc_cidr" {
  description = "Bloc /16 du VPC (distinct par environnement pour permettre un appairage)."
  type        = string
}

variable "az_count" {
  description = "Nombre de zones de disponibilité."
  type        = number
}

variable "single_nat_gateway" {
  description = "Une seule passerelle NAT (staging) ou une par zone (prod)."
  type        = bool
}

variable "enable_interface_endpoints" {
  description = "Points de terminaison d'interface ECR/STS/Secrets Manager."
  type        = bool
  default     = true
}

variable "cluster_version" {
  description = "Version Kubernetes EKS."
  type        = string
  default     = "1.34"
}

variable "endpoint_public_access" {
  description = "API Kubernetes accessible publiquement (restreinte par CIDR)."
  type        = bool
  default     = true
}

variable "endpoint_public_access_cidrs" {
  description = "CIDR autorisés sur l'API Kubernetes publique."
  type        = list(string)
}

variable "admin_role_arns" {
  description = "Rôles IAM administrateurs du cluster."
  type        = list(string)
  default     = []
}

variable "node_instance_types" {
  description = "Types d'instances des nœuds."
  type        = list(string)
}

variable "node_capacity_type" {
  description = "ON_DEMAND ou SPOT."
  type        = string
  default     = "ON_DEMAND"
}

variable "node_min_size" {
  description = "Nœuds minimum."
  type        = number
}

variable "node_max_size" {
  description = "Nœuds maximum."
  type        = number
}

variable "node_desired_size" {
  description = "Nœuds au démarrage."
  type        = number
}

variable "k8s_namespace" {
  description = "Namespace Kubernetes de l'application."
  type        = string
  default     = "smartagri92"
}

variable "k8s_ml_namespace" {
  description = "Namespace Kubernetes de la plateforme IA (inference, mlflow, ré-entraînement)."
  type        = string
  default     = "smartagri92-ml"
}

variable "create_ecr" {
  description = "Crée le registre partagé (true dans le seul compte qui le porte, en général prod)."
  type        = bool
  default     = false
}

variable "ecr_pull_account_ids" {
  description = "Comptes autorisés à tirer les images du registre partagé."
  type        = list(string)
  default     = []
}

variable "github_repository" {
  description = "Dépôt GitHub « organisation/depot » autorisé à publier dans ECR (avec create_ecr)."
  type        = string
  default     = null
}

variable "create_github_oidc_provider" {
  description = "Crée le fournisseur OIDC GitHub dans ce compte."
  type        = bool
  default     = true
}

variable "set_database_url_secret" {
  description = "Terraform écrit DATABASE_URL dans Secrets Manager (sinon : valeur posée hors bande)."
  type        = bool
  default     = false
}

variable "database_url" {
  description = "URL PostgreSQL/TimescaleDB (sensible)."
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
}

variable "budget_alert_emails" {
  description = "Destinataires des alertes de budget."
  type        = list(string)
}

variable "tags" {
  description = "Étiquettes complémentaires."
  type        = map(string)
  default     = {}
}
