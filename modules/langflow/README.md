# Langflow

Low-code visual builder for LLM chains, agents and RAG flows.

## Overview

| | |
|---|---|
| Documentation | [Langflow](https://docs.langflow.org/) |
| Image | built from `modules/langflow/Dockerfile` (base `langflowai/langflow:1.12.3`, plus `langflow[bundles]` and `lfx-bundles[litellm]`) |
| Container(s) | `langflow` |
| GPU | Not used |
| Make target | `make langflow` (rebuild with `make build`) |

## What it is used for

* Drag-and-drop design of flows, agents and RAG pipelines.
* Calls Ollama or LiteLLM as model providers.
* `langflow.json` holds example flows to import.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| Web UI / API | http://localhost:7860 | http://langflow:7860 |

Default login: `lang` / `lang` (`LANGFLOW_SUPERUSER`, `LANGFLOW_SUPERUSER_PASSWORD`).

## Quick start

```sh
make langflow
make langflow-logs
```

Open http://localhost:7860, log in, then import `modules/langflow/langflow.json` from the UI to get example flows.

## Configuration

Edit `modules/langflow/.env` (created by `make create-envs` from `example.env`), then `make langflow` to apply.

| Variable | Default | Description |
|---|---|---|
| `LANGFLOW_PORT` | `7860` | Host port |
| `LANGFLOW_DATABASE_URL` | `postgresql://lang:lang@postgres:5432/langflow` | Shared Postgres. Credentials must match `common-services` |
| `LANGFLOW_SUPERUSER` / `LANGFLOW_SUPERUSER_PASSWORD` | `lang` / `lang` | Admin account. Change the password |
| `LANGFLOW_AUTO_LOGIN` | `false` | Skip the login page when `true` |
| `LANGFLOW_NEW_USER_IS_ACTIVE` | `false` | New users need an admin to activate them |
| `LANGFLOW_LOG_LEVEL` | `debug` | Log verbosity |
| `LANGFLOW_SSRF_ALLOWED_HOSTS` | commented out | Hosts that components may call, if blocked by SSRF protection |

In components, use container names, not `localhost`:

* Ollama: `http://ollama:11434`
* LiteLLM: `http://litellm:4000`

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Postgres database `langflow` (flows are stored there) |
| Depends on | `ollama` | Optional, runtime: model provider |
| Depends on | `litellm` | Optional, runtime: model gateway |
| Used by | none | |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Flows, users | Postgres database `langflow` | yes |
| Extra state | `langflow-data` named volume | yes |

## Operations

```sh
make langflow-down     # stop, keep data
make build             # rebuild the custom image
```

Upgrade: change the base image tag in `Dockerfile`, then rebuild and `make langflow`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Cannot reach Ollama from a component | Use `http://ollama:11434`, not `localhost` |
| `database "langflow" does not exist` | `make databases` |
| New user cannot log in | Activate the user as the superuser (`LANGFLOW_NEW_USER_IS_ACTIVE=false`) |
| Port already in use | Change `LANGFLOW_PORT` |

## Notes

* Defaults are for local development only.
