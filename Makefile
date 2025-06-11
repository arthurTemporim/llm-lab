# Define variables
current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
user := $(shell whoami)

.PHONY: check-env init start start-full logs down build common-services langflow notebook

# Check if .env exists, else create it from example.env
check-env:
	@bash scripts/check_env.sh

# Important to start ollama docker-compose first because
# it shares "lang" network with others docker-compose files
init: check-env
	$(MAKE) build
	$(MAKE) common-services
	$(MAKE) langflow

start: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	echo "Finished starting"

start-full: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	cd $(modules_dir)notebooks && docker compose up -d
	echo "Finished starting"

logs: check-env
	cd $(modules_dir)langflow && docker compose logs -f

down: check-env
	cd $(modules_dir)common-services && docker compose down 
	cd $(modules_dir)langflow && docker compose down
	cd $(modules_dir)notebooks && docker compose down
	echo "Finished down"

build: check-env
	cd $(modules_dir)common-services && docker compose build
	cd $(modules_dir)langflow && docker compose build
	cd $(modules_dir)notebooks && docker compose build
	echo "Finished building"

common-services: check-env
	cd $(modules_dir)common-services && docker compose up -d
	cd scripts/ && ./ollama_pull_model.sh &
	echo "Ollama is pulling a model in background, service up and running"

langflow: check-env
	cd $(modules_dir)langflow && docker compose up -d

notebook: check-env
	cd $(modules_dir)notebooks && docker compose up -d
	echo "notebooks is up and Running"

