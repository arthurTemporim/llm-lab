# Conventions

The rules every module, script and doc in llm-lab follows: naming, Compose, env files, integration between modules, documentation and scripts. [MODULES.md](MODULES.md) shows the module layout, and [CONFIGURATIONS.md](CONFIGURATIONS.md) explains how env files load.

**TLDR:** a module `x` runs services `x` and `x-<role>`, with `container_name` equal to the service name. Its volumes are `x-<data>`, its host ports are `X[_<ROLE>]_PORT`, and its own variables are `X_*`. Values that several modules share are defined once in `common-services/.env` and referenced as `${VAR}`. Docs take every value from `docker-compose.yml` and `example.env`. `scripts/check_conventions.sh` enforces the rules marked ✔ below. It runs in CI and in `validate.sh`.

## Naming

| Thing | Pattern | Example | Checked |
|---|---|---|---|
| Module folder | lowercase upstream name, kebab-case | `openwebui`, `common-services` | |
| Service key and `container_name` | equal; `<module>` for the main service, `<module>-<role>` for the others | `litellm`, `litellm-init`, `langfuse-clickhouse` | ✔ |
| Shared services in `common-services` | the technology name | `postgres`, `redis`, `garage` | ✔ |
| Volume key | `<module or service>-<data>` | `ollama-models`, `postgres-data` | ✔ |
| Host port variable | `<MODULE or SERVICE>[_<ROLE>]_PORT` | `LITELLM_PORT`, `LITELLM_PROMETHEUS_PORT`, `GARAGE_S3_PORT` | ✔ |
| Module variable | `<MODULE>_*` | `DOCLING_MANAGER_CONCURRENCY` | |
| GPU pin | `<MODULE>_GPU_ID` | `VLLM_GPU_ID` | |
| Upstream variable | keep the name the image reads | `ENABLE_*` (Open WebUI), `SERVER_*` (Hatchet) | |
| Global variable | `LAB_*` for lab-wide values, `<SERVICE>_HOST`/`_URL`/`_PORT` for shared services | `LAB_PUBLIC_HOST`, `POSTGRES_URL`, `OLLAMA_URL` | |
| Postgres database, Garage bucket | the module name | `litellm`, `langfuse` | |
| Script | `<module>_<action>.sh` for one module, `<verb>_<noun>.sh` for the repo | `ollama_pull_model.sh`, `check_env.sh` | |
| Doc in `docs/` | `UPPER_SNAKE.md` | `MODEL_EVAL_REPORT.md` | |

Exceptions:

- A port variable must not clash with a name the image reads from its env. Then use `<MODULE>_HOST_PORT` instead. Example: vLLM reads `VLLM_PORT`, so the module uses `VLLM_HOST_PORT`.
- Volumes created before this convention keep their Docker name with `name:`, so the data stays. Example: `ollama-models: { name: ollama_ollama }`. To rename a volume key, always pin the old name this way: the Docker name is `<module folder>_<old key>`.

## Compose

- One Compose project per folder. Every service joins the external `lang` network. Only `common-services` creates it.
- Pin every image tag, never `latest` ✔. Services that share an image use the same tag (`litellm-init` and `litellm`).
- Every service has `env_file: .env`. Use `${VAR:-default}` only for host ports and derived values ✔ (every `${VAR}` exists in an `example.env`).
- Publish ports as `"${X_PORT:-default}:<container port>"`. Every host port is unique across the lab ✔. Bind admin-only ports (no LAN client needs them) to `127.0.0.1`.
- `restart: unless-stopped`. One-shot or manager-started services use `"no"` (`litellm-init`, `docling-worker`).
- Add a `healthcheck` when the image ships a way to check health (curl, wget, python).
- `depends_on` only within the module. The order between modules comes from the Makefile (`up-<module>` starts `common-services` first).
- The base file runs on CPU. NVIDIA settings go in `docker-compose.gpu.yml`, which may swap in the CUDA image. `vllm` is the only GPU-only module.
- Register the module in the `Makefile` `MODULES` list ✔. Each module has `docker-compose.yml`, `example.env` and `README.md` ✔.

## Env files

