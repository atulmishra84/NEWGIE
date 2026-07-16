# Guardrails Intelligence Engine (GIE)

Enterprise multi-agent platform that analyzes AI applications and produces normalized context, risk, policy, compliance, and deployment recommendations.

## Overview

GIE scans AI application codebases, runtime environments, and cloud resources to build a **Context Model** (`gie.context.v1`) — a structured, evidence-backed representation of frameworks, models, prompts, MCP servers, secrets (fingerprinted), and deployment topology.

The first agent in the platform is **Context Intelligence**, responsible for discovery and normalization. Downstream agents consume its output for risk scoring, policy evaluation, and compliance reporting.

## Repository Structure

```
GIE/
├── agents/context-intelligence/   # Context Intelligence Agent (API, workers, scanners)
├── packages/                      # Shared libraries (contracts, observability, security)
├── deploy/                        # Kubernetes, Helm, Terraform
├── docs/                          # Architecture, API, security, performance
└── docker-compose.yml             # Local full stack
```

See [FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) for the complete layout.

## Agents

| Agent | Status | Capability |
|-------|--------|------------|
| **Context Intelligence** | Active | Scan AI projects → normalized Context Model (`gie.context.v1`) |
| Risk Assessment | Planned | Consume context models for threat scoring |
| Policy Engine | Planned | Evaluate policies against detected capabilities |
| Compliance | Planned | Map findings to regulatory frameworks |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- (Optional) [uv](https://github.com/astral-sh/uv) for faster installs

### Local Stack

Start PostgreSQL, Redis, Neo4j, Qdrant, Kafka, API, and Celery worker:

```bash
docker compose up -d
```

Verify health:

```bash
curl http://localhost:8080/healthz
```

### Install Agent (development)

```bash
cd agents/context-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
```

### Run API Locally

```bash
uvicorn context_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8080 --reload
```

### CLI Scan

```bash
gie-context scan /path/to/ai-project --output context-model.json --tenant acme
```

### Run Tests

```bash
cd agents/context-intelligence
pytest tests/ -v
```

## API

REST API documented in [docs/api/openapi.yaml](docs/api/openapi.yaml).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/scans` | POST | Create scan (async via Celery) |
| `/v1/scans/{scan_id}` | GET | Scan status |
| `/v1/context-models/{model_id}` | GET | Retrieve context model |
| `/healthz` | GET | Liveness probe |
| `/ready` | GET | Readiness (DB, Redis, Neo4j, Qdrant) |
| `/metrics` | GET | Prometheus metrics |

Authentication: Bearer JWT or `X-API-Key` header. See [SECURITY.md](docs/SECURITY.md).

Example (JWT with write role):

```bash
curl -X POST http://localhost:8080/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":{"type":"folder","path":"/workspace/my-ai-app"}}'
```

## Deployment

| Method | Path | Description |
|--------|------|-------------|
| Kubernetes | [deploy/k8s/](deploy/k8s/) | Deployment, Service, ConfigMap, Secret, HPA, ServiceMonitor |
| Helm | [deploy/helm/context-intelligence/](deploy/helm/context-intelligence/) | Parameterized chart with ingress and autoscaling |
| Terraform | [deploy/terraform/](deploy/terraform/) | AWS VPC, RDS PostgreSQL, ElastiCache Redis |

```bash
# Helm
helm upgrade --install context-intelligence deploy/helm/context-intelligence \
  --namespace gie --create-namespace

# Terraform
cd deploy/terraform && terraform init && terraform apply -var="environment=dev"
```

## CI/CD

| Workflow | Trigger | Jobs |
|----------|---------|------|
| [ci.yml](.github/workflows/ci.yml) | Push/PR to main | Lint, test, Docker build, Helm lint, Terraform validate |
| [release.yml](.github/workflows/release.yml) | Tag `v*.*.*` | Build/push GHCR image, package Helm chart, GitHub Release |

## Documentation

| Document | Description |
|----------|-------------|
| [Agent.md](docs/Agent.md) | Context Intelligence Agent specification |
| [Architecture.md](docs/Architecture.md) | Clean/hexagonal architecture, DDD, CQRS, events |
| [DATABASE.md](docs/DATABASE.md) | PostgreSQL, Neo4j, Qdrant, Redis, events |
| [SECURITY.md](docs/SECURITY.md) | Authn/z, RBAC, mTLS, secrets |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | STRIDE threat analysis |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | SLOs and capacity planning |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology choices |
| [FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) | Repository layout |
| [API](docs/api/openapi.yaml) | OpenAPI 3.1 specification |
| [Sequence diagram](docs/diagrams/sequence-scan.md) | Scan flow |
| [Class diagram](docs/diagrams/class-diagram.md) | Domain model |

## Data Stores (Local)

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Scans, models, outbox |
| Redis | 6379 | Cache, Celery broker |
| Neo4j | 7474/7687 | Graph relationships |
| Qdrant | 6333 | Evidence vectors |
| Kafka | 9092 | Domain events |

Schema: [schema.sql](agents/context-intelligence/infrastructure/persistence/schema.sql)

## Secret Handling

The agent **fingerprints** detected secrets (SHA-256 with pepper) and never stores or returns raw values. See `domain/secrets_detector.py` and integration tests in `tests/integration/test_folder_scan.py`.

## License

Apache-2.0
