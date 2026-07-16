# GIE Context Intelligence — Terraform

Provisions AWS networking, RDS PostgreSQL, and ElastiCache Redis for the Context Intelligence Agent data plane.

## Prerequisites

- Terraform >= 1.6
- AWS credentials with permissions for VPC, RDS, ElastiCache, Secrets Manager
- S3 bucket `gie-terraform-state` and DynamoDB table `gie-terraform-lock` for remote state

## Usage

```bash
cd deploy/terraform
terraform init
terraform workspace select dev || terraform workspace new dev
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"
```

## Modules

| Module | Purpose |
|--------|---------|
| `network` | VPC, public/private subnets, app security group |
| `postgres` | RDS PostgreSQL 16 with Secrets Manager credentials |
| `redis` | ElastiCache Redis 7 replication group |

## Outputs

After apply, wire these into Kubernetes secrets or External Secrets Operator:

- `postgres_connection_string_template` — inject password from `postgres_secret_arn`
- `redis_connection_url` — TLS-enabled Redis URL for Celery and cache

## Environment sizing

| Variable | dev default | production recommendation |
|----------|-------------|---------------------------|
| `postgres_instance_class` | db.t4g.medium | db.r6g.large |
| `redis_node_type` | cache.t4g.small | cache.r6g.large |

Neo4j, Qdrant, and Kafka are deployed separately (Helm or managed services) and are not included in this Terraform stack.
