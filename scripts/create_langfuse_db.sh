#!/usr/bin/env bash
# Creates the "langfuse" database in the shared postgres if it does not exist yet.
set -euo pipefail

PG_USER="${POSTGRES_USER:-lang}"
DB_NAME="${LANGFUSE_DB_NAME:-langfuse}"

if docker exec postgres psql -U "$PG_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  echo "[langfuse-db] database '${DB_NAME}' already exists"
else
  docker exec postgres psql -U "$PG_USER" -d postgres -c "CREATE DATABASE ${DB_NAME}"
  echo "[langfuse-db] database '${DB_NAME}' created"
fi
