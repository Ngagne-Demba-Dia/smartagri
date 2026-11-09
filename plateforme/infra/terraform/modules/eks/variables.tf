variable "cluster_name" {
  description = "Nom du cluster EKS."
  type        = string
}

variable "cluster_version" {
  description = "Version Kubernetes. Choisir une version en support standard EKS au moment du déploiement (aws eks describe-cluster-versions)."
  type        = string
  default     = "1.34"
}

variable "vpc_id" {
  description = "VPC du cluster."
  type        = string
}

variable "private_subnet_ids" {
  description = "Sous-réseaux privés pour le plan de contrôle et les nœuds."
  type        = list(string)
}

variable "endpoint_public_access" {
  description = "Expose l'API Kubernetes publiquement (restreinte par CIDR). false si accès via VPN/bastion."
  type        = bool
  default     = true
}

variable "endpoint_public_access_cidrs" {
  description = "CIDR autorisés à joindre l'API Kubernetes publique (IP fixes de l'équipe, runners)."
  type        = list(string)

  validation {
    condition     = !contains(var.endpoint_public_access_cidrs, "0.0.0.0/0")
    error_message = "L'API Kubernetes ne doit pas être ouverte à 0.0.0.0/0."
  }
}

variable "admin_role_arns" {
  description = "Rôles IAM administrateurs du cluster (entrées d'accès EKS)."
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "Rétention des journaux du plan de contrôle (jours)."
  type        = number
  default     = 90
}

variable "node_instance_types" {
  description = "Types d'instances des nœuds gérés."
  type        = list(string)
  default     = ["t3.large"]
}

variable "node_capacity_type" {
  description = "ON_DEMAND ou SPOT."
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "node_capacity_type doit valoir ON_DEMAND ou SPOT."
  }
}

variable "node_min_size" {
  description = "Nombre minimal de nœuds."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Nombre maximal de nœuds."
  type        = number
  default     = 6
}

variable "node_desired_size" {
  description = "Nombre initial de nœuds."
  type        = number
  default     = 3
}

variable "node_disk_size_gb" {
  description = "Taille du disque racine des nœuds (Go)."
  type        = number
  default     = 50
}

variable "tags" {
  description = "Étiquettes appliquées aux ressources."
  type        = map(string)
  default     = {}
}
