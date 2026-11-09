variable "name_prefix" {
  description = "Préfixe des compartiments (ex. smartagri92-prod) ; l'identifiant de compte est ajouté pour l'unicité."
  type        = string
}

variable "noncurrent_version_days" {
  description = "Durée de conservation des versions remplacées ou supprimées (jours)."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
