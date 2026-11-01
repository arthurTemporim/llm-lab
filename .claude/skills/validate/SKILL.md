---
name: validate
description: Run llm-lab's static validation (the CI checks) — compose config with the global env, Makefile dry runs and check-env, bash -n + ShellCheck, check_conventions.sh (naming, README sections, links), yamllint, evals syntax. Use after any change, for one module or the whole repo. Never starts containers.
---

# validate

```bash
bash .claude/skills/validate/validate.sh [all|compose|make|shell|conventions|yaml|evals|<module>]...   # default: all
```

| Scope | Runs |
|---|---|
| `compose` | `docker compose --env-file ../common-services/.env --env-file .env config -q` per module, base and GPU override; "variable is not set" fails |
| `make` | `make check-env`, `make help`, `make -n` on the main and per-module targets (also `GPU=1`) |
| `shell` | `bash -n` and ShellCheck on `scripts/*.sh` and skill scripts |
| `conventions` | `scripts/check_conventions.sh`: files, Makefile registration, pinned images, port clashes, naming, README sections, Markdown links, script headers |
| `yaml` | yamllint (installed, `pipx` or `uvx`, pinned like CI) |
| `evals` | parses `evals/*.py` |
| `<module>` | compose config of that module + `conventions` |

Scopes combine: `validate.sh compose shell`. A missing tool prints `SKIP`. Missing `.env` files print `FAIL` with the fix (`make create-envs`); the script never creates them.

When to run:
- Changed one module → `<module>`. Scripts → `shell`. Makefile → `make`. Docs → `conventions` (links, README sections).
- Before a commit or PR → `all`.
- Prefer delegating to `validator-agent` so the log stays out of the main context.

`make check-env` also fails on stale local `.env` files (a global variable missing, an old variable name). That is a local setup issue, not a code failure: report which file and variable, don't edit `.env` files without asking.

On failure: fix the root cause. Never weaken a check to make it pass.
