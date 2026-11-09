variable "name_prefix" {
  description = "Préfixe du budget (ex. smartagri92-prod)."
  type        = string
}

variable "monthly_limit_usd" {
  description = "Plafond mensuel en USD."
  type        = number

  validation {
    condition     = var.monthly_limit_usd > 0
    error_message = "monthly_limit_usd doit être positif."
  }
}

variable "alert_emails" {
  description = "Destinataires des alertes de budget."
  type        = list(string)

  validation {
    condition     = length(var.alert_emails) > 0
    error_message = "Au moins un destinataire est requis."
  }
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
