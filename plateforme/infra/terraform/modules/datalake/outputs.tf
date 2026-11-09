output "bucket_names" {
  description = "Noms des compartiments par zone (raw, curated, models, images)."
  value       = { for zone, bucket in aws_s3_bucket.zone : zone => bucket.id }
}

output "bucket_arns" {
  description = "ARN des compartiments par zone."
  value       = { for zone, bucket in aws_s3_bucket.zone : zone => bucket.arn }
}

output "kms_key_arn" {
  description = "Clé KMS du lac de données."
  value       = aws_kms_key.datalake.arn
}
