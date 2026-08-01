# Full+GIE One-Shot Scope Freeze

**Status:** FROZEN — expanded production scope  
**Branch:** `cursor/full-gie-oneshot-fleet-2448`

## In scope

| Layer | Components |
|-------|------------|
| Ingress | Chief Orchestrator — **text + voice** with **commercial STT/TTS providers** (OpenAI / Deepgram) + stub fallback |
| Delivery | PM, UX, Senior Dev, Frontend, Backend |
| Security | AppSec, Vulnerability Eng (**OSV + optional Snyk**), Security Test, Compliance |
| Release/Ops | QA, Release Manager, DevOps (**multi-region/multi-cluster**), SRE, Tech Writer |
| GIE platform | Context Intelligence, Risk Assessment, Policy Engine |
| Evidence | Artifact dir + run evidence package + voice transcripts |
| Gates | Critical findings block; Policy deny; prod promote |
| Env | Live staging **and** customer prod (human confirm **or** unsupervised when explicitly enabled) |

## Newly in scope (expanded)

1. **Unsupervised customer production deploy** — when `ORCH_ALLOW_CUSTOMER_PROD=true` and `ORCH_UNSUPERVISED_PROD=true`, a successful gated golden/change run auto-promotes to all configured prod regions (still blocked by security/policy failures).
2. **Commercial STT/TTS** — `ORCH_STT_PROVIDER` / `ORCH_TTS_PROVIDER` = `openai` | `deepgram` | `stub` with API keys via env.
3. **Multi-cluster / multi-region** — topology in `deploy/full-gie/multi-region.yaml`; DevOps promotes per region/cluster.
4. **Real CVE scanner SaaS** — OSV (Google) always available; Snyk when `ORCH_SNYK_TOKEN` is set.

## Fleet registry

All agents above are registered and heartbeated (Orchestrator + 17 specialists = **18**).  
Live-test gate requires **≥ 16** healthy agents (plan minimum).

## Safety defaults

| Flag | Default | Meaning |
|------|---------|---------|
| `ORCH_ALLOW_CUSTOMER_PROD` | `false` | Prod promote disabled (dry-run) |
| `ORCH_UNSUPERVISED_PROD` | `false` | Even with prod allowed, require confirm phrase unless true |
| `ORCH_STT_PROVIDER` / `ORCH_TTS_PROVIDER` | `stub` | Use commercial only when keys + provider set |
| `ORCH_CVE_PROVIDERS` | `osv` | Comma list: `osv`, `snyk` |

## Success criteria

1. One deploy command → fleet + GIE + text/voice online  
2. Live-test LT-1…LT-5 green  
3. Demo URL + evidence package returned  
4. Prod promote works (dry-run by default; unsupervised when flags on)  
5. Change-request follow-up works on same stack  
6. Multi-region topology applied on promote  
7. Real CVE providers consulted (OSV minimum)  
