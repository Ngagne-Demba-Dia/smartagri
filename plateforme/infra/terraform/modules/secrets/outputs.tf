output "app_secret_arn" {
  description = "ARN du secret applicatif."
  value       = aws_secretsmanager_secret.app.arn
}

output "app_secret_name" {
  description = "Nom du secret applicatif (clé lue par l'ExternalSecret)."
  value       = aws_secretsmanager_secret.app.name
}

output "database_secret_arn" {
  description = "ARN du secret de base de données."
  value       = aws_secretsmanager_secret.database.arn
}

output "database_secret_name" {
  description = "Nom du secret de base de données."
  value       = aws_secretsmanager_secret.database.name
}

output "ml_secret_arn" {
  description = "ARN du secret de la plateforme IA."
  value       = aws_secretsmanager_secret.ml.arn
}

output "ml_secret_name" {
  description = "Nom du secret de la plateforme IA."
  value       = aws_secretsmanager_secret.ml.name
}

output "kms_key_arn" {
  description = "Clé KMS des secrets."
  value       = aws_kms_key.secrets.arn
}
