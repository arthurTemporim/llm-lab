.PHONY: help \
        create-envs init start start-full logs down build \
        common-services langflow notebooks openwebui ollama litellm \
        ollama-down ollama-logs ollama-build \
        litellm-down litellm-logs litellm-build

# =================== Variables ===================
current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
scripts_dir := $(current_dir)scripts/

mod_ollama := $(modules_dir)ollama
mod_common := $(modules_dir)common-services
mod_openwebui := $(modules_dir)openwebui
mod_langflow := $(modules_dir)langflow
mod_notebooks := $(modules_dir)notebooks
mod_litellm := $(modules_dir)litellm

help:
	@echo "Main targets:"
	@echo "  init            -> creates .envs and starts common-services + openwebui + ollama + litellm"
	@echo "  create-envs     -> creates ALL required .envs (root, ollama, langflow, openwebui, litellm)"
	@echo "  start           -> starts common-services + openwebui + ollama + litellm (assumes .envs already created)"
	@echo "  down            -> stops all modules"
	@echo "  build           -> builds all modules"
	@echo "  logs            -> openwebui logs"
	@echo "  ollama          -> starts the ollama stack"
	@echo "  ollama-logs     -> ollama logs"
	@echo "  ollama-down     -> stops ollama"
	@echo "  litellm         -> starts litellm"
	@echo "  litellm-logs    -> litellm logs"
	@echo "  litellm-down    -> stops litellm"
	@echo "  common-services -> starts postgres/redis"
	@echo "  langflow        -> starts langflow"
	@echo "  notebooks       -> starts notebooks"

# =================== .env creation ===================
create-envs:
	@if [ ! -f .env ]; then \
		echo "[create-envs] creating .env in project root"; \
		if [ -f example.env ]; then cp example.env .env; else echo "OLLAMA_HOST=0.0.0.0" > .env; fi; \
	fi
	@if [ ! -f $(mod_langflow)/.env ]; then \
		echo "[create-envs] creating .env for langflow"; \
		if [ -f $(mod_langflow)/example.env ]; then cp $(mod_langflow)/example.env $(mod_langflow)/.env; fi; \
	fi
	@if [ ! -f $(mod_openwebui)/.env ]; then \
		echo "[create-envs] creating .env for openwebui"; \
		if [ -f $(mod_openwebui)/example.env ]; then cp $(mod_openwebui)/example.env $(mod_openwebui)/.env; fi; \
	fi
	@if [ ! -f $(mod_ollama)/.env ]; then \
		echo "[create-envs] creating .env for ollama"; \
		if [ -f $(mod_ollama)/example.env ]; then cp $(mod_ollama)/example.env $(mod_ollama)/.env; fi; \
	fi
	@if [ ! -f $(mod_litellm)/.env ]; then \
		echo "[create-envs] creating .env for litellm"; \
		if [ -f $(mod_litellm)/example.env ]; then cp $(mod_litellm)/example.env $(mod_litellm)/.env; fi; \
	fi

# =================== Orchestration ===================
init: create-envs
	$(MAKE) build
	$(MAKE) start
	./scripts/ollama_pull_model.sh
	@echo "Init done."

start:
	$(MAKE) common-services
	$(MAKE) ollama
	$(MAKE) openwebui
	@echo "Finished full start"

logs:
	cd $(mod_openwebui) && docker compose logs -f

down:
	cd $(mod_ollama) && docker compose down
	cd $(mod_openwebui) && docker compose down
	cd $(mod_langflow) && docker compose down
	cd $(mod_common) && docker compose down
	cd $(mod_notebooks) && docker compose down
	cd $(mod_litellm) && docker compose down
	@echo "All services stopped"

build:
	cd $(mod_common) && docker compose build
	cd $(mod_openwebui) && docker compose build
	cd $(mod_ollama) && docker compose build
	@echo "Finished building all modules"

# =================== Individual modules ===================
common-services:
	cd $(mod_common) && docker compose up -d
	@echo "Common services are up"

langflow:
	cd $(mod_langflow) && docker compose up -d
	@echo "Langflow is up and running"

notebooks:
	cd $(mod_notebooks) && docker compose up -d
	@echo "Notebooks are up and running"

openwebui:
	cd $(mod_openwebui) && docker compose up -d
	@echo "Open WebUI is up and running"

ollama:
	cd $(mod_ollama) && docker compose up -d
	@echo "Ollama stack is up"

litellm:
	cd $(mod_litellm) && docker compose up -d
	@echo "LiteLLM is up and running"

