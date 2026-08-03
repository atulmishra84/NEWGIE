#!/usr/bin/env bash
# Smoke-test local docker-compose GIE stack
set -euo pipefail

ORCH="${ORCH_URL:-http://127.0.0.1:8091}"
WEB="${WEB_URL:-http://127.0.0.1:5173}"

echo "== Orchestrator health =="
curl -fsS "$ORCH/healthz" | jq .

echo "== Peer /healthz =="
for entry in \
  "8080:context" \
  "8081:knowledge" \
  "8082:policy" \
  "8083:risk" \
  "8084:compliance" \
  "8085:recommendation" \
  "8086:generator" \
  "8087:explainability" \
  "8088:validation" \
  "8089:learning" \
  "8090:integration"
do
  IFS=':' read -r port name <<<"$entry"
  echo -n "  :${port} (${name}) ... "
  curl -fsS "http://127.0.0.1:${port}/healthz" >/dev/null
  echo ok
done

echo "== Orchestrator status =="
curl -fsS "$ORCH/status" -H 'x-tenant-id: local-demo' \
  | jq '{healthy: .data.healthy, agents: [.data.agents[] | {id: .agent_id, healthy, base_url}]}'

echo "== Analyze (live peers) =="
ANALYZE="$(curl -fsS -X POST "$ORCH/analyze" \
  -H 'content-type: application/json' \
  -H 'x-tenant-id: local-demo' \
  -d '{"tenant_id":"local-demo","source":{"type":"folder","path":"/demo"},"mode":"sync","options":{"parallel":true},"cache":false}')"
echo "$ANALYZE" | jq '{status: .data.status, steps: [.data.steps[] | {id: .step_id, status, summary: .output.summary}], confidence: .data.confidence.score}'

SUCCEEDED="$(echo "$ANALYZE" | jq '[.data.steps[] | select(.status=="succeeded" or .status=="cached")] | length')"
if [[ "$SUCCEEDED" -lt 1 ]]; then
  echo "FAIL: expected succeeded/cached steps, got $SUCCEEDED" >&2
  exit 1
fi

# Live invoker summaries mention "reached at" — simulated say "analysis complete"
LIVE_HINTS="$(echo "$ANALYZE" | jq '[.data.steps[].output.summary // "" | select(test("reached at"))] | length')"
echo "Live peer invoke hints: $LIVE_HINTS"

echo "== Web =="
curl -fsS "$WEB/" >/dev/null
curl -fsS "$WEB/dashboard.html" >/dev/null
echo "Web OK"

echo "LOCAL SMOKE OK"
