# Lac de données S3 en quatre zones : raw (télémétrie et messages bruts), curated (jeux préparés),
# models (artefacts de modèles), images (photos de feuilles pour le diagnostic).
# Pour chaque compartiment : propriété imposée (ACL désactivées), blocage de tout accès public,
# versionnage, chiffrement SSE-KMS avec clé dédiée (rotation annuelle), TLS >= 1.2 obligatoire,
# cycle de vie vers des classes moins chères.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id

  # Jours avant transition (null = pas de transition). raw reste lisible instantanément pour le
  # réentraînement (Glacier Instant Retrieval) ; les images anciennes vont en Glacier Flexible Retrieval.
  zones = {
    raw     = { ia_days = 30, archive_days = 180, archive_class = "GLACIER_IR" }
    curated = { ia_days = 90, archive_days = null, archive_class = null }
    models  = { ia_days = null, archive_days = null, archive_class = null }
    images  = { ia_days = 90, archive_days = 365, archive_class = "GLACIER" }
  }
}

data "aws_iam_policy_document" "kms" {
  statement {
    sid       = "AccountAdministration"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${local.account_id}:root"]
    }
  }
}

resource "aws_kms_key" "datalake" {
  description             = "Chiffrement du lac de données ${var.name_prefix}"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy                  = data.aws_iam_policy_document.kms.json
  tags                    = var.tags
}

resource "aws_kms_alias" "datalake" {
  name          = "alias/${var.name_prefix}-datalake"
  target_key_id = aws_kms_key.datalake.key_id
}

resource "aws_s3_bucket" "zone" {
  for_each = local.zones

  #checkov:skip=CKV_AWS_144:Réplication inter-régions non retenue (une seule région, contrainte de souveraineté) ; reprise via le versionnage.
  #checkov:skip=CKV2_AWS_62:Aucun consommateur d'événements S3 à ce stade.
  #checkov:skip=CKV_AWS_18:Journalisation des accès par les événements de données CloudTrail, activés au niveau du compte.
  bucket        = "${var.name_prefix}-${each.key}-${local.account_id}"
  force_destroy = false
  tags          = merge(var.tags, { zone = each.key })
}

resource "aws_s3_bucket_ownership_controls" "zone" {
  for_each = aws_s3_bucket.zone

  bucket = each.value.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "zone" {
  for_each = aws_s3_bucket.zone

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "zone" {
  for_each = aws_s3_bucket.zone

  bucket = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "zone" {
  for_each = aws_s3_bucket.zone

  bucket = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.datalake.arn
    }
    bucket_key_enabled = true
  }
}

data "aws_iam_policy_document" "tls_only" {
  for_each = aws_s3_bucket.zone

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [each.value.arn, "${each.value.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid       = "DenyOutdatedTls"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [each.value.arn, "${each.value.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "NumericLessThan"
      variable = "s3:TlsVersion"
      values   = ["1.2"]
    }
  }
}

resource "aws_s3_bucket_policy" "zone" {
  for_each = aws_s3_bucket.zone

  bucket = each.value.id
  policy = data.aws_iam_policy_document.tls_only[each.key].json

  depends_on = [aws_s3_bucket_public_access_block.zone]
}

resource "aws_s3_bucket_lifecycle_configuration" "zone" {
  for_each = local.zones

  bucket = aws_s3_bucket.zone[each.key].id

  rule {
    id     = "tiering-and-cleanup"
    status = "Enabled"

    filter {}

    dynamic "transition" {
      for_each = each.value.ia_days == null ? [] : [each.value.ia_days]
      content {
        days          = transition.value
        storage_class = "STANDARD_IA"
      }
    }

    dynamic "transition" {
      for_each = each.value.archive_days == null ? [] : [each.value.archive_days]
      content {
        days          = transition.value
        storage_class = each.value.archive_class
      }
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.zone]
}
