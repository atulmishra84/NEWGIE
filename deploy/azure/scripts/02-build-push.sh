#!/usr/bin/env bash
# Build agent images (and web) and push to ACR
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_DIR="$ROOT/deploy/azure"
OUT="$AZURE_DIR/.last-outputs.json"
SANDBOX_MODE="${SANDBOX_MODE:-full}"
TAG="${TAG:-1.0.0}"

if [[ ! -f "$OUT" ]]; then
  echo "Missing $OUT — run 01-infra.sh first." >&2
  exit 1
fi

ACR_NAME="$(jq -r '.acrName.value' "$OUT")"
ACR_SERVER="$(jq -r '.acrLoginServer.value' "$OUT")"

echo "Logging into ACR $ACR_NAME..."
az acr login --name "$ACR_NAME"

IMAGES_FILE="$AZURE_DIR/.last-images.txt"
: > "$IMAGES_FILE"

build_push() {
  local name="$1"
  local dockerfile="$2"
  local context="${3:-$ROOT}"
  local image="$ACR_SERVER/gie-${name}:${TAG}"
  echo "Building $image ..."
  docker build -f "$dockerfile" -t "$image" "$context"
  echo "Pushing $image ..."
  docker push "$image"
  echo "$image" >> "$IMAGES_FILE"
}

# Always build orchestrator
build_push "orchestrator" "$ROOT/agents/orchestrator/Dockerfile" "$ROOT"

if [[ "$SANDBOX_MODE" == "full" ]]; then
  build_push "context-intelligence" "$ROOT/agents/context-intelligence/Dockerfile" "$ROOT"
  build_push "knowledge-intelligence" "$ROOT/agents/knowledge-intelligence/Dockerfile" "$ROOT"
  build_push "policy-intelligence" "$ROOT/agents/policy-intelligence/Dockerfile" "$ROOT"
  build_push "risk-intelligence" "$ROOT/agents/risk-intelligence/Dockerfile" "$ROOT"
  build_push "compliance-intelligence" "$ROOT/agents/compliance-intelligence/Dockerfile" "$ROOT"
  build_push "recommendation-intelligence" "$ROOT/agents/recommendation-intelligence/Dockerfile" "$ROOT"
  build_push "policy-generator" "$ROOT/agents/policy-generator/Dockerfile" "$ROOT"
  build_push "explainability-intelligence" "$ROOT/agents/explainability-intelligence/Dockerfile" "$ROOT"
  build_push "validation-intelligence" "$ROOT/agents/validation-intelligence/Dockerfile" "$ROOT"
  build_push "learning-intelligence" "$ROOT/agents/learning-intelligence/Dockerfile" "$ROOT"
  build_push "integration-intelligence" "$ROOT/agents/integration-intelligence/Dockerfile" "$ROOT"
  build_push "web" "$ROOT/web/Dockerfile" "$ROOT/web"
fi

echo "Pushed images (SANDBOX_MODE=$SANDBOX_MODE):"
cat "$IMAGES_FILE"
echo "$ACR_SERVER/gie-orchestrator:$TAG" > "$AZURE_DIR/.last-image.txt"
