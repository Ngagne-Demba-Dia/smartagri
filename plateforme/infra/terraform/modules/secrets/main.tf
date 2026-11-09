# Conteneurs de secrets AWS Secrets Manager, lus dans le cluster par External Secrets Operator.
#
# Terraform crée les conteneurs (nom, clé KMS, politique) mais PAS les valeurs applicatives :
#  - une valeur gérée par Terraform finit en clair dans l'état et parfois dans la sortie de plan, donc
#    lisible par quiconque accède au backend d'état ou aux journaux de CI ;
#  - la rotation (fuite, départ d'un membre) se fait sans plan ni revue d'infrastructure.
# Les valeurs sont posées hors bande par un opérateur habilité (voir infra/terraform/README.md).
#
# Exception optionnelle : DATABASE_URL et MIGRATION_DATABASE_URL peuvent être écrites par Terraform
# (set_database_url_secret = true) quand la base est créée dans la même pile ; elles sont alors présentes,
# chiffrées, dans l'état S3. Terraform possède alors tout le JSON du secret : les deux URL sont exigées,
# sinon une propriété posée hors bande serait effacée à l'application suivante.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_iam_policy_document" "kms" {
  statement {
    sid       = "AccountAdministration"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
}

resource "aws_kms_key" "secrets" {
  description             = "Chiffrement des secrets ${var.name_prefix}"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy                  = data.aws_iam_policy_document.kms.json
  tags                    = var.tags
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.name_prefix}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_secretsmanager_secret" "app" {
  #checkov:skip=CKV2_AWS_57:Rotation manuelle documentée (secrets applicatifs sans fonction de rotation Lambda).
  name                    = "${var.name_prefix}/app"
  description             = "JSON : JWT_SECRET, DEVICE_KEY_PEPPER, ANTHROPIC_API_KEY, MQTT_USERNAME, MQTT_PASSWORD. Valeurs posées hors Terraform."
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = var.tags
}

resource "aws_secretsmanager_secret" "database" {
  #checkov:skip=CKV2_AWS_57:Rotation portée par le fournisseur de base (Timescale Cloud ou opérateur PostgreSQL).
  name                    = "${var.name_prefix}/database"
  description             = "JSON : DATABASE_URL (rôle de l'API, postgresql+psycopg://...) et MIGRATION_DATABASE_URL (rôle propriétaire du schéma, postgresql://..., lu seulement par le Job de migration)."
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = var.tags
}

resource "aws_secretsmanager_secret" "ml" {
  #checkov:skip=CKV2_AWS_57:Clé d'API OctOpus renouvelée auprès du fournisseur, rotation manuelle documentée.
  name                    = "${var.name_prefix}/ml"
  description             = "JSON : OCTOPUS_API_KEY, MLFLOW_BACKEND_STORE_URI, AGRIML_PSEUDO_SALT, AGRIML_PSEUDO_SALT_ID (sel de pseudonymisation des instantanés OctOpus). Valeurs posées hors Terraform."
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = var.recovery_window_in_days
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "database" {
  count = var.set_database_url_secret ? 1 : 0

  secret_id     = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    DATABASE_URL           = var.database_url
    MIGRATION_DATABASE_URL = var.migration_database_url
  })

  lifecycle {
    precondition {
      condition     = length(coalesce(var.database_url, "")) > 0
      error_message = "set_database_url_secret = true exige la variable sensible database_url."
    }
    precondition {
      condition     = length(coalesce(var.migration_database_url, "")) > 0
      error_message = "set_database_url_secret = true exige la variable sensible migration_database_url (Job de migration)."
    }
  }
}
