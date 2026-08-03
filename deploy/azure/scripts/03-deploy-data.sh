#!/usr/bin/env bash
# Deploy in-cluster Redis (always) + Neo4j/Qdrant/Kafka (full sandbox)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_DIR="$ROOT/deploy/azure"
SANDBOX_MODE="${SANDBOX_MODE:-full}"

kubectl apply -f "$AZURE_DIR/k8s/namespace.yaml"

# Redis is always required (Azure Cache for Redis is retiring / blocked on many subscriptions)
echo "Applying in-cluster Redis..."
kubectl apply -f "$AZURE_DIR/k8s/data-plane/redis.yaml"
kubectl -n gie rollout status deployment/redis --timeout=180s
echo "  redis.gie.svc.cluster.local:6379"

if [[ "$SANDBOX_MODE" == "minimal" ]]; then
  echo "SANDBOX_MODE=minimal — skipping Neo4j/Qdrant/Kafka."
  exit 0
fi

NEO4J_PASSWORD="${NEO4J_PASSWORD:-$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)}"
# NEO4J_AUTH format: user/password
NEO4J_AUTH="neo4j/${NEO4J_PASSWORD}"

kubectl -n gie create secret generic gie-dataplane-secrets \
  --from-literal=neo4j-auth="$NEO4J_AUTH" \
  --from-literal=neo4j-user=neo4j \
  --from-literal=neo4j-password="$NEO4J_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "$NEO4J_PASSWORD" > "$AZURE_DIR/.last-neo4j-password.txt"
chmod 600 "$AZURE_DIR/.last-neo4j-password.txt"

echo "Applying Neo4j, Qdrant, Kafka..."
kubectl apply -f "$AZURE_DIR/k8s/data-plane/neo4j.yaml"
kubectl apply -f "$AZURE_DIR/k8s/data-plane/qdrant.yaml"
kubectl apply -f "$AZURE_DIR/k8s/data-plane/kafka.yaml"

echo "Waiting for Neo4j, Qdrant, Kafka to become ready..."
kubectl -n gie rollout status deployment/neo4j --timeout=300s
kubectl -n gie rollout status deployment/qdrant --timeout=300s
kubectl -n gie rollout status deployment/kafka --timeout=360s

echo "Data plane ready."
echo "  neo4j.gie.svc.cluster.local:7687"
echo "  qdrant.gie.svc.cluster.local:6333"
echo "  kafka.gie.svc.cluster.local:9092"
