CREATE TABLE IF NOT EXISTS compliance_reports (
    report_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    application_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    compliance_score DOUBLE PRECISION NOT NULL,
    policy_version TEXT NOT NULL,
    applicable_frameworks JSONB NOT NULL DEFAULT '[]',
    assessments JSONB NOT NULL DEFAULT '[]',
    gaps JSONB NOT NULL DEFAULT '[]',
    matrix JSONB NOT NULL DEFAULT '[]',
    evidence JSONB NOT NULL DEFAULT '[]',
    audit_package JSONB NOT NULL DEFAULT '{}',
    control_mappings JSONB NOT NULL DEFAULT '{}',
    reasoning_path JSONB NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comp_app ON compliance_reports(tenant_id, application_id, created_at DESC);

CREATE TABLE IF NOT EXISTS regulatory_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    framework TEXT NOT NULL,
    version TEXT NOT NULL,
    summary TEXT NOT NULL,
    effective_date DATE,
    catalog_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
