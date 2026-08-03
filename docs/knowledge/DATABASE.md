# Knowledge Intelligence Persistence

See [`schema.sql`](../../agents/knowledge-intelligence/src/knowledge_intelligence/infrastructure/persistence/schema.sql) and [Architecture.md](Architecture.md).

## PostgreSQL tables

`knowledge_nodes`, `knowledge_edges`, `knowledge_versions`, `knowledge_evidence`, `outbox_events`, `audit_log`, `ingest_jobs`

## Neo4j

- Label: `KnowledgeNode`
- Relationships: `MAPS_TO`, `MITIGATES`, `EXPLOITS`, `REQUIRES`, `IMPLEMENTS`, `RELATED_TO`, `SUPERSEDES`, `EVIDENCED_BY`, `OWNS`, `CONSTRAINS`

## Qdrant

- Collection: `knowledge_embeddings`
- Vector size: 384 (configurable)
- Payload: `node_id`, `domain`, `kind`, `version`, `title`
