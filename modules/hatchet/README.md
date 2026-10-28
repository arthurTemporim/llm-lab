# Hatchet

Durable task queue and workflow engine: workers register tasks and workflows over gRPC, Hatchet schedules, retries and records every run (Hatchet Lite).

## Overview

| | |
|---|---|
| Documentation | [Hatchet](https://docs.hatchet.run), [self-hosting with Hatchet Lite](https://docs.hatchet.run/self-hosting/hatchet-lite), [configuration options](https://docs.hatchet.run/self-hosting/configuration-options) |
| Image | `ghcr.io/hatchet-dev/hatchet/hatchet-lite:v0.110.8` |
| Container(s) | `hatchet-lite` |
| GPU | Not used |
| Make target | `make hatchet` |

## What it is used for

* One shared workflow engine for lab projects (for example gollum's document parsing): retries, concurrency limits, fan-out and run history without a queue in every project.
* Dashboard to see runs, inputs, outputs, logs and failures, and to re-run tasks.
* Workers run anywhere (on the `lang` network or another machine on the LAN) and call the lab's models and services (`litellm`, `docling`, `ollama`) from their tasks.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| Dashboard and REST API | http://localhost:8889 | http://hatchet-lite:8888 |
| gRPC (workers, SDK clients) | `localhost:7077` | `hatchet-lite:7077` |

Both ports listen on all interfaces. From another machine use `HATCHET_PUBLIC_HOST` instead of `localhost`.

Default login: `admin@example.com` / `Admin123!!` (change it in `.env` before the first start, or in the dashboard). New users can sign up in the dashboard.

## Quick start

```sh
make hatchet                       # starts common-services first (creates the hatchet database), then this module
make logs-hatchet
./scripts/hatchet_token.sh         # prints an API token for the default tenant
```

Check that it works:

```sh
docker inspect --format '{{.State.Health.Status}}' hatchet-lite   # healthy
curl -I http://localhost:8889
```

Point a worker at it (Python SDK shown; the other SDKs read the same variables):

```sh
HATCHET_CLIENT_TOKEN=<token from hatchet_token.sh>
HATCHET_CLIENT_HOST_PORT=hatchet-lite:7077   # on the lang network; <HATCHET_PUBLIC_HOST>:7077 elsewhere
HATCHET_CLIENT_TLS_STRATEGY=none
```

## Configuration

Edit `modules/hatchet/.env` (created by `make create-envs` from `example.env`), then `make hatchet` to apply.

| Variable | Default | Description |
|---|---|---|
| `HATCHET_PORT` | `8889` | Host port of the dashboard and REST API (8888 is taken by `notebooks`) |
| `HATCHET_GRPC_PORT` | `7077` | Host port of gRPC for workers |
| `HATCHET_PUBLIC_HOST` | `localhost` | Host name or IP clients use to reach this machine. Builds `SERVER_URL`, the cookie domain and the gRPC broadcast address. Set it to the LAN IP for remote access |
| `DATABASE_URL` | `postgresql://lang:lang@postgres:5432/hatchet?sslmode=disable` | Must match the Postgres user/password in `common-services` |
| `DATABASE_MAX_CONNS` | `20` | Connection pool cap (Hatchet default 50); Postgres is shared |
| `SERVER_AUTH_COOKIE_INSECURE`, `SERVER_GRPC_INSECURE` | `t` | Plain HTTP and gRPC (no TLS) |
| `SERVER_GRPC_BIND_ADDRESS`, `SERVER_GRPC_PORT` | `0.0.0.0`, `7077` | gRPC listener inside the container |
| `SERVER_AUTH_SET_EMAIL_VERIFIED` | `t` | New users need no email verification |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | `admin@example.com`, `Admin123!!` | Admin user, created on the first start only |

`SERVER_URL`, `SERVER_AUTH_COOKIE_DOMAIN` and the gRPC broadcast addresses are derived in `docker-compose.yml`; don't set them in `.env`. Every other Hatchet variable is in the [configuration options](https://docs.hatchet.run/self-hosting/configuration-options); add it to `.env` and restart.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Postgres database `hatchet` (in `POSTGRES_DATABASES`) |
| Used by | Workers and clients (for example gollum) | gRPC `hatchet-lite:7077` on the `lang` network or `<HATCHET_PUBLIC_HOST>:7077`, with `HATCHET_CLIENT_TOKEN` |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Tenants, users, workflows, runs | Postgres database `hatchet` (`common-services`) | yes |
| Generated keys, cookie secrets, client config | `hatchet-config` volume | yes |

## Operations

```sh
make down-hatchet     # stop, keep data
```

Upgrade: change the image tag, then `docker compose pull && docker compose up -d` in `modules/hatchet/`. Migrations run at every start. Check the [release notes](https://github.com/hatchet-dev/hatchet/releases) and keep the SDK version of your workers compatible.

Reset: `docker compose down -v` in `modules/hatchet/` and drop the `hatchet` database (`docker exec postgres psql -U lang -d postgres -c 'DROP DATABASE hatchet'`), then `make hatchet`. Every existing token stops working; create new ones with `scripts/hatchet_token.sh`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Login succeeds but the dashboard sends you back to the login page | The browser URL host does not match `HATCHET_PUBLIC_HOST` (cookie domain). Open the dashboard at `http://<HATCHET_PUBLIC_HOST>:<HATCHET_PORT>` |
| Remote worker connects, then fails with `connection refused` to `localhost:7077` | `HATCHET_PUBLIC_HOST` is `localhost`; set it to the server's IP, or set `HATCHET_CLIENT_HOST_PORT` in the worker |
| Port 7077 or 8889 already in use | Another Hatchet runs on the host (for example a project's own `hatchet-lite`). Stop it or change `HATCHET_GRPC_PORT` / `HATCHET_PORT` |
| `too many clients already` in Postgres logs | Lower `DATABASE_MAX_CONNS` here or in the other modules |
| `hatchet_token.sh`: tenant not found | Hatchet has not finished its first start, or the tenant slug is wrong. Check `make logs-hatchet` |

## Notes

* No TLS and a public sign-up page: keep it on a trusted LAN. Change the admin password.
* Tokens are signed with the keys in the `hatchet-config` volume and embed the gRPC broadcast address of their creation time. After changing `HATCHET_PUBLIC_HOST`, create new tokens or set `HATCHET_CLIENT_HOST_PORT` in the workers.
