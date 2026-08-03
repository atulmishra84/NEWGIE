# Knowledge Intelligence Threat Model (STRIDE)

| Threat | Risk | Mitigation |
|--------|------|------------|
| Spoofing | Forged upserts pollute knowledge | JWT/API key auth, RBAC write roles |
| Tampering | Malicious corpus injection | Versioning, checksums, audit log, signed webhooks |
| Repudiation | Deny knowledge changes | Audit log with actor/tenant |
| Information Disclosure | Sensitive regulatory notes leak | Tenant isolation, authz on read/query |
| DoS | Expensive queries/reindex | Rate limits, top_k caps, Celery queue |
| Elevation | Viewer gains write | Strict knowledge RBAC permissions |
