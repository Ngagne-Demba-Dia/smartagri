# Rôles IAM à moindre privilège.
#  - IRSA : chaque ServiceAccount Kubernetes obtient un rôle distinct, assumable uniquement par ce
#    ServiceAccount précis (conditions :sub et :aud). Namespace applicatif : api, ingestor,
#    external-secrets-reader. Namespace ML : ml-jobs, inference, mlflow, external-secrets-reader.
#  - GitHub Actions (OIDC, sans clé longue durée) : rôle de publication ECR limité au dépôt GitHub et à
#    l'environnement de déploiement ; l'environnement GitHub n'autorise que la branche main.

locals {
  # Clé du rôle => "namespace:ServiceAccount" autorisé à l'assumer.
  service_accounts = {
    api                 = "${var.namespace}:agri-api"
    ingestor            = "${var.namespace}:agri-ingestor"
    external-secrets    = "${var.namespace}:external-secrets-reader"
    ml-jobs             = "${var.ml_namespace}:agri-ml-jobs"
    inference           = "${var.ml_namespace}:agri-inference"
    mlflow              = "${var.ml_namespace}:agri-mlflow"
    external-secrets-ml = "${var.ml_namespace}:external-secrets-reader"
  }

  github_oidc_url = "token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "irsa_assume" {
  for_each = local.service_accounts

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider}:sub"
      values   = ["system:serviceaccount:${each.value}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "irsa" {
  for_each = local.service_accounts

  name                 = "${var.name_prefix}-${each.key}"
  assume_role_policy   = data.aws_iam_policy_document.irsa_assume[each.key].json
  max_session_duration = 3600
  tags                 = var.tags
}

