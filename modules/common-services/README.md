# Common services

Shared Postgres (pgvector), Redis and Garage (S3) used by the other modules. It also creates the `lang` Docker network.

## Overview

| | |
|---|---|
| Documentation | [pgvector](https://github.com/pgvector/pgvector), [Redis](https://redis.io/docs/), [Garage](https://garagehq.deuxfleurs.fr/documentation/) |
| Image | `pgvector/pgvector:pg17`, `redis:8.6.7-alpine`, `dxflrs/garage:v2.5.0` |
| Container(s) | `postgres`, `redis`, `garage` |
| GPU | Not used |
| Make target | `make common-services` (also started by every other module target) |

## What it is used for

* Creates the `lang` network that every other module joins.
* Postgres: databases for `langflow`, `langfuse` and `litellm`, with the `vector` extension for RAG.
* Redis: queues and cache (Langfuse).
* Garage: S3-compatible object storage (Langfuse events, media and exports).

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| Postgres | `localhost:5432` | `postgres:5432` |
| Redis | `localhost:6380` | `redis:6379` |
| Garage S3 API | http://localhost:9100 | http://garage:3900 (path-style access, region `garage`) |

Default logins: Postgres `lang` / `lang`, Garage the `GARAGE_DEFAULT_ACCESS_KEY` / `GARAGE_DEFAULT_SECRET_KEY` from `.env`. Redis has no password. Garage has no web console; use its CLI: `docker exec garage /garage bucket list`.

## Quick start

```sh
make common-services
make logs-common-services
```

Check that it works:

```sh
docker exec postgres psql -U lang -c '\l'
docker exec redis redis-cli ping
docker exec garage /garage status
```

## Configuration

Edit `modules/common-services/.env` (created by `make create-envs` from `example.env`), then `make common-services` to apply.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `lang` / `lang` | Postgres credentials. Connection strings in other modules must use the same values |
| `POSTGRES_DATABASES` | `langflow langfuse litellm` | Space separated databases created (with `vector`) by `make databases` |
| `GARAGE_DEFAULT_ACCESS_KEY` / `GARAGE_DEFAULT_SECRET_KEY` | fixed local defaults | S3 key (`GK` + 24 hex) and secret (64 hex), created at start if missing. **Must match** `modules/langfuse/.env` (`make check-env`) |
| `GARAGE_DEFAULT_BUCKET` | `langfuse` | Bucket created at every start if missing (one bucket only) |
| `GARAGE_RPC_SECRET` | generated | Internal RPC secret, 64 hex chars |
| `POSTGRES_PORT` | `5432` | Host port of Postgres |
| `REDIS_PORT` | `6380` | Host port of Redis (6379 is commonly taken) |
| `GARAGE_S3_PORT` | `9100` | Host port of the S3 API |

A new database for a new module goes in `POSTGRES_DATABASES`. Other Garage settings (paths, S3 region) are in `garage.toml`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | none | Creates the network |
| Used by | `langflow` | Database `langflow` |
| Used by | `langfuse` | Database `langfuse`, Redis queues, Garage bucket `langfuse` |
| Used by | `litellm` | Database `litellm` |
| Used by | all | The `lang` network |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Postgres databases | `postgres` named volume, mounted at `PGDATA` | yes |
| Redis data | named volume | yes |
| Garage objects and metadata | `garage-data` named volume | yes |

Only `docker compose down -v` removes them.

## Operations

```sh
make down-common-services   # stop, keep data
make databases              # create missing databases (idempotent)
make check-env              # verify the Garage credentials match
```

Upgrade: change the image tag, then `docker compose pull && docker compose up -d` in `modules/common-services/`. Do not change the Postgres major version without a dump.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `database "x" does not exist` | Add it to `POSTGRES_DATABASES`, run `make databases` |
| `NoSuchBucket` | Check `GARAGE_DEFAULT_BUCKET`, then `docker compose up -d garage` |
| `AuthorizationHeaderMalformed` (region) | The client must use the region `s3_region` from `garage.toml` (`garage`) |
| Port already in use | Change the matching `*_PORT` variable |
| Databases empty after an old lab was recreated | The Postgres volume changed; restore from a `pg_dumpall` taken before |

## Notes

* Redis runs with `--maxmemory-policy noeviction` because Langfuse (BullMQ) requires it. Keep it.
* The Garage S3 host port is 9100 on purpose to avoid clashes with ClickHouse (9000).
* Garage runs as a single node (`--single-node`) without replication, and creates the default key and bucket at start (`--default-bucket`).
* Garage rejects requests signed for another region than `s3_region` in `garage.toml`.
* Defaults are for local development only.
