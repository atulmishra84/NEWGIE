CREATE TABLE IF NOT EXISTS recommendation_reports (
    report_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    recommendations JSONB NOT NULL DEFAULT '[]',
    by_priority JSONB NOT NULL DEFAULT '{}',
    by_audience JSONB NOT NULL DEFAULT '{}',
    counts JSONB NOT NULL DEFAULT '{}',
    summary TEXT NOT NULL DEFAULT '',
    reasoning_path JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rec_agent ON recommendation_reports(tenant_id, agent_id, created_at DESC);
