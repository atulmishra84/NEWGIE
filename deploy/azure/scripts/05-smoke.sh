#!/usr/bin/env bash
# Smoke test full or minimal Azure sandbox
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_DIR="$ROOT/deploy/azure"
SANDBOX_MODE="${SANDBOX_MODE:-full}"
NS=gie

if [[ -n "${BASE_URL:-}" ]]; then
  BASE="$BASE_URL"
elif [[ -f "$AZURE_DIR/.last-url.txt" ]]; then
  BASE="$(cat "$AZURE_DIR/.last-url.txt")"
else
  IP="$(kubectl -n "$NS" get svc gie-orchestrator -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
  BASE="http://${IP}:8091"
fi

echo "Smoke against Orchestrator $BASE (SANDBOX_MODE=$SANDBOX_MODE)"
curl -fsS "$BASE/healthz" | jq .

STATUS="$(curl -fsS "$BASE/status" -H 'x-tenant-id: azure-demo')"
echo "$STATUS" | jq '{healthy: .data.healthy, agents: (.data.agents|length), active: .data.active_executions}'

ANALYZE="$(curl -fsS -X POST "$BASE/analyze" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: azure-demo' \
  -d '{"tenant_id":"azure-demo","source":{"type":"folder","path":"/demo"},"mode":"sync","options":{"parallel":true},"cache":true}')"
echo "$ANALYZE" | jq '{status: .data.status, steps: [.data.steps[].step_id], step_statuses: [.data.steps[].status], confidence: .data.confidence.score, duration_ms: .data.duration_ms}'

if [[ "$SANDBOX_MODE" == "full" ]]; then
  echo "Checking peer agents inside the cluster..."
  AGENTS=(
    "context-intelligence:8080:/healthz"
    "knowledge-intelligence:8081:/healthz"
    "policy-intelligence:8082:/healthz"
    "risk-intelligence:8083:/healthz"
    "compliance-intelligence:8084:/healthz"
    "recommendation-intelligence:8085:/healthz"
    "policy-generator:8086:/healthz"
    "explainability-intelligence:8087:/healthz"
    "validation-intelligence:8088:/healthz"
    "learning-intelligence:8089:/healthz"
    "integration-intelligence:8090:/healthz"
  )

  kubectl -n "$NS" delete pod gie-smoke-curl --ignore-not-found >/dev/null 2>&1 || true
  kubectl -n "$NS" run gie-smoke-curl --image=curlimages/curl:8.5.0 --restart=Never --command -- sleep 120 >/dev/null
  kubectl -n "$NS" wait --for=condition=Ready pod/gie-smoke-curl --timeout=60s

  for entry in "${AGENTS[@]}"; do
    IFS=':' read -r svc port path <<<"$entry"
    echo -n "  ${svc}${path} ... "
    kubectl -n "$NS" exec gie-smoke-curl -- curl -fsS "http://${svc}:${port}${path}" >/dev/null
    echo "ok"
  done

  echo -n "  context-intelligence/ready ... "
  kubectl -n "$NS" exec gie-smoke-curl -- curl -fsS "http://context-intelligence:8080/ready" | jq -c .
  echo "ok"

  # Live mode should not mark every step as pure cache/sim without agents — require >=1 succeeded step
  SUCCEEDED="$(echo "$ANALYZE" | jq '[.data.steps[] | select(.status=="succeeded" or .status=="cached")] | length')"
  if [[ "${SUCCEEDED}" -lt 1 ]]; then
    echo "Expected at least one succeeded/cached step in live analyze; got ${SUCCEEDED}" >&2
    kubectl -n "$NS" delete pod gie-smoke-curl --ignore-not-found >/dev/null 2>&1 || true
    exit 1
  fi

  if [[ -f "$AZURE_DIR/.last-web-url.txt" ]]; then
    WEB="$(cat "$AZURE_DIR/.last-web-url.txt")"
    echo "Checking web UI $WEB ..."
    curl -fsS "$WEB/" >/dev/null
    curl -fsS "$WEB/dashboard.html" >/dev/null
    echo "Web OK"
  fi

  kubectl -n "$NS" delete pod gie-smoke-curl --ignore-not-found >/dev/null 2>&1 || true
fi

echo "SMOKE OK"
