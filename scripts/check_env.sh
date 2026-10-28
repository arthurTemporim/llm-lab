#!/usr/bin/env bash
# Checks the global env file (modules/common-services/.env), which the Makefile loads before every
# module's .env:
#   - it has every variable of its example.env (older .env files miss the new ones)
#   - no module .env redefines a global variable with another value (the module would win)
# A module may pass a global value through as NAME=${NAME}.
# Ex: ./scripts/check_env.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)/modules"
global="$root/common-services/.env"
status=0
fail() { echo "[check-env] $*"; status=1; }

[ -f "$global" ] || { fail "missing common-services/.env: run make create-envs"; exit 1; }

names() { grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$1" | tr -d = || true; }
value() { grep -E "^$2=" "$1" | tail -n1 | cut -d= -f2- || true; }

for var in $(names "$root/common-services/example.env"); do
  grep -qE "^$var=" "$global" || fail "common-services/.env is missing $var (copy it from example.env)"
done

for env in "$root"/*/.env; do
  m="$(basename "$(dirname "$env")")"
  [ "$m" = common-services ] && continue
  for var in $(names "$env"); do
    grep -qE "^$var=" "$global" || continue
    v="$(value "$env" "$var")"
    if [ "$v" != "\${$var}" ] && [ "$v" != "$(value "$global" "$var")" ]; then
      fail "$m/.env redefines $var, which is set in common-services/.env: remove it or use $var=\${$var}"
    fi
  done
done

# Renamed in the naming cleanup (docs/CONVENTIONS.md); older .env files still use the old names
if grep -qE '^CLICKHOUSE_(MIGRATION_)?URL=.*//clickhouse:' "$root/langfuse/.env" 2>/dev/null; then
  fail "langfuse/.env: the ClickHouse service is now langfuse-clickhouse; fix CLICKHOUSE_URL and CLICKHOUSE_MIGRATION_URL"
fi
if grep -qE '^PROMETHEUS_PORT=' "$root/litellm/.env" 2>/dev/null; then
  echo "[check-env] warning: litellm/.env: PROMETHEUS_PORT is now LITELLM_PROMETHEUS_PORT (the old name is ignored)"
fi

[ "$status" -eq 0 ] && echo "[check-env] ok"
exit "$status"
