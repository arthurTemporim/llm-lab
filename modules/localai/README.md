# LocalAI

OpenAI-compatible server for LLMs, embeddings, images and audio, running locally.

## Overview

| | |
|---|---|
| Documentation | [LocalAI](https://localai.io/) |
| Image | `localai/localai:v3.12.1-aio-cpu` (GPU: `v3.12.1-aio-gpu-nvidia-cuda-13`) |
| Container(s) | `localai` |
| GPU | Optional (`docker-compose.gpu.yml` swaps the image and reserves NVIDIA GPUs, added automatically) |
| Make target | `make localai` |

## What it is used for

* Second inference server, next to Ollama, with an OpenAI-compatible API.
* Covers more than text: images and audio models.
* The all-in-one image ships preconfigured models and downloads them on first start.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| API and web UI | http://localhost:8080 | http://localai:8080 |

Clients must send `Authorization: Bearer <LOCALAI_API_KEY>`.

## Quick start

```sh
make localai
make localai-logs
```

The first start downloads models and can take several minutes. Check that it works:

```sh
curl http://localhost:8080/readyz
curl http://localhost:8080/v1/models -H "Authorization: Bearer $(grep LOCALAI_API_KEY modules/localai/.env | cut -d= -f2)"
```

## Configuration

Edit `modules/localai/.env` (created by `make create-envs` from `example.env`), then `make localai` to apply.

| Variable | Default | Description |
|---|---|---|
| `LOCALAI_PORT` | `8080` | Host port |
| `LOCALAI_API_KEY` | `sk-CHANGE_ME` | **Secret.** Key clients must send. `make create-envs` generates a random one |

Other LocalAI settings can be added to `.env`: it is loaded into the container with `env_file`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network |
| Used by | `openwebui` | Add it as an OpenAI connection in the admin settings (`http://localai:8080/v1`) |
| Used by | `litellm` | Optional provider (OpenAI-compatible) |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Models | bind mount `modules/localai/models` (git-ignored) | yes |
| Backends | bind mount `modules/localai/backends` (git-ignored) | yes |

## Operations

```sh
make localai-down     # stop, keep models
```

Upgrade: change the image tag in both compose files, then `docker compose pull && docker compose up -d` in `modules/localai/`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `401` from the API | Send the key from `.env` as a Bearer token |
| Not ready for minutes | First start downloads models; follow `make localai-logs` |
| Out of VRAM | Run one inference server at a time (shares the GPU with Ollama and Open WebUI) |
| Port already in use | Change `LOCALAI_PORT` |

## Notes

* Model downloads are many GB.
* `DEBUG=true` is set in compose, so logs are verbose.
