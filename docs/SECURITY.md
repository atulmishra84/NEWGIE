# Security — Context Intelligence Agent

## Authentication

### Bearer Tokens

All `/v1/*` endpoints require `Authorization: Bearer <token>` unless `REQUIRE_AUTH=false` (local dev only).

Supported token formats (dev/staging):

| Prefix | Role | Example |
|--------|------|---------|
| `admin:{tenant_id}` | admin | `admin:acme` |
| `scanner:{tenant_id}` | scanner | `scanner:acme` |
| `viewer:{tenant_id}` | viewer | `viewer:acme` |

Production uses signed JWTs validated against `JWT_SECRET` or hashed API keys stored in `api_keys` table.

### API Keys

- Stored as `sha256(pepper + raw_key)` — never plaintext
- Scoped to tenant + role
- Rotation via admin API (planned)

## Authorization (RBAC)

See `context_intelligence.domain.rbac`:

| Role | scan:create | scan:read | model:read | model:delete | admin:metrics |
|------|:-----------:|:---------:|:----------:|:------------:|:-------------:|
| viewer | | ✓ | ✓ | | |
| scanner | ✓ | ✓ | ✓ | | |
| admin | ✓ | ✓ | ✓ | ✓ | ✓ |

Enforcement points:

1. FastAPI dependency `get_auth`
2. `require_permission()` before handler logic

## Transport Security

| Layer | Control |
|-------|---------|
| Ingress | TLS 1.2+ (cert-manager / ACM) |
| Service mesh | mTLS between pods (Istio/Linkerd recommended) |
| Data stores | TLS to RDS, ElastiCache (`rediss://`), Neo4j bolt+s |

### mTLS Configuration (Istio example)

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: context-intelligence
  namespace: gie
spec:
  mtls:
    mode: STRICT
```

## Secrets Management

| Secret | Storage | Rotation |
|--------|---------|----------|
| `JWT_SECRET` | K8s Secret / AWS Secrets Manager | 90 days |
| `API_KEY_PEPPER` | K8s Secret / AWS Secrets Manager | 90 days |
| `DATABASE_URL` | External Secrets Operator | On credential rotation |
| Scan target tokens | `token_secret_ref` → vault | Per integration |

Never commit secrets. Example manifests use `CHANGE_ME` placeholders.

## Scan Target Security

- Read-only filesystem access
- Path canonicalization prevents traversal
- Skip files > `SCAN_MAX_FILE_BYTES`
- No arbitrary code execution from scanned content
- Workers run as non-root (UID 1000)

## Secret Detection Policy

Detected secrets are **fingerprinted**, never stored or logged:

```python
fingerprint = sha256(f"{pepper}:{raw_secret}")[:32]
```

API responses include `SecretFinding.fingerprint` only.

## Network Policies

Recommended Kubernetes `NetworkPolicy`:

- Ingress: allow from ingress controller only
- Egress: allow postgres, redis, neo4j, qdrant, kafka DNS names
- Deny all other egress

## Audit Logging

Structured JSON logs include:

- `trace_id`, `request_id`, `tenant_id`
- `scan_id`, `model_id` on mutations
- Never log bearer tokens or secret values

## Compliance Mapping

| Control | Implementation |
|---------|----------------|
| SOC2 CC6.1 | RBAC + auth |
| SOC2 CC6.7 | TLS + encryption at rest |
| GDPR Art. 32 | Tenant isolation, encryption |
| ISO 27001 A.9 | Access control policy |

See [THREAT_MODEL.md](THREAT_MODEL.md) for STRIDE analysis.
