-- gie.integration.v1
CREATE TABLE IF NOT EXISTS integration_connections (
  connection_id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  platform_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  auth_method TEXT NOT NULL,
  config JSONB NOT NULL DEFAULT '{}',
  scopes JSONB NOT NULL DEFAULT '[]',
  endpoint_url TEXT,
  circuit_breaker_state TEXT NOT NULL DEFAULT 'closed',
  failure_count INT NOT NULL DEFAULT 0,
  last_success_at TIMESTAMPTZ,
  last_error TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_int_conn_tenant ON integration_connections(tenant_id);

CREATE TABLE IF NOT EXISTS integration_webhooks (
  event_id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  platform_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  signature_valid BOOLEAN,
  delivery_status TEXT NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  last_error TEXT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integration_audit (
  audit_id UUID PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  platform_id TEXT,
  outcome TEXT NOT NULL,
  detail JSONB NOT NULL DEFAULT '{}',
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integration_syncs (
  sync_id UUID PRIMARY KEY,
  connection_id UUID NOT NULL,
  tenant_id TEXT NOT NULL,
  platform_id TEXT NOT NULL,
  status TEXT NOT NULL,
  records_sent INT NOT NULL DEFAULT 0,
  records_received INT NOT NULL DEFAULT 0,
  retries INT NOT NULL DEFAULT 0,
  duration_ms INT NOT NULL DEFAULT 0,
  message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
