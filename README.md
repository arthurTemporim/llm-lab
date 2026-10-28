# llm-lab

[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-v2-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Self-hosted](https://img.shields.io/badge/Self--hosted-local--first-555555)](#why-llm-lab)
[![Open Source](https://img.shields.io/badge/Open_Source-%E2%99%A5-brightgreen)](#contributing)

[![Ollama](https://img.shields.io/badge/Ollama-000000?logo=ollama&logoColor=white)](modules/ollama)
[![LocalAI](https://img.shields.io/badge/LocalAI-7C3AED)](modules/localai)
[![vLLM](https://img.shields.io/badge/vLLM-30A2FF)](modules/vllm)
[![Docling](https://img.shields.io/badge/Docling-0F62FE)](modules/docling)
[![Open WebUI](https://img.shields.io/badge/Open_WebUI-111827)](modules/openwebui)
[![Langflow](https://img.shields.io/badge/Langflow-E11D48)](modules/langflow)
[![Jupyter](https://img.shields.io/badge/Jupyter-F37626?logo=jupyter&logoColor=white)](modules/notebooks)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-2563EB)](modules/litellm)
[![Langfuse](https://img.shields.io/badge/Langfuse-0F172A)](modules/langfuse)
[![Hatchet](https://img.shields.io/badge/Hatchet-6366F1)](modules/hatchet)
[![PostgreSQL + pgvector](https://img.shields.io/badge/Postgres_%2B_pgvector-4169E1?logo=postgresql&logoColor=white)](modules/common-services)
[![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)](modules/common-services)
[![Garage](https://img.shields.io/badge/Garage-FF9329?logoColor=white)](modules/common-services)

A self-hosted, modular lab to try LLM models, tools and services on your own machine. It is infrastructure as Docker Compose: no app code, just modules you start when you need them.

## Documentation

| Document | Read it to… |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | understand the network, dependencies, data flows, storage and design decisions |
| [docs/MODULES.md](docs/MODULES.md) | see what each module does and the rules for new ones |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | follow the naming, Compose, env, integration and docs rules |
| [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md) | learn how configuration, secrets, GPU/CPU and upgrades work |
| [docs/MODELS.md](docs/MODELS.md) | see the models served through LiteLLM, their settings, links and when to use each |
| [docs/MODEL_EVAL_REPORT.md](docs/MODEL_EVAL_REPORT.md) | compare the chat, embedding and decision models (results of [evals/](evals/README.md)) |
| [CLAUDE.md](CLAUDE.md) | give AI coding agents the project's conventions, gotchas, sub-agents and skills |

## Why llm-lab?

- **Modular.** Each technology is a folder with its own `docker-compose.yml` and `example.env`. Start only what you need.
- **Shared infrastructure.** Postgres (with pgvector), Redis and Garage (S3) run once and every module reuses them over one Docker network.
- **Local first.** Models run on your hardware (CPU or NVIDIA GPU). No cloud API key required.
- **Reproducible.** Pinned images, env templates and one `Makefile`.

## Modules

| Module | Purpose |
|---|---|
| `common-services` | Postgres + pgvector, Redis, Garage (S3). Creates the shared network. |
| `ollama` | Run and serve open-weight models |
| `localai` | OpenAI-compatible inference server |
| `vllm` | High-throughput Hugging Face model server (NVIDIA GPU only) |
| `docling` | Document conversion (PDF, Office, images) to Markdown over HTTP; started on demand, so it frees VRAM when idle |
| `openwebui` | Chat UI |
| `langflow` | Visual builder for flows, agents and RAG |
| `notebooks` | Jupyter with LangChain |
| `litellm` | Unified LLM gateway with metrics |
| `langfuse` | LLM observability: traces, prompts, evals |
| `hatchet` | Durable task queue and workflow engine with a dashboard |

Details are in [docs/MODULES.md](docs/MODULES.md).

### Services

Default host ports (each is a `*_PORT` variable in the module's `.env`). From another machine, replace `localhost` with `LAB_PUBLIC_HOST`. Services marked internal have no host port and are reached by container name on the `lang` network.

| Service | URL | Version | Module |
|---|---|---|---|
| `postgres` | `postgresql://localhost:5432` | `pgvector/pgvector:0.8.7-pg17` | [common-services](modules/common-services/README.md) |
| `redis` | `redis://localhost:6380` | `8.10.3` | [common-services](modules/common-services/README.md) |
| `garage` (S3 API) | http://localhost:9100 | `v2.5.0` | [common-services](modules/common-services/README.md) |
| `ollama` | http://localhost:11434 | `0.40.12` | [ollama](modules/ollama/README.md) |
| `localai` | http://localhost:8080 | `v4.12.1` | [localai](modules/localai/README.md) |
| `vllm` | http://localhost:8000 | `v0.32.0` | [vllm](modules/vllm/README.md) |
| `docling` (API and UI at `/ui`) | http://localhost:5001 | manager built on `python:3.13.18-slim` | [docling](modules/docling/README.md) |
| `docling-worker` | internal | docling-serve `v1.38.2` | [docling](modules/docling/README.md) |
| `openwebui` | http://localhost:3000 | `v0.12.4` | [openwebui](modules/openwebui/README.md) |
| `langflow` | http://localhost:7860 | `1.13.0` | [langflow](modules/langflow/README.md) |
| `notebooks` | http://localhost:8888 | `quay.io/jupyter/minimal-notebook:2026-10-28` | [notebooks](modules/notebooks/README.md) |
| `litellm` (API, UI at `/ui`) | http://localhost:4000 | `v1.106.5` | [litellm](modules/litellm/README.md) |
| `litellm-prometheus` | http://localhost:9090 | `v3.15.1` | [litellm](modules/litellm/README.md) |
| `langfuse-web` | http://localhost:3001 | `4.71` | [langfuse](modules/langfuse/README.md) |
| `langfuse-worker` | http://127.0.0.1:3030 (admin only) | `4.71` | [langfuse](modules/langfuse/README.md) |
| `langfuse-clickhouse` | internal | `25.12` | [langfuse](modules/langfuse/README.md) |
| `hatchet-lite` (dashboard) | http://localhost:8889 | `v0.114.2` | [hatchet](modules/hatchet/README.md) |
| `hatchet-lite` (gRPC for workers) | `localhost:7077` | `v0.114.2` | [hatchet](modules/hatchet/README.md) |

## How it fits together

All containers join one external Docker network called `lang`, created by `common-services`. Inside it they reach each other by container name (for example `ollama` or `postgres`). From your host, use `localhost` and the port published in the module's `docker-compose.yml`.

```text
modules/
  common-services/   shared Postgres, Redis, Garage + the network (start first)
  <module>/          docker-compose.yml, example.env, optional Dockerfile and README
scripts/             helper scripts used by the Makefile (`lab.py` is the setup orchestrator)
evals/               DeepEval model evaluations (python, own virtualenv)
docs/                architecture, modules, configuration
Makefile             single entry point (run `make help`)
```

## Getting started

**Requirements:** Docker with Compose v2, GNU Make, and optionally an NVIDIA GPU with the NVIDIA Container Toolkit (detected automatically; CPU otherwise). Images and models take many GB of disk.

```sh
git clone https://github.com/arthurTemporim/llm-lab.git
cd llm-lab
make init
```

`make init` runs `scripts/lab.py init` (Python 3.9+, stdlib only). It creates the `.env` files, starts `common-services` and `ollama`, pulls the models listed in `scripts/ollama_pull_model.sh` (edit that list first), starts the other selected modules, and prints the URLs, the default login (`LAB_USER` / `LAB_EMAIL`, set in `modules/common-services/.env` before the first start) and where each password is stored. On the first run it sets `LAB_PUBLIC_HOST` to the machine's LAN IP, picks the GPU for `vllm`/`docling`, and writes `evals/.env`. It is safe to re-run and never overwrites values you set by hand. Choose modules and options with `ARGS`:

```sh
make init ARGS="--modules all"                                  # core (default), all, or a comma list
make init ARGS="--modules litellm,hatchet --host 192.168.15.102"
```

Other options: `--no-pull` (skip model pulls), `--gpu 0|1`. If `hatchet` is selected, its worker token is created automatically.

Then add optional modules:

```sh
make langflow
make notebooks
make litellm
make langfuse
```

Stop everything (data stays in volumes):

```sh
make down
```

Published ports, URLs and default credentials live in each module's `docker-compose.yml` and `example.env`.

### GPU or CPU

The Makefile detects the NVIDIA Container Toolkit and adds each module's `docker-compose.gpu.yml` (`ollama`, `localai`, `docling`, `openwebui`) when it is found. Force it with `make GPU=1 ...` or `make GPU=0 ...`. `vllm` is GPU only and always reserves a GPU. On CPU prefer small models. See [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md).

## Makefile

Run `make help` for the full list. Common targets:

| Target | Description |
|---|---|
| `make init [ARGS=...]` | Configure, start the core (or `--modules` selection), pull models, print URLs |
| `make configure [ARGS=--host IP]` | Create envs, set `LAB_PUBLIC_HOST` and GPU ids, write `evals/.env`; starts nothing |
| `make gpu [ARGS=--dry-run]` | Pick the best GPU (compute capability 7.5+, most memory) for `VLLM_GPU_ID` and `DOCLING_GPU_ID` |
| `make hatchet-token [ARGS=--force]` | Create the Hatchet worker token in the global `.env` |
| `make up` / `make build` | Start or build the core modules (`common-services`, `ollama`) |
| `make up-all` / `make build-all` | Start or build every module |
| `make create-envs` | Copy each `example.env` to `.env` (never overwrites) |
| `make up-<module>` (or `make <module>`) | Start a module (`common-services` is started first automatically) |
| `make down-<module>` / `build-<module>` / `logs-<module>` | Stop a module (data is kept), only build its images, or follow its logs |
| `make databases` | Create the Postgres databases if missing (idempotent) |
| `make check-env` | Verify the global `common-services/.env` and that no module redefines its values (runs before every start) |
| `make down` | Stop all modules, keep volumes |

## Helper scripts

The `scripts/` folder holds `lab.py` (setup orchestrator behind `make init`, `configure`, `gpu` and `hatchet-token`; see `./scripts/lab.py --help`) and small helpers: pulling, listing and prompting Ollama models, downloading Hugging Face models for vLLM and testing the server, creating the Postgres databases, creating Hatchet API tokens, generating random passwords and secrets for new `.env` files and checking the global env file.

## CI

`.github/workflows/validate.yml` runs static checks on every PR into `devel` or `main`; it never pulls, builds or starts containers. It validates every compose file (with its GPU override), dry-runs the Makefile, runs `make check-env`, ShellCheck and yamllint, and runs `scripts/check_conventions.sh` (modules registered in `MODULES`, `${VAR}`s documented in `example.env`, pinned images, unique host ports). Run that script locally after `make create-envs`.

## Configuration

- `modules/common-services/.env` is the global file: Postgres user, password and URL, Redis, Garage keys, public host, Ollama URL and Langfuse keys. Every module loads it before its own `.env` and references its values as `${VAR}`, so you change a shared value in one place.
- Each module reads `modules/<module>/.env`, created from `example.env`. Edit the `.env`, then restart the module.
- `LAB_PUBLIC_HOST` is set to the LAN IP by the first `make configure`/`init` (or `--host IP`); after changing it, run `make hatchet-token ARGS=--force`.
- `make create-envs` never overwrites an existing `.env`. It fills the `CHANGE_ME*` placeholders with random passwords, keys and secrets.
- Every host port is a variable in the module's `.env`.
- See [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Network `lang` not found | Start `common-services` first |
| NVIDIA driver error | Install the NVIDIA Container Toolkit, or use `GPU=0` |
| Port already allocated | Change the module's `*_PORT` variable in its `.env` |
| A module can't reach another | Inside containers use the container name, not `localhost` |
| Database does not exist | `make databases` |

## Adding a module

Create `modules/<name>/` with a `docker-compose.yml` that joins the `lang` network as external, plus an `example.env`. Reuse the shared services, pin image versions, add Makefile targets and update the docs. The full checklist is in [docs/MODULES.md](docs/MODULES.md).

## Contributing

Branch from `devel`, keep changes self-contained in a module, test from a clean state, and open a pull request against `devel`.

## Security notice

llm-lab is for **local experimentation**. Defaults are deliberately simple: a well-known default user name and email, open sign-up on some services and no auth on some services. Do not expose it to the internet as is. Change every credential and put services behind TLS and authentication before using a shared network.

## License

Distributed under the [MIT License](LICENSE).
