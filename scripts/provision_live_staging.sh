#!/usr/bin/env bash
# Provision Full+GIE live staging (Docker Compose when available, else local uvicorn).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${STAGING_MODE:-auto}"
ARTIFACT_DIR="${ORCH_ARTIFACT_DIR:-/tmp/gie-fleet-artifacts}"
PID_DIR="${ARTIFACT_DIR}/pids"
LOG_DIR="${ARTIFACT_DIR}/logs"

mkdir -p "$ARTIFACT_DIR" "$PID_DIR" "$LOG_DIR"

docker_bin() {
  if docker info >/dev/null 2>&1; then
    echo "docker"
  elif sudo docker info >/dev/null 2>&1; then
    echo "sudo docker"
  else
    return 1
  fi
}

have_docker() {
  command -v docker >/dev/null 2>&1 && docker_bin >/dev/null 2>&1
}

provision_docker() {
  echo "==> Provisioning live staging via Docker Compose"
  local dc
  dc="$(docker_bin)"
  # shellcheck disable=SC2086
  $dc compose -f docker-compose.yml -f docker-compose.full-gie.yml up -d --build
  echo "docker" > "${ARTIFACT_DIR}/staging_mode"
}

stop_local() {
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
}

provision_local() {
  echo "==> Provisioning live staging via local uvicorn (no Docker)"
  export PATH="${HOME}/.local/bin:${PATH}"
  python3 -m pip install -q -e packages/gie-contracts \
    -e agents/chief-orchestrator \
    -e agents/risk-assessment \
    -e agents/policy-engine

  stop_local
  sleep 1

  python3 "${ROOT}/scripts/context_stub.py" >"${LOG_DIR}/context.log" 2>&1 &
  echo $! >"${PID_DIR}/context.pid"

  PYTHONPATH=agents/risk-assessment/src \
    uvicorn risk_assessment.app:app --host 127.0.0.1 --port 8091 \
    >"${LOG_DIR}/risk.log" 2>&1 &
  echo $! >"${PID_DIR}/risk.pid"

  PYTHONPATH=agents/policy-engine/src \
    uvicorn policy_engine.app:app --host 127.0.0.1 --port 8092 \
    >"${LOG_DIR}/policy.log" 2>&1 &
  echo $! >"${PID_DIR}/policy.pid"

  ORCH_ENV=staging \
  ORCH_STAGING_BASE_URL=http://127.0.0.1:8090 \
  ORCH_GOLDEN_STAGING_URL=http://127.0.0.1:8090/demo/golden \
  ORCH_CONTEXT_INTELLIGENCE_URL="${ORCH_CONTEXT_INTELLIGENCE_URL:-http://127.0.0.1:8080}" \
  ORCH_RISK_ASSESSMENT_URL=http://127.0.0.1:8091 \
  ORCH_POLICY_ENGINE_URL=http://127.0.0.1:8092 \
  ORCH_ALLOW_CUSTOMER_PROD=false \
  ORCH_ARTIFACT_DIR="${ARTIFACT_DIR}" \
  PYTHONPATH=agents/chief-orchestrator/src \
    uvicorn chief_orchestrator.app:app --host 127.0.0.1 --port 8090 \
    >"${LOG_DIR}/orch.log" 2>&1 &
  echo $! >"${PID_DIR}/orch.pid"

  echo "local" > "${ARTIFACT_DIR}/staging_mode"
}

case "$MODE" in
  docker)
    provision_docker
    ;;
  local)
    provision_local
    ;;
  auto)
    if have_docker; then
      provision_docker
    else
      echo "==> Docker not available; falling back to local staging"
      provision_local
    fi
    ;;
  *)
    echo "Unknown STAGING_MODE=$MODE (use auto|docker|local)" >&2
    exit 2
    ;;
esac

echo "==> Staging provisioned (mode=$(cat "${ARTIFACT_DIR}/staging_mode"))"
echo "Artifacts: ${ARTIFACT_DIR}"
