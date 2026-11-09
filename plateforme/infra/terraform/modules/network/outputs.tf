output "vpc_id" {
  description = "Identifiant du VPC."
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "Bloc CIDR du VPC (utilisé par les NetworkPolicies Kubernetes)."
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "Sous-réseaux privés (nœuds EKS, points de terminaison)."
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Sous-réseaux publics (répartiteurs de charge uniquement)."
  value       = module.vpc.public_subnets
}

output "private_route_table_ids" {
  description = "Tables de routage privées."
  value       = module.vpc.private_route_table_ids
}
