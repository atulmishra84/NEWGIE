-- gie.orchestrator.v1
CREATE TABLE IF NOT EXISTS orchestrator_executions (
  execution_id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  workflow_id TEXT NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_orch_exec_tenant ON orchestrator_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_orch_exec_trace ON orchestrator_executions(trace_id);

CREATE TABLE IF NOT EXISTS orchestrator_traces (
  trace_id TEXT PRIMARY KEY,
  execution_id UUID NOT NULL,
  tenant_id TEXT NOT NULL,
  spans JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
