#!/usr/bin/env bash
# Static validation for llm-lab, the same checks as .github/workflows/validate.yml.
# Nothing is pulled, built or started. Needs the .env files (make create-envs).
# Usage: validate.sh [all|compose|make|shell|conventions|yaml|evals|<module>]...   (default: all)
#   <module>: compose config of that module + conventions
# Ex: bash .claude/skills/validate/validate.sh compose shell
set -uo pipefail

repo="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo" || exit 2
failed=0

# step <label> <cmd...>: runs cmd, prints PASS/FAIL, returns cmd status
step() {
  local label="$1"; shift
  local out
  if out="$("$@" 2>&1)"; then
    echo "PASS  $label"
  else
    echo "FAIL  $label"
    echo "$out" | tail -n 40 | sed 's/^/      /'
    failed=1
    return 1
  fi
}
skip() { echo "SKIP  $1"; }
has() { command -v "$1" > /dev/null 2>&1; }

envs_ok() { # every module (or the given one) has its .env and the global one exists
  local missing=()
  for d in modules/common-services "${@:-modules/*}"; do
    for dir in $d; do [ -f "$dir/.env" ] || missing+=("$dir/.env"); done
  done
  [ "${#missing[@]}" -eq 0 ] && return 0
  echo "FAIL  .env files missing (run make create-envs): ${missing[*]}"
  failed=1
  return 1
}

# compose_config <module>: base file, then with the GPU override; unset variables fail too
compose_config() {
  local dir="modules/$1" out files
  local variants=("-f docker-compose.yml")
  [ -f "$dir/docker-compose.gpu.yml" ] && variants+=("-f docker-compose.yml -f docker-compose.gpu.yml")
  for files in "${variants[@]}"; do
    # shellcheck disable=SC2086 # $files holds several -f arguments
    if out="$(cd "$dir" && docker compose --env-file ../common-services/.env --env-file .env $files config -q 2>&1)" \
      && ! grep -qi 'variable is not set' <<<"$out"; then
      continue
    fi
    echo "$files:"; echo "$out"
    return 1
  done
}

compose() {
  has docker || { skip "compose (docker not installed)"; return; }
  envs_ok || return
  for dir in modules/*/; do
    step "compose config: $(basename "$dir")" compose_config "$(basename "$dir")"
  done
}

module() {
  has docker || { skip "$1 (docker not installed)"; return; }
  envs_ok "modules/$1" || return
  step "compose config: $1" compose_config "$1"
}

make_targets() {
  envs_ok || return
  step "make check-env" make -s check-env
  step "make help" make -s help
  step "make -n main targets" make -n create-envs build build-all up up-all down logs
  step "make -n GPU=1" make -n GPU=1 build-all up-all
  local m
  # shellcheck disable=SC2016 # $(MODULES) is expanded by make
  for m in $(make -s --eval 'print-modules: ; @echo $(MODULES)' print-modules); do
    step "make -n $m targets" make -n "$m" "up-$m" "down-$m" "build-$m" "logs-$m"
  done
}

shell() {
  local f
  for f in scripts/*.sh .claude/skills/*/*.sh; do step "bash -n $f" bash -n "$f"; done
  if has shellcheck; then step "shellcheck" shellcheck scripts/*.sh .claude/skills/*/*.sh
  elif has uvx; then step "shellcheck (uvx)" uvx --from shellcheck-py==0.10.0.1 shellcheck scripts/*.sh .claude/skills/*/*.sh
  else skip "shellcheck (install shellcheck or uv)"
  fi
}

conventions() {
  if ! has docker || ! has jq; then skip "conventions (needs docker and jq)"; return; fi
  envs_ok || return
  step "check_conventions.sh" ./scripts/check_conventions.sh
}

yaml() {
  if has yamllint; then step "yamllint" yamllint .
  elif has pipx; then step "yamllint (pipx)" pipx run --spec yamllint==1.37.1 yamllint .
  elif has uvx; then step "yamllint (uvx)" uvx yamllint==1.37.1 .
  else skip "yamllint (install yamllint, pipx or uv)"
  fi
}

evals() {
  has python3 || { skip "evals (python3 not installed)"; return; }
  # Parse only: py_compile would write __pycache__ into evals/
  step "evals syntax" python3 -I -c 'import ast, sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]' evals/*.py
}

[ "$#" -eq 0 ] && set -- all
for scope in "$@"; do
  case "$scope" in
    all) compose; make_targets; shell; conventions; yaml; evals ;;
    compose) compose ;;
    make) make_targets ;;
    shell) shell ;;
    conventions) conventions ;;
    yaml) yaml ;;
    evals) evals ;;
    *)
      if [ -d "modules/$scope" ]; then module "$scope"; conventions
      else echo "usage: $0 [all|compose|make|shell|conventions|yaml|evals|<module>]..." >&2; exit 2
      fi ;;
  esac
done

if (( failed )); then echo "RESULT: FAIL"; exit 1; fi
echo "RESULT: PASS"
