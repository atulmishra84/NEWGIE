-- GIE Context Intelligence Agent — PostgreSQL schema
-- Version: 1.0.0

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS context_intel;
SET search_path TO context_intel, public;

CREATE TABLE tenants (
    tenant_id       TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scans (
    scan_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    status          TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    source_type     TEXT NOT NULL,
    source_payload  JSONB NOT NULL DEFAULT '{}',
    idempotency_key TEXT,
    requested_by    TEXT NOT NULL,
    model_id        UUID,
    error_code      TEXT,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, idempotency_key)
);

CREATE INDEX idx_scans_tenant_status ON scans (tenant_id, status);
CREATE INDEX idx_scans_created_at ON scans (created_at DESC);

CREATE TABLE context_models (
    model_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    scan_id         UUID NOT NULL REFERENCES scans(scan_id),
    schema_version  TEXT NOT NULL DEFAULT 'gie.context.v1',
    version         INTEGER NOT NULL DEFAULT 1,
    payload         JSONB NOT NULL,
    confidence      REAL NOT NULL DEFAULT 0,
    source_digest   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_context_models_tenant ON context_models (tenant_id, created_at DESC);
CREATE INDEX idx_context_models_scan ON context_models (scan_id);

CREATE TABLE secret_fingerprints (
    fingerprint_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    scan_id         UUID NOT NULL REFERENCES scans(scan_id),
    kind            TEXT NOT NULL,
    location        TEXT NOT NULL,
    fingerprint     TEXT NOT NULL,
    severity        TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, fingerprint, location)
);

CREATE INDEX idx_secret_fingerprints_scan ON secret_fingerprints (scan_id);

CREATE TABLE outbox_events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         JSONB NOT NULL,
    published       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ
);

CREATE INDEX idx_outbox_unpublished ON outbox_events (published, created_at)
    WHERE published = FALSE;

CREATE TABLE api_keys (
    key_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    key_hash        TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('viewer', 'scanner', 'admin')),
    label           TEXT,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_tenant ON api_keys (tenant_id) WHERE revoked_at IS NULL;

-- Materialized summary for list endpoints
CREATE VIEW scan_summaries AS
SELECT
    s.scan_id,
    s.tenant_id,
    s.status,
    s.source_type,
    s.model_id,
    s.duration_ms,
    s.created_at,
    cm.confidence,
    cm.schema_version
FROM scans s
LEFT JOIN context_models cm ON cm.model_id = s.model_id;
