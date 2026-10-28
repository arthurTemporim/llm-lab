#!/usr/bin/env bash
# Fails when a module breaks the repo conventions (CLAUDE.md, docs/MODULES.md): module files
# and Makefile registration, ${VAR}s documented in example.env, pinned images, unique host ports.
# Reads the resolved compose config, so the .env files must exist (make create-envs).
# Ex: ./scripts/check_conventions.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
status=0
fail() { echo "[conventions] $*"; status=1; }

# The one image allowed to float (see modules/common-services/docker-compose.yml)
unpinned_ok="cgr.dev/chainguard/minio:latest"

pinned() { # <image>: true when it has a digest or a tag other than latest
  local name="${1##*/}" # drop the registry, whose port would look like a tag
  [[ "$1" == *@sha256:* ]] || { [[ "$name" == *:* ]] && [ "${name##*:}" != latest ]; }
}

check_image() { # <module> <where> <image>
  [ "$3" = "$unpinned_ok" ] || pinned "$3" || fail "$1: $2 uses unpinned image $3"
}

# shellcheck disable=SC2016 # $(MODULES) is expanded by make, not bash
registered=" $(make -s --no-print-directory -C "$root" --eval 'print-modules: ; @echo $(MODULES)' print-modules) "
for m in $registered; do
  [ -d "$root/modules/$m" ] || fail "$m is in the Makefile MODULES list but modules/$m does not exist"
done

declare -A port_owner
for dir in "$root"/modules/*/; do
  dir="${dir%/}"
  m="$(basename "$dir")"
  [[ "$registered" == *" $m "* ]] || fail "$m is not in the Makefile MODULES list"
  missing=0
  for f in docker-compose.yml example.env README.md; do
    [ -f "$dir/$f" ] || { fail "$m: missing $f"; missing=1; }
  done
  [ "$missing" -eq 0 ] || continue

  # Every ${VAR} in the compose files is in example.env, set or commented out ($${VAR} is escaped)
  for var in $(grep -hv '^\s*#' "$dir"/docker-compose*.yml | grep -oP '(?<!\$)\$\{\K[A-Za-z_][A-Za-z0-9_]*' | sort -u || true); do
    grep -qE "^#?\s*$var=" "$dir/example.env" || fail "$m: \${$var} is used in docker-compose but not in example.env"
  done

  # Resolved config: base file alone, then with the GPU override (it swaps images)
  base="$(docker compose -f "$dir/docker-compose.yml" config --format json)" || { fail "$m: docker compose config failed"; continue; }
  configs=("$base")
  if [ -f "$dir/docker-compose.gpu.yml" ]; then
    gpu="$(docker compose -f "$dir/docker-compose.yml" -f "$dir/docker-compose.gpu.yml" config --format json)" \
      || { fail "$m: docker compose config with docker-compose.gpu.yml failed"; continue; }
    configs+=("$gpu")
  fi
  while read -r svc image; do
    check_image "$m" "service $svc" "$image"
  done < <(for json in "${configs[@]}"; do
    jq -r '.services | to_entries[] | select(.value.build == null) | "\(.key) \(.value.image)"' <<<"$json"
  done | sort -u)
  if [ -f "$dir/Dockerfile" ]; then
    while read -r image; do
      check_image "$m" "Dockerfile FROM" "$image"
    done < <(awk 'toupper($1) == "FROM" { print $2 }' "$dir/Dockerfile")
  fi

  # Host ports must not clash with another module (or service)
  while read -r svc port; do
    if [ -n "${port_owner[$port]:-}" ]; then
      fail "host port $port is used by ${port_owner[$port]} and $m/$svc"
    else
      port_owner[$port]="$m/$svc"
    fi
  done < <(jq -r '.services | to_entries[] | .key as $s | (.value.ports // [])[] | select(.published) | "\($s) \(.published)"' <<<"$base")
done

[ "$status" -eq 0 ] && echo "[conventions] ok"
exit "$status"
