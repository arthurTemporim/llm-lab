# Langfuse

[Langfuse](https://langfuse.com) is an open source LLM observability platform (traces, prompts, evals, datasets). This module runs **Langfuse 4.54** locally with Docker, reusing the shared services of the lab.

## Architecture

```
                         network: lang
 ┌──────────────┐   ┌───────────────────┐
 │ langfuse-web │──▶│ clickhouse        │  (this module: traces / observations / scores)
 │  :3000       │   └───────────────────┘
 ├──────────────┤   ┌───────────────────┐
 │ langfuse-    │──▶│ postgres :5432    │  (common-services: db "langfuse")
 │ worker       │   ├───────────────────┤
 │  :3030       │──▶│ redis    :6379    │  (common-services: queues / cache)
 └──────────────┘   ├───────────────────┤
                    │ minio    :9000    │  (common-services: S3 events, media, exports)
                    └───────────────────┘
```

| Service            | Where             | Why |
|--------------------|-------------------|-----|
| `langfuse-web`     | this module       | UI + public API (`localhost:3000`) |
| `langfuse-worker`  | this module       | Async processing of ingested events |
| `clickhouse`       | this module       | Analytics store (v3+ requirement), internal only |
| `postgres`         | common-services   | Transactional data (users, projects, prompts), database `langfuse` |
| `redis`            | common-services   | Queues (BullMQ) and cache. Runs with `noeviction`, as Langfuse requires |
| `minio`            | common-services   | S3-compatible blob storage (raw events, media, batch exports), bucket `langfuse` |

## Prerequisites

* Docker with the compose plugin.
* The `common-services` module running (it creates the `lang` network and provides postgres, redis and minio).

## Quick start

```sh
make create-envs      # creates .env files from the example.env files
# edit modules/langfuse/.env and set NEXTAUTH_SECRET, SALT, ENCRYPTION_KEY (see below)
make common-services  # postgres, redis, minio
make langfuse         # creates the "langfuse" db if missing, then starts the module
```

Or by hand:

```sh
cd modules/common-services && cp example.env .env && docker compose up -d
cd ../langfuse && cp example.env .env && docker compose up -d
```

Wait ~30-60 s on the first start (ClickHouse and Postgres migrations), then check:

```sh
curl localhost:3000/api/public/health   # {"status":"OK","version":"4.54.0"}
```

| What          | URL / address                                    |
|---------------|--------------------------------------------------|
| Langfuse UI   | http://localhost:3000                            |
| MinIO console | http://localhost:9101 (`minio` / `miniosecret`)  |
| MinIO S3 API  | http://localhost:9100                            |
| Worker health | http://localhost:3030/api/health (localhost only) |

### Generate the secrets

```sh
openssl rand -hex 32   # run 3 times: NEXTAUTH_SECRET, SALT, ENCRYPTION_KEY
```

`ENCRYPTION_KEY` must be exactly 64 hex characters. Keep it: it encrypts stored LLM API keys, and changing it makes them unreadable. `docker compose` refuses to start when these are missing.

### First login

With the defaults of `example.env` the first start seeds (once):

* user `admin@example.com` / `change-me-admin`
* organization and project `llm-lab`
* API keys `pk-lf-llm-lab-local` / `sk-lf-llm-lab-local`

Change them before the first start. Seeding runs only if the user/org/project do not exist yet. To skip it, leave the `LANGFUSE_INIT_*` variables empty and sign up in the UI.

## Configuration (`modules/langfuse/.env`)

| Variable | Default | Description |
|---|---|---|
| `LANGFUSE_VERSION` | `4.54` | Tag for `langfuse/langfuse` and `langfuse/langfuse-worker` |
| `LANGFUSE_PORT` | `3000` | Host port of the web UI |
| `NEXTAUTH_URL` | `http://localhost:3000` | Public URL of the UI (auth callbacks) |
| `NEXTAUTH_SECRET` / `SALT` / `ENCRYPTION_KEY` | none, **required** | Secrets, see above |
| `TELEMETRY_ENABLED` | `false` | Anonymous usage telemetry |
| `AUTH_DISABLE_SIGNUP` | `false` | Disable public sign-up after creating your user |
| `DATABASE_URL` | `postgresql://lang:lang@postgres:5432/langfuse` | Shared Postgres |
| `REDIS_HOST` / `REDIS_PORT` | `redis` / `6379` | Shared Redis (no password) |
| `CLICKHOUSE_USER` / `CLICKHOUSE_PASSWORD` | `clickhouse` | ClickHouse credentials |
| `CLICKHOUSE_URL` / `CLICKHOUSE_MIGRATION_URL` | `http://clickhouse:8123` / `clickhouse://clickhouse:9000` | ClickHouse HTTP and native endpoints |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minio` / `miniosecret` | S3 credentials, **must match** `common-services/.env` |
| `LANGFUSE_S3_BUCKET` | `langfuse` | Bucket (must be listed in `MINIO_BUCKETS` of common-services) |
| `LANGFUSE_S3_ENDPOINT` | `http://minio:9000` | S3 endpoint inside the `lang` network |
| `LANGFUSE_S3_EXTERNAL_ENDPOINT` | `http://localhost:9100` | S3 endpoint reachable from your browser (presigned media/export URLs) |
| `LANGFUSE_S3_BATCH_EXPORT_ENABLED` | `false` | Enable batch exports to S3 |
| `LANGFUSE_INIT_*` | see `example.env` | Headless org / project / keys / user |

MinIO settings (`MINIO_*`, ports, buckets) live in `modules/common-services/example.env`.

## Sending traces

Langfuse v4 ingests traces over **OpenTelemetry (OTLP)**. The legacy `/api/public/ingestion` endpoint only accepts scores, so use a v4-compatible SDK (Python SDK v3+ / JS SDK v4+) or any OTLP exporter.

```sh
pip install langfuse
export LANGFUSE_PUBLIC_KEY=pk-lf-llm-lab-local
export LANGFUSE_SECRET_KEY=sk-lf-llm-lab-local
export LANGFUSE_HOST=http://localhost:3000     # use http://langfuse-web:3000 from containers in the lang network
```

```python
from langfuse import observe

@observe()
def ask(question: str) -> str:
    return "hello"

ask("hi")
```

Plain OTLP (JSON) example:

```sh
AUTH=$(printf 'pk-lf-llm-lab-local:sk-lf-llm-lab-local' | base64 -w0)
curl -X POST http://localhost:3000/api/public/otel/v1/traces \
  -H "Authorization: Basic $AUTH" -H 'content-type: application/json' \
  -H 'x-langfuse-ingestion-version: 4' \
  -d '{"resourceSpans":[...]}'
```

### LiteLLM

The `litellm` module is on the same network. Add to its `.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-llm-lab-local
LANGFUSE_SECRET_KEY=sk-lf-llm-lab-local
LANGFUSE_HOST=http://langfuse-web:3000
```

and set `litellm_settings: { success_callback: ["langfuse"] }` in its `config.yaml`.

## Operations

```sh
make langfuse-logs    # follow logs
make langfuse-down    # stop (data is kept)
make langfuse-db      # (re)create the postgres database if missing
```

Full reset (**deletes all Langfuse data**):

```sh
cd modules/langfuse && docker compose down -v
docker exec postgres psql -U lang -d postgres -c 'DROP DATABASE langfuse' && make langfuse-db
docker exec minio sh -c 'rm -rf /data/langfuse/*'
```

Upgrade: change `LANGFUSE_VERSION`, then `docker compose pull && docker compose up -d`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `set NEXTAUTH_SECRET in .env` on `compose up` | `.env` is missing or the secrets are empty |
| `network lang declared as external, but could not be found` | Start common-services first (`make common-services`) |
| `database "langfuse" does not exist` | Postgres volume predates this module: run `make langfuse-db` |
| Web restarts with ClickHouse errors | `docker compose logs clickhouse`; check the password matches `CLICKHOUSE_PASSWORD` |
| S3 / `NoSuchBucket` errors in the worker | The bucket must be in `MINIO_BUCKETS` (common-services `.env`), then `docker compose up -d minio` there |
| S3 `SignatureDoesNotMatch` / `InvalidAccessKeyId` | `MINIO_ROOT_*` differ between the two `.env` files |
| Images or media do not load in the UI | `LANGFUSE_S3_EXTERNAL_ENDPOINT` must be reachable from the browser (default `http://localhost:9100`) |
| `Event type "trace-create" is not accepted` | v4 expects OTLP / a v4 SDK (see above) |
| Port already in use | Change `LANGFUSE_PORT`, or `MINIO_API_PORT` / `MINIO_CONSOLE_PORT` in common-services |

## Notes

* `clickhouse` has no host ports on purpose (9000 is commonly taken); it is reachable only inside the `lang` network.
* The MinIO image comes from Chainguard (`cgr.dev/chainguard/minio`) because MinIO no longer publishes images on Docker Hub; it is the same image the official Langfuse compose uses.
* Defaults are for local development only. Do not expose this setup as is.
