# Ollama

Pulls, runs and serves open-weight LLMs and embedding models over HTTP.

## Overview

| | |
|---|---|
| Documentation | [Ollama](https://ollama.com/), [API](https://github.com/ollama/ollama/blob/main/docs/api.md) |
| Image | `ollama/ollama:0.40.0` |
| Container(s) | `ollama` |
| GPU | Optional (`docker-compose.gpu.yml` reserves NVIDIA GPUs, added automatically) |
| Make target | `make ollama` |

## What it is used for

* Main local inference server of the lab (chat and embedding models).
* Backend for Open WebUI, Langflow, LiteLLM and the notebooks.
* Offers its own API and an OpenAI-compatible one (`/v1`).

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| API | http://localhost:11434 | http://ollama:11434 |

No login.

## Quick start

```sh
make ollama
make ollama-logs
```

Pull a model (edit the list in `scripts/ollama_pull_model.sh`, or pull one):

```sh
./scripts/ollama_pull_model.sh
docker exec ollama ollama pull llama3.2
```

Check that it works:

```sh
./scripts/ollama_send_prompt.sh
curl http://localhost:11434/api/tags
```

## Configuration

Edit `modules/ollama/.env` (created by `make create-envs` from `example.env`), then `make ollama` to apply.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_PORT` | `11434` | Host port |
| `OLLAMA_HOST` | `0.0.0.0` | Bind address inside the container. Keep it so other modules can reach it |
| `OLLAMA_ORIGINS` | `*` | Allowed CORS origins (e.g. `app://obsidian.md*`) |
| `OLLAMA_KEEP_ALIVE` | `5m` | How long a model stays loaded between calls |
| `OLLAMA_NUM_PARALLEL`, `OLLAMA_NUM_THREADS`, `OLLAMA_FLASH_ATTENTION` | commented out | Optional performance tuning |
| `NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES` | `all`, `compute,utility` | NVIDIA runtime; ignored on CPU-only hosts |

GPU: auto-detected by the Makefile. Force with `GPU=1 make ollama` or disable with `GPU=0 make ollama`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network |
| Used by | `openwebui` | `OLLAMA_BASE_URL=http://ollama:11434` |
| Used by | `langflow` | Ollama components, base URL `http://ollama:11434` |
| Used by | `litellm` | Optional provider, `ollama/<model>` |
| Used by | `notebooks` | `base_url="http://ollama:11434"` in LangChain |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Models | `ollama` named volume (`/root/.ollama`) | yes |

## Operations

```sh
make ollama-down                      # stop, keep models
docker exec ollama ollama list        # installed models
docker exec ollama ollama rm <model>  # free disk space
```

Upgrade: change the image tag, then `docker compose pull && docker compose up -d` in `modules/ollama/`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Other containers cannot connect | Use `http://ollama:11434`, not `localhost` |
| Slow, runs on CPU | Check the NVIDIA runtime, or force `GPU=1` |
| Out of memory with several models | Lower `OLLAMA_KEEP_ALIVE` or run one inference server at a time (shares VRAM with LocalAI and Open WebUI) |
| Port already in use | Change `OLLAMA_PORT` |

## Notes

* The API has no authentication. Do not expose the port beyond your machine.
* Model downloads are many GB.
