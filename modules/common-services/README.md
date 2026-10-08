# Common services

Shared Postgres (pgvector), Redis and MinIO used by the other modules. It also creates the `lang` Docker network.

## Overview

| | |
|---|---|
| Documentation | [pgvector](https://github.com/pgvector/pgvector), [Redis](https://redis.io/docs/), [MinIO](https://min.io/docs/minio/container/index.html) |
| Image | `pgvector/pgvector:pg17`, `redis:8.6.7-alpine`, `cgr.dev/chainguard/minio:latest` |
| Container(s) | `postgres`, `redis`, `minio` |
| GPU | Not used |
| Make target | `make common-services` (also started by every other module target) |

## What it is used for

* Creates the `lang` network that every other module joins.
* Postgres: databases for `langflow`, `langfuse` and `litellm`, with the `vector` extension for RAG.
* Redis: queues and cache (Langfuse).
* MinIO: S3-compatible object storage (Langfuse events, media and exports).

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| Postgres | `localhost:5432` | `postgres:5432` |
| Redis | `localhost:6380` | `redis:6379` |
| MinIO S3 API | http://localhost:9100 | http://minio:9000 (path-style access) |
| MinIO console | http://localhost:9101 (localhost only) | `minio:9001` |

Default logins: Postgres `lang` / `lang`, MinIO `minio` / `miniosecret`. Redis has no password.

## Quick start

```sh
make common-services
make common-services-logs
```

Check that it works:

```sh
docker exec postgres psql -U lang -c '\l'
docker exec redis redis-cli ping
```

## Configuration

Edit `modules/common-services/.env` (created by `make create-envs` from `example.env`), then `make common-services` to apply.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `lang` / `lang` | Postgres credentials. Connection strings in other modules must use the same values |
| `POSTGRES_DATABASES` | `langflow langfuse litellm` | Space separated databases created (with `vector`) by `make databases` |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minio` / `miniosecret` | MinIO credentials. **Must match** `modules/langfuse/.env` (`make check-env`) |
| `MINIO_BUCKETS` | `langfuse` | Space separated buckets created at every start if missing |
| `POSTGRES_PORT` | `5432` | Host port of Postgres |
| `REDIS_PORT` | `6380` | Host port of Redis (6379 is commonly taken) |
| `MINIO_API_PORT` | `9100` | Host port of the S3 API |
| `MINIO_CONSOLE_PORT` | `9101` | Host port of the console, bound to `127.0.0.1` |

A new database for a new module goes in `POSTGRES_DATABASES`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | none | Creates the network |
| Used by | `langflow` | Database `langflow` |
| Used by | `langfuse` | Database `langfuse`, Redis queues, MinIO bucket `langfuse` |
| Used by | `litellm` | Database `litellm` |
| Used by | all | The `lang` network |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Postgres databases | `postgres` named volume, mounted at `PGDATA` | yes |
| Redis data | named volume | yes |
| MinIO objects | named volume | yes |

Only `docker compose down -v` removes them.

## Operations

```sh
make common-services-down   # stop, keep data
make databases              # create missing databases (idempotent)
make check-env              # verify the MinIO credentials match
```

Upgrade: change the image tag, then `docker compose pull && docker compose up -d` in `modules/common-services/`. Do not change the Postgres major version without a dump.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `database "x" does not exist` | Add it to `POSTGRES_DATABASES`, run `make databases` |
| `NoSuchBucket` | Add the bucket to `MINIO_BUCKETS`, then `docker compose up -d minio` |
| Port already in use | Change the matching `*_PORT` variable |
| Databases empty after an old lab was recreated | The Postgres volume changed; restore from a `pg_dumpall` taken before |

## Notes

* Redis runs with `--maxmemory-policy noeviction` because Langfuse (BullMQ) requires it. Keep it.
* The MinIO API port is non-standard on purpose to avoid clashes with ClickHouse (9000).
* MinIO is the only image on `latest` (Chainguard publishes no other free tag).
* Defaults are for local development only.
