output "cluster_name" {
  description = "Nom du cluster EKS (aws eks update-kubeconfig --name ...)."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Point d'accès de l'API Kubernetes."
  value       = module.eks.cluster_endpoint
}

output "vpc_cidr_block" {
  description = "CIDR du VPC (à reporter dans les NetworkPolicies d'egress vers la base)."
  value       = module.network.vpc_cidr_block
}

output "datalake_buckets" {
  description = "Compartiments du lac par zone."
  value       = module.datalake.bucket_names
}

output "ecr_repository_urls" {
  description = "Dépôts ECR (vide hors compte porteur du registre)."
  value       = var.create_ecr ? module.ecr[0].repository_urls : {}
}

output "irsa_role_arns" {
  description = "Rôles IRSA à reporter dans les annotations des ServiceAccounts."
  value       = module.iam.irsa_role_arns
}

output "github_ecr_push_role_arn" {
  description = "Rôle OIDC de publication ECR pour GitHub Actions."
  value       = module.iam.github_ecr_push_role_arn
}

output "secret_names" {
  description = "Secrets à alimenter hors bande."
  value       = [module.secrets.app_secret_name, module.secrets.database_secret_name, module.secrets.ml_secret_name]
}
