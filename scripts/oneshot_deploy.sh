#!/usr/bin/env bash
# One-shot Full+GIE deploy to live staging.
# Uses Docker Compose when available; otherwise local uvicorn stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ARTIFACT_DIR="${ORCH_ARTIFACT_DIR:-/tmp/gie-fleet-artifacts}"
mkdir -p "$ARTIFACT_DIR"

echo "==> Full+GIE one-shot deploy"
"${ROOT}/scripts/provision_live_staging.sh"

echo "==> Waiting for Chief Orchestrator health"
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8090/healthz >/dev/null; then
    echo "Orchestrator healthy"
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    echo "ERROR: Orchestrator failed to become healthy" >&2
    if [[ -f "${ARTIFACT_DIR}/logs/orch.log" ]]; then
      tail -n 50 "${ARTIFACT_DIR}/logs/orch.log" >&2 || true
    fi
    exit 1
  fi
  sleep 2
done

echo "==> Waiting for Risk + Policy"
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8091/healthz >/dev/null \
    && curl -sf http://127.0.0.1:8092/healthz >/dev/null; then
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "ERROR: Risk/Policy not healthy" >&2
    exit 1
  fi
  sleep 2
done

echo "==> Smoke: text status"
curl -sf -X POST http://127.0.0.1:8090/v1/command \
  -H 'content-type: application/json' \
  -d '{"text":"status","channel":"text"}' >/tmp/gie-smoke-status.json

echo "==> Smoke: voice round-trip"
python3 - <<'PY'
import json, struct, wave, urllib.request
wav = "/tmp/gie-smoke.wav"
with wave.open(wav, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
    wf.writeframes(struct.pack("<h", 0) * 800)
import uuid
boundary = "----smoke" + uuid.uuid4().hex
parts = []
parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"transcript\"\r\n\r\nstatus\r\n".encode())
with open(wav, "rb") as f:
    audio = f.read()
parts.append(
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"s.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode()
    + audio + b"\r\n" + f"--{boundary}--\r\n".encode()
)
req = urllib.request.Request(
    "http://127.0.0.1:8090/v1/command/voice",
    data=b"".join(parts),
    headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    body = json.loads(resp.read().decode())
assert "tts_wav_base64" in body, body
print("voice smoke ok")
PY

echo "==> Fleet status"
curl -sf http://127.0.0.1:8090/v1/fleet | python3 -m json.tool | head -n 50

date -u +"{\"ready_at\":\"%Y-%m-%dT%H:%M:%SZ\"}" > "${ARTIFACT_DIR}/LIVE_STAGING_READY.json"
echo "LIVE_STAGING_READY" | tee "${ARTIFACT_DIR}/LIVE_STAGING_READY"
echo "Orchestrator: http://127.0.0.1:8090"
echo "Risk:         http://127.0.0.1:8091"
echo "Policy:       http://127.0.0.1:8092"
echo "Context:      http://127.0.0.1:8080 (optional; stub used if down)"
echo "Mode:         $(cat "${ARTIFACT_DIR}/staging_mode" 2>/dev/null || echo unknown)"
