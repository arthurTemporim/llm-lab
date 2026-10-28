# CLAUDE.md

`llm-lab` is a self-hosted lab for trying LLM tools, models and services. It is **infrastructure as Docker Compose**, not an application: no app code, build step or test suite. Deliverables are `docker-compose.yml` files, `example.env` templates, shell scripts, a `Makefile`, Jupyter notebooks and docs.

## Where to find things

- Commands and targets: `Makefile` (or `make help`) and the Makefile section of `README.md`
- Setup, modules overview, troubleshooting: `README.md`
- Network, dependencies, data flows, design decisions: `docs/ARCHITECTURE.md`
- Per-module reference and the module contract: `docs/MODULES.md`, `modules/<name>/README.md`
- Naming, Compose, env, integration and docs rules: `docs/CONVENTIONS.md`
- Env loading, shared values, secrets, GPU/CPU, ports, upgrades: `docs/CONFIGURATIONS.md`
- Helper scripts: `scripts/`

Read the relevant file before changing a module. Don't guess commands, ports or env values.

## Layout

- `modules/<name>/`: one self-contained Compose project per technology (`docker-compose.yml`, `example.env`, optional `Dockerfile`, `README.md`)
- `modules/common-services/`: Postgres+pgvector, Redis, Garage (S3). Creates the `lang` network, which every other module uses as `external: true`
- `evals/`: DeepEval model evaluations against the LiteLLM gateway (results in `docs/MODEL_EVAL_REPORT.md`)
- `.claude/agents/`, `.claude/skills/`: sub-agents and skills (see Delegation)

## Delegation

Use sub-agents whenever a task fits one. Launch independent agents **in parallel** (one message, multiple calls).

| Agent | Use for |
|---|---|
| `ai-agent` | Modules (compose, GPU overrides, `example.env`, configs), models (Ollama, LiteLLM, vLLM), integrations, evals, notebooks, scripts, Makefile |
| `documenter-agent` | All docs (`README.md`, `docs/`, module and evals READMEs), after changes to modules, ports, env vars, integrations, models or conventions |
| `validator-agent` | Static validation, after any change. Never edits |

Skills (`.claude/skills/`):

- `validate`: run the CI checks locally, for one module, one scope or `all`.
- `add-module`: add a technology as a module, end to end.
- `add-model`: add or remove a served model (Ollama, LiteLLM, vLLM, evals, docs).
- `connect-modules`: wire one module to another (global env, consumer config, docs).
- `upgrade-image`: bump a pinned image version safely.

## Conventions

Follow the module pattern; look at an existing module before adding or editing one. The full rules, with naming, are in `docs/CONVENTIONS.md`; the essentials:

- Services `<module>` / `<module>-<role>` with `container_name` equal to the service name; volumes `<module>-<data>`; host ports `<MODULE>[_<ROLE>]_PORT`.
- Pinned image tags, no `latest`.
- `env_file: .env` in every service. Use `${VAR:-default}` only for host ports and derived values.
- Every host port is a `*_PORT` variable in `example.env`; check other modules for clashes. Admin-only ports bind to `127.0.0.1`.
- The base compose file must run on CPU. GPU config goes in `docker-compose.gpu.yml`. Exception: `vllm` is GPU only (reservation in its base file).
- Every new env var goes in `example.env` with a safe default and a comment (`CHANGE_ME` for generated secrets). Never commit or print real secrets.
- Use shared services (Postgres, Redis, Garage, Ollama) by container name on `lang`. No module-local copies. New databases go in `POSTGRES_DATABASES` in `modules/common-services/example.env`.
- `modules/common-services/.env` is the global env file: the Makefile loads it before every module's `.env`. Reference shared values as `${VAR}` (e.g. `DATABASE_URL=${POSTGRES_URL}/<db>`), never copy them. Passwords use `CHANGE_ME_PASSWORD`, secrets `CHANGE_ME` (`scripts/generate_secrets.sh`).
- Adding a module also means updating the `Makefile` `MODULES` list and the docs listed above (doc map in `docs/CONVENTIONS.md`).
- Docs and comments are in English.

## Constraints

- Module `.env` files must not redefine global values (`make check-env`). `GARAGE_S3_REGION` must equal `s3_region` in `modules/common-services/garage.toml`.
- Redis keeps `--maxmemory-policy noeviction` (Langfuse/BullMQ).
- Postgres data stays mounted at `PGDATA` (`/var/lib/postgresql/data`).
- Keep Garage's S3 host port (9100) and ClickHouse's lack of host ports.
- Never change Langfuse `ENCRYPTION_KEY`/`SALT` or the LiteLLM salt key after first use.

## Validating changes

No tests exist. Run `bash .claude/skills/validate/validate.sh [all|<module>|<scope>]` (or delegate to `validator-agent`): it runs the CI checks below. By hand: `docker compose --env-file modules/common-services/.env --env-file modules/<name>/.env -f modules/<name>/docker-compose.yml config -q`, `make -n <target>`, `bash -n scripts/<script>.sh` and `scripts/check_conventions.sh` (needs the `.env` files; also checks naming, README sections and Markdown links). CI (`.github/workflows/validate.yml`) runs these plus ShellCheck and yamllint on PRs. Only start or stop containers when the task needs it: they may be in use and GPU modules download many GB.

## Git

Feature branch → PR into `devel` → `devel` merged into `main` by PR. Never push to `main` directly.

<!-- rtk-instructions v2 -->
# Command output

Command output here is condensed to save tokens, keeping every signal and
dropping costly noise. Treat it as the complete result: run commands
normally, and batch related commands into one call to avoid extra turns.
Truncated results state their recovery path in their own output. Re-run a
command as `rtk proxy <cmd>` only when its result is unusable: empty when
output was clearly expected, contradicting its exit code, or garbled.
<!-- /rtk-instructions -->