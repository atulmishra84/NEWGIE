variable "aws_region" {
  description = "AWS region for GIE Context Intelligence infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be dev, staging, or production"
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "AZs for multi-AZ subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "postgres_instance_class" {
  description = "RDS instance class for PostgreSQL"
  type        = string
  default     = "db.t4g.medium"
}

variable "postgres_allocated_storage_gb" {
  description = "Initial allocated storage for RDS (GB)"
  type        = number
  default     = 50
}

variable "postgres_database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "gie_context"
}

variable "postgres_master_username" {
  description = "RDS master username"
  type        = string
  default     = "gie_admin"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.small"
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}
