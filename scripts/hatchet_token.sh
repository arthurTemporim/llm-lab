#!/usr/bin/env bash
# Creates a Hatchet API token for a tenant and prints it. Workers and clients set it as
# HATCHET_CLIENT_TOKEN. The tenant defaults to the one seeded at first start (slug "default").
# Ex: ./scripts/hatchet_token.sh
#     ./scripts/hatchet_token.sh <tenant-slug>
set -euo pipefail

slug="${1:-default}"
[[ "$slug" =~ ^[a-z0-9-]+$ ]] || { echo "[hatchet] invalid tenant slug: $slug" >&2; exit 1; }

tenant_id="$(docker exec postgres sh -c 'psql -U "$POSTGRES_USER" -d hatchet -tAc "$1"' -- \
  "SELECT id FROM \"Tenant\" WHERE slug = '${slug}'")"
[ -n "$tenant_id" ] || { echo "[hatchet] tenant '${slug}' not found (is hatchet up?)" >&2; exit 1; }

token="$(docker exec hatchet-lite /hatchet-admin token create --config /config --tenant-id "$tenant_id" \
  | tail -n1 | tr -d '\r')"
[ -n "$token" ] || { echo "[hatchet] token creation failed" >&2; exit 1; }
echo "$token"
