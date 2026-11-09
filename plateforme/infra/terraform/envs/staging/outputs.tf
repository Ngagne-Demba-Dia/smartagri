output "cluster_name" {
  description = "Nom du cluster EKS."
  value       = module.stack.cluster_name
}

output "cluster_endpoint" {
  description = "Point d'accès de l'API Kubernetes."
  value       = module.stack.cluster_endpoint
}

output "vpc_cidr_block" {
  description = "CIDR du VPC."
  value       = module.stack.vpc_cidr_block
}

output "datalake_buckets" {
  description = "Compartiments du lac de données."
  value       = module.stack.datalake_buckets
}

output "irsa_role_arns" {
  description = "Rôles IRSA (annotations des ServiceAccounts)."
  value       = module.stack.irsa_role_arns
}

output "secret_names" {
  description = "Secrets à alimenter hors bande."
  value       = module.stack.secret_names
}
