# llm-lab

A self-hosted, modular lab to try LLM models, tools and services on your own machine. It is infrastructure as Docker Compose: no app code, just modules you start when you need them.

## Documentation

| Document | Read it to… |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | understand the network, dependencies, data flows, storage and design decisions |
| [docs/MODULES.md](docs/MODULES.md) | see what each module does and the rules for new ones |
| [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md) | learn how configuration, secrets, GPU/CPU and upgrades work |
| [CLAUDE.md](CLAUDE.md) | give AI coding agents the project's conventions and gotchas |

## Why llm-lab?

- **Modular.** Each technology is a folder with its own `docker-compose.yml` and `example.env`. Start only what you need.
- **Shared infrastructure.** Postgres (with pgvector), Redis and MinIO run once and every module reuses them over one Docker network.
- **Local first.** Models run on your hardware (CPU or NVIDIA GPU). No cloud API key required.
- **Reproducible.** Pinned images, env templates and one `Makefile`.

## Modules

| Module | Purpose |
|---|---|
| `common-services` | Postgres + pgvector, Redis, MinIO. Creates the shared network. |
| `ollama` | Run and serve open-weight models |
| `localai` | OpenAI-compatible inference server |
| `openwebui` | Chat UI |
| `langflow` | Visual builder for flows, agents and RAG |
| `notebooks` | Jupyter with LangChain |
| `litellm` | Unified LLM gateway with metrics |
| `langfuse` | LLM observability: traces, prompts, evals |

Details are in [docs/MODULES.md](docs/MODULES.md).

## How it fits together

All containers join one external Docker network called `lang`, created by `common-services`. Inside it they reach each other by container name (for example `ollama` or `postgres`). From your host, use `localhost` and the port published in the module's `docker-compose.yml`.

```text
modules/
  common-services/   shared Postgres, Redis, MinIO + the network (start first)
  <module>/          docker-compose.yml, example.env, optional Dockerfile and README
scripts/             helper shell scripts used by the Makefile
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

`make init` creates the `.env` files, builds and starts the core modules, and pulls the models listed in `scripts/ollama_pull_model.sh`. Edit that list first to keep only the models you want.

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

The Makefile detects the NVIDIA Container Toolkit and adds each module's `docker-compose.gpu.yml` (`ollama`, `localai`, `openwebui`) when it is found. Force it with `make GPU=1 ...` or `make GPU=0 ...`. On CPU prefer small models. See [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md).

## Makefile

Run `make help` for the full list. Common targets:

| Target | Description |
|---|---|
| `make init` | Create envs, build, start the core modules, pull models |
| `make create-envs` | Copy each `example.env` to `.env` (never overwrites) |
| `make <module>` | Start a module (`common-services` is started first automatically) |
| `make <module>-logs` / `-down` | Follow logs or stop any module |
| `make databases` | Create the Postgres databases if missing (idempotent) |
| `make check-env` | Verify values that must match across modules |
| `make down` | Stop all modules, keep volumes |

## Helper scripts

The `scripts/` folder holds small helpers: pulling, listing and prompting Ollama models, creating the Postgres databases, generating random secrets for new `.env` files and checking values that must match.

## Configuration

- Each module reads `modules/<module>/.env`, created from `example.env`. Edit the `.env`, then restart the module.
- `make create-envs` never overwrites an existing `.env`; `CHANGE_ME` placeholders become random secrets.
- Every host port is a variable in the module's `.env`.
- Some values must match across modules (MinIO credentials); `make check-env` verifies them. See [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md).

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

llm-lab is for **local experimentation**. Defaults are deliberately simple: well-known passwords, open sign-up and no auth on some services. Do not expose it to the internet as is. Change every credential and put services behind TLS and authentication before using a shared network.

## License

Distributed under the [MIT License](LICENSE).
