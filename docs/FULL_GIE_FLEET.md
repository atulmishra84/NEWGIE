# Full+GIE Fleet — One-Shot Deploy & Live Testing

## What this is

Production-shaped **Full+GIE** delivery swarm with:

- **Chief Orchestrator** (text + voice) on `:8090`
- Role agents (delivery / security / release-ops) registered in-process with heartbeats
- **GIE Context Intelligence** `:8080`
- **GIE Risk Assessment** `:8091`
- **GIE Policy Engine** `:8092`

You command only the Orchestrator.

## Scope freeze

See [FULL_GIE_ONESHOT_SCOPE.md](FULL_GIE_ONESHOT_SCOPE.md) and enablement guide [FULL_GIE_EXPANDED_SCOPE.md](FULL_GIE_EXPANDED_SCOPE.md) for:

- unsupervised prod deploy
- commercial STT/TTS (OpenAI / Deepgram)
- multi-region / multi-cluster topology
- real CVE scanners (OSV + optional Snyk)


## One-shot deploy (live staging)

```bash
chmod +x scripts/*.sh scripts/live_test_full_gie.py
./scripts/oneshot_deploy.sh
```

Uses Docker Compose when available; otherwise local uvicorn (`STAGING_MODE=local|docker|auto`).

Or force Compose:

```bash
STAGING_MODE=docker docker compose -f docker-compose.yml -f docker-compose.full-gie.yml up -d --build
```

When ready the deploy script prints `LIVE_STAGING_READY`.

## Live tests

```bash
ORCH_URL=http://127.0.0.1:8090 python scripts/live_test_full_gie.py
./scripts/go_no_go_report.sh
```

Covers LT-1 (text/voice), LT-2 (golden run), LT-3 (gates), LT-4 (change request), LT-5 (trace/registry/audit).

Rollback: `./scripts/rollback_full_gie.sh`

## Command examples

```bash
# Text status
curl -s -X POST http://127.0.0.1:8090/v1/command \
  -H 'content-type: application/json' \
  -d '{"text":"status","channel":"text"}' | jq .

# Golden run
curl -s -X POST http://127.0.0.1:8090/v1/command \
  -H 'content-type: application/json' \
  -d '{"text":"Build the golden demo app, run full security and QA, scan with GIE, deploy to staging, and show me the result.","channel":"text"}' | jq .

# Voice (transcript + wav)
curl -s -X POST http://127.0.0.1:8090/v1/command/voice \
  -F 'transcript=status' \
  -F 'audio=@sample.wav;type=audio/wav' | jq .

# Prod approve dry-run (staging does not touch customer prod)
curl -s -X POST http://127.0.0.1:8090/v1/command \
  -H 'content-type: application/json' \
  -d '{"text":"approve production deploy","channel":"text","prod_confirm_phrase":"approve production deploy"}' | jq .
```

## Go / No-Go

```bash
curl -s http://127.0.0.1:8090/v1/go-no-go | jq .
```

Customer production stays off unless `ORCH_ALLOW_CUSTOMER_PROD=true` and a human confirms.
