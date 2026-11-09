output "irsa_role_arns" {
  description = "ARN des rôles IRSA par ServiceAccount (à reporter dans infra/k8s/overlays/*/irsa.yaml)."
  value       = { for key, role in aws_iam_role.irsa : key => role.arn }
}

output "github_ecr_push_role_arn" {
  description = "Rôle assumé par GitHub Actions pour publier dans ECR (variable de dépôt AWS_ECR_PUSH_ROLE_ARN)."
  value       = try(aws_iam_role.github_ecr_push[0].arn, null)
}
