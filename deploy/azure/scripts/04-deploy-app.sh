#!/usr/bin/env bash
# Helm install agents (+ workers/web in full mode) into AKS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_DIR="$ROOT/deploy/azure"
OUT="$AZURE_DIR/.last-outputs.json"
SANDBOX_MODE="${SANDBOX_MODE:-full}"
TAG="${TAG:-1.0.0}"
NS=gie

if [[ ! -f "$OUT" ]]; then
  echo "Missing $OUT — run 01-infra.sh first." >&2
  exit 1
fi

RG="${RG:-gie-sandbox}"
POSTGRES_ADMIN="${POSTGRES_ADMIN:-gieadmin}"
if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "Set POSTGRES_PASSWORD to the same value used in 01-infra.sh" >&2
  exit 1
fi

ACR_SERVER="$(jq -r '.acrLoginServer.value' "$OUT")"
PG_FQDN="$(jq -r '.postgresFqdn.value' "$OUT")"
# In-cluster Redis (Azure Cache for Redis is retiring / blocked on many subscriptions)
REDIS_HOST="${REDIS_HOST:-redis.gie.svc.cluster.local}"
REDIS_PORT="${REDIS_PORT:-6379}"
# Reuse the Context Intelligence JWT when present so Orchestrator can mint
# matching bearer tokens for live peer calls (scans, etc.).
JWT_CACHE="${JWT_CACHE:-/tmp/gie-last-jwt-secret.txt}"
if [[ -z "${JWT_SECRET:-}" ]]; then
  JWT_SECRET="$(kubectl -n "$NS" get secret context-intelligence-secrets \
    -o jsonpath='{.data.JWT_SECRET}' 2>/dev/null | base64 -d || true)"
fi
if [[ -z "${JWT_SECRET:-}" && -f "$JWT_CACHE" ]]; then
  JWT_SECRET="$(cat "$JWT_CACHE")"
fi
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
umask 077
echo "$JWT_SECRET" > "$JWT_CACHE"
API_KEY_PEPPER="${API_KEY_PEPPER:-$(openssl rand -hex 16)}"

pg_url() {
  local db="$1"
  # URL-encode is skipped; password must avoid reserved URL chars for sandbox
  echo "postgresql+asyncpg://${POSTGRES_ADMIN}:${POSTGRES_PASSWORD}@${PG_FQDN}:5432/${db}?ssl=require"
}

redis_url() {
  local db_index="$1"
  echo "redis://${REDIS_HOST}:${REDIS_PORT}/${db_index}"
}

NEO4J_PASSWORD=""
if [[ -f "$AZURE_DIR/.last-neo4j-password.txt" ]]; then
  NEO4J_PASSWORD="$(cat "$AZURE_DIR/.last-neo4j-password.txt")"
fi

helm_agent() {
  local release="$1"
  local chart="$2"
  local db="$3"
  local redis_db="$4"
  shift 4 || true

  helm upgrade --install "$release" "$ROOT/deploy/helm/$chart" \
    --namespace "$NS" --create-namespace \
    -f "$AZURE_DIR/helm/agent-values.yaml" \
    --set "image.repository=${ACR_SERVER}/gie-${chart}" \
    --set "image.tag=${TAG}" \
    --set "secrets.databaseUrl=$(pg_url "$db")" \
    --set "secrets.redisUrl=$(redis_url "$redis_db")" \
    --set "secrets.jwtSecret=${JWT_SECRET}" \
    "$@" \
    --wait --timeout 5m
}

echo "Deploying apps (SANDBOX_MODE=$SANDBOX_MODE)..."

