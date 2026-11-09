# Cluster EKS : plan de contrôle chiffré (KMS sur les Secrets Kubernetes), journaux d'audit,
# authentification par entrées d'accès (pas de ConfigMap aws-auth), IRSA, nœuds gérés AL2023 en
# sous-réseaux privés, IMDSv2 obligatoire avec un seul saut (les pods n'atteignent pas l'IMDS du nœud).

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.31.6"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id                   = var.vpc_id
  subnet_ids               = var.private_subnet_ids
  control_plane_subnet_ids = var.private_subnet_ids

  cluster_endpoint_private_access      = true
  cluster_endpoint_public_access       = var.endpoint_public_access
  cluster_endpoint_public_access_cidrs = var.endpoint_public_access_cidrs

  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = false
  access_entries = {
    for index, arn in var.admin_role_arns : "admin-${index}" => {
      principal_arn = arn
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  enable_irsa = true

  cluster_enabled_log_types              = ["api", "audit", "authenticator"]
  cloudwatch_log_group_retention_in_days = var.log_retention_days

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent    = true
      before_compute = true
      # Active l'application des NetworkPolicies par le CNI VPC (infra/k8s/base/networkpolicies.yaml).
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }
  }

  eks_managed_node_groups = {
    general = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      metadata_options = {
        http_endpoint               = "enabled"
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = var.node_disk_size_gb
            volume_type           = "gp3"
            encrypted             = true
            delete_on_termination = true
          }
        }
      }

      labels = {
        workload = "general"
      }
    }
  }

  tags = var.tags
}
