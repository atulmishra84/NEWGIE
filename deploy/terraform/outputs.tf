output "vpc_id" {
  description = "VPC ID hosting Context Intelligence data plane"
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for EKS/RDS/ElastiCache"
  value       = module.network.private_subnet_ids
}

output "app_security_group_id" {
  description = "Security group for Context Intelligence workloads"
  value       = module.network.app_security_group_id
}

output "postgres_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = module.postgres.endpoint
  sensitive   = true
}

output "postgres_connection_string_template" {
  description = "Async SQLAlchemy connection string template — inject password from Secrets Manager"
  value       = module.postgres.connection_string_template
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.redis.primary_endpoint
}

output "redis_connection_url" {
  description = "Redis URL for Celery broker and cache"
  value       = module.redis.connection_url
  sensitive   = true
}

output "postgres_secret_arn" {
  description = "Secrets Manager ARN for RDS master credentials"
  value       = module.postgres.secret_arn
}
