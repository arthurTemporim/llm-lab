# Configurations

How configuration works in llm-lab: env files, values that must match, secrets, GPU/CPU, ports, upgrades and resets. The full list of variables for each module, with defaults and comments, is in its `example.env`.

## How configuration is loaded

1. Each module has a committed **`example.env`** template.
2. **`make create-envs`** copies it to **`.env`** (git-ignored) and never overwrites an existing one. Every `CHANGE_ME` value becomes a random secret (LocalAI key, LiteLLM keys, Langfuse secrets).
3. Every module loads its whole `.env` with `env_file: .env`, so a new variable reaches the container with no compose change. Compose also uses the same `.env` for `${VAR:-default}` interpolation, which modules use only for host ports and derived values (for example Langfuse's S3 settings).
4. Apply changes with `make <module>` (or `docker compose up -d` in the module folder). Check the result with `docker compose config`.

## Values that must match

| Value | Keep in sync between |
|---|---|
| Postgres user, password and database names | `common-services` and the connection strings in `langflow`, `litellm`, `langfuse`, `hatchet` |
| Garage key and secret (`GARAGE_DEFAULT_*`) | `common-services/.env` and `langfuse/.env` (verified by `make check-env`, which `make langfuse` runs) |
| Garage bucket, endpoint and region | `common-services/.env` and `garage.toml` (`s3_region`), and the S3 settings in `langfuse/.env` |
| Langfuse port and public URL | both in `langfuse/.env` |
| Hatchet public host and ports | `HATCHET_PUBLIC_HOST`, `HATCHET_PORT`, `HATCHET_GRPC_PORT` in `hatchet/.env` and the URL clients use; tokens created before a change keep the old gRPC address |
| Langfuse API keys | `langfuse/.env` and any client, such as `litellm/.env` |
| LocalAI API key | `localai/.env` and its clients (LiteLLM, Open WebUI) |

## Secrets

All defaults are for local use. Change them before exposing anything beyond your machine, and generate values with `openssl rand -hex 32`.

- **Passwords and keys:** Postgres, Garage, ClickHouse, Langflow, LiteLLM, Langfuse and LocalAI all ship with simple defaults.
- **Never change after first use:** the LiteLLM salt key (encrypts stored provider keys) and the Langfuse `ENCRYPTION_KEY`.
- **Langfuse seed values** (`LANGFUSE_INIT_*`) and the **Hatchet admin user** (`ADMIN_*`) apply only on the first start.
- **Hatchet keys** live in the `hatchet-config` volume; removing it invalidates every Hatchet API token.
- **Jupyter** runs without a token. Add one in its compose command to enable auth.
- Never commit or print real secrets. `.env` files are git-ignored.

## Open WebUI persistent config

Most Open WebUI settings are stored in its database after the first start, and the admin UI then wins over env vars. Set `ENABLE_PERSISTENT_CONFIG=false` to always use env values.

## Connecting services

- **Between containers:** use container names, for example `postgres`, `redis` or `http://ollama:<port>`.
- **From the host:** use `localhost` and the published host port.

## GPU and CPU

`ollama`, `localai`, `docling` and `openwebui` have a base `docker-compose.yml` that runs on CPU and a `docker-compose.gpu.yml` override that reserves NVIDIA GPUs (and, for LocalAI, Docling and Open WebUI, swaps in the CUDA image). The Makefile adds the override when it detects the NVIDIA Container Toolkit (`docker info`).

- **Force it:** `make GPU=1 <module>` or `make GPU=0 <module>`.
- **Without make:** `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` in the module folder.
- **Limit GPUs:** set `NVIDIA_VISIBLE_DEVICES` in `ollama/.env`, or use `device_ids` instead of `count: all` in the override.
- **CPU:** prefer small models (a few billion parameters) with low parallelism.
- **`vllm` is GPU only.** Its NVIDIA reservation is in the base `docker-compose.yml` (no override file), so `GPU=0` does not turn it off. It needs a card with compute capability 7.5+ (the Tesla P4 does not qualify): set `VLLM_GPU_ID` to the index shown by `nvidia-smi -L`.
- **`docling` pins one card.** Its CUDA 12.8 image does not run on Pascal cards (Tesla P4), so the override reserves only `DOCLING_GPU_ID` (a Turing or newer index from `nvidia-smi -L`) for `docling-worker`. The worker holds that VRAM only while it has work: the `docling` manager stops it after `DOCLING_MANAGER_IDLE_TIMEOUT` seconds idle.

## Changing ports

Every published host port is a `*_PORT` variable in the module's `.env` (for example `OLLAMA_PORT`, `LANGFUSE_PORT`, `GARAGE_S3_PORT`). If a port is also used in another setting (for example Langfuse's public URL or the Langfuse S3 external endpoint), update it too. Container ports and in-network addresses never change.

## Versions and upgrades

Image versions are pinned in each `docker-compose.yml` or `Dockerfile` (Langfuse uses `LANGFUSE_VERSION` in `.env`). No image uses `latest` (`scripts/check_conventions.sh` enforces it).

| Case | Upgrade |
|---|---|
| Image in compose | Edit the tag, then `docker compose pull && docker compose up -d` |
| Image in a Dockerfile (langflow, notebooks, the docling manager) | Edit, then `docker compose up -d --build` |
| Langfuse | Change the version, pull and restart; migrations run automatically. Check the ClickHouse version it supports first. |
| Hatchet | Change the tag, pull and restart; migrations run at start. Keep worker SDK versions compatible. |
| Postgres major version | Needs `pg_dumpall` and a restore |

## Integrations

- **LiteLLM → Ollama / LocalAI.** Ollama models are registered automatically at `make litellm` (`litellm-init` builds `config.yaml` from Ollama and `modules/litellm/models.yaml`). Add LocalAI and other backends under `extra_models` in `models.yaml`. Use container names for `api_base`.
- **LiteLLM → Langfuse.** Add the Langfuse public key, secret key and host to `litellm/.env` and enable the Langfuse success callback.
- **Open WebUI → LocalAI / LiteLLM.** Add an OpenAI-compatible connection in the admin settings, with the matching API key.
- **Langflow / notebooks → pgvector.** Use the Postgres connection string for the `langflow` database, where `vector` is enabled.

## Reset and cleanup

| Goal | Command |
|---|---|
| Stop a module, keep data | `make down-<module>` or `docker compose down` |
| Stop everything | `make down` |
| Reset a module's `.env` | `rm modules/<name>/.env && make create-envs` |
| Wipe a module's volumes | `docker compose down -v` in its folder |
| Recreate missing databases | `make databases` |
| Wipe Postgres | `docker compose down -v` in `common-services` (**deletes every database**), then `make common-services` |
| Free model disk space | `docker exec ollama ollama rm <model>`, or delete files in `modules/localai/models/` |
