# GIE Context Intelligence — Architecture

The Context Intelligence Agent follows **Clean Architecture** with **Hexagonal (Ports & Adapters)**, **Domain-Driven Design**, **CQRS**, and **Event-Driven** integration.

## Layer Overview

```mermaid
flowchart TB
    subgraph Adapters["Adapters (Driving & Driven)"]
        REST[REST API / FastAPI]
        CLI[CLI gie-context]
        Worker[Celery Worker]
        PG[(PostgreSQL)]
        Redis[(Redis Cache)]
        Neo4j[(Neo4j Graph)]
        Qdrant[(Qdrant Vectors)]
        Kafka[[Kafka Events]]
    end

    subgraph Application["Application Layer"]
        ScanSvc[ScanService]
        QuerySvc[ContextModelQueryService]
        CmdBus[Command Handlers]
        EventPub[Outbox Publisher]
    end

    subgraph Domain["Domain Layer"]
        Detectors[Detector Registry]
        Merge[Context Model Merger]
        Secrets[Secrets Detector]
        RBAC[RBAC Policy]
        CM[ContextModel Aggregate]
    end

    REST --> ScanSvc
    CLI --> ScanSvc
    Worker --> ScanSvc
    ScanSvc --> Detectors
    Detectors --> Merge
    Detectors --> Secrets
    ScanSvc --> CM
    ScanSvc --> CmdBus
    CmdBus --> PG
    QuerySvc --> PG
    QuerySvc --> Redis
    ScanSvc --> Neo4j
    ScanSvc --> Qdrant
    EventPub --> Kafka
    CmdBus --> EventPub
    REST --> RBAC
```

## Hexagonal Boundaries

| Port | Adapter | Direction |
|------|---------|-----------|
| `ScanPort` | REST, CLI, Celery | Driving |
| `ContextModelRepository` | PostgreSQL | Driven |
| `GraphRepository` | Neo4j | Driven |
| `VectorRepository` | Qdrant | Driven |
| `EventPublisher` | Kafka outbox | Driven |
| `SecretScanner` | filesystem detector | Domain service |

## DDD Bounded Context

**Context Intelligence** is a bounded context responsible for *understanding* AI applications. It publishes `ContextModelUpdated` events that other GIE contexts subscribe to:

- **Risk Assessment** — consumes secret findings and autonomous capabilities
- **Policy Engine** — consumes frameworks and data stores
- **Compliance** — consumes provenance and evidence

The `ContextModel` is the aggregate root. `Scan` is a process manager coordinating detector execution.

## CQRS Split

| Side | Responsibility | Storage |
|------|----------------|---------|
| **Commands** | Create scan, persist model, emit events | PostgreSQL write model + outbox |
| **Queries** | Get scan status, fetch context model | PostgreSQL + Redis read cache |

Write path:

```
POST /v1/scans → ScanCommand → ScanService → Detectors → Merge → Persist → Outbox
```

Read path:

```
GET /v1/context-models/{id} → QueryHandler → Redis? → PostgreSQL → Envelope
```

## Event Flow

```mermaid
sequenceDiagram
    participant API as REST API
    participant Svc as ScanService
    participant DB as PostgreSQL
    participant OB as Outbox
    participant K as Kafka
    participant Risk as Risk Agent

    API->>Svc: ScanCommand
    Svc->>DB: INSERT scan (pending)
    Svc->>Svc: run detectors
    Svc->>DB: INSERT context_model
    Svc->>OB: INSERT context.scan.completed
    OB-->>K: relay event
    K-->>Risk: context.model.updated
```

## Detector Pipeline

Detectors implement a common protocol and run concurrently where safe. Results merge with deduplication by `(name, version)` for items and `(kind, location, fingerprint)` for secrets.

## Cross-Cutting Concerns

- **Observability:** OpenTelemetry traces, Prometheus metrics, structlog JSON
- **Security:** JWT/API key auth, RBAC, mTLS at ingress (see SECURITY.md)
- **Resilience:** Per-detector failure isolation, Celery retries, idempotency keys

## Technology Mapping

See [TECH_STACK.md](TECH_STACK.md) and [FOLDER_STRUCTURE.md](FOLDER_STRUCTURE.md).
