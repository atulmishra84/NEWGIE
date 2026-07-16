# Performance & SLOs — Context Intelligence Agent

## Service Level Objectives

| SLI | Target (production) | Measurement window |
|-----|---------------------|-------------------|
| API availability | **99.9%** | 30-day rolling |
| Scan success rate | **≥99%** (excl. client errors) | 7-day rolling |
| P95 scan latency (folder ≤5k files) | **≤30s** | 7-day rolling |
| P99 scan latency (folder ≤5k files) | **≤60s** | 7-day rolling |
| P95 GET /v1/context-models/{id} (cache hit) | **≤50ms** | 7-day rolling |
| P95 GET /v1/context-models/{id} (cache miss) | **≤200ms** | 7-day rolling |
| P95 POST /v1/scans (async accept) | **≤500ms** | 7-day rolling |
| Event publish lag (outbox → Kafka) | **≤5s** P99 | 7-day rolling |

## Service Level Indicators

Prometheus metrics (prefix `gie_context_*`):

| Metric | Type | Labels |
|--------|------|--------|
| `gie_context_scan_requests_total` | Counter | tenant_id, source_type, status |
| `gie_context_scan_duration_seconds` | Histogram | source_type |
| `gie_context_model_gets_total` | Counter | cache_hit |
| `gie_context_active_scans` | Gauge | — |

## Capacity Planning

### API Tier

- Baseline: 2 replicas (HPA min)
- Scale trigger: CPU >70% or memory >80%
- Max replicas: 10
- Per-pod budget: 2 CPU / 2Gi RAM

### Worker Tier

- Queue: `scans` on Redis
- Concurrency: 4 tasks/worker (recommended)
- Scale on queue depth (KEDA recommended)

### Scan Budgets

| Limit | Default | Rationale |
|-------|---------|-----------|
| `SCAN_MAX_FILES` | 10,000 | Prevent unbounded traversal |
| `SCAN_MAX_FILE_BYTES` | 1 MiB | Skip binaries/large artifacts |
| Concurrent scans/tenant | 5 (recommended) | Fair scheduling |

## Latency Breakdown (typical folder scan)

| Phase | P50 | P95 |
|-------|-----|-----|
| Auth + validation | 5ms | 15ms |
| Filesystem walk + digest | 200ms | 2s |
| Manifest detector | 50ms | 500ms |
| Secret detector | 100ms | 1s |
| Merge + persist | 20ms | 100ms |
| **Total** | **~400ms** | **~4s** |

Large monorepos (5k files) shift P95 toward 15–30s depending on disk I/O.

## Caching Strategy

1. **L1 — In-process:** none (stateless API)
2. **L2 — Redis:** context model by `(tenant_id, model_id)`, TTL 15m
3. **L3 — PostgreSQL:** source of truth

Cache invalidation on `context.model.updated` event.

## Error Budget

99.9% availability → **43.8 minutes/month** downtime budget.

Burn rate alerts (recommended):

- Fast burn: 2% budget in 1 hour → page
- Slow burn: 10% budget in 6 hours → ticket

## Load Testing

Light load test: `tests/load/test_scan_throughput.py`

Production load test (manual):

```bash
locust -f tests/load/locustfile.py --headless -u 20 -r 2 -t 60s
```

## Optimization Roadmap

1. Parallel detector execution with asyncio
2. Incremental scans via `source_digest` comparison
3. Streaming manifest parsing for large monorepos
4. Qdrant embedding cache for prompt similarity
