# CLAUDE.md

`llm-lab` is a self-hosted lab for trying LLM tools, models and services. It is **infrastructure as Docker Compose**, not an application: no app code, build step or test suite. Deliverables are `docker-compose.yml` files, `example.env` templates, shell scripts, a `Makefile`, Jupyter notebooks and docs.

## Where to find things

- Commands and targets: `Makefile` (or `make help`) and the Makefile section of `README.md`
- Setup, modules overview, troubleshooting: `README.md`
- Network, dependencies, data flows, design decisions: `docs/ARCHITECTURE.md`
- Per-module reference and the module contract: `docs/MODULES.md`, `modules/<name>/README.md`
- Env loading, shared values, secrets, GPU/CPU, ports, upgrades: `docs/CONFIGURATIONS.md`
- Helper scripts: `scripts/`

Read the relevant file before changing a module. Don't guess commands, ports or env values.

## Layout

- `modules/<name>/`: one self-contained Compose project per technology (`docker-compose.yml`, `example.env`, optional `Dockerfile`, `README.md`)
- `modules/common-services/`: Postgres+pgvector, Redis, MinIO. Creates the `lang` network, which every other module uses as `external: true`

## Conventions

Follow the module pattern; look at an existing module before adding or editing one (see `docs/MODULES.md`).

- Pinned image tags. The only exception is MinIO (`latest`); don't add more.
- `env_file: .env` in every service. Use `${VAR:-default}` only for host ports and derived values.
- Every host port is a `*_PORT` variable in `example.env`; check other modules for clashes. Admin-only ports bind to `127.0.0.1`.
- The base compose file must run on CPU. GPU config goes in `docker-compose.gpu.yml`.
- Every new env var goes in `example.env` with a safe default and a comment (`CHANGE_ME` for generated secrets). Never commit or print real secrets.
- Use shared services (Postgres, Redis, MinIO, Ollama) by container name on `lang`. No module-local copies. New databases go in `POSTGRES_DATABASES` in `modules/common-services/example.env`.
- Adding a module also means updating the `Makefile` `MODULES` list and the docs listed above.
- Docs and comments are in English.

## Constraints

- `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` must match between `common-services` and `langfuse` (checked by the Makefile).
- Redis keeps `--maxmemory-policy noeviction` (Langfuse/BullMQ).
- Postgres data stays mounted at `PGDATA` (`/var/lib/postgresql/data`).
- Keep MinIO's non-standard host API port and ClickHouse's lack of host ports.
- Never change Langfuse `ENCRYPTION_KEY`/`SALT` or the LiteLLM salt key after first use.

## Validating changes

No tests exist. Use `docker compose -f modules/<name>/docker-compose.yml config -q`, `make -n <target>` and `bash -n scripts/<script>.sh`. Only start or stop containers when the task needs it: they may be in use and GPU modules download many GB.

## Git

Feature branch → PR into `devel` → `devel` merged into `main` by PR. Never push to `main` directly.
