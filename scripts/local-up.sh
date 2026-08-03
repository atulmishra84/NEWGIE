#!/usr/bin/env bash
# Bring up the full local GIE stack.
# Uses host networking override when Docker bridge networking is unavailable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-0}"
export COMPOSE_DOCKER_CLI_BUILD="${COMPOSE_DOCKER_CLI_BUILD:-0}"

MODE="${LOCAL_NET_MODE:-auto}" # auto | bridge | host

compose() {
  if [[ "$MODE" == "host" ]]; then
    docker compose -f docker-compose.yml -f docker-compose.host.yml "$@"
  else
    docker compose "$@"
  fi
}

detect_mode() {
  if [[ "$MODE" != "auto" ]]; then
    return
  fi
  # Probe: start is expensive; prefer host if nftables/bridge looks broken.
  if ! iptables -L >/dev/null 2>&1; then
    MODE=host
    return
  fi
  # Default to host in CI sandboxes; override with LOCAL_NET_MODE=bridge on real Docker Desktop/Linux.
  if [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    MODE=host
  else
    MODE=host
  fi
}

detect_mode
echo "Using LOCAL_NET_MODE=$MODE"

compose down --remove-orphans >/dev/null 2>&1 || true
compose up -d --build "$@"
echo "Stack starting. Smoke with: ./scripts/local-smoke.sh"
