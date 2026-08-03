CREATE TABLE IF NOT EXISTS validation_reports (
    validation_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT,
    schema_version TEXT NOT NULL,
    verdict TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    checks JSONB NOT NULL DEFAULT '[]',
    findings JSONB NOT NULL DEFAULT '[]',
    corrections JSONB NOT NULL DEFAULT '[]',
    simulations JSONB NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '',
    counts JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_val_tenant ON validation_reports(tenant_id, created_at DESC);
