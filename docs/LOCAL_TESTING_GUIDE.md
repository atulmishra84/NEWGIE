# Full+GIE — Step-by-Step Local Testing Guide

This guide covers two ways to test locally:

1. **Local (uvicorn)** — fastest, no Docker required  
2. **Docker Compose** — full stack (recommended for end-to-end)

---

## Prerequisites

- Python 3.12+
- `curl`
- Git checkout of this repo
- For Docker path: Docker Engine + Compose plugin

```bash
cd /path/to/GIE
chmod +x scripts/*.sh scripts/*.py
```

---

## Option A — Local uvicorn (quick)

### Step 1: Install Python packages

```bash
pip install -e packages/gie-contracts \
  -e agents/chief-orchestrator \
  -e agents/risk-assessment \
  -e agents/policy-engine
```

### Step 2: Deploy local staging

```bash
STAGING_MODE=local ./scripts/oneshot_deploy.sh
```

Wait until you see:

```text
LIVE_STAGING_READY
```

### Step 3: Smoke-check services

```bash
curl -s http://127.0.0.1:8090/healthz   # Orchestrator
curl -s http://127.0.0.1:8091/healthz   # Risk
curl -s http://127.0.0.1:8092/healthz   # Policy
curl -s http://127.0.0.1:8080/healthz   # Context stub
```

### Step 4: Run end-to-end live tests

```bash
ORCH_URL=http://127.0.0.1:8090 python3 scripts/live_test_full_gie.py
```

Expected ending:

```text
Passed: 19  Failed: 0
LIVE_TEST_GREEN
```

### Step 5: Go / No-Go report

```bash
./scripts/go_no_go_report.sh
```

Expected:

```text
GO_NO_GO=GO
```

### Step 6: Manual commands (optional)

**Text status**

```bash
curl -s -X POST http://127.0.0.1:8090/v1/command \
  -H 'content-type: application/json' \
  -d '{"text":"status","channel":"text"}' | python3 -m json.tool
```

**Golden run**

```bash
curl -s -X POST http://127.0.0.1:8090/v1/command \
  -H 'content-type: application/json' \
  -d '{"text":"Build the golden demo app, run full security and QA, scan with GIE, deploy to staging, and show me the result.","channel":"text"}' \
  | python3 -m json.tool
```

**Demo URL**

```bash
curl -s http://127.0.0.1:8090/demo/golden | python3 -m json.tool
```

### Step 7: Stop local stack

```bash
./scripts/rollback_full_gie.sh
```

---

## Option B — Docker Compose (full stack)

### Step 1: Start Docker

```bash
docker info
# If Docker is not running, start the daemon for your OS
```

If you see permission errors:

```bash
sudo usermod -aG docker "$USER"
# then log out/in, or use: sudo docker ...
```

### Step 2: One-shot Docker deploy

```bash
STAGING_MODE=docker ./scripts/oneshot_deploy.sh
```

Or manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.full-gie.yml up -d --build
```

Default Docker e2e uses `context-stub` on `:8080`. The full Context Intelligence API/worker are behind Compose profile `full-ci` (optional, when that agent boots cleanly):

```bash
docker compose -f docker-compose.yml -f docker-compose.full-gie.yml --profile full-ci up -d --build
```

Wait for:

```text
LIVE_STAGING_READY
```

### Step 3: Check containers

```bash
docker compose -f docker-compose.yml -f docker-compose.full-gie.yml ps
```

You should see healthy/up for at least:

- `chief-orchestrator` (`:8090`)
- `risk-assessment` (`:8091`)
- `policy-engine` (`:8092`)
- `context-stub` (`:8080`)
- postgres, redis, neo4j, qdrant, kafka

### Step 4: Health checks

```bash
curl -s http://127.0.0.1:8090/healthz
curl -s http://127.0.0.1:8091/healthz
curl -s http://127.0.0.1:8092/healthz
curl -s http://127.0.0.1:8080/healthz
```

### Step 5: End-to-end live tests

```bash
ORCH_URL=http://127.0.0.1:8090 python3 scripts/live_test_full_gie.py
./scripts/go_no_go_report.sh
```

Expected:

```text
LIVE_TEST_GREEN
GO_NO_GO=GO
```

### Step 6: Useful Docker commands

```bash
# Logs
docker compose -f docker-compose.yml -f docker-compose.full-gie.yml logs -f chief-orchestrator

# Restart one service
docker compose -f docker-compose.yml -f docker-compose.full-gie.yml restart chief-orchestrator

# Tear down
./scripts/rollback_full_gie.sh
# or
docker compose -f docker-compose.yml -f docker-compose.full-gie.yml down
```

---

## What the live test covers

| ID | Area | What it checks |
|----|------|----------------|
| LT-1 | Ingress | Text + voice status, ambiguous voice does not build |
| LT-2 | Golden run | All delivery/security/ops lanes + GIE risk/policy + demo package |
| LT-3 | Gates | Critical finding block, policy deny, prod confirm rules |
| LT-4 | Change request | Follow-up feature change on same stack |
| LT-5 | Audit | Trace, voice transcript, ≥16 agents healthy |

---

## Optional expanded features

See [FULL_GIE_EXPANDED_SCOPE.md](FULL_GIE_EXPANDED_SCOPE.md).

Examples:

```bash
# Unsupervised prod (careful)
export ORCH_ALLOW_CUSTOMER_PROD=true
export ORCH_UNSUPERVISED_PROD=true

# Commercial voice
export ORCH_STT_PROVIDER=openai
export ORCH_TTS_PROVIDER=openai
export ORCH_OPENAI_API_KEY=sk-...

# CVE scanners
export ORCH_CVE_PROVIDERS=osv,snyk
export ORCH_SNYK_TOKEN=...
```

Then redeploy and re-run the live test.

---

## URLs cheat sheet

| Service | URL |
|---------|-----|
| Orchestrator | http://127.0.0.1:8090 |
| Demo | http://127.0.0.1:8090/demo/golden |
| Fleet status | http://127.0.0.1:8090/v1/fleet |
| Go/No-Go | http://127.0.0.1:8090/v1/go-no-go |
| Topology | http://127.0.0.1:8090/v1/topology |
| Risk | http://127.0.0.1:8091/healthz |
| Policy | http://127.0.0.1:8092/healthz |
| Context | http://127.0.0.1:8080/healthz |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port already in use | `./scripts/rollback_full_gie.sh` then redeploy |
| `docker: command not found` | Install Docker, or use Option A |
| `permission denied` on Docker socket | Use `sudo` or add user to `docker` group |
| Orchestrator healthy but platform false (Docker) | Confirm `host.docker.internal` / published ports; restart `chief-orchestrator` |
| Live test fails mid-way | Check `docker compose ... logs chief-orchestrator` and `/tmp/gie-fleet-artifacts/logs/` |
| Want clean rebuild | `docker compose -f docker-compose.yml -f docker-compose.full-gie.yml down -v` then redeploy |

Artifacts from a run are written under `/tmp/gie-fleet-artifacts/` (`go-no-go.json`, `live-test-summary.json`, logs).
