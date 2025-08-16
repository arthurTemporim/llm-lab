.PHONY: help \
        create-envs init start start-full logs down build \
        common-services langflow notebooks openwebui \
        ollama ollama-down ollama-logs ollama-build

# =================== Variables ===================
current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
scripts_dir := $(current_dir)scripts/

OLLAMA_COMPOSE_FILE := docker-compose.yml
COMMON_COMPOSE_FILE := docker-compose.yml
DEFAULT_COMPOSE_FILE := docker-compose.yml

mod_ollama := $(modules_dir)ollama
mod_common := $(modules_dir)common-services
mod_openwebui := $(modules_dir)openwebui
mod_langflow := $(modules_dir)langflow
mod_notebooks := $(modules_dir)notebooks

help:
	@echo "Targets principais:"
	@echo "  init            -> cria .envs e sobe common-services + openwebui + ollama"
	@echo "  create-envs     -> cria TODAS as .envs necessárias (root, ollama, langflow, openwebui)"
	@echo "  start           -> sobe common-services + openwebui + ollama (assume .envs já criadas)"
	@echo "  down            -> derruba todos os módulos"
	@echo "  build           -> build em todos os módulos"
	@echo "  logs            -> logs do openwebui"
	@echo "  ollama          -> sobe o stack do ollama (nginx + ollama)"
	@echo "  ollama-logs     -> logs do ollama"
	@echo "  ollama-down     -> derruba o ollama"
	@echo "  common-services -> sobe postgres/redis"
	@echo "  langflow        -> sobe langflow"
	@echo "  notebooks       -> sobe notebooks"

# =================== Criação de .envs ===================
create-envs:
	@if [ ! -f .env ]; then \
		echo "[create-envs] criando .env na raiz"; \
		if [ -f example.env ]; then cp example.env .env; else echo "OLLAMA_HOST=0.0.0.0" > .env; fi; \
	fi
	@if [ ! -f $(mod_langflow)/.env ]; then \
		echo "[create-envs] criando .env para langflow"; \
		if [ -f $(mod_langflow)/example.env ]; then cp $(mod_langflow)/example.env $(mod_langflow)/.env; fi; \
	fi
	@if [ ! -f $(mod_openwebui)/.env ]; then \
		echo "[create-envs] criando .env para openwebui"; \
		if [ -f $(mod_openwebui)/example.env ]; then cp $(mod_openwebui)/example.env $(mod_openwebui)/.env; fi; \
	fi
	@if [ ! -f $(mod_ollama)/.env ]; then \
		echo "[create-envs] criando .env para ollama"; \
		printf "OLLAMA_HOST=0.0.0.0\nOLLAMA_ORIGINS=app://obsidian.md*\nOLLAMA_KEEP_ALIVE=5m\nNVIDIA_VISIBLE_DEVICES=all\nNVIDIA_DRIVER_CAPABILITIES=compute,utility\n" > $(mod_ollama)/.env; \
	fi

# =================== Orquestração ===================
init: create-envs
	$(MAKE) common-services
	$(MAKE) openwebui
	$(MAKE) ollama
	@echo "Init done."

start:
	cd $(mod_common) && docker compose -f $(COMMON_COMPOSE_FILE) up -d
	cd $(mod_openwebui) && docker compose up -d
	cd $(mod_ollama) && docker compose -f $(OLLAMA_COMPOSE_FILE) up -d
	@echo "Finished full start"

start-full: start

logs:
	cd $(mod_openwebui) && docker compose logs -f

down:
	cd $(mod_ollama) && docker compose -f $(OLLAMA_COMPOSE_FILE) down
	cd $(mod_openwebui) && docker compose down
	cd $(mod_langflow) && docker compose down
	cd $(mod_common) && docker compose -f $(COMMON_COMPOSE_FILE) down
	cd $(mod_notebooks) && docker compose down
	@echo "All services stopped"

build:
	cd $(mod_common) && docker compose -f $(COMMON_COMPOSE_FILE) build
	cd $(mod_langflow) && docker compose build
	cd $(mod_openwebui) && docker compose build
	cd $(mod_notebooks) && docker compose build
	cd $(mod_ollama) && docker compose -f $(OLLAMA_COMPOSE_FILE) build
	@echo "Finished building all modules"

# =================== Módulos individuais ===================
common-services:
	cd $(mod_common) && docker compose -f $(COMMON_COMPOSE_FILE) up -d
	cd $(scripts_dir) && ./ollama_pull_model.sh &
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
	cd $(mod_ollama) && docker compose -f $(OLLAMA_COMPOSE_FILE) up -d
	@echo "Ollama stack is up (nginx + ollama)"

ollama-logs:
	cd $(mod_ollama) && docker compose -f $(OLLAMA_COMPOSE_FILE) logs -f

ollama-down:
	cd $(mod_ollama) && docker compose -f $(OLLAMA_COMPOSE_FILE) down
	@echo "Ollama stack stopped"
