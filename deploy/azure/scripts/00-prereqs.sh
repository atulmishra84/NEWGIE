#!/usr/bin/env bash
set -euo pipefail

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required tool: $1" >&2
    exit 1
  }
}

need az
need docker
need helm
need kubectl
need jq
need openssl

az account show >/dev/null

echo "Prereqs OK"
az account show --query '{subscription:name, id:id, tenant:tenantId}' -o table

cat <<'EOF'

Sandbox notes
-------------
- SANDBOX_MODE=full (default): 3× Standard_D4s_v5 + 12 DBs + Neo4j/Qdrant/Kafka + all agents.
  Expect roughly $400–700+/month while running; tear down when idle.
- SANDBOX_MODE=minimal: 2× Standard_B2s, Orchestrator-only with SIMULATE_AGENTS=true.
- Building all 12 images needs ~10–20 GB free Docker disk.

EOF
