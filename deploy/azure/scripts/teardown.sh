#!/usr/bin/env bash
# Destroy the sandbox resource group (irreversible)
set -euo pipefail

RG="${RG:-gie-sandbox}"

echo "This deletes resource group: $RG"
read -r -p "Type the RG name to confirm: " CONFIRM
if [[ "$CONFIRM" != "$RG" ]]; then
  echo "Aborted."
  exit 1
fi

az group delete --name "$RG" --yes --no-wait
echo "Delete started for $RG"
