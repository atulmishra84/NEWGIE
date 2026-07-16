# Scan Sequence Diagram

End-to-end flow for a folder scan via REST API.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Ingress as Ingress / mTLS
    participant API as Context Intelligence API
    participant Auth as Auth Middleware
    participant RBAC as RBAC Enforcer
    participant Scan as ScanService
    participant Reg as DetectorRegistry
    participant Man as ManifestDetector
    participant Sec as SecretsDetector
    participant Merge as ModelMerger
    participant PG as PostgreSQL
    participant Redis as Redis Cache
    participant OB as Outbox
    participant Kafka as Kafka

    Client->>Ingress: POST /v1/scans {source: folder}
    Ingress->>API: forward (JWT)
    API->>Auth: validate bearer token
    Auth->>RBAC: check scan:create
    RBAC-->>API: allowed

    API->>Scan: scan_folder(path, tenant_id)
    Scan->>Reg: run_all(detectors)
    par Manifest detection
        Reg->>Man: detect(root)
        Man-->>Reg: partial ContextModel
    and Secret scanning
        Reg->>Sec: scan .env files
        Sec-->>Reg: SecretFinding[] (fingerprints)
    end
    Reg-->>Scan: DetectorResult[]

    Scan->>Merge: merge_context_models(partials)
    Merge-->>Scan: ContextModel

    Scan->>PG: persist scan + model
    Scan->>Redis: invalidate tenant cache
    Scan->>OB: enqueue context.scan.completed

    API-->>Client: 202 ObservabilityEnvelope {scan_id, model_id}

    OB-->>Kafka: publish event (async)
    Note over Kafka: Downstream agents consume context.model.updated
```

## Failure Isolation

If `ManifestDetector` throws, `DetectorRegistry` captures the error and continues. The merged model includes provenance from successful detectors only; failed detector IDs appear in logs with `error` field.

## Idempotency

Clients may supply `idempotency_key`. Duplicate keys within a tenant return the existing scan record without re-running detectors.
