terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket         = "gie-terraform-state"
    key            = "context-intelligence/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "gie-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "gie"
      Component   = "context-intelligence"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "network" {
  source = "./modules/network"

  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

module "postgres" {
  source = "./modules/postgres"

  environment             = var.environment
  vpc_id                  = module.network.vpc_id
  private_subnet_ids      = module.network.private_subnet_ids
  allowed_security_groups = [module.network.app_security_group_id]
  instance_class          = var.postgres_instance_class
  allocated_storage_gb    = var.postgres_allocated_storage_gb
  database_name           = var.postgres_database_name
  master_username         = var.postgres_master_username
}

module "redis" {
  source = "./modules/redis"

  environment             = var.environment
  vpc_id                  = module.network.vpc_id
  private_subnet_ids      = module.network.private_subnet_ids
  allowed_security_groups = [module.network.app_security_group_id]
  node_type               = var.redis_node_type
  engine_version          = var.redis_engine_version
}
