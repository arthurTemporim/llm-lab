# Notebooks

Jupyter playground with LangChain and the Ollama integration.

## Overview

| | |
|---|---|
| Documentation | [LangChain](https://python.langchain.com/docs/introduction/), [Jupyter](https://jupyter-docker-stacks.readthedocs.io/) |
| Image | built from `modules/notebooks/Dockerfile` (base `jupyter/minimal-notebook:python-3.11`) |
| Container(s) | `jupyter` |
| GPU | Not used |
| Make target | `make notebooks` (rebuild with `make build`) |

## What it is used for

* Experiments with LangChain and local models.
* `langchain.ipynb`: basic chain. `rag-example.ipynb`: RAG example.

## Access

| What | Host (browser, CLI) | Inside the `lang` network |
|---|---|---|
| JupyterLab | http://localhost:8888 | http://jupyter:8888 |

No token or password.

## Quick start

```sh
make notebooks
make notebooks-logs
```

Open http://localhost:8888 and run `langchain.ipynb`.

## Configuration

Edit `modules/notebooks/.env` (created by `make create-envs` from `example.env`), then `make notebooks` to apply.

| Variable | Default | Description |
|---|---|---|
| `NOTEBOOKS_PORT` | `8888` | Host port |

Python packages are in `modules/notebooks/requirements.txt` (`numpy`, `pandas`, `langchain`, `langchain-ollama`). Edit it and run `make build`.

In notebooks use the container name as base URL: `base_url="http://ollama:11434"`.

## Connections

| Direction | Module | How |
|---|---|---|
| Depends on | `common-services` | Only the `lang` network |
| Depends on | `ollama` | Runtime: the notebooks call `http://ollama:11434` |
| Used by | none | |

## Storage

| Data | Where | Survives `down` |
|---|---|---|
| Notebooks | bind mount `modules/notebooks/notebooks` | yes |

## Operations

```sh
make notebooks-down    # stop, keep notebooks
make build             # rebuild after changing requirements.txt
```

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Connection refused to Ollama | Use `http://ollama:11434`, not `localhost`, and pull the model first |
| Missing Python package | Add it to `requirements.txt`, then `make build` |
| Port already in use | Change `NOTEBOOKS_PORT` |

## Notes

* Runs **without a token**, so keep the port on your machine only.
* The base image uses a floating `python-3.11` tag; rebuilds can change packages.
