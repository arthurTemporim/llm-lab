#!/usr/bin/env bash
# Fails when a module breaks the repo conventions (CLAUDE.md, docs/MODULES.md): module files
# and Makefile registration, ${VAR}s documented in example.env, pinned images, unique host ports.
# Reads the resolved compose config, so the .env files must exist (make create-envs). Like the
# Makefile, it loads the global common-services/.env before each module's .env.
# Ex: ./scripts/check_conventions.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
global_example="$root/modules/common-services/example.env"
status=0
fail() { echo "[conventions] $*"; status=1; }

pinned() { # <image>: true when it has a digest or a tag other than latest
  local name="${1##*/}" # drop the registry, whose port would look like a tag
  [[ "$1" == *@sha256:* ]] || { [[ "$name" == *:* ]] && [ "${name##*:}" != latest ]; }
}

check_image() { # <module> <where> <image>
  pinned "$3" || fail "$1: $2 uses unpinned image $3"
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

  # Every ${VAR} in the compose files is in example.env or the global one, set or commented out
  # ($${VAR} is escaped)
  for var in $(grep -hv '^\s*#' "$dir"/docker-compose*.yml | grep -oP '(?<!\$)\$\{\K[A-Za-z_][A-Za-z0-9_]*' | sort -u || true); do
    grep -qE "^#?\s*$var=" "$dir/example.env" "$global_example" \
      || fail "$m: \${$var} is used in docker-compose but not in example.env or common-services/example.env"
  done
  # Every ${VAR} referenced in example.env is defined there or in the global one
  for var in $(grep -v '^\s*#' "$dir/example.env" | grep -oP '\$\{\K[A-Za-z_][A-Za-z0-9_]*' | sort -u || true); do
    grep -qE "^$var=" "$dir/example.env" "$global_example" \
      || fail "$m: example.env references \${$var}, which is not set in it or in common-services/example.env"
  done

  # Resolved config: base file alone, then with the GPU override (it swaps images)
  envs=(--env-file "$root/modules/common-services/.env" --env-file "$dir/.env")
  base="$(docker compose "${envs[@]}" -f "$dir/docker-compose.yml" config --format json)" || { fail "$m: docker compose config failed"; continue; }
  configs=("$base")
  if [ -f "$dir/docker-compose.gpu.yml" ]; then
    gpu="$(docker compose "${envs[@]}" -f "$dir/docker-compose.yml" -f "$dir/docker-compose.gpu.yml" config --format json)" \
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

  # Naming (docs/CONVENTIONS.md): service key = container_name = <module> or <module>-<role>
  # (common-services: the service name), volume keys <module|service>-<data>, host port
  # variables <MODULE|SERVICE>[_<ROLE>]_PORT
  services="$(jq -r '.services | keys[]' <<<"$base")"
  while read -r svc cname; do
    [ "$cname" = "$svc" ] || fail "$m: service $svc has container_name '${cname}', it must equal the service name"
    if [ "$m" != common-services ] && [ "$svc" != "$m" ] && [[ "$svc" != "$m"-* ]]; then
      fail "$m: service $svc must be named $m or $m-<role>"
    fi
  done < <(jq -r '.services | to_entries[] | "\(.key) \(.value.container_name // "")"' <<<"$base")
  prefixes="$(printf '%s\n' "$m" "$services" | sort -u | paste -sd'|')"
  while read -r vol; do
    [[ "$vol" =~ ^($prefixes)-[a-z0-9-]+$ ]] || fail "$m: volume $vol must be named <module or service>-<data>"
  done < <(jq -r '.volumes // {} | keys[]' <<<"$base")
  upper="$(tr 'a-z-' 'A-Z_' <<<"$prefixes")"
  for var in $(grep -hoP '^\s*-\s*"?(127\.0\.0\.1:)?\$\{\K[A-Za-z0-9_]+(?=(:-[0-9]+)?\}:)' "$dir"/docker-compose*.yml | sort -u || true); do
    [[ "$var" =~ ^($upper)(_[A-Z0-9]+)*_PORT$ ]] || fail "$m: host port variable $var must be named <MODULE>[_<ROLE>]_PORT"
  done

  # README.md keeps the template's sections, in order (extra sections are allowed)
  expected=("Overview" "What it is used for" "Access" "Quick start" "Configuration" "Connections" "Storage" "Operations" "Troubleshooting" "Notes")
  i=0
  while read -r heading; do
    [ "$i" -lt "${#expected[@]}" ] && [ "$heading" = "${expected[$i]}" ] && i=$((i + 1))
  done < <(sed -n 's/^## //p' "$dir/README.md")
  [ "$i" -eq "${#expected[@]}" ] || fail "$m: README.md is missing '## ${expected[$i]}' or has it out of order (docs/MODULE_README_TEMPLATE.md)"
done

# Relative links in Markdown files point to existing files (code blocks are skipped)
while read -r md; do
  while read -r target; do
    target="${target%%#*}"
    [ -z "$target" ] || [ -e "$(dirname "$root/$md")/$target" ] || fail "$md: broken link to $target"
  done < <(awk '
    /^ *```/ { match($0, /`+/); n = RLENGTH
               if (!fence) { fence = n; next } else if (n >= fence) { fence = 0; next } }
    !fence' "$root/$md" \
    | grep -oP '\]\(\K[^)\s]+' | grep -vE '^(https?:|mailto:|#)' || true)
done < <(git -C "$root" ls-files --cached --others --exclude-standard '*.md')

# Scripts: portable shebang and a usage line
for f in "$root"/scripts/*.sh; do
  s="scripts/$(basename "$f")"
  [ "$(head -n1 "$f")" = "#!/usr/bin/env bash" ] || fail "$s: first line must be #!/usr/bin/env bash"
  grep -q '^# Ex:' "$f" || fail "$s: add a '# Ex:' usage line to the header comment"
done

[ "$status" -eq 0 ] && echo "[conventions] ok"
exit "$status"