if [[ "$SANDBOX_MODE" == "full" ]]; then
  if [[ -z "$NEO4J_PASSWORD" ]]; then
    echo "Missing Neo4j password — run 03-deploy-data.sh first." >&2
    exit 1
  fi

  # Context
  CTX_VALUES="$(mktemp)"
  sed "s|REPLACE_ACR_LOGIN_SERVER|${ACR_SERVER}|g" "$AZURE_DIR/helm/context-values.yaml" > "$CTX_VALUES"
  helm upgrade --install context-intelligence "$ROOT/deploy/helm/context-intelligence" \
    --namespace "$NS" --create-namespace \
    -f "$CTX_VALUES" \
    --set "image.repository=${ACR_SERVER}/gie-context-intelligence" \
    --set "image.tag=${TAG}" \
    --set "secrets.databaseUrl=$(pg_url gie_context)" \
    --set "secrets.redisUrl=$(redis_url 0)" \
    --set "secrets.jwtSecret=${JWT_SECRET}" \
    --set "secrets.apiKeyPepper=${API_KEY_PEPPER}" \
    --set "secrets.neo4jUser=neo4j" \
    --set "secrets.neo4jPassword=${NEO4J_PASSWORD}" \
    --wait --timeout 7m
  rm -f "$CTX_VALUES"

  # Knowledge
  KNOW_VALUES="$(mktemp)"
  sed "s|REPLACE_ACR_LOGIN_SERVER|${ACR_SERVER}|g" "$AZURE_DIR/helm/knowledge-values.yaml" > "$KNOW_VALUES"
  helm upgrade --install knowledge-intelligence "$ROOT/deploy/helm/knowledge-intelligence" \
    --namespace "$NS" --create-namespace \
    -f "$KNOW_VALUES" \
    --set "image.repository=${ACR_SERVER}/gie-knowledge-intelligence" \
    --set "image.tag=${TAG}" \
    --set "secrets.databaseUrl=$(pg_url gie_knowledge)" \
    --set "secrets.redisUrl=$(redis_url 1)" \
    --set "secrets.jwtSecret=${JWT_SECRET}" \
    --set "secrets.apiKeyPepper=${API_KEY_PEPPER}" \
    --set "secrets.neo4jUser=neo4j" \
    --set "secrets.neo4jPassword=${NEO4J_PASSWORD}" \
    --wait --timeout 7m
  rm -f "$KNOW_VALUES"

  helm_agent policy-intelligence policy-intelligence gie_policy 2
  helm_agent risk-intelligence risk-intelligence gie_risk 3
  helm_agent compliance-intelligence compliance-intelligence gie_compliance 4
  helm_agent recommendation-intelligence recommendation-intelligence gie_recommendation 5
  helm_agent policy-generator policy-generator gie_policygen 6
  helm_agent explainability-intelligence explainability-intelligence gie_explainability 7
  helm_agent validation-intelligence validation-intelligence gie_validation 8
  helm_agent learning-intelligence learning-intelligence gie_learning 9 \
    --set env.ALLOW_AUTO_PUBLISH=false
  helm_agent integration-intelligence integration-intelligence gie_integration 10

  # Workers (reuse API images + celery command)
  CTX_IMG="${ACR_SERVER}/gie-context-intelligence:${TAG}"
  KNOW_IMG="${ACR_SERVER}/gie-knowledge-intelligence:${TAG}"
  sed "s|REPLACE_IMAGE|${CTX_IMG}|g" "$AZURE_DIR/k8s/workers/context-worker.yaml" | kubectl apply -f -
  sed "s|REPLACE_IMAGE|${KNOW_IMG}|g" "$AZURE_DIR/k8s/workers/knowledge-worker.yaml" | kubectl apply -f -
  kubectl -n "$NS" rollout status deployment/context-worker --timeout=300s || true
  kubectl -n "$NS" rollout status deployment/knowledge-worker --timeout=300s || true

  # Static web
  WEB_IMG="${ACR_SERVER}/gie-web:${TAG}"
  sed "s|REPLACE_IMAGE|${WEB_IMG}|g" "$AZURE_DIR/k8s/web/gie-web.yaml" | kubectl apply -f -
  kubectl -n "$NS" rollout status deployment/gie-web --timeout=180s
fi

# Orchestrator last
ORCH_SRC="$AZURE_DIR/helm/orchestrator-values.yaml"
if [[ "$SANDBOX_MODE" == "minimal" ]]; then
  ORCH_SRC="$AZURE_DIR/helm/orchestrator-values-minimal.yaml"
fi
ORCH_VALUES="$(mktemp)"
sed "s|REPLACE_ACR_LOGIN_SERVER|${ACR_SERVER}|g" "$ORCH_SRC" > "$ORCH_VALUES"

helm upgrade --install gie-orchestrator "$ROOT/deploy/helm/orchestrator" \
  --namespace "$NS" --create-namespace \
  -f "$ORCH_VALUES" \
  --set "image.repository=${ACR_SERVER}/gie-orchestrator" \
  --set "image.tag=${TAG}" \
  --set "secrets.databaseUrl=$(pg_url gie_orchestrator)" \
  --set "secrets.redisUrl=$(redis_url 11)" \
  --set "secrets.jwtSecret=${JWT_SECRET}" \
  --wait --timeout 5m
rm -f "$ORCH_VALUES"

echo "Waiting for Orchestrator LoadBalancer..."
for _ in $(seq 1 60); do
  IP="$(kubectl -n "$NS" get svc gie-orchestrator -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  if [[ -n "${IP}" ]]; then
    echo "Orchestrator URL: http://${IP}:8091"
    echo "http://${IP}:8091" > "$AZURE_DIR/.last-url.txt"
    break
  fi
  sleep 5
done

if [[ "$SANDBOX_MODE" == "full" ]]; then
  for _ in $(seq 1 60); do
    WEB_IP="$(kubectl -n "$NS" get svc gie-web -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
    if [[ -n "${WEB_IP}" ]]; then
      echo "Web URL: http://${WEB_IP}"
      echo "http://${WEB_IP}" > "$AZURE_DIR/.last-web-url.txt"
      break
    fi
    sleep 5
  done
fi

if [[ ! -f "$AZURE_DIR/.last-url.txt" ]]; then
  echo "Service created; external IP still pending. Check: kubectl -n gie get svc"
fi

echo "Deploy complete (SANDBOX_MODE=$SANDBOX_MODE)."
