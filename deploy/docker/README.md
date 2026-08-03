# Local Docker stack

Full GIE mesh on Docker Compose for pre-Azure validation.

## Quick start

```bash
# From repo root
./scripts/local-up.sh          # host-network override by default in sandboxes
./scripts/local-smoke.sh
```

URLs:

| Surface | URL |
|---------|-----|
| Landing / dashboard | http://127.0.0.1:5173 |
| Orchestrator | http://127.0.0.1:8091 |
| Agents | `:8080`–`:8090` |

## Networking modes

| `LOCAL_NET_MODE` | When to use |
|------------------|-------------|
| `host` (default via `local-up.sh`) | Docker bridge/iptables broken (many CI/sandbox VMs) |
| `bridge` | Normal Docker Desktop / Linux hosts |

```bash
LOCAL_NET_MODE=bridge docker compose up -d --build
# or
LOCAL_NET_MODE=host ./scripts/local-up.sh
```

Host mode uses [docker-compose.host.yml](../../docker-compose.host.yml) so every service talks over `127.0.0.1`.

## What is verified

`scripts/local-smoke.sh` checks:

1. All 11 peer `/healthz` + Orchestrator
2. `GET /status` with healthy peers (`SIMULATE_AGENTS=false`)
3. `POST /analyze` with live “reached at …” step summaries
4. Web UI (`/` + `/dashboard.html`)

Context `/ready` should report database, redis, neo4j, and qdrant true when the data plane is healthy.

## Notes

- Postgres init script creates all twelve `gie_*` databases on first boot.
- Local DB URLs use `?ssl=disable` (Postgres image has no TLS).
- Kafka image is `apache/kafka:3.7.1` (Bitnami `3.7` tags were removed).
- Tear down: `docker compose -f docker-compose.yml -f docker-compose.host.yml down -v`
