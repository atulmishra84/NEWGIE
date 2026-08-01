#!/usr/bin/env bash
# Live-test script LT-1..LT-5 against Full+GIE staging Orchestrator.
set -euo pipefail

ORCH="${ORCH_URL:-http://127.0.0.1:8090}"
PASS=0
FAIL=0
declare -a FAILED

check() {
  local name="$1"
  shift
  if "$@"; then
    echo "PASS  $name"
    PASS=$((PASS + 1))
    return 0
  else
    echo "FAIL  $name"
    FAIL=$((FAIL + 1))
    FAILED+=("$name")
    return 1
  fi
}

json_field() {
  python - "$1" "$2" <<'PY'
import json, sys
path, raw = sys.argv[1], sys.stdin.read()
data = json.loads(raw)
cur = data
for part in path.split("."):
    if part.endswith("]"):
        name, idx = part[:-1].split("[")
        cur = cur[name][int(idx)]
    else:
        cur = cur[part]
print(cur)
PY
}

echo "==> LT-1 Ingress (text + voice)"
STATUS_JSON=$(curl -sf -X POST "$ORCH/v1/command" -H 'content-type: application/json' \
  -d '{"text":"status","channel":"text"}')
check "LT-1.1 text status" bash -c "echo '$STATUS_JSON' | grep -q '\"fleet_size\"'"

# Create tiny wav for voice channel presence
WAV=/tmp/gie-live-test.wav
python - <<'PY'
import struct, wave
with wave.open("/tmp/gie-live-test.wav", "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
    wf.writeframes(struct.pack("<h", 0) * 1600)
PY

VOICE_JSON=$(curl -sf -X POST "$ORCH/v1/command/voice" \
  -F "transcript=status" \
  -F "audio=@${WAV};type=audio/wav")
check "LT-1.2 voice status + tts" bash -c "echo '$VOICE_JSON' | grep -q tts_wav_base64"

AMBIG=$(curl -sf -X POST "$ORCH/v1/command/voice" -F "transcript=ummm" -F "audio=@${WAV};type=audio/wav")
check "LT-1.3 ambiguous voice no build" bash -c "echo '$AMBIG' | grep -q needs_clarification && ! echo '$AMBIG' | grep -q '\"run\":'"

echo "==> LT-2 Full lane golden run"
GOLDEN=$(curl -sf -X POST "$ORCH/v1/command" -H 'content-type: application/json' \
  -d '{"text":"Build the golden demo app, run full security and QA, scan with GIE, deploy to staging, and show me the result.","channel":"text"}')
check "LT-2.1 delivery steps present" bash -c "echo '$GOLDEN' | grep -q product-manager && echo '$GOLDEN' | grep -q senior-developer"
check "LT-2.2 security lane present" bash -c "echo '$GOLDEN' | grep -q vulnerability-engineer && echo '$GOLDEN' | grep -q compliance-officer"
check "LT-2.3 release/ops present" bash -c "echo '$GOLDEN' | grep -q devops && echo '$GOLDEN' | grep -q sre-observability"
check "LT-2.4 GIE context model id" bash -c "echo '$GOLDEN' | grep -q gie_context_model_id"
check "LT-2.5 risk and policy" bash -c "echo '$GOLDEN' | grep -q '\"decision\"' && echo '$GOLDEN' | grep -q '\"score\"'"
check "LT-2.6 demo package staging url" bash -c "echo '$GOLDEN' | grep -q staging_url && echo '$GOLDEN' | grep -q succeeded"

echo "==> LT-3 Gate behavior"
CRIT=$(curl -sf -X POST "$ORCH/v1/command" -H 'content-type: application/json' \
  -d '{"text":"Build the golden demo app, run full security and QA, scan with GIE, deploy to staging, and show me the result.","channel":"text","inject_critical_finding":true}')
check "LT-3.1 critical finding blocks" bash -c "echo '$CRIT' | grep -q blocked"

DENY=$(curl -sf -X POST "$ORCH/v1/command" -H 'content-type: application/json' \
  -d '{"text":"Build the golden demo app, run full security and QA, scan with GIE, deploy to staging, and show me the result.","channel":"text","force_policy_deny":true}')
check "LT-3.2 policy deny" bash -c "echo '$DENY' | grep -q blocked && echo '$DENY' | grep -qi policy"

NOCONF=$(curl -sf -X POST "$ORCH/v1/command/voice" -F "transcript=approve production please" -F "audio=@${WAV};type=audio/wav")
check "LT-3.3 voice prod without confirm rejected" bash -c "echo '$NOCONF' | grep -Eq 'rejected|needs_clarification|confirm'"

DRY=$(curl -sf -X POST "$ORCH/v1/command" -H 'content-type: application/json' \
  -d '{"text":"approve production deploy","channel":"text","prod_confirm_phrase":"approve production deploy"}')
check "LT-3.4 prod approve dry-run no customer prod" bash -c "echo '$DRY' | grep -q customer_prod_touched && echo '$DRY' | grep -q false"

echo "==> LT-4 Change-request follow-up"
CHG=$(curl -sf -X POST "$ORCH/v1/command" -H 'content-type: application/json' \
  -d '{"text":"Add a small feature X to the golden app","channel":"text"}')
check "LT-4.1 change request succeeds" bash -c "echo '$CHG' | grep -q succeeded && echo '$CHG' | grep -q feature-x"
check "LT-4.2 demo still healthy" bash -c "curl -sf '$ORCH/demo/golden' | grep -q ok"

echo "==> LT-5 Observability and audit"
FLEET=$(curl -sf "$ORCH/v1/fleet")
check "LT-5.3 agent registry >= 16" bash -c "python -c \"import json,sys; d=json.loads(sys.argv[1]); assert d['fleet_size']>=16 and d['healthy']>=16\" '$FLEET'"
VOICE2=$(curl -sf -X POST "$ORCH/v1/command/voice" -F "transcript=status" -F "audio=@${WAV};type=audio/wav")
check "LT-5.2 voice transcript stored in response" bash -c "echo '$VOICE2' | grep -q '\"transcript\": \"status\"'"

# Mark live checks for go/no-go via a successful golden already stored
GNG=$(curl -sf "$ORCH/v1/go-no-go")
echo "==> Go/No-Go"
echo "$GNG" | python -m json.tool

echo ""
echo "Passed: $PASS  Failed: $FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  echo "Failed checks: ${FAILED[*]}"
  exit 1
fi
echo "LIVE_TEST_GREEN"
