#!/bin/bash
# Creates extra logical databases for GIE agents (runs once on first Postgres boot).
set -euo pipefail

dbs=(
  gie_context
  gie_knowledge
  gie_policy
  gie_risk
  gie_compliance
  gie_recommendation
  gie_policygen
  gie_explainability
  gie_validation
  gie_learning
  gie_integration
  gie_orchestrator
)

for db in "${dbs[@]}"; do
  exists="$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'")"
  if [[ "$exists" != "1" ]]; then
    echo "Creating database ${db}"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -c "CREATE DATABASE ${db}"
  else
    echo "Database ${db} already exists"
  fi
done
