CREATE TABLE IF NOT EXISTS risk_reports (
    report_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    overall_ai_risk_score DOUBLE PRECISION NOT NULL,
    trust_score DOUBLE PRECISION NOT NULL,
    severity TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    category_scores JSONB NOT NULL DEFAULT '{}',
    factors JSONB NOT NULL DEFAULT '[]',
    remediations JSONB NOT NULL DEFAULT '[]',
    mappings_summary JSONB NOT NULL DEFAULT '{}',
    heatmap JSONB NOT NULL DEFAULT '[]',
    risk_graph JSONB NOT NULL DEFAULT '{}',
    timeline JSONB NOT NULL DEFAULT '[]',
    reasoning_path JSONB NOT NULL DEFAULT '[]',
    input_digest TEXT,
    model_id TEXT NOT NULL DEFAULT 'default-v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_risk_agent ON risk_reports(tenant_id, agent_id, created_at DESC);