- `example.env` is the committed template. Every variable has a comment above it. Group long files with `# --- Name ---` headers.
- Placeholders are filled by `make create-envs`: `CHANGE_ME` for keys and secrets, `CHANGE_ME_PASSWORD` for passwords, `CHANGE_ME_HEX24` for a Garage key id. Never commit or print a real value.
- **Global values** live only in `modules/common-services/example.env`. The Makefile loads that file before each module's `.env`. A module references global values as `${VAR}` and never copies them. To pass one through under the same name, write `NAME=${NAME}`. `make check-env` fails when a module redefines a global value.
- Every `${VAR}` referenced in an `example.env` is defined there or in the global file ✔.
- A renamed or removed variable needs a migration guard in `scripts/check_env.sh`, because existing `.env` files keep the old name.

## Integration

- **Shared address or credential** (used by two or more modules): add it to the global env (`<SERVICE>_URL`, keys) and reference it, e.g. `DATABASE_URL=${POSTGRES_URL}/litellm` or `OLLAMA_API_BASE=${OLLAMA_URL}`.
- **One-off link:** container name + container port, e.g. `http://docling:5001`. Inside a container, never use `localhost`, a host IP or the host port.
- **Browser-facing URLs** use `${LAB_PUBLIC_HOST}` and the host port, e.g. `GARAGE_S3_EXTERNAL_ENDPOINT`.
- **Shared services:** use Postgres, Redis, Garage and Ollama; never bundle a module-local copy. A new database goes in `POSTGRES_DATABASES`, and a new bucket follows the Garage setup in `common-services`.
- **Document both ends:** the `Connections` table in each module's README, the global-values or "Values that must match" table in [CONFIGURATIONS.md](CONFIGURATIONS.md), and [ARCHITECTURE.md](ARCHITECTURE.md) when the change adds a dependency or a data flow.

## Documentation

All docs are in English and short: lead with what the reader needs, skip the obvious. Take every port, image, variable and default from `docker-compose.yml` and `example.env`; never invent one. Update docs in the same change as the code.

| When you change… | Update |
|---|---|
| A module's compose or `example.env` | its `README.md` (Overview, Access, Configuration, Storage) |
| Add or remove a module | `README.md` module table, [MODULES.md](MODULES.md), [CONFIGURATIONS.md](CONFIGURATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md) if it adds a dependency, `CLAUDE.md` if a rule changes |
| A link between modules or a global value | both modules' `Connections`, [CONFIGURATIONS.md](CONFIGURATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md) |
| Models served (Ollama, LiteLLM, vLLM) | [MODELS.md](MODELS.md) |
| Eval code or results | `evals/README.md`, [MODEL_EVAL_REPORT.md](MODEL_EVAL_REPORT.md) |
| Make targets | `README.md` Makefile section, `make help` |
| A rule in this file | this file, `CLAUDE.md` and `.claude/agents` if they repeat it |

- Module READMEs follow [MODULE_README_TEMPLATE.md](MODULE_README_TEMPLATE.md): the ten sections in order ✔. Extra module-specific sections go between `Access` and `Operations`.
- Image versions appear only in compose and in the README `Overview` table. Elsewhere, link to the README. Reports keep the versions they ran with.
- Inside the network, write container names; from the host, write `localhost` (or `<host>`) and the host port.
- Relative links must resolve ✔. Diagrams are Mermaid, each with a one-line explanation, and kept small (about 12 nodes at most).

## Scripts

- Start with `#!/usr/bin/env bash` ✔, then a header comment that says what the script does and gives a `# Ex:` usage line ✔. Use `set -euo pipefail` in new scripts.
- Read settings from the module's `.env`; don't hardcode ports or keys.
- Must pass `bash -n` and ShellCheck (CI).

## Enforcement

| Check | Where |
|---|---|
| Compose config (base and GPU) with both env files, no unset variables | CI `compose`, `validate.sh compose` |
| Rules marked ✔ above | `scripts/check_conventions.sh` (CI `conventions`, `validate.sh conventions`) |
| Global env complete, no redefinitions, migration guards | `scripts/check_env.sh` (`make check-env`, before every module starts) |
| Makefile targets | `make -n` dry runs (CI `makefile`, `validate.sh make`) |
| Shell and YAML | ShellCheck, yamllint (CI, `validate.sh shell yaml`) |
