# postgresql://lang:lang@pgvector:5432/vectordb
# Common services

| Service  | Image                         | Host port            | In-network address |
|----------|-------------------------------|----------------------|--------------------|
| postgres | `pgvector/pgvector:pg17`      | `5432`               | `postgres:5432`    |
| redis    | `redis:alpine` (`noeviction`) | `6380`               | `redis:6379`       |
| minio    | `cgr.dev/chainguard/minio`    | `9100` API, `9101` console | `minio:9000` |

All of them join the `lang` Docker network.

## MinIO

S3-compatible storage shared by the modules (used by `langfuse`).

* Configure via `.env` (copy `example.env`): `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKETS`, `MINIO_API_PORT`, `MINIO_CONSOLE_PORT`.
* `MINIO_BUCKETS` is a space separated list (e.g. `langfuse another-bucket`); buckets are created on every start if missing.
* Console: [http://localhost:9101](http://localhost:9101) (login with the root user/password).
* From other containers use `http://minio:9000` with path-style access.

## Postgres databases

`init/pgvector.sql` creates the `langflow` and `langfuse` databases, **only on the first start of an empty volume**. For an existing volume run `make langfuse-db` (or `scripts/create_langfuse_db.sh`).
