CREATE TABLE IF NOT EXISTS policy_packages (
    package_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    version TEXT NOT NULL,
    source TEXT NOT NULL,
    policies JSONB NOT NULL DEFAULT '[]',
    artifacts JSONB NOT NULL DEFAULT '[]',
    named_artifacts JSONB NOT NULL DEFAULT '{}',
    validation JSONB NOT NULL DEFAULT '{}',
    rollback JSONB NOT NULL DEFAULT '{}',
    summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_policygen_agent ON policy_packages(tenant_id, agent_id, created_at DESC);
