#!/usr/bin/env bash
# Fetch Go/No-Go from Orchestrator and write artifact copies.
set -euo pipefail

ORCH="${ORCH_URL:-http://127.0.0.1:8090}"
ARTIFACT_DIR="${ORCH_ARTIFACT_DIR:-/tmp/gie-fleet-artifacts}"
OUT_DIR="${1:-${ARTIFACT_DIR}}"
mkdir -p "$OUT_DIR"

TMP="$(mktemp)"
curl -sf "${ORCH}/v1/go-no-go" >"$TMP"
python3 -m json.tool <"$TMP" | tee "${OUT_DIR}/go-no-go.json" >/dev/null
python3 -m json.tool <"$TMP"
cp "$TMP" "${OUT_DIR}/go-no-go.raw.json"

READY=$(python3 -c "import json; print(json.load(open('${TMP}'))['ready_for_prod_approve'])")
SUMMARY=$(python3 -c "import json; print(json.load(open('${TMP}'))['summary'])")
rm -f "$TMP"

if [[ "$READY" == "True" ]]; then
  echo "GO_NO_GO=GO"
  exit 0
fi
echo "GO_NO_GO=NO-GO (${SUMMARY})"
exit 1
