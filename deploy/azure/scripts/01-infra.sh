#!/usr/bin/env bash
# Provision ACR + AKS + Postgres Flexible Server (multi-DB) + Redis (Basic)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
AZURE_DIR="$ROOT/deploy/azure"

LOCATION="${LOCATION:-centralus}"
RG="${RG:-gie-sandbox}"
PREFIX="${PREFIX:-gie}"
POSTGRES_ADMIN="${POSTGRES_ADMIN:-gieadmin}"
SANDBOX_MODE="${SANDBOX_MODE:-full}"

# Full sandbox defaults; override with AKS_NODE_COUNT / AKS_VM_SIZE
if [[ "$SANDBOX_MODE" == "minimal" ]]; then
  DEFAULT_NODE_COUNT=2
  DEFAULT_VM_SIZE="Standard_D2s_v3"
else
  DEFAULT_NODE_COUNT=3
  DEFAULT_VM_SIZE="Standard_D4s_v3"
fi

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "Set POSTGRES_PASSWORD (12+ chars, upper/lower/number/special)." >&2
  exit 1
fi

echo "Creating resource group $RG in $LOCATION (SANDBOX_MODE=$SANDBOX_MODE)..."
az group create --name "$RG" --location "$LOCATION" -o none

echo "Deploying Bicep (10–25 min typical for full sandbox)..."
az deployment group create \
  --resource-group "$RG" \
  --template-file "$AZURE_DIR/bicep/main.bicep" \
  --parameters @"$AZURE_DIR/bicep/parameters.dev.json" \
  --parameters namePrefix="$PREFIX" \
              postgresAdminLogin="$POSTGRES_ADMIN" \
              postgresAdminPassword="$POSTGRES_PASSWORD" \
              aksNodeCount="${AKS_NODE_COUNT:-$DEFAULT_NODE_COUNT}" \
              aksNodeVmSize="${AKS_VM_SIZE:-$DEFAULT_VM_SIZE}" \
  --query properties.outputs \
  -o json | tee "$AZURE_DIR/.last-outputs.json"

echo "Fetching AKS credentials..."
AKS_NAME="$(jq -r '.aksName.value' "$AZURE_DIR/.last-outputs.json")"
az aks get-credentials --resource-group "$RG" --name "$AKS_NAME" --overwrite-existing

kubectl apply -f "$AZURE_DIR/k8s/namespace.yaml"

echo "Infra ready. Outputs saved to deploy/azure/.last-outputs.json"
