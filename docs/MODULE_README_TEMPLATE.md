# Module README template

Copy this file to `modules/<name>/README.md` and fill every section. Keep the order and the headings so all modules read the same. Delete a section only if it truly does not apply (write `None.` instead when a reader might wonder). Keep it short: link to [docs/](.) for anything that is not specific to the module.

How to fill each section:

| Section | What goes in it |
|---|---|
| Title + tagline | Module name and one sentence on what it is |
| Overview | Official documentation link, image(s) and version, container name(s), and whether it needs a GPU |
| What it is used for | The role in the lab, in 2-4 bullets |
| Access | Every URL/port: host side, in-network address, and who can use it (`localhost` only or all interfaces). Default credentials if any |
| Quick start | The `make` target first, then how to check it works |
| Configuration | The `.env` variables (from `example.env`) in a table, plus the config files or UI settings. Mark required and secret values |
| Connections | `Depends on` and `Used by`, with how each one connects |
| Storage | Volumes or bind mounts, and what survives `down` |
| Operations | Logs, stop, upgrade, reset |
| Troubleshooting | Symptom and fix, only for real problems seen with the module |
| Notes | Anything else relevant: limits, security, known issues |

Rules:

* Take ports, images, variables and defaults from `docker-compose.yml` and `example.env`. Do not invent them. When they change, change the README in the same commit.
* Never write real secrets. Use the defaults from `example.env` or `CHANGE_ME`.
* Use container names for in-network addresses and `localhost` for host-side URLs.
* English only.

---

## Template

````markdown
# <Module name>

<One sentence: what it is.>

## Overview

| | |
|---|---|
| Documentation | [<site name>](https://example.com/docs) |
| Image | `<image>:<tag>` (GPU: `<image>:<tag>`, if different) |
| Container(s) | `<container_name>` |
| GPU | Optional / Required / Not used |
| Make target | `make <name>` |

## What it is used for

* <Main use in the lab.>
* <Second use.>

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| <UI / API> | http://localhost:<PORT> | http://<container>:<port> |

Default login: `<user>` / `<password>` (change it in `.env`). <or "No login.">

## Quick start

```sh
make <name>          # starts common-services first, then this module
make <name>-logs
```

Check that it works:

```sh
curl http://localhost:<PORT>/<health>
```

## Configuration

Edit `modules/<name>/.env` (created by `make create-envs` from `example.env`), then `make <name>` to apply.

| Variable | Default | Description |
|---|---|---|
| `<NAME>_PORT` | `<port>` | Host port |
| `<VAR>` | `<default>` | <What it does. Say if required, secret or must match another module.> |

<Other places to configure: config files, UI settings.>

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | <postgres database `x`, redis, minio bucket `y`> |
| Used by | `<module>` | <address and purpose> |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| <what> | `<volume or path>` | yes |

## Operations

```sh
make <name>-down     # stop, keep data
```

Upgrade: change the image tag, then `docker compose pull && docker compose up -d` in `modules/<name>/`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| <symptom> | <fix> |

## Notes

* <Limits, security, known issues.>
````
