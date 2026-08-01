# Full+GIE Expanded Scope — Enablement Guide

Previously out-of-scope items are now implemented. Enable via env flags.

## 1) Unsupervised customer production deploy

```bash
export ORCH_ALLOW_CUSTOMER_PROD=true
export ORCH_UNSUPERVISED_PROD=true
```

- Golden/change runs that pass security + GIE policy **auto-promote** to all prod regions in [`deploy/full-gie/multi-region.yaml`](../deploy/full-gie/multi-region.yaml).
- With only `ORCH_ALLOW_CUSTOMER_PROD=true`, promote still requires confirm phrase: `approve production deploy`.
- Defaults remain safe: both flags `false` → dry-run only (LT-3.4).

## 2) Commercial STT/TTS

```bash
export ORCH_STT_PROVIDER=openai   # or deepgram | stub
export ORCH_TTS_PROVIDER=openai   # or deepgram | stub
export ORCH_OPENAI_API_KEY=sk-...
# or
export ORCH_DEEPGRAM_API_KEY=...
```

Voice endpoint `/v1/command/voice` uses provider STT when no `transcript=` is passed. Falls back to stub WAV TTS if keys/provider fail.

## 3) Multi-cluster / multi-region

Topology: [`deploy/full-gie/multi-region.yaml`](../deploy/full-gie/multi-region.yaml)

```bash
export ORCH_MULTI_REGION_CONFIG=/workspace/deploy/full-gie/multi-region.yaml
curl -s http://127.0.0.1:8090/v1/topology | jq .
curl -s http://127.0.0.1:8090/v1/prod/targets | jq .
```

Prod demo surfaces: `/demo/prod/us-east-1`, `/demo/prod/eu-west-1`.

## 4) Real CVE scanners

```bash
export ORCH_CVE_PROVIDERS=osv,snyk   # osv alone needs no key
export ORCH_SNYK_TOKEN=...           # optional
export ORCH_CVE_BLOCK_HIGH=false     # set true to block HIGH as well as CRITICAL
# optional package manifest JSON list:
export ORCH_CVE_MANIFEST_PATH=/path/to/packages.json
```

Vulnerability Engineer queries **OSV** (and Snyk when token present) during golden runs.
