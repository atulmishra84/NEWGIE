# Knowledge Intelligence Security Controls

## Authentication

- OAuth2 / JWT (HS256) via `Authorization: Bearer`
- API keys via `X-API-Key` (`gie_dev_*` for local operator flows)
- mTLS-ready at the ingress/gateway layer

## Authorization (RBAC)

| Role | Permissions |
|------|-------------|
| viewer | `knowledge:read`, `knowledge:query` |
| analyst | read + query |
| operator | + `knowledge:write`, `knowledge:version`, `knowledge:reindex` |
| admin | all including `knowledge:admin` |

## Data protection

- Evidence stores citations/excerpts, not customer secrets from scanned apps
- Audit log for upserts, publishes, reindex
- Version checksums for published graphs
- Webhook ingest requires `X-Webhook-Secret`

## Least privilege

Write and reindex are operator/admin only. Query endpoints are rate-limited per tenant.
