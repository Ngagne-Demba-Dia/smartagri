# Registre d'images : une seule copie partagée (créée dans le compte de production), lue par les autres
# comptes. Principe « construire une fois, déployer partout » : le même condensat passe de staging à prod.
# Étiquettes immuables, analyse de vulnérabilités à l'envoi, chiffrement KMS (clé gérée aws/ecr,
# compatible avec le tirage inter-comptes).

resource "aws_ecr_repository" "this" {
  for_each = toset(var.repositories)

  name                 = each.value
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each = aws_ecr_repository.this

  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Images non étiquetées supprimées après 14 jours"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 14
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Conserver les ${var.keep_images} artefacts étiquetés les plus récents"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.keep_images
        }
        action = { type = "expire" }
      }
    ]
  })
}

data "aws_iam_policy_document" "cross_account_pull" {
  count = length(var.pull_account_ids) > 0 ? 1 : 0

  statement {
    sid = "CrossAccountPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]

    principals {
      type        = "AWS"
      identifiers = [for account_id in var.pull_account_ids : "arn:aws:iam::${account_id}:root"]
    }
  }
}

resource "aws_ecr_repository_policy" "cross_account_pull" {
  for_each = length(var.pull_account_ids) > 0 ? aws_ecr_repository.this : {}

  repository = each.value.name
  policy     = data.aws_iam_policy_document.cross_account_pull[0].json
}
