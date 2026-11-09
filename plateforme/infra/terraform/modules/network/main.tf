# Réseau : VPC sur 2 ou 3 zones, sous-réseaux privés pour les nœuds EKS, publics pour les répartiteurs
# de charge uniquement, NAT, journaux de flux et points de terminaison VPC (S3, ECR, STS, Secrets Manager)
# pour que le trafic AWS ne sorte pas par le NAT (coût et surface d'exposition).

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  # /16 découpé : sous-réseaux privés /20 (index 0..n), publics /24 à partir de l'index 48 (10.x.48.0/24 ...).
  private_subnets = [for index, _ in local.azs : cidrsubnet(var.vpc_cidr, 4, index)]
  public_subnets  = [for index, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, 48 + index)]

  interface_endpoints = var.enable_interface_endpoints ? {
    ecr_api        = "ecr.api"
    ecr_dkr        = "ecr.dkr"
    sts            = "sts"
    secretsmanager = "secretsmanager"
  } : {}
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.16.0"

  name = var.name
  cidr = var.vpc_cidr
  azs  = local.azs

  private_subnets = local.private_subnets
  public_subnets  = local.public_subnets

  enable_nat_gateway     = true
  single_nat_gateway     = var.single_nat_gateway
  one_nat_gateway_per_az = !var.single_nat_gateway

  enable_dns_hostnames    = true
  enable_dns_support      = true
  map_public_ip_on_launch = false

  # Groupe de sécurité par défaut vidé : aucune ressource ne doit s'y rattacher par accident.
  manage_default_security_group  = true
  default_security_group_ingress = []
  default_security_group_egress  = []

  enable_flow_log                                 = true
  create_flow_log_cloudwatch_log_group            = true
  create_flow_log_cloudwatch_iam_role             = true
  flow_log_max_aggregation_interval               = 60
  flow_log_cloudwatch_log_group_retention_in_days = var.flow_log_retention_days

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = var.tags
}

module "vpc_endpoints" {
  source  = "terraform-aws-modules/vpc/aws//modules/vpc-endpoints"
  version = "5.16.0"

  vpc_id = module.vpc.vpc_id

  create_security_group      = var.enable_interface_endpoints
  security_group_name_prefix = "${var.name}-vpce-"
  security_group_description = "Points de terminaison VPC : HTTPS depuis le VPC uniquement"
  security_group_rules = {
    ingress_https = {
      description = "HTTPS depuis le VPC"
      cidr_blocks = [module.vpc.vpc_cidr_block]
    }
  }

  endpoints = merge(
    {
      # Point de terminaison passerelle S3 : gratuit, évite le NAT pour le lac de données et les couches ECR.
      s3 = {
        service         = "s3"
        service_type    = "Gateway"
        route_table_ids = module.vpc.private_route_table_ids
        tags            = { Name = "${var.name}-s3" }
      }
    },
    {
      for key, service in local.interface_endpoints : key => {
        service             = service
        private_dns_enabled = true
        subnet_ids          = module.vpc.private_subnets
        tags                = { Name = "${var.name}-${key}" }
      }
    }
  )

  tags = var.tags
}
