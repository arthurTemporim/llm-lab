# Docling

Converts PDFs, Office files, HTML and images to Markdown, JSON or text over HTTP, with layout, table and OCR models (docling-serve).

## Overview

| | |
|---|---|
| Documentation | [docling-serve](https://github.com/docling-project/docling-serve), [configuration](https://github.com/docling-project/docling-serve/blob/main/docs/configuration.md), [API usage](https://github.com/docling-project/docling-serve/blob/main/docs/usage.md) |
| Image | `ghcr.io/docling-project/docling-serve-cpu:v1.38.2` (GPU: `ghcr.io/docling-project/docling-serve-cu128:v1.38.2`) |
| Container(s) | `docling` |
| GPU | Optional (`docker-compose.gpu.yml` swaps in the CUDA image and reserves one card, added automatically) |
| Make target | `make docling` |

## What it is used for

* One shared document converter: clients upload a file and get Markdown back, without shipping Docling, PyTorch and its models in their own images.
* Caps conversion load in one place (`DOCLING_SERVE_ENG_LOC_NUM_WORKERS`), so clients (for example Hatchet workers) can scale freely.
* Runs the layout, table and OCR models on the GPU when available, several times faster than on CPU.
* Web UI to try conversions by hand.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| API, `/health`, `/docs` (OpenAPI) | http://localhost:5001 | http://docling:5001 |
| Web UI | http://localhost:5001/ui | http://docling:5001/ui |

No login. If `DOCLING_SERVE_API_KEY` is set, every API call needs the `X-Api-Key` header.

## Quick start

```sh
make docling          # starts common-services first, then this module
make docling-logs
```

The models are in the image, so there is no download at first start, but the image is large (about 4.4 GB on CPU, 11.4 GB with CUDA).

Check that it works:

```sh
curl http://localhost:5001/health
```

Convert a file and print the Markdown (sync, waits up to `DOCLING_SERVE_MAX_SYNC_WAIT` seconds):

```sh
curl -s -F 'files=@document.pdf;type=application/pdf' -F to_formats=md \
  http://localhost:5001/v1/convert/file | jq -r .document.md_content
```

For long documents, use the async endpoint and poll the task:

```sh
id=$(curl -s -F 'files=@document.pdf;type=application/pdf' -F to_formats=md \
  http://localhost:5001/v1/convert/file/async | jq -r .task_id)
curl -s http://localhost:5001/v1/status/poll/$id | jq -r .task_status   # pending|started|success|failure
curl -s http://localhost:5001/v1/result/$id | jq -r .document.md_content
```

Results are single-use: `/v1/result/{task_id}` returns them once.

## Configuration

Edit `modules/docling/.env` (created by `make create-envs` from `example.env`), then `make docling` to apply.

| Variable | Default | Description |
|---|---|---|
| `DOCLING_PORT` | `5001` | Host port |
| `DOCLING_SERVE_ENABLE_UI` | `true` | Web UI at `/ui` |
| `DOCLING_SERVE_ENG_LOC_NUM_WORKERS` | `2` | Conversions processed at once; extra requests queue. Each worker loads its own models |
| `DOCLING_SERVE_ENG_LOC_SHARE_MODELS` | commented out | `true` makes the workers share one set of models (less RAM/VRAM) |
| `DOCLING_SERVE_MAX_SYNC_WAIT` | `120` | Seconds the sync endpoint waits before it fails |
| `DOCLING_SERVE_MAX_NUM_PAGES`, `DOCLING_SERVE_MAX_FILE_SIZE` | commented out | Per-document limits |
| `DOCLING_DEVICE` | commented out (auto) | `cpu`, `cuda` or `cuda:<n>` |
| `DOCLING_NUM_THREADS` | commented out (`4`) | Torch threads on CPU |
| `DOCLING_SERVE_API_KEY` | empty | Secret. When set, clients must send it as `X-Api-Key` |
| `DOCLING_SERVE_LOG_LEVEL` | `WARNING` | `WARNING`, `INFO` or `DEBUG` |
| `DOCLING_GPU_ID` | `0` | GPU index from `nvidia-smi -L`. Must be Turing or newer (not the Tesla P4) |
| `NVIDIA_DRIVER_CAPABILITIES` | `compute,utility` | NVIDIA runtime; ignored on CPU-only hosts |

Every docling-serve variable is in its [configuration docs](https://github.com/docling-project/docling-serve/blob/main/docs/configuration.md); add it to `.env` and restart.

GPU: auto-detected by the Makefile. Force with `GPU=1 make docling` or disable with `GPU=0 make docling`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network |
| Used by | External clients (e.g. Hatchet workers) | `POST http://docling:5001/v1/convert/file` when they join the `lang` network, `http://localhost:5001` otherwise. Files are sent as multipart uploads, so a shared volume does not help |
| Used by | `openwebui` (optional) | Admin settings > Documents > content extraction engine `Docling`, URL `http://docling:5001` |

## Storage

None. The models are in the image and conversion results stay in a temporary folder until they are fetched.

## Operations

```sh
make docling-down     # stop
```

Upgrade: change the tag in both `docker-compose.yml` and `docker-compose.gpu.yml` (keep them equal), then `docker compose pull && docker compose up -d` in `modules/docling/` (add `-f docker-compose.yml -f docker-compose.gpu.yml` on GPU, or run `make docling`).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Sync call fails on long documents | It hit `DOCLING_SERVE_MAX_SYNC_WAIT`. Use the async endpoint or raise the value |
| `no kernel image is available` / CUDA errors at start | `DOCLING_GPU_ID` points at a Pascal card (Tesla P4). Use the RTX 3060 / Turing or newer index |
| Out of memory (RAM or VRAM) | Lower `DOCLING_SERVE_ENG_LOC_NUM_WORKERS` or set `DOCLING_SERVE_ENG_LOC_SHARE_MODELS=true`. The GPU is shared with Ollama, vLLM and LocalAI |
| `401`/`403` from the API | `DOCLING_SERVE_API_KEY` is set; send it as `X-Api-Key` |
| Port already in use | Change `DOCLING_PORT` |

## Notes

* No authentication by default. Do not expose the port beyond your machine, or set `DOCLING_SERVE_API_KEY`.
* Every upload goes over HTTP; large scans cost a network hop compared to the in-process library.
* The CUDA images have no `latest` tag; always pin a version.
