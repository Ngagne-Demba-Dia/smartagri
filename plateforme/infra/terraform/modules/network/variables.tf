variable "name" {
  description = "Préfixe de nommage (ex. smartagri92-prod)."
  type        = string
}

variable "vpc_cidr" {
  description = "Bloc CIDR du VPC (/16 attendu)."
  type        = string
  default     = "10.40.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0)) && endswith(var.vpc_cidr, "/16")
    error_message = "vpc_cidr doit être un bloc /16 valide."
  }
}

variable "az_count" {
  description = "Nombre de zones de disponibilité (2 en staging, 3 en production)."
  type        = number
  default     = 3

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count doit valoir 2 ou 3."
  }
}

variable "single_nat_gateway" {
  description = "true : une seule passerelle NAT (staging, économique) ; false : une par zone (production)."
  type        = bool
  default     = false
}

variable "enable_interface_endpoints" {
  description = "Crée les points de terminaison d'interface ECR/STS/Secrets Manager (environ 7 USD/mois chacun et par zone)."
  type        = bool
  default     = true
}

variable "flow_log_retention_days" {
  description = "Rétention des journaux de flux VPC (jours)."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
