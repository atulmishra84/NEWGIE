# GIE — Azure Full-Capability Sandbox

Sandbox landing zone for **Guardrails Intelligence Engine** on Azure.

Default mode (`SANDBOX_MODE=full`) deploys the **full platform path**: scaled AKS, multi-DB Postgres, Azure Redis, in-cluster Neo4j/Qdrant/Kafka, all 12 agents with live peer HTTP (`SIMULATE_AGENTS=false`), Celery workers, and the static web UI.

## What you get

| Resource | SKU (full default) | Purpose |
|----------|--------------------|---------|
| Resource Group | — | `gie-sandbox` |
| ACR | Basic | All agent + web images |
| AKS | 3× `Standard_D4s_v3` | Agents + data plane |
| PostgreSQL Flexible | Burstable `B1ms` | 12 databases (`gie_*`) |
| Redis | In-cluster (`redis:7-alpine`) | Shared cache (DB indexes 0–11); Azure Cache for Redis is retiring |
| Neo4j / Qdrant / Kafka | In-cluster (single-node) | Context + Knowledge data plane (full mode) |

**Cost:** roughly **$400–700+/month** while running. Tear down when idle.

```text
Internet
   │
   ├──────────────► gie-web LB (:80)  landing + dashboard
   │
   └──────────────► Orchestrator LB (:8091)
                         │  SIMULATE_AGENTS=false
                         ▼
              11 peer agents (ClusterIP)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Azure Postgres   Redis/Neo4j/Qdrant/Kafka (in-cluster)
```

## Modes

| `SANDBOX_MODE` | Behavior |
|----------------|----------|
| `full` (default) | Data plane + all agents + workers + web + live Orchestrator |
| `minimal` | Orchestrator only, `SIMULATE_AGENTS=true`, smaller AKS (2× D2s_v3) |

## Prerequisites

```bash
./deploy/azure/scripts/00-prereqs.sh
```

Needs Azure CLI login, Docker, Helm 3, kubectl, jq, openssl. Full builds need ~10–20 GB free Docker disk.

## Deploy (5 steps)

```bash
export RG=gie-sandbox
export LOCATION=centralus  # sponsorship often blocks Postgres in eastus/eastus2
export POSTGRES_PASSWORD='Replace_With_Strong_P@ssw0rd'
export SANDBOX_MODE=full   # or minimal

# 1) Infra (15–25 minutes for full)
./deploy/azure/scripts/01-infra.sh

# 2) Build & push images (orchestrator only in minimal; all 12 + web in full)
./deploy/azure/scripts/02-build-push.sh

# 3) In-cluster Neo4j + Qdrant + Kafka (no-op in minimal)
./deploy/azure/scripts/03-deploy-data.sh

# 4) Helm agents + workers + web + Orchestrator
./deploy/azure/scripts/04-deploy-app.sh

# 5) Smoke
./deploy/azure/scripts/05-smoke.sh
```

Useful outputs:

- `deploy/azure/.last-outputs.json` — ACR / AKS / Postgres / Redis
- `deploy/azure/.last-url.txt` — Orchestrator public base URL
- `deploy/azure/.last-web-url.txt` — Web UI public URL (full mode)
- `deploy/azure/.last-neo4j-password.txt` — Neo4j password (full mode, gitignored)

## Dashboard

After full deploy, open the web LoadBalancer URL and set **API base** to the Orchestrator URL from `.last-url.txt`.

```bash
WEB=$(cat deploy/azure/.last-web-url.txt)
API=$(cat deploy/azure/.last-url.txt)
echo "Open $WEB/dashboard.html  → API base $API"
```

## Smoke manually

```bash
BASE=$(cat deploy/azure/.last-url.txt)

curl -sS "$BASE/healthz" | jq .
curl -sS "$BASE/status" -H 'x-tenant-id: azure-demo' | jq '.data.healthy, (.data.agents|length)'
curl -sS -X POST "$BASE/analyze" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: azure-demo' \
  -d '{"tenant_id":"azure-demo","source":{"type":"folder","path":"/demo"},"mode":"sync"}' \
  | jq '{status: .data.status, steps: [.data.steps[].status]}'
```

## Design notes

1. **Live peers** — Orchestrator uses `HttpAgentInvoker` (`GIE_ENV=azure`, `SIMULATE_AGENTS=false`). Invoke currently health-checks `/healthz` on each peer; expand to full agent APIs as contracts harden.
2. **Context / Knowledge** — wired to Azure Postgres + in-cluster Redis/Neo4j/Qdrant/Kafka. Workers process Celery queues `scans` / `knowledge`.
3. **Other agents** — boot with in-memory stores today; DBs/Redis URLs are injected for future persistence.
4. **Public LoadBalancers** — fine for demo; for pilot use private AKS + App Gateway / Front Door + Entra (`REQUIRE_AUTH=true`).
5. **Postgres firewall** — Azure services only. Laptop clients need your IP allowlisted.
6. **Region** — Azure sponsorship often blocks Postgres Flexible in `eastus`/`eastus2`; `centralus` is a known-good default. Redis runs in-cluster because Azure Cache for Redis no longer accepts new creates on many subscriptions.
7. **Secrets** — JWT / Neo4j / connection strings set at deploy time. Prefer Key Vault + CSI beyond sandbox.

## Teardown

```bash
./deploy/azure/scripts/teardown.sh
# or
az group delete -n gie-sandbox --yes
```

## Files

```
deploy/azure/
├── README.md
├── bicep/                 # ACR, AKS (D4s_v3×3), Postgres (12 DBs)
├── helm/                  # Azure values (full + minimal)
├── k8s/
│   ├── namespace.yaml
│   ├── data-plane/        # Redis, Neo4j, Qdrant, Kafka
│   ├── workers/           # Context + Knowledge Celery
│   └── web/               # Landing + dashboard
└── scripts/               # 00→05 + teardown
```
