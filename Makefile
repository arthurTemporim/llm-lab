# llm-lab: single entry point. Run `make help`.
MODULES := common-services ollama localai vllm openwebui langflow notebooks litellm langfuse
OTHERS  := $(filter-out common-services,$(MODULES))
# Default set for `make build` and `make start`; the *-all targets use every module.
CORE    := common-services ollama openwebui

.PHONY: help init start start-all build build-all down create-envs check-env databases logs $(MODULES) \
	$(addprefix start-,$(MODULES)) $(addprefix build-,$(MODULES)) $(addprefix logs-,$(MODULES))

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
	@echo "  make start-<module>   same as make <module>"
	@echo "  make build-<module>   build a module's images without starting it"
	@echo "  make <module>-logs    follow a module's logs"
	@echo "  make logs-<module>    same as make <module>-logs"
	@echo "  make <module>-down    stop a module (data is kept)"
	@echo ""
	@echo "  make init             create-envs + build + start + pull ollama models"
	@echo "  make start            start the core modules: $(CORE)"
	@echo "  make start-all        start every module"
	@echo "  make build            build the core modules: $(CORE)"
	@echo "  make build-all        build every module that has a Dockerfile"
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

start: $(CORE)
	@echo "Finished core start"

start-all: $(MODULES)
	@echo "Finished full start"

build: create-envs
	@for m in $(CORE); do $(call compose,$$m) build || exit 1; done

build-all: create-envs
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

$(addprefix start-,$(MODULES)): start-%: %

$(addprefix build-,$(MODULES)): build-%: create-envs
	@$(call compose,$*) build

%-logs:
	@$(call compose,$*) logs -f

$(addprefix logs-,$(MODULES)): logs-%: %-logs

%-down:
	@$(call compose,$*) down
