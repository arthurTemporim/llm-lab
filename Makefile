# llm-lab: single entry point. Run `make help`.
MODULES := common-services ollama localai vllm docling openwebui langflow notebooks litellm langfuse hatchet
OTHERS  := $(filter-out common-services,$(MODULES))
# Default set for `make build` and `make up`; the *-all targets use every module.
CORE    := common-services ollama

.PHONY: help init configure gpu hatchet-token up up-all build build-all down create-envs check-env databases logs $(MODULES) \
	$(addprefix up-,$(MODULES)) $(addprefix down-,$(MODULES)) $(addprefix build-,$(MODULES)) $(addprefix logs-,$(MODULES))

modules_dir := $(CURDIR)/modules/
scripts_dir := $(CURDIR)/scripts/

# GPU=1 adds each module's docker-compose.gpu.yml (if it has one). Auto-detected from
# the NVIDIA Container Toolkit; force it with `make GPU=1 ...` or `make GPU=0 ...`.
GPU ?= $(if $(shell docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -i nvidia),1,0)

# $(call compose,<module>) -> docker compose command for that module. The global
# common-services/.env is loaded first, then the module's .env (later files win), so module
# files can reference shared values as ${VAR}.
compose = cd $(modules_dir)$(1) && docker compose --env-file ../common-services/.env --env-file .env $(if $(and $(filter 1,$(GPU)),$(wildcard $(modules_dir)$(1)/docker-compose.gpu.yml)),-f docker-compose.yml -f docker-compose.gpu.yml)

help:
	@echo "Modules: $(MODULES)"
	@echo "  make up-<module>      start a module (starts common-services first)"
	@echo "  make <module>         same as make up-<module>"
	@echo "  make down-<module>    stop a module (data is kept)"
	@echo "  make build-<module>   build a module's images without starting it"
	@echo "  make logs-<module>    follow a module's logs"
	@echo ""
	@echo "  make init             configure + start $(CORE) + pull ollama models + hatchet token"
	@echo "                        (ARGS=\"--modules all\" or ARGS=\"--modules litellm,hatchet --host <ip>\")"
	@echo "  make configure        env files, LAB_PUBLIC_HOST, GPU ids, evals/.env (starts nothing)"
	@echo "  make gpu              pick the GPU for vllm/docling and write their GPU ids"
	@echo "  make hatchet-token    create the Hatchet worker token (ARGS=--force to replace it)"
	@echo "  make up               start the core modules: $(CORE)"
	@echo "  make up-all           start every module"
	@echo "  make build            build the core modules: $(CORE)"
	@echo "  make build-all        build every module that has a Dockerfile"
	@echo "  make down             stop all modules (data is kept)"
	@echo "  make logs             follow the logs of all running modules"
	@echo "  make create-envs      example.env -> .env for every module (never overwrites)"
	@echo "  make check-env        verify the global env file and that modules do not redefine its values"
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

check-env: create-envs
	@$(scripts_dir)check_env.sh

databases:
	@$(scripts_dir)create_databases.sh

# =================== Orchestration ===================
# The setup steps live in scripts/lab.py (./scripts/lab.py --help); ARGS is passed through.
init:
	@$(scripts_dir)lab.py init $(ARGS)

configure:
	@$(scripts_dir)lab.py configure $(ARGS)

gpu:
	@$(scripts_dir)lab.py gpu $(ARGS)

hatchet-token:
	@$(scripts_dir)lab.py hatchet-token $(ARGS)

up: $(addprefix up-,$(CORE))
	@echo "Finished core start"

up-all: $(addprefix up-,$(MODULES))
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
# Every module gets up-<module>, down-<module>, build-<module> and logs-<module>.
# common-services creates the "lang" network, so every other module needs it first.
up-common-services: create-envs check-env
	@$(call compose,common-services) up -d --build
	@$(MAKE) --no-print-directory databases

$(addprefix up-,$(OTHERS)): up-%: up-common-services
	@$(call compose,$*) up -d --build
	@echo "$* is up"

# `make <module>` is a shortcut for `make up-<module>`
$(MODULES): %: up-%

$(addprefix down-,$(MODULES)): down-%:
	@$(call compose,$*) down

$(addprefix build-,$(MODULES)): build-%: create-envs
	@$(call compose,$*) build

$(addprefix logs-,$(MODULES)): logs-%:
	@$(call compose,$*) logs -f