# --- api : photos de feuilles (diagnostic) dans le compartiment images ---
data "aws_iam_policy_document" "api" {
  statement {
    sid       = "ImagesReadWrite"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${var.bucket_arns["images"]}/*"]
  }

  statement {
    sid       = "DatalakeKms"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.datalake_kms_key_arn]
  }
}

# --- ingestor : archive des messages bruts sous raw/telemetry/ (écriture seule) ---
data "aws_iam_policy_document" "ingestor" {
  statement {
    sid       = "RawTelemetryWrite"
    actions   = ["s3:PutObject"]
    resources = ["${var.bucket_arns["raw"]}/telemetry/*"]
  }

  statement {
    sid       = "DatalakeKms"
    actions   = ["kms:GenerateDataKey"]
    resources = [var.datalake_kms_key_arn]
  }
}

# --- ml-jobs : lit raw/curated/images, écrit curated/models (réentraînement, dérive) ---
data "aws_iam_policy_document" "ml_jobs" {
  statement {
    sid     = "ListZones"
    actions = ["s3:ListBucket"]
    resources = [
      var.bucket_arns["raw"],
      var.bucket_arns["curated"],
      var.bucket_arns["models"],
      var.bucket_arns["images"],
    ]
  }

  statement {
    sid     = "ReadInputs"
    actions = ["s3:GetObject"]
    resources = [
      "${var.bucket_arns["raw"]}/*",
      "${var.bucket_arns["curated"]}/*",
      "${var.bucket_arns["images"]}/*",
      "${var.bucket_arns["models"]}/*",
    ]
  }

  statement {
    sid     = "WriteOutputs"
    actions = ["s3:PutObject"]
    resources = [
      "${var.bucket_arns["curated"]}/*",
      "${var.bucket_arns["models"]}/*",
    ]
  }

  statement {
    sid       = "DatalakeKms"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.datalake_kms_key_arn]
  }
}

# --- external-secrets-reader : lecture des deux secrets de l'environnement, rien d'autre ---
data "aws_iam_policy_document" "external_secrets" {
  statement {
    sid       = "ReadEnvironmentSecrets"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = var.secret_arns
  }

  statement {
    sid       = "SecretsKms"
    actions   = ["kms:Decrypt"]
    resources = [var.secrets_kms_key_arn]
  }
}

# --- inference : lecture seule des paquets de modèles ---
data "aws_iam_policy_document" "inference" {
  statement {
    sid       = "ReadModelBundles"
    actions   = ["s3:GetObject"]
    resources = ["${var.bucket_arns["models"]}/bundles/*"]
  }

  statement {
    sid       = "DatalakeKms"
    actions   = ["kms:Decrypt"]
    resources = [var.datalake_kms_key_arn]
  }
}

# --- mlflow : artefacts d'expériences sous models/mlflow/ uniquement ---
data "aws_iam_policy_document" "mlflow" {
  statement {
    sid       = "ListMlflowPrefix"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arns["models"]]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["mlflow/*"]
    }
  }

  statement {
    sid       = "MlflowArtifacts"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${var.bucket_arns["models"]}/mlflow/*"]
  }

  statement {
    sid       = "DatalakeKms"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [var.datalake_kms_key_arn]
  }
}

# --- external-secrets-reader du namespace ML : uniquement le secret <prefix>/ml ---
data "aws_iam_policy_document" "external_secrets_ml" {
  statement {
    sid       = "ReadMlSecrets"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = var.ml_secret_arns
  }

  statement {
    sid       = "SecretsKms"
    actions   = ["kms:Decrypt"]
    resources = [var.secrets_kms_key_arn]
  }
}

locals {
  irsa_policies = {
    api                 = data.aws_iam_policy_document.api.json
    ingestor            = data.aws_iam_policy_document.ingestor.json
    external-secrets    = data.aws_iam_policy_document.external_secrets.json
    ml-jobs             = data.aws_iam_policy_document.ml_jobs.json
    inference           = data.aws_iam_policy_document.inference.json
    mlflow              = data.aws_iam_policy_document.mlflow.json
    external-secrets-ml = data.aws_iam_policy_document.external_secrets_ml.json
  }
}

resource "aws_iam_role_policy" "irsa" {
  for_each = local.irsa_policies

  name   = "${var.name_prefix}-${each.key}"
  role   = aws_iam_role.irsa[each.key].id
  policy = each.value
}

# --- GitHub Actions : publication d'images dans ECR (compte qui porte le registre) ---
resource "aws_iam_openid_connect_provider" "github" {
  count = var.github_repository != null && var.create_github_oidc_provider ? 1 : 0

  url             = "https://${local.github_oidc_url}"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
  tags            = var.tags
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.github_repository != null && !var.create_github_oidc_provider ? 1 : 0

  url = "https://${local.github_oidc_url}"
}

locals {
  github_oidc_provider_arn = var.github_repository == null ? null : (
    var.create_github_oidc_provider
    ? aws_iam_openid_connect_provider.github[0].arn
    : data.aws_iam_openid_connect_provider.github[0].arn
  )
}

data "aws_iam_policy_document" "github_assume" {
  count = var.github_repository == null ? 0 : 1

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_url}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_url}:sub"
      values   = ["repo:${var.github_repository}:environment:${var.github_push_environment}"]
    }
  }
}

data "aws_iam_policy_document" "github_ecr_push" {
  count = var.github_repository == null ? 0 : 1

  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = var.ecr_repository_arns
  }
}

resource "aws_iam_role" "github_ecr_push" {
  count = var.github_repository == null ? 0 : 1

  name                 = "${var.name_prefix}-github-ecr-push"
  assume_role_policy   = data.aws_iam_policy_document.github_assume[0].json
  max_session_duration = 3600
  tags                 = var.tags
}

resource "aws_iam_role_policy" "github_ecr_push" {
  count = var.github_repository == null ? 0 : 1

  name   = "${var.name_prefix}-github-ecr-push"
  role   = aws_iam_role.github_ecr_push[0].id
  policy = data.aws_iam_policy_document.github_ecr_push[0].json
}
