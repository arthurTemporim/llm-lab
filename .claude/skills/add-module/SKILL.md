---
name: add-module
description: Add a new technology to llm-lab as a module — compose file (+ GPU override), example.env, README from the template, Makefile registration, shared database/bucket, docs. Use when asked to add, try or integrate a new tool, model server or service.
---

# add-module

Read `docs/CONVENTIONS.md` first. Names below use module `x`.

1. **Discover.** Pick the closest existing module (one inference server: `ollama`; web app with Postgres: `langflow`; several services: `langfuse`; GPU-only: `vllm`) and mirror it. Read the upstream docs for the image, ports, env vars, health endpoint and data paths. Never guess them.
2. **Compose** (`modules/x/docker-compose.yml`):
   - services `x` and `x-<role>`, with `container_name` equal to the service name
   - pinned image tag; `env_file: .env`; `restart: unless-stopped`; a `healthcheck` if the image allows it
   - ports `"${X_PORT:-<free port>}:<container port>"`; check the other modules for clashes; admin-only ports on `127.0.0.1`
   - volumes `x-<data>`; the external `lang` network
   - runs on CPU; NVIDIA settings go in `docker-compose.gpu.yml`
3. **Env** (`modules/x/example.env`): every variable commented, `X_*` names (upstream names kept), `CHANGE_ME`/`CHANGE_ME_PASSWORD` for secrets. Shared values are references: `DATABASE_URL=${POSTGRES_URL}/x`, `${REDIS_URL}`, `${OLLAMA_URL}`, `${LAB_PUBLIC_HOST}`; an admin login's user name and email are `${LAB_USER}` / `${LAB_EMAIL}`. Never copy a global value.
4. **Shared services.** Need a database: add `x` to `POSTGRES_DATABASES` in `modules/common-services/example.env`. Need S3: follow the Garage bucket setup in `common-services`. Never bundle Postgres, Redis or S3.
5. **Register.** Add `x` to `MODULES` in the `Makefile` (nothing else is needed).
6. **README.** Copy `docs/MODULE_README_TEMPLATE.md` to `modules/x/README.md` and fill all ten sections from the files you just wrote.
7. **Docs.** `README.md` module table, Services table (URL, version, README link) and badges, `docs/MODULES.md` section, `docs/CONFIGURATIONS.md` (shared values, GPU), `docs/ARCHITECTURE.md` (layer, dependencies, flows). Delegate to `documenter-agent` when available.
8. **Validate.** `cp modules/x/example.env modules/x/.env` (or `make create-envs`), then `bash .claude/skills/validate/validate.sh x make`. Start it (`make x`) only if asked.
