-- Knowledge Intelligence Agent — PostgreSQL schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS knowledge_nodes (
    node_id          TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,
    domain           TEXT NOT NULL,
    title            TEXT NOT NULL,
    summary          TEXT NOT NULL DEFAULT '',
    body             TEXT NOT NULL DEFAULT '',
    tags             JSONB NOT NULL DEFAULT '[]',
    attributes       JSONB NOT NULL DEFAULT '{}',
    evidence         JSONB NOT NULL DEFAULT '[]',
    version          TEXT NOT NULL DEFAULT '1.0.0',
    schema_version   TEXT NOT NULL DEFAULT 'gie.knowledge.v1',
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    confidence_rationale TEXT,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_by    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kn_domain ON knowledge_nodes(domain);
CREATE INDEX IF NOT EXISTS idx_kn_kind ON knowledge_nodes(kind);
CREATE INDEX IF NOT EXISTS idx_kn_version ON knowledge_nodes(version);
CREATE INDEX IF NOT EXISTS idx_kn_active ON knowledge_nodes(active);
CREATE INDEX IF NOT EXISTS idx_kn_title_trgm ON knowledge_nodes USING gin (to_tsvector('english', title || ' ' || summary || ' ' || body));

CREATE TABLE IF NOT EXISTS knowledge_edges (
    edge_id       TEXT PRIMARY KEY,
    source_id     TEXT NOT NULL REFERENCES knowledge_nodes(node_id),
    target_id     TEXT NOT NULL REFERENCES knowledge_nodes(node_id),
    relationship  TEXT NOT NULL,
    weight        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    attributes    JSONB NOT NULL DEFAULT '{}',
    evidence      JSONB NOT NULL DEFAULT '[]',
    version       TEXT NOT NULL DEFAULT '1.0.0',
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ke_source ON knowledge_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_ke_target ON knowledge_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_ke_rel ON knowledge_edges(relationship);

CREATE TABLE IF NOT EXISTS knowledge_versions (
    version      TEXT PRIMARY KEY,
    snapshot_id  UUID NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'gie.knowledge.v1',
    node_count   INT NOT NULL,
    edge_count   INT NOT NULL,
    domains      JSONB NOT NULL DEFAULT '[]',
    checksum     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_evidence (
    evidence_id   TEXT PRIMARY KEY,
    node_id       TEXT REFERENCES knowledge_nodes(node_id),
    source_uri    TEXT,
    source_title  TEXT,
    citation      TEXT,
    content_hash  TEXT,
    excerpt       TEXT,
    retrieved_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic         TEXT NOT NULL,
    event_key     TEXT,
    payload       JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_log (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     TEXT NOT NULL,
    actor         TEXT NOT NULL,
    action        TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT,
    details       JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingest_jobs (
    job_id           UUID PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    status           TEXT NOT NULL,
    idempotency_key  TEXT NOT NULL UNIQUE,
    requested_by     TEXT NOT NULL,
    node_count       INT NOT NULL DEFAULT 0,
    edge_count       INT NOT NULL DEFAULT 0,
    error            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ
);
