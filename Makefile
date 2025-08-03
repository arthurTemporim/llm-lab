# Load .env file if it exists
-include .env
export $(shell sed 's/=.*//' .env 2>/dev/null)

# Variables
current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
user := $(shell whoami)

.PHONY: check-env init start start-full logs down build \
        common-services langflow notebook

check-env:
	@if [ ! -f langflow/.env ]; then \
		echo "langflow/.env not found. Creating from langflow/example.env..."; \
		cp langflow/example.env langflow/.env; \
	else \
		echo "langflow/.env exists."; \
	fi

init: check-env
	make common-services
	make langflow

start: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	echo "Finished starting"

start-full: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	cd $(modules_dir)langchain && docker compose up -d
	echo "Finished full start"

logs: check-env
	cd $(modules_dir)langflow && docker compose logs -f

down: check-env
	cd $(modules_dir)common-services && docker compose down
	cd $(modules_dir)langflow && docker compose down
	cd $(modules_dir)langchain && docker compose down
	echo "All services stopped"

build: check-env
	cd $(modules_dir)common-services && docker compose build
	cd $(modules_dir)langflow && docker compose build
	cd $(modules_dir)langchain && docker compose build
	echo "Finished building all modules"

common-services: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd scripts/ && ./ollama_pull_model.sh &
	echo "Ollama model pull started in background"

langflow: check-env
	cd $(modules_dir)langflow && docker compose up -d
	echo "Langflow is up and running"

notebook: check-env
	cd $(modules_dir)langchain && docker compose up -d
	echo "Langchain is up and running"