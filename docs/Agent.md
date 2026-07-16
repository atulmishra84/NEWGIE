# Context Intelligence Agent Specification

**Agent ID:** `context-intelligence`  
**Schema:** `gie.context.v1`  
**Version:** 1.0.0

## Mission

The Context Intelligence Agent scans AI application artifacts—source trees, manifests, runtime environments, and cloud resources—and produces a normalized **Context Model** consumed by downstream GIE agents (Risk, Policy, Compliance, Deployment).

## Responsibilities

| In scope | Out of scope |
|----------|--------------|
| Detect AI frameworks, SDKs, models, prompts | Policy enforcement |
| Fingerprint secrets (never store raw values) | Runtime interception |
| Normalize detections into `gie.context.v1` | Vulnerability patching |
| Emit scan lifecycle events | User authentication for target apps |
| Build evidence graph (Neo4j) | Billing / cost optimization |

## Scan Sources

Supported source discriminators (see `gie_contracts.sources`):

- **Local:** `folder`, `zip`, `git`, IDE workspaces (`cursor_project`, `vscode_workspace`)
- **Runtime:** `container`, `process`, `kubernetes`
- **Cloud:** `aws`, `azure`, `gcp`, `github`
- **Framework hints:** `langgraph`, `openai_agents`, `crewai`, `autogen`, `semantic_kernel`, `azure_ai_foundry`

## Detectors

Detectors are isolated plugins registered in `DetectorRegistry`. Each detector returns a partial `ContextModel` merged by `merge_context_models`.

| Detector ID | Input | Output sections |
|-------------|-------|-----------------|
| `manifest.detector.v1` | package.json, pyproject.toml, mcp.json, prompts, .env | identity, ai, interfaces, data.secret_findings |
| `secrets.detector.v1` | text files | data.secret_findings (fingerprints only) |
| `cloud.aws.detector.v1` | AWS APIs (flag-gated) | deployment.cloud_resources |
| `k8s.detector.v1` | cluster API (flag-gated) | deployment.kubernetes |

Detector failures are isolated—one failing detector does not abort the scan.

## Context Model Sections

```
ContextModel
├── identity        languages, package managers, runtimes, cloud providers
├── ai              frameworks, sdks, models, prompts, workflows
├── interfaces      apis, tools, mcp_servers, webhooks
├── data            vector_databases, data_stores, secret_findings
├── security        identity_providers, auth_schemes, secret_managers
├── deployment      containers, kubernetes, cloud_resources
├── graph           nodes/edges for relationship queries
└── provenance      scan metadata, detectors, evidence, confidence
```

## API Surface

REST endpoints (OpenAPI 3.1 in `docs/api/openapi.yaml`):

- `POST /v1/scans` — enqueue or synchronous folder scan
- `GET /v1/scans/{scan_id}` — scan status
- `GET /v1/context-models/{model_id}` — retrieve normalized model
- `GET /healthz`, `GET /metrics`

All mutating endpoints require bearer authentication. Responses wrap data in `ObservabilityEnvelope` with trace/request/correlation IDs.

## Events

Kafka topics (via transactional outbox):

| Event | Trigger |
|-------|---------|
| `context.scan.requested` | Scan accepted |
| `context.scan.started` | Worker picked up job |
| `context.scan.completed` | Model persisted |
| `context.scan.failed` | Unrecoverable error |
| `context.model.updated` | New model version available |

## RBAC

| Role | Permissions |
|------|-------------|
| `viewer` | scan:read, model:read |
| `scanner` | scan:create, scan:read, model:read |
| `admin` | all permissions including admin:metrics |

## Secret Handling

1. Pattern-match potential secrets in files
2. Compute `sha256:<peppered-hash>` fingerprint
3. Store fingerprint + location + severity — **never raw value**
4. Redact from logs and API responses

## SLO Targets

See [PERFORMANCE.md](PERFORMANCE.md). Summary:

- P95 folder scan (≤5k files): **≤30s**
- API availability: **99.9%**
- Model GET cache hit P95: **≤50ms**

## CLI

```bash
gie-context scan /path/to/project --output context-model.json --tenant acme
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | local postgres | Async SQLAlchemy DSN |
| `REDIS_URL` | redis://localhost:6379/0 | Celery broker + cache |
| `JWT_SECRET` | — | API token validation |
| `API_KEY_PEPPER` | — | Secret fingerprint pepper |
| `FLAG_ENABLE_CLOUD_SCANNERS` | false | Enable AWS/K8s detectors |
| `SCAN_MAX_FILE_BYTES` | 1048576 | Skip large files |
| `SCAN_MAX_FILES` | 10000 | Scan budget per request |

## Deployment Artifacts

- Kubernetes: `deploy/k8s/context-intelligence.yaml`
- Helm: `deploy/helm/context-intelligence/`
- Terraform: `deploy/terraform/` (Postgres + Redis + network)
