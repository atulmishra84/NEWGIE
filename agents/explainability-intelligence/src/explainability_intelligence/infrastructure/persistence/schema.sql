CREATE TABLE IF NOT EXISTS explanations (
    explanation_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT,
    decision_id TEXT,
    schema_version TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    dimensions JSONB NOT NULL DEFAULT '{}',
    views JSONB NOT NULL DEFAULT '{}',
    reasoning_path JSONB NOT NULL DEFAULT '[]',
    artifacts JSONB NOT NULL DEFAULT '[]',
    mermaid_diagram TEXT NOT NULL DEFAULT '',
    figma_diagram JSONB NOT NULL DEFAULT '{}',
    summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_explain_decision ON explanations(tenant_id, decision_id, created_at DESC);
