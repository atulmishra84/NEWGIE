# Technology Stack — GIE Context Intelligence

## Runtime

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.12+ |
| API framework | FastAPI | ≥0.115 |
| ASGI server | Uvicorn | ≥0.30 |
| Task queue | Celery + Redis | 5.4 / 7.x |
| Validation | Pydantic v2 | ≥2.8 |
| ORM | SQLAlchemy (async) | ≥2.0 |

## Shared Packages

| Package | Purpose |
|---------|---------|
| `gie-contracts` | Context Model schema, events, sources |
| `gie-observability` | Logging, tracing, metrics |
| `gie-security` | Auth utilities (planned) |

## Data Stores

| Store | Technology | Use case |
|-------|------------|----------|
| Primary DB | PostgreSQL 16 | Scans, models, outbox |
| Cache / Queue | Redis 7 | Celery broker, response cache |
| Graph | Neo4j 5 Community | Relationship queries |
| Vectors | Qdrant 1.12 | Prompt embeddings |
| Events | Kafka 3.7 (KRaft) | Domain events |

## Observability

| Concern | Tool |
|---------|------|
| Logs | structlog → JSON stdout |
| Traces | OpenTelemetry → OTLP |
| Metrics | prometheus-client → `/metrics` |
| Dashboards | Grafana (recommended) |

## Infrastructure

| Layer | Tool |
|-------|------|
| Containers | Docker |
| Orchestration | Kubernetes |
| Packaging | Helm 3 |
| IaC | Terraform (AWS) |
| CI/CD | GitHub Actions |
| Registry | GHCR |

## Development Tools

| Tool | Purpose |
|------|---------|
| pytest | Unit, integration, contract tests |
| ruff | Lint + format |
| mypy | Type checking |
| openapi-spec-validator | API contract validation |
| locust | Load testing (optional) |

## Cloud Services (production)

| Service | AWS equivalent |
|---------|------------------|
| PostgreSQL | RDS PostgreSQL 16 |
| Redis | ElastiCache Redis 7 |
| Secrets | Secrets Manager |
| Ingress TLS | ACM + ALB |
| Container registry | ECR or GHCR |

Neo4j, Qdrant, and Kafka are deployed via Helm charts or managed offerings (MSK, Confluent Cloud) depending on environment.

## API Contract

- OpenAPI 3.1: `docs/api/openapi.yaml`
- Response envelope: `ObservabilityEnvelope[T]`
- Schema version: `gie.context.v1`
