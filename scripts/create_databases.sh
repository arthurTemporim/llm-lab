#!/usr/bin/env bash
# Creates the databases listed in POSTGRES_DATABASES (common-services/.env) in the
# shared postgres, with the vector extension. Idempotent, works on existing volumes.
# Ex: ./scripts/create_databases.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$root/modules/common-services/.env"
[ -f "$env_file" ] || env_file="$root/modules/common-services/example.env"
databases="$(grep -E '^POSTGRES_DATABASES=' "$env_file" | cut -d= -f2-)"

psql_exec() { docker exec postgres sh -c 'psql -U "$POSTGRES_USER" "$@"' -- "$@"; }

for _ in $(seq 1 30); do
  docker exec postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d postgres' >/dev/null 2>&1 && break
  sleep 2
done

for db in $databases; do
  if psql_exec -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'" | grep -q 1; then
    echo "[databases] '${db}' already exists"
  else
    psql_exec -d postgres -c "CREATE DATABASE ${db}"
    echo "[databases] '${db}' created"
  fi
  psql_exec -d "$db" -c "CREATE EXTENSION IF NOT EXISTS vector" >/dev/null
done
