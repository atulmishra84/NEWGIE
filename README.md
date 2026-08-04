# Guardrails Intelligence Engine (GIE)

Enterprise multi-agent platform that analyzes AI applications and produces normalized context, risk, policy, compliance, and deployment recommendations.

## Overview

GIE scans AI application codebases, runtime environments, and cloud resources to build a **Context Model** (`gie.context.v1`) — a structured, evidence-backed representation of frameworks, models, prompts, MCP servers, secrets (fingerprinted), and deployment topology.

**Context Intelligence** discovers and normalizes application context. **Knowledge Intelligence** is the platform brain — a versioned knowledge graph (OWASP LLM, MITRE ATLAS, NIST AI RMF, compliance frameworks, attacks, guardrails) with explainable semantic retrieval.

## Repository Structure

```
GIE/
├── agents/context-intelligence/   # Context Intelligence Agent (API, workers, scanners)
├── agents/knowledge-intelligence/ # Knowledge Intelligence Agent (graph brain)
├── agents/policy-intelligence/    # Policy Intelligence Agent (guardrail policies)
├── agents/risk-intelligence/      # Risk Intelligence Agent (AI risk posture)
├── agents/compliance-intelligence/ # Compliance Intelligence Agent (regs & gaps)
├── agents/recommendation-intelligence/ # Recommendation Agent (prioritized actions)
├── agents/policy-generator/       # Policy Generator Agent (deployment-ready policies)
├── agents/explainability-intelligence/ # Explainability Agent (decision narratives)
├── agents/validation-intelligence/ # Validation Agent (pre-deploy policy checks)
├── agents/learning-intelligence/  # Learning Agent (feedback loop & knowledge proposals)
├── agents/integration-intelligence/ # Integration Agent (enterprise platforms)
├── agents/orchestrator/           # Orchestrator Agent (unified pipeline)
├── agents/chief-orchestrator/     # Full+GIE front door (text + voice + command console)
├── agents/risk-assessment/        # Risk scoring agent
├── agents/policy-engine/          # Deploy allow/deny policy agent
├── packages/                      # Shared libraries (contracts, observability, security)
├── deploy/                        # Kubernetes, Helm, Terraform, Azure sandbox
├── docs/                          # Architecture, API, security, performance
├── frontend/command-console/      # Simple command UI (served by chief-orchestrator)
├── web/                           # Landing page + Orchestrator dashboard (static)
├── docker-compose.yml             # Local full stack / Context Intelligence
└── docker-compose.full-gie.yml    # Full+GIE one-shot overlay
```

See [FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) and [FULL_GIE_FLEET.md](docs/FULL_GIE_FLEET.md).

Azure sandbox (full mesh + data plane, or minimal Orchestrator): [deploy/azure/README.md](deploy/azure/README.md).

Web UI (landing + dashboard): [web/README.md](web/README.md).

Command Console (chief-orchestrator): [docs/COMMAND_CONSOLE.md](docs/COMMAND_CONSOLE.md).

## Agents

| Agent | Status | Capability |
|-------|--------|------------|
| **Chief Orchestrator** | Active | Text+voice command surface; runs Full+GIE lanes |
| **Context Intelligence** | Active | Scan AI projects → normalized Context Model (`gie.context.v1`) |
| **Knowledge Intelligence** | Active | Versioned knowledge graph + explainable retrieval (`gie.knowledge.v1`) |
| **Policy Intelligence** | Active | Guardrail selection + deployment-ready policies (`gie.policy.v1`) |
| **Risk Intelligence** | Active | AI risk posture scoring + remediations (`gie.risk.v1`) |
| **Compliance Intelligence** | Active | Regulatory applicability, gaps, evidence (`gie.compliance.v1`) |
| **Recommendation Intelligence** | Active | Prioritized security recommendations (`gie.recommendation.v1`) |
| **Policy Generator** | Active | Recommendations → deployment-ready policies (`gie.policygen.v1`) |
| **Explainability Intelligence** | Active | Multi-audience decision explanations (`gie.explainability.v1`) |
| **Validation Intelligence** | Active | Pre-deploy policy validation + simulation (`gie.validation.v1`) |
| **Learning Intelligence** | Active | Feedback-driven recommendation improvement (`gie.learning.v1`) |
| **Integration Intelligence** | Active | Enterprise platform connectors & webhooks (`gie.integration.v1`) |
| **Orchestrator** | Active | Coordinates all agents via unified `/analyze` (`gie.orchestrator.v1`) |
| **Risk Assessment** | Active | Score risk from context + findings |
| **Policy Engine** | Active | Allow/deny deploy decisions |
| Delivery / Security / Release-Ops roles | Active (fleet registry) | PM, UX, Dev, AppSec, Vuln, SecTest, Compliance, QA, Release, DevOps, SRE, Docs |

### Full+GIE one-shot (live staging)

```bash
./scripts/oneshot_deploy.sh
python scripts/live_test_full_gie.py
```

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

### Knowledge Intelligence Agent

```bash
cd agents/knowledge-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn knowledge_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8081 --reload

# CLI explainable query
gie-knowledge query "prompt injection mitigations" --top-k 5
```

