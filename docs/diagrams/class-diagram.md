# Context Intelligence — Class Diagram

Core domain and application types.

```mermaid
classDiagram
    class ContextModel {
        +UUID model_id
        +str schema_version
        +int version
        +IdentitySection identity
        +AiSection ai
        +InterfacesSection interfaces
        +DataSection data
        +SecuritySection security
        +DeploymentSection deployment
        +GraphSection graph
        +ProvenanceSection provenance
        +overall_confidence() float
    }

    class SecretFinding {
        +str kind
        +str location
        +str fingerprint
        +Severity severity
        +Confidence confidence
    }

    class Detector {
        <<interface>>
        +str detector_id
        +detect(root, tenant_id, scan_id) DetectorResult
    }

    class ManifestDetector {
        +detector_id: manifest.detector.v1
        +detect() DetectorResult
        -scan_package_json()
        -scan_pyproject()
        -scan_mcp_json()
    }

    class DetectorRegistry {
        -detectors: List~Detector~
        +register(detector)
        +run_all(root) List~DetectorResult~
    }

    class ScanService {
        +scan_folder(path, tenant_id) ContextModel
        -build_registry() DetectorRegistry
        -digest_root(root) str
    }

    class MergeService {
        +merge_context_models(base, others) ContextModel
        -dedupe_items(items) List~DetectedItem~
        -dedupe_secrets(findings) List~SecretFinding~
    }

    class SecretsDetector {
        +fingerprint_secret(raw, pepper) str
        +scan_text_for_secrets(text, location) List~SecretFinding~
        +scan_file_for_secrets(path) List~SecretFinding~
    }

    class RBAC {
        +has_permission(role, permission) bool
        +require_permission(role, permission) void
    }

    class Role {
        <<enumeration>>
        VIEWER
        SCANNER
        ADMIN
    }

    class Permission {
        <<enumeration>>
        SCAN_CREATE
        SCAN_READ
        MODEL_READ
        MODEL_DELETE
        ADMIN_METRICS
    }

    class FastAPIApp {
        +create_scan()
        +get_scan()
        +get_context_model()
        +healthz()
    }

    Detector <|.. ManifestDetector
    DetectorRegistry o-- Detector
    ScanService --> DetectorRegistry
    ScanService --> MergeService
    ManifestDetector --> SecretsDetector
    ContextModel *-- SecretFinding
    FastAPIApp --> ScanService
    FastAPIApp --> RBAC
    RBAC --> Role
    RBAC --> Permission
```

## Package Layout

| Package | Classes |
|---------|---------|
| `domain/` | Detectors, merge, secrets, rbac |
| `application/` | ScanService, query handlers |
| `adapters/rest/` | FastAPIApp, auth middleware |
| `adapters/persistence/` | Repository implementations |
| `infrastructure/` | Celery, Kafka outbox relay |
