#!/usr/bin/env bash
# Rollback Full+GIE staging app plane.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="${ORCH_ARTIFACT_DIR:-/tmp/gie-fleet-artifacts}"
MODE="$(cat "${ARTIFACT_DIR}/staging_mode" 2>/dev/null || echo local)"

echo "==> Rolling back Full+GIE staging (mode=${MODE})"
if [[ "$MODE" == "docker" ]] && command -v docker >/dev/null 2>&1; then
  cd "$ROOT"
  if docker info >/dev/null 2>&1; then
    docker compose -f docker-compose.yml -f docker-compose.full-gie.yml down || true
  else
    sudo docker compose -f docker-compose.yml -f docker-compose.full-gie.yml down || true
  fi
else
  PID_DIR="${ARTIFACT_DIR}/pids"
  for name in orch risk policy context; do
    if [[ -f "${PID_DIR}/${name}.pid" ]]; then
      kill "$(cat "${PID_DIR}/${name}.pid")" 2>/dev/null || true
      rm -f "${PID_DIR}/${name}.pid"
    fi
  done
  pkill -f "uvicorn chief_orchestrator.app:app" 2>/dev/null || true
  pkill -f "uvicorn risk_assessment.app:app" 2>/dev/null || true
  pkill -f "uvicorn policy_engine.app:app" 2>/dev/null || true
  pkill -f "scripts/context_stub.py" 2>/dev/null || true
fi
rm -f "${ARTIFACT_DIR}/LIVE_STAGING_READY" "${ARTIFACT_DIR}/LIVE_STAGING_READY.json"
echo "ROLLBACK_COMPLETE"
