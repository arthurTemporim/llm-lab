# llm-lab: single entry point. Run `make help`.
MODULES := common-services ollama localai openwebui langflow notebooks litellm langfuse
OTHERS  := $(filter-out common-services,$(MODULES))

.PHONY: help init start build down create-envs check-env databases logs $(MODULES)

modules_dir := $(CURDIR)/modules/
scripts_dir := $(CURDIR)/scripts/

# GPU=1 adds each module's docker-compose.gpu.yml (if it has one). Auto-detected from
# the NVIDIA Container Toolkit; force it with `make GPU=1 ...` or `make GPU=0 ...`.
GPU ?= $(if $(shell docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -i nvidia),1,0)

# $(call compose,<module>) -> docker compose command for that module
compose = cd $(modules_dir)$(1) && docker compose $(if $(and $(filter 1,$(GPU)),$(wildcard $(modules_dir)$(1)/docker-compose.gpu.yml)),-f docker-compose.yml -f docker-compose.gpu.yml)

help:
	@echo "Modules: $(MODULES)"
	@echo "  make <module>         start a module (starts common-services first)"
	@echo "  make <module>-logs    follow a module's logs"
	@echo "  make <module>-down    stop a module (data is kept)"
	@echo ""
	@echo "  make init             create-envs + build + start + pull ollama models"
	@echo "  make start            common-services + ollama + localai + openwebui"
	@echo "  make build            build every module that has a Dockerfile"
	@echo "  make down             stop all modules (data is kept)"
	@echo "  make logs             follow the logs of all running modules"
	@echo "  make create-envs      example.env -> .env for every module (never overwrites)"
	@echo "  make check-env        verify values that must match across modules"
	@echo "  make databases        create the postgres databases (idempotent)"
	@echo ""
	@echo "GPU=$(GPU) (override with GPU=0 or GPU=1)"

# =================== Setup ===================
create-envs:
	@for m in $(MODULES); do \
		d=$(modules_dir)$$m; \
		if [ -f $$d/example.env ] && [ ! -f $$d/.env ]; then \
			cp $$d/example.env $$d/.env; \
			$(scripts_dir)generate_secrets.sh $$d/.env; \
			echo "[create-envs] created $$m/.env"; \
		fi; \
	done

check-env:
	@$(scripts_dir)check_env.sh

databases:
	@$(scripts_dir)create_databases.sh

# =================== Orchestration ===================
init: create-envs
	$(MAKE) build
	$(MAKE) start
	$(scripts_dir)ollama_pull_model.sh
	@echo "Init done."

start: ollama localai openwebui
	@echo "Finished full start"

build: create-envs
	@for m in $(MODULES); do $(call compose,$$m) build || exit 1; done

down:
	@for m in $$(printf '%s\n' $(MODULES) | tac); do $(call compose,$$m) down || exit 1; done
	@echo "All services stopped"

# Follow every module at once (modules that are not running just print nothing and exit).
logs:
	@trap 'kill 0' INT TERM; \
	$(foreach m,$(MODULES),$(call compose,$(m)) logs -f --tail=20 & ) \
	wait

# =================== Modules ===================
# common-services creates the "lang" network, so every other module needs it first.
common-services: create-envs
	@$(call compose,$@) up -d --build
	@$(MAKE) --no-print-directory databases

$(OTHERS): common-services
	@$(call compose,$@) up -d --build
	@echo "$@ is up"

langfuse: check-env

%-logs:
	@$(call compose,$*) logs -f

%-down:
	@$(call compose,$*) down
