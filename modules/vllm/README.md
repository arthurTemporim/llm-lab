# vLLM

High-throughput inference server for Hugging Face models, with an OpenAI-compatible API. GPU only.

## Overview

| | |
|---|---|
| Documentation | [vLLM](https://docs.vllm.ai/), [supported models](https://docs.vllm.ai/en/latest/models/supported_models/), [OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/) |
| Image | `vllm/vllm-openai:v0.32.0-cu129` (needs an NVIDIA driver for CUDA 12.9 or newer) |
| Container(s) | `vllm` |
| GPU | Required (the reservation is in `docker-compose.yml`; there is no CPU mode and no `docker-compose.gpu.yml`) |
| Make target | `make vllm` |

## What it is used for

* Serve Hugging Face safetensors models (chat, vision, embeddings, speech-to-text) with continuous batching, which is faster than Ollama under concurrent load.
* Run uncensored or abliterated models that are not published for Ollama. Candidates are in [docs/HUGGINGFACE_MODELS.md](../../docs/HUGGINGFACE_MODELS.md).
* Backend for LiteLLM, Open WebUI, Langflow and the notebooks through the OpenAI API.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| OpenAI API (`/v1`), `/health`, `/metrics` | http://localhost:8000 | http://vllm:8000 |

Every `/v1` call needs `Authorization: Bearer $VLLM_API_KEY` (generated into `.env`). `/health` needs none.

## Quick start

```sh
make vllm          # starts common-services first, then this module
make vllm-logs
```

The first start downloads the model (many GB) and compiles kernels, which can take several minutes. Wait until the log shows `Application startup complete`.

To download models ahead of time, edit the list in `scripts/vllm_pull_model.sh` (each line has its size, and the script prints the total) and run it. It fills the same cache volume, needs no GPU, and skips files already downloaded:

```sh
./scripts/vllm_pull_model.sh
```

Check that it works:

```sh
curl http://localhost:8000/health
curl http://localhost:8000/v1/models -H "Authorization: Bearer $VLLM_API_KEY"
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $VLLM_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"dphn/Dolphin3.0-Llama3.1-8B","messages":[{"role":"user","content":"Hello"}]}'
```

Switch model: edit `VLLM_MODEL` (and `VLLM_EXTRA_ARGS`) in `.env`, then `make vllm`. The model name clients send is the Hugging Face id, unless you set `--served-model-name`.

## Configuration

Edit `modules/vllm/.env` (created by `make create-envs` from `example.env`), then `make vllm` to apply.

| Variable | Default | Description |
|---|---|---|
| `VLLM_MODEL` | `dphn/Dolphin3.0-Llama3.1-8B` | Hugging Face repo to serve. One model per process |
| `VLLM_MAX_MODEL_LEN` | `8192` | Context window in tokens. Lower it when VRAM runs out |
| `VLLM_GPU_MEMORY_UTILIZATION` | `0.90` | Share of the GPU's VRAM vLLM reserves up front |
| `VLLM_EXTRA_ARGS` | `--quantization fp8` | Extra `vllm serve` flags (quantization, `--runner pooling` for embeddings, tool parsers) |
| `VLLM_API_KEY` | `sk-CHANGE_ME` | **Secret.** Key clients must send. Replaced by a random value in `make create-envs` |
| `HF_TOKEN` | empty | Hugging Face token, only for gated or private repos |
| `VLLM_GPU_ID` | `0` | GPU index (`nvidia-smi -L`). Must be a card with compute capability 7.5 or newer |
| `VLLM_HOST_PORT` | `8000` | Host port |
| `NVIDIA_DRIVER_CAPABILITIES` | `compute,utility` | NVIDIA runtime |

Sizing rule: weights take about 2 bytes per parameter in bf16, 1 in fp8 and 0.55 in 4-bit, plus 1-3 GB for the KV cache and CUDA overhead. See [docs/HUGGINGFACE_MODELS.md](../../docs/HUGGINGFACE_MODELS.md) for models that fit a 12 GB card.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network |
| Used by | `litellm` | Add a model with provider `openai/<hugging-face-id>`, `api_base` `http://vllm:8000/v1` and `api_key` = `VLLM_API_KEY` |
| Used by | `openwebui` | Admin settings, OpenAI connection with URL `http://vllm:8000/v1` and the key |
| Used by | `langflow`, `notebooks` | OpenAI-compatible components, base URL `http://vllm:8000/v1` |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Downloaded models (Hugging Face cache) | `vllm_huggingface` named volume (`/root/.cache/huggingface`) | yes |

## Operations

```sh
make vllm-down                                  # stop, keep downloaded models
docker exec vllm ls /root/.cache/huggingface/hub   # cached models
docker volume rm vllm_huggingface               # free the disk (after down)
```

Upgrade: change the image tag, then `docker compose pull && docker compose up -d` in `modules/vllm/`. Check the new tag's CUDA version against your driver first.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `CUDA out of memory` or `No available memory for the cache blocks` | Lower `VLLM_MAX_MODEL_LEN`, use `--quantization fp8` or `bitsandbytes`, or stop Ollama/LocalAI: they share the card and vLLM reserves its share up front |
| Fails on the Tesla P4 | vLLM needs compute capability 7.5+; the P4 is 6.1. Set `VLLM_GPU_ID` to the RTX 3060 |
| `could not select device driver "nvidia"` | Install the NVIDIA Container Toolkit. This module has no CPU fallback |
| CUDA driver too old | The image targets CUDA 12.9. Update the driver, or pick an older image tag |
| `Unknown vLLM environment variable detected: VLLM_...` in the log | Harmless warning: `.env` is passed to the container whole |
| Architecture not supported | The model is not in vLLM's [supported list](https://docs.vllm.ai/en/latest/models/supported_models/). Use another repo or Ollama |
| 401 on `/v1/...` | Send `Authorization: Bearer $VLLM_API_KEY` |
| Gated repo download fails | Accept the license on the model page and set `HF_TOKEN` |
| Healthcheck `starting` for minutes | Normal on the first start (download plus compile). The grace period is 10 minutes |

## Notes

* This module is the exception to the "base compose runs on CPU" rule: it is GPU only. `make GPU=0 vllm` still asks for a GPU.
* Serving the lab's Ollama models and a vLLM model at once will not fit in 12 GB. Run one inference server at a time or share VRAM on purpose (`VLLM_GPU_MEMORY_UTILIZATION`, Ollama `keep_alive`).
* Uncensored models answer what you ask: keep the port local and the API key set, and read the model's license.
* Not yet run on a GPU: the compose file was only validated with `docker compose config`, and the settings follow the vLLM docs.
