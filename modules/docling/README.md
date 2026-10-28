# Docling

Converts PDFs, Office files, HTML and images to Markdown, JSON or text over HTTP, with layout, table and OCR models (docling-serve). A small manager in front of it starts docling-serve only when there is work, restarts it when a conversion fails, and stops it when idle to free GPU VRAM.

## Overview

| | |
|---|---|
| Documentation | [docling-serve](https://github.com/docling-project/docling-serve), [configuration](https://github.com/docling-project/docling-serve/blob/main/docs/configuration.md), [API usage](https://github.com/docling-project/docling-serve/blob/main/docs/usage.md) |
| Image | Worker: `ghcr.io/docling-project/docling-serve-cpu:v1.38.2` (GPU: `ghcr.io/docling-project/docling-serve-cu128:v1.38.2`). Manager: built from `manager/Dockerfile` (`python:3.13.18-slim`) |
| Container(s) | `docling` (manager, the API clients use), `docling-worker` (docling-serve, started on demand) |
| GPU | Optional, worker only (`docker-compose.gpu.yml` swaps in the CUDA image and reserves one card, added automatically) |
| Make target | `make docling` |

## What it is used for

* One shared document converter: clients upload a file and get Markdown back, without shipping Docling, PyTorch and its models in their own images.
* Caps conversion load in one place (the manager queue, `DOCLING_MANAGER_CONCURRENCY`), so clients (for example Hatchet workers) can scale freely.
* Runs the layout, table and OCR models on the GPU when available, several times faster than on CPU, and frees the VRAM when there is nothing to convert.
* Recovers from OCR/model crashes and stuck conversions by restarting docling-serve and retrying the job.
* Web UI to try conversions by hand.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| API, `/health`, `/docs` (OpenAPI) | http://localhost:5001 | http://docling:5001 |
| Web UI | http://localhost:5001/ui | http://docling:5001/ui |

No login. If `DOCLING_SERVE_API_KEY` is set, every API call needs the `X-Api-Key` header.

`docling-worker` has no host port: everything goes through the manager. Opening the UI or the docs starts the worker, which stops again `DOCLING_MANAGER_IDLE_TIMEOUT` seconds after the last request. To keep it up while you use the UI, run `curl -X POST http://localhost:5001/manager/start`, then `curl -X POST http://localhost:5001/manager/stop` when you are done.

## How the manager works

```text
client ──HTTP──▶ docling (manager) ──Docker API──▶ start / restart / stop docling-worker
                       │
                       └──async convert, poll, result──▶ docling-worker (docling-serve)
```

* **Same API as docling-serve.** `POST /v1/convert/{file,source}`, `POST /v1/chunk/<chunker>/{file,source}` and their `/async` variants become jobs. `GET /v1/status/poll/{task_id}` (optional `wait=<seconds>`) and `GET /v1/result/{task_id}` work as in docling-serve, with task ids owned by the manager. Every other path (`/ui`, `/docs`, `/v1/capabilities`, ...) is proxied to the worker.
* **Queue.** Jobs wait in the manager. At most `DOCLING_MANAGER_CONCURRENCY` run on the worker at once, always through its async endpoints, so a sync client is bound only by `DOCLING_MANAGER_SYNC_WAIT`.
* **On-demand start.** The first job starts `docling-worker` and waits until `/health` answers (cold start: models load again, from a few seconds up to `DOCLING_MANAGER_START_TIMEOUT`).
* **Restart and retry.** A crash, connection error, 5xx, task `failure`, or an attempt longer than `DOCLING_MANAGER_TASK_TIMEOUT` restarts the worker and retries the job, up to `DOCLING_MANAGER_MAX_RETRIES` times. When one crash breaks several jobs, the worker restarts once, and the other jobs retry without using up a retry. A 4xx from the worker (bad input, size limit) is returned to the client as is, with no retry.
* **Idle stop.** When no job is queued or running and nothing has been proxied for `DOCLING_MANAGER_IDLE_TIMEOUT` seconds, the manager stops `docling-worker`. It also stops the worker this way after `make docling`, because Compose starts it too.
* **State in memory.** The queue and results live in the manager, and the request and result files in its `/tmp`. Restarting the `docling` container loses queued jobs and unfetched results. Use Hatchet when you need durable runs.

Manager endpoints:

| Endpoint | What it does |
|---|---|
| `GET /health` | Manager health. Never starts the worker |
| `GET /manager/status` | Worker state, generation (restart count), queued and running jobs, idle time |
| `POST /manager/start` | Starts the worker and turns idle stop off |
| `POST /manager/stop` | Turns idle stop back on and stops the worker if it is idle |

## Quick start

```sh
make docling          # starts common-services first, then this module
make logs-docling
```

The models are in the image, so there is no download at first start, but the image is large (about 4.4 GB on CPU, 11.4 GB with CUDA). Compose starts the worker too. The manager stops it after `DOCLING_MANAGER_IDLE_TIMEOUT` seconds.

Check that it works:

```sh
curl http://localhost:5001/health           # manager
curl http://localhost:5001/manager/status   # worker state: running or exited
```

Convert a file and print the Markdown (sync, waits up to `DOCLING_MANAGER_SYNC_WAIT` seconds, cold start included):

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
| `DOCLING_PORT` | `5001` | Host port of the manager |
| `DOCLING_MANAGER_IDLE_TIMEOUT` | `30` | Seconds without work before the worker is stopped |
| `DOCLING_MANAGER_START_TIMEOUT` | `300` | Seconds to wait for the worker to become healthy |
| `DOCLING_MANAGER_TASK_TIMEOUT` | `1800` | Seconds one attempt may run before it counts as stuck (restart and retry) |
| `DOCLING_MANAGER_MAX_RETRIES` | `2` | Retries per job; each one restarts the worker first |
| `DOCLING_MANAGER_CONCURRENCY` | `2` | Jobs sent to the worker at once. Keep it equal to `DOCLING_SERVE_ENG_LOC_NUM_WORKERS` |
| `DOCLING_MANAGER_SYNC_WAIT` | `1800` | Seconds the sync endpoints wait, cold start and retries included |
| `DOCLING_MANAGER_RESULT_TTL` | `3600` | Seconds an unfetched result is kept |
| `DOCLING_MANAGER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `DOCLING_SERVE_ENABLE_UI` | `true` | Web UI at `/ui` |
| `DOCLING_SERVE_ENG_LOC_NUM_WORKERS` | `2` | Conversions processed at once; extra requests queue. Each worker loads its own models |
| `DOCLING_SERVE_ENG_LOC_SHARE_MODELS` | commented out | `true` makes the workers share one set of models (less RAM/VRAM) |
| `DOCLING_SERVE_MAX_SYNC_WAIT` | `120` | docling-serve's own sync limit. Not used through the manager, which always calls the async endpoints |
| `DOCLING_SERVE_MAX_NUM_PAGES`, `DOCLING_SERVE_MAX_FILE_SIZE` | commented out | Per-document limits |
| `DOCLING_DEVICE` | commented out (auto) | `cpu`, `cuda` or `cuda:<n>` |
| `DOCLING_NUM_THREADS` | commented out (`4`) | Torch threads on CPU |
| `DOCLING_SERVE_API_KEY` | unset | Secret. When set, clients must send it as `X-Api-Key`; the manager checks it and forwards it to the worker |
| `DOCLING_SERVE_LOG_LEVEL` | `WARNING` | `WARNING`, `INFO` or `DEBUG` |
| `DOCLING_GPU_ID` | `0` | GPU index from `nvidia-smi -L`. Must be Turing or newer (not the Tesla P4) |
| `NVIDIA_DRIVER_CAPABILITIES` | `compute,utility` | NVIDIA runtime; ignored on CPU-only hosts |

Both containers read the same `.env`. Every docling-serve variable is in its [configuration docs](https://github.com/docling-project/docling-serve/blob/main/docs/configuration.md); add it to `.env` and restart.

GPU: auto-detected by the Makefile. Force with `GPU=1 make docling` or disable with `GPU=0 make docling`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network |
| Depends on | Docker host | `/var/run/docker.sock` mounted in the manager to start, restart and stop `docling-worker` |
| Used by | External clients (e.g. Hatchet workers) | `POST http://docling:5001/v1/convert/file` when they join the `lang` network, `http://localhost:5001` otherwise. Files are sent as multipart uploads, so a shared volume does not help |
| Used by | `openwebui` (optional) | Admin settings > Documents > content extraction engine `Docling`, URL `http://docling:5001` |

## Storage

None. The models are in the image. Uploads and results stay in the manager's `/tmp` until they are fetched (or expire after `DOCLING_MANAGER_RESULT_TTL`), and are lost when the `docling` container is recreated.

## Operations

```sh
make down-docling                                  # stop and remove both containers
curl -X POST http://localhost:5001/manager/stop    # only free the worker's memory now (if idle)
docker logs -f docling-worker                      # docling-serve logs (make logs-docling shows both)
```

Upgrade docling-serve: change the tag in both `docker-compose.yml` and `docker-compose.gpu.yml` (keep them equal), then `docker compose pull && docker compose up -d` in `modules/docling/` (add `-f docker-compose.yml -f docker-compose.gpu.yml` on GPU, or run `make docling`). Upgrade the manager: edit `manager/Dockerfile` or `manager/requirements.txt`, then `make docling` (it rebuilds).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Sync call fails on long documents (`504`) | It hit `DOCLING_MANAGER_SYNC_WAIT`. The job keeps running: poll the task id from the error, use the async endpoint, or raise the value |
| First request after a pause is slow | Cold start: the worker was stopped after `DOCLING_MANAGER_IDLE_TIMEOUT` and loads its models again. Raise the timeout to keep it up longer |
| `502` "failed after N attempts" | The worker failed on every attempt (crash, task failure or timeout). See `docker logs docling` for each attempt and `docker logs docling-worker` for the cause. A document that always crashes OCR fails after `DOCLING_MANAGER_MAX_RETRIES` restarts |
| `503` "docling worker unavailable" / `container docling-worker not found` | The worker container is missing or does not start: run `make docling` and check `docker logs docling-worker` |
| Worker keeps running while idle | Idle stop is off after `POST /manager/start`: call `POST /manager/stop`. Check `GET /manager/status` |
| `no kernel image is available` / CUDA errors at start | `DOCLING_GPU_ID` points at a Pascal card (Tesla P4). Use the RTX 3060 / Turing or newer index |
| Out of memory (RAM or VRAM) | Lower `DOCLING_SERVE_ENG_LOC_NUM_WORKERS` or set `DOCLING_SERVE_ENG_LOC_SHARE_MODELS=true`. The GPU is shared with Ollama, vLLM and LocalAI |
| `401`/`403` from the API | `DOCLING_SERVE_API_KEY` is set; send it as `X-Api-Key` |
| Port already in use | Change `DOCLING_PORT` |

## Notes

* No authentication by default. Do not expose the port beyond your machine, or set `DOCLING_SERVE_API_KEY`.
* The manager mounts the Docker socket, which is root-equivalent on the host. It only calls the start, restart, stop and inspect endpoints for `docling-worker`.
* `docling-worker` uses `restart: "no"` (an exception to the module rules) so only the manager starts it. `docker compose up` starts it as well; the manager stops it when idle.
* The status WebSocket (`/v1/status/ws/{task_id}`) is not available through the manager; poll instead.
* Every upload goes over HTTP; large scans cost a network hop compared to the in-process library.
* The CUDA images have no `latest` tag; always pin a version.
