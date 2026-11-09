variable "name_prefix" {
  description = "Préfixe des secrets (ex. smartagri92-prod) : secrets « <prefix>/app » et « <prefix>/database »."
  type        = string
}

variable "recovery_window_in_days" {
  description = "Délai avant suppression définitive d'un secret supprimé (7 à 30 jours)."
  type        = number
  default     = 30

  validation {
    condition     = var.recovery_window_in_days >= 7 && var.recovery_window_in_days <= 30
    error_message = "recovery_window_in_days doit être compris entre 7 et 30."
  }
}

variable "set_database_url_secret" {
  description = "true : Terraform écrit DATABASE_URL dans le secret « database » (la valeur passe alors par l'état chiffré)."
  type        = bool
  default     = false
}

variable "database_url" {
  description = "URL de connexion PostgreSQL (sensible). Utilisée seulement si set_database_url_secret = true."
  type        = string
  default     = null
  sensitive   = true
}

variable "migration_database_url" {
  description = "URL PostgreSQL du rôle propriétaire du schéma (droits DDL, sensible), lue par le Job de migration. Exigée si set_database_url_secret = true."
  type        = string
  default     = null
  sensitive   = true
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
