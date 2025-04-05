include .env
export $(shell sed 's/=.*//' .env)

current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
user := $(shell whoami)

# Important to start ollama docker-compose first because
# it shares "lang" network with others docker-compose files
init:
	make common-services
	make langflow

start:
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	echo "Finished starting"

start-full:
	cd $(modules_dir)common-services && docker compose up -d
	cd $(modules_dir)langflow && docker compose up -d
	cd $(modules_dir)langchain && docker compose up -d
	echo "Finished starting"

logs:
	cd $(modules_dir)langflow && docker compose logs -f

down:
	cd $(modules_dir)common-services && docker compose down 
	cd $(modules_dir)langflow && docker compose down
	cd $(modules_dir)langchain && docker compose down
	echo "Finished down"

build:
	cd $(modules_dir)common-services && docker compose build
	cd $(modules_dir)langflow && docker compose build
	cd $(modules_dir)langchain && docker compose build
	echo "Finished building"

common-services:
	cd $(modules_dir)common-services && docker compose up -d
	cd scripts/ && ./ollama_pull_model.sh &
	echo "Ollama is pulling a model in background, service up and running"

langflow:
	cd $(modules_dir)langflow && docker compose up -d

notebook:
	cd $(modules_dir)langchain && docker compose up -d
	echo "Langchain is up and Running"
