include .env
export $(shell sed 's/=.*//' .env)

current_dir := $(shell pwd)/
modules_dir := $(current_dir)modules/
user := $(shell whoami)

# Important to start ollama docker-compose first because
# it shares "lang" network with others docker-compose files
init:
	make ollama
	make build
	make langflow
	make langchain

build:
	cd $(modules_dir)langflow && docker compose build
	cd $(modules_dir)langchain && docker compose build
	cd $(modules_dir)ollama && docker compose build
	echo "Langflow is up and Running"

langflow:
	cd $(modules_dir)langflow && docker compose up -d

langchain:
	cd $(modules_dir)langchain && docker compose up -d
	echo "Langchain is up and Running"

ollama:
	cd $(modules_dir)ollama && docker compose up -d
	cd scripts/ && ./ollama_pull_model.sh &
	echo "Ollama is pulling a model in background, service up and running"
