CREATE TABLE IF NOT EXISTS policy_decisions (
    decision_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    input_digest TEXT,
    recommendations JSONB NOT NULL DEFAULT '[]',
    artifacts JSONB NOT NULL DEFAULT '[]',
    reasoning_path JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pol_tenant ON policy_decisions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pol_created ON policy_decisions(created_at DESC);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    event_key TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_id TEXT,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
