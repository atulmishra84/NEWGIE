# Folder Structure — GIE Monorepo

```
GIE/
├── agents/
│   └── context-intelligence/          # Context Intelligence Agent
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── infrastructure/
│       │   └── persistence/
│       │       └── schema.sql           # PostgreSQL DDL
│       ├── src/
│       │   └── context_intelligence/
│       │       ├── __init__.py
│       │       ├── config.py            # Settings (pydantic-settings)
│       │       ├── cli.py               # gie-context CLI
│       │       ├── adapters/
│       │       │   └── rest/
│       │       │       └── app.py       # FastAPI application
│       │       ├── application/
│       │       │   └── scan_service.py  # Scan orchestration
│       │       ├── domain/
│       │       │   ├── detectors/
│       │       │   │   ├── base.py      # Detector protocol + registry
│       │       │   │   └── manifest.py  # Manifest detector
│       │       │   ├── merge.py         # Context model merger
│       │       │   ├── normalizer.py    # Detection normalizer
│       │       │   ├── rbac.py          # Role-based access control
│       │       │   └── secrets_detector.py
│       │       └── infrastructure/
│       │           ├── celery_app.py
│       │           └── tasks.py
│       └── tests/
│           ├── conftest.py
│           ├── fixtures/
│           │   └── sample_ai_project/   # Scan test fixture
│           ├── unit/
│           ├── integration/
│           ├── contract/
│           ├── load/
│           ├── security/
│           └── chaos/
│
├── packages/
│   ├── gie-contracts/                   # Shared schemas & events
│   │   └── src/gie_contracts/
│   │       ├── context_model.py
│   │       ├── events.py
│   │       ├── envelope.py
│   │       └── sources.py
│   ├── gie-observability/               # Logging, tracing, metrics
│   │   └── src/gie_observability/
│   └── gie-security/                    # Auth utilities (planned)
│
├── deploy/
│   ├── k8s/
│   │   └── context-intelligence.yaml    # Raw Kubernetes manifests
│   ├── helm/
│   │   └── context-intelligence/        # Helm chart
│   └── terraform/                       # AWS IaC (network, RDS, Redis)
│
├── docs/
│   ├── Agent.md                         # Agent specification
│   ├── Architecture.md
│   ├── DATABASE.md
│   ├── FOLDER_STRUCTURE.md
│   ├── PERFORMANCE.md
│   ├── SECURITY.md
│   ├── TECH_STACK.md
│   ├── THREAT_MODEL.md
│   ├── api/
│   │   └── openapi.yaml
│   └── diagrams/
│       ├── class-diagram.md
│       └── sequence-scan.md
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
│
├── scripts/
│   └── bootstrap_gie.py
├── docker-compose.yml                   # Local full stack
├── pyproject.toml                       # Workspace root
└── README.md
```

## Layer Mapping (Clean Architecture)

| Directory | Layer |
|-----------|-------|
| `domain/` | Entities, domain services, detector plugins |
| `application/` | Use cases, orchestration |
| `adapters/` | Driving (REST, CLI) and driven (persistence) adapters |
| `infrastructure/` | Framework wiring (Celery, DB connections) |

## Conventions

- Python packages use `src/` layout
- Tests mirror source structure under `tests/`
- Shared contracts live in `packages/` — agents depend on packages, never vice versa
- Deploy artifacts are environment-agnostic templates with placeholder secrets
