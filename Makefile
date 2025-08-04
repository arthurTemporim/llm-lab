.PHONY: check-env check-langflow-env init start start-full logs down build \
        common-services langflow notebook

# Check for root .env
check-env:
	@if [ ! -f .env ]; then \
		echo ".env not found in root. Creating from example.env if available..."; \
		if [ -f example.env ]; then cp example.env .env; else echo "No example.env in root, skipping."; fi \
	else \
		echo ".env exists in root. Not overwriting."; \
	fi

# Check for langflow/.env in modules
check-langflow-env:
	@if [ ! -f $(modules_dir)langflow/.env ]; then \
		echo "$(modules_dir)langflow/.env not found. Creating from example.env..."; \
		cp $(modules_dir)langflow/example.env $(modules_dir)langflow/.env; \
	else \
		echo "$(modules_dir)langflow/.env exists. Not overwriting."; \
	fi

init: check-env check-langflow-env
	make common-services
	make langflow

start: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	echo "Finished starting"

start-full: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	cd $(modules_dir)notebooks && docker compose up -d
	echo "Finished full start"

logs: check-env
	cd $(modules_dir)langflow && docker compose logs -f

down: check-env
	cd $(modules_dir)common-services && docker compose down
	cd $(modules_dir)langflow && docker compose down
	cd $(modules_dir)notebooks && docker compose down
	echo "All services stopped"

build: check-env check-langflow-env
	cd $(modules_dir)common-services && docker compose build
	cd $(modules_dir)langflow && docker compose build
	cd $(modules_dir)notebooks && docker compose build
	echo "Finished building all modules"

common-services: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd scripts/ && ./ollama_pull_model.sh &
	echo "Ollama model pull started in background"

langflow: check-env check-langflow-env
	cd $(modules_dir)langflow && docker compose up -d
	echo "Langflow is up and running"

notebook: check-env
	cd $(modules_dir)notebooks && docker compose up -d
	echo "notebooks is up and running"

