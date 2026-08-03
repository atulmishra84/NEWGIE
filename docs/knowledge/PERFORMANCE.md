# Performance Targets

| Operation | Target |
|-----------|--------|
| Cached query p95 | < 50ms |
| Uncached hybrid query p95 (warm index) | < 300ms |
| Node GET p95 | < 50ms |
| Upsert 100 nodes | < 2s |
| Reindex full seed (~100 nodes) | < 10s |

Horizontal scaling: stateless API replicas; shared Postgres/Neo4j/Qdrant/Redis.