Docs: [docs/knowledge/Agent.md](docs/knowledge/Agent.md) · OpenAPI: [docs/api/openapi-knowledge.yaml](docs/api/openapi-knowledge.yaml)

```bash
curl -s http://localhost:8081/healthz
curl -s -X POST http://localhost:8081/v1/knowledge/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"OWASP LLM prompt injection","top_k":5}'
```

### Policy Intelligence Agent

```bash
cd agents/policy-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn policy_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8082 --reload
```

Docs: [docs/policy/Agent.md](docs/policy/Agent.md) · OpenAPI: [docs/api/openapi-policy.yaml](docs/api/openapi-policy.yaml)

### Risk Intelligence Agent

```bash
cd agents/risk-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn risk_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8083 --reload
```

Docs: [docs/risk/Agent.md](docs/risk/Agent.md) · OpenAPI: [docs/api/openapi-risk.yaml](docs/api/openapi-risk.yaml)

### Compliance Intelligence Agent

```bash
cd agents/compliance-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn compliance_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8084 --reload
```

Docs: [docs/compliance/Agent.md](docs/compliance/Agent.md) · OpenAPI: [docs/api/openapi-compliance.yaml](docs/api/openapi-compliance.yaml)

### Recommendation Intelligence Agent

```bash
cd agents/recommendation-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn recommendation_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8085 --reload
```

Docs: [docs/recommendation/Agent.md](docs/recommendation/Agent.md) · OpenAPI: [docs/api/openapi-recommendation.yaml](docs/api/openapi-recommendation.yaml)

### Policy Generator Agent

```bash
cd agents/policy-generator
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn policy_generator.adapters.rest.app:app --host 0.0.0.0 --port 8086 --reload
```

Docs: [docs/policy-generator/Agent.md](docs/policy-generator/Agent.md) · OpenAPI: [docs/api/openapi-policy-generator.yaml](docs/api/openapi-policy-generator.yaml)

### Explainability Intelligence Agent

```bash
cd agents/explainability-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn explainability_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8087 --reload
```

Docs: [docs/explainability/Agent.md](docs/explainability/Agent.md) · OpenAPI: [docs/api/openapi-explainability.yaml](docs/api/openapi-explainability.yaml)

### Validation Intelligence Agent

```bash
cd agents/validation-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn validation_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8088 --reload
```

Docs: [docs/validation/Agent.md](docs/validation/Agent.md) · OpenAPI: [docs/api/openapi-validation.yaml](docs/api/openapi-validation.yaml)

### Learning Intelligence Agent

```bash
cd agents/learning-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn learning_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8089 --reload
```

Docs: [docs/learning/Agent.md](docs/learning/Agent.md) · OpenAPI: [docs/api/openapi-learning.yaml](docs/api/openapi-learning.yaml)

### Integration Intelligence Agent

```bash
cd agents/integration-intelligence
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn integration_intelligence.adapters.rest.app:app --host 0.0.0.0 --port 8090 --reload
```

Docs: [docs/integration/Agent.md](docs/integration/Agent.md) · OpenAPI: [docs/api/openapi-integration.yaml](docs/api/openapi-integration.yaml)

### Orchestrator Agent

```bash
cd agents/orchestrator
pip install -e "../../packages/gie-contracts" "../../packages/gie-observability" "../../packages/gie-security"
pip install -e ".[dev]"
uvicorn orchestrator.adapters.rest.app:app --host 0.0.0.0 --port 8091 --reload
```

Docs: [docs/orchestrator/Agent.md](docs/orchestrator/Agent.md) · Architecture: [docs/orchestrator/Architecture.md](docs/orchestrator/Architecture.md) · OpenAPI: [docs/api/openapi-orchestrator.yaml](docs/api/openapi-orchestrator.yaml)

### Run Tests

```bash
cd agents/context-intelligence && pytest tests/ -v
cd ../knowledge-intelligence && pytest tests/ -v
cd ../policy-intelligence && pytest tests/ -v
cd ../risk-intelligence && pytest tests/ -v
cd ../compliance-intelligence && pytest tests/ -v
cd ../recommendation-intelligence && pytest tests/ -v
cd ../policy-generator && pytest tests/ -v
cd ../explainability-intelligence && pytest tests/ -v
cd ../validation-intelligence && pytest tests/ -v
cd ../learning-intelligence && pytest tests/ -v
cd ../integration-intelligence && pytest tests/ -v
cd ../orchestrator && pytest tests/ -v
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
| [Presentations](docs/presentations/README.md) | Overview + technical deep-dive PowerPoints |
| [DATABASE.md](docs/DATABASE.md) | PostgreSQL, Neo4j, Qdrant, Redis, events |
| [SECURITY.md](docs/SECURITY.md) | Authn/z, RBAC, mTLS, secrets |
| [THREAT_MODEL.md](docs/THREAT_MODEL.md) | STRIDE threat analysis |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | SLOs and capacity planning |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology choices |
| [FOLDER_STRUCTURE.md](docs/FOLDER_STRUCTURE.md) | Repository layout |
| [Web UI](web/README.md) | Landing page and Orchestrator dashboard |
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
