output "repository_urls" {
  description = "URL des dépôts par nom."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.repository_url }
}

output "repository_arns" {
  description = "ARN des dépôts par nom."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.arn }
}
