variable "repositories" {
  description = "Dépôts d'images à créer."
  type        = list(string)
  default     = ["smartagri92/api", "smartagri92/ml", "smartagri92/mlflow", "smartagri92/web"]
}

variable "keep_images" {
  description = "Nombre d'artefacts étiquetés conservés par dépôt (une image signée produit aussi des artefacts de signature et d'attestation)."
  type        = number
  default     = 150
}

variable "pull_account_ids" {
  description = "Comptes AWS autorisés à tirer les images (ex. compte staging)."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for id in var.pull_account_ids : can(regex("^[0-9]{12}$", id))])
    error_message = "Chaque identifiant de compte doit comporter 12 chiffres."
  }
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
