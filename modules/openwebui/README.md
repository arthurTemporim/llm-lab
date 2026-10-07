# Open WebUI

ChatGPT-style web UI with RAG, web search, code execution and image generation.

## Overview

| | |
|---|---|
| Documentation | [Open WebUI](https://docs.openwebui.com/) |
| Image | `ghcr.io/open-webui/open-webui:v0.11.4` (GPU: `v0.11.4-cuda`) |
| Container(s) | `openwebui` |
| GPU | Optional, for local embeddings (`docker-compose.gpu.yml`, added automatically) |
| Make target | `make openwebui` |

## What it is used for

* Main chat interface of the lab.
* RAG over uploaded documents, web search, code execution and image generation.
* Front end for Ollama, and for any OpenAI-compatible server (LocalAI, LiteLLM).

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| Web UI | http://localhost:3000 | http://openwebui:8080 |

The first account you sign up becomes admin.

## Quick start

```sh
make openwebui
make openwebui-logs
```

Open http://localhost:3000, create the admin account and pick a model (pull one in Ollama first, see `modules/ollama/README.md`).

## Configuration

Edit `modules/openwebui/.env` (created by `make create-envs` from `example.env`), then `make openwebui` to apply. Most settings can also be changed in the admin panel.

| Variable | Default | Description |
|---|---|---|
| `OPENWEBUI_PORT` | `3000` | Host port |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama address |
| `ENABLE_OLLAMA_API` / `ENABLE_OPENAI_API` | `true` / `true` | Enable each connection type |
| `ENABLE_SIGNUP` | `true` | Allow new sign-ups. Set `false` after creating your users |
| `ENABLE_SIGNUP_PASSWORD_CONFIRMATION` | `false` | Ask to confirm the password on sign-up |
| `ENABLE_LOGIN_FORM` | `true` | Show the login form |
| `ENABLE_CODE_EXECUTION` | `true` | Code execution in chats |
| `ENABLE_WEB_SEARCH` | `true` | Web search |
| `ENABLE_IMAGE_GENERATION` | `true` | Image generation |
| `OFFLINE_MODE` | `true` | Do not download models or data from the internet |
| `RESPONSE_WATERMARK` | `This text is AI generated` | Text appended to responses |
| `MODELS_CACHE_TTL` / `AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST` | `10` / `30` | Model list cache and timeout (seconds) |
| `RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE` | `false` | Allow remote code in embedding models |
| `DATA_DIR` | `./data` | Data directory inside the container |
| `WEBUI_URL`, `WEBUI_NAME`, `DEFAULT_PROMPT_SUGGESTIONS`, `CORS_ALLOW_ORIGIN`, `USE_CUDA_DOCKER`, `IMAGE_GENERATION_MODEL` | commented out | Optional, see `example.env` |

To add LocalAI or LiteLLM: Admin Settings, Connections, add an OpenAI connection (`http://localai:8080/v1` or `http://litellm:4000/v1`) with its API key.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network (it keeps its own state) |
| Depends on | `ollama` | Runtime: no models are listed until it is up |
| Used by | none | |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Users, chats, uploads, vector data | `open-webui` named volume (`/app/backend/data`) | yes |

## Operations

```sh
make openwebui-down    # stop, keep data
```

Upgrade: change the image tag in both compose files, then `docker compose pull && docker compose up -d` in `modules/openwebui/`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| No models in the list | Pull a model in Ollama and check `OLLAMA_BASE_URL` |
| Cannot download embedding or other models | `OFFLINE_MODE=true`; set it to `false` for the first download |
| Port already in use | Change `OPENWEBUI_PORT` |

## Notes

* Sign-up is open by default. Disable it once your users exist.
* Defaults are for local development only.
