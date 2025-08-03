# Use `-include` so it does not fail if .env missing
-include .env
export $(shell sed 's/=.*//' .env)

current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
user := $(shell whoami)

check-env:
	@if [ ! -f .env ]; then \
		echo ".env file not found. Creating from example.env..."; \
		cp example.env .env; \
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
	echo "Finished starting"

logs: check-env
	cd $(modules_dir)langflow && docker compose logs -f

down: check-env
	cd $(modules_dir)common-services && docker compose down 
	cd $(modules_dir)langflow && docker compose down
	cd $(modules_dir)langchain && docker compose down
	echo "Finished down"

build: check-env
	cd $(modules_dir)common-services && docker compose build
	cd $(modules_dir)langflow && docker compose build
	cd $(modules_dir)langchain && docker compose build
	echo "Finished building"

common-services: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd scripts/ && ./ollama_pull_model.sh &
	echo "Ollama is pulling a model in background, service up and running"

langflow: check-env
	cd $(modules_dir)langflow
	if [ ! -f .env ]; then \
		echo ".env file not found. Creating from example.env..."; \
		cp example.env .env; \
	fi
	docker compose up -d

notebook: check-env
	cd $(modules_dir)langchain && docker compose up -d
	echo "Langchain is up and Running"


