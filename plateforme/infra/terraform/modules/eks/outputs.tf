output "cluster_name" {
  description = "Nom du cluster."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Point d'accès de l'API Kubernetes."
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Certificat de l'autorité du cluster (base64)."
  value       = module.eks.cluster_certificate_authority_data
}

output "oidc_provider_arn" {
  description = "ARN du fournisseur OIDC (IRSA)."
  value       = module.eks.oidc_provider_arn
}

output "oidc_provider" {
  description = "Émetteur OIDC sans https:// (clé des conditions :sub et :aud)."
  value       = module.eks.oidc_provider
}

output "node_security_group_id" {
  description = "Groupe de sécurité des nœuds."
  value       = module.eks.node_security_group_id
}
