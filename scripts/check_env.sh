#!/usr/bin/env bash
# Fails when values that must be identical across modules differ.
# Ex: ./scripts/check_env.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)/modules"
get() { grep -E "^$2=" "$root/$1/.env" 2>/dev/null | cut -d= -f2- || true; }
status=0

check() { # <var> <module-a> <module-b>
  if [ "$(get "$2" "$1")" != "$(get "$3" "$1")" ]; then
    echo "[check-env] $1 differs between $2/.env and $3/.env"
    status=1
  fi
}

check GARAGE_DEFAULT_ACCESS_KEY common-services langfuse
check GARAGE_DEFAULT_SECRET_KEY common-services langfuse
[ "$status" -eq 0 ] && echo "[check-env] ok"
exit "$status"
