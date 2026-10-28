---
name: connect-modules
description: Wire one llm-lab module to another (e.g. LiteLLM → Langfuse, Open WebUI → LiteLLM, a module → Postgres/Redis/Garage/Ollama) — global env values, consumer config, start order, Connections tables and architecture docs. Use when asked to integrate, connect or point a module at another service.
---

# connect-modules

Consumer `A` uses provider `B`. Read the Integration section of `docs/CONVENTIONS.md` first.

1. **Find the address.** `B`'s container name and container port (from its compose file), not the host port. Check `modules/common-services/example.env` for a global value that already covers it (`POSTGRES_URL`, `REDIS_URL`, `GARAGE_S3_ENDPOINT`, `OLLAMA_URL`, `LANGFUSE_HOST`, keys).
2. **Global or local.**
   - `B` is (or will be) used by two or more modules, or its credentials must be shared: add `<SERVICE>_URL` / keys once to `modules/common-services/example.env` (commented, `CHANGE_ME` for secrets), then reference them from `A`.
   - One-off link: the container name + port goes directly in `A`'s `example.env`.
3. **Consumer config.** In `modules/A/example.env`, use the variable name `A`'s image reads, set to a reference: `DATABASE_URL=${POSTGRES_URL}/A`, `OLLAMA_API_BASE=${OLLAMA_URL}`. Same name as the global: `NAME=${NAME}`. Never copy a value. Settings that live only in a UI (Open WebUI connections) go in the README instead.
4. **Provider side.** A database goes in `POSTGRES_DATABASES`; a bucket follows the Garage setup; an API key is generated in `B`'s `.env` or the global one.
5. **Start order.** `depends_on` works only inside one module. Across modules, `A` must tolerate `B` being down (retries or a healthcheck), or document "start `B` first". `common-services` always starts first through the Makefile.
6. **Docs.** `Connections` table in both READMEs (`Depends on` in `A`, `Used by` in `B`), `docs/CONFIGURATIONS.md` (global values / Integrations), `docs/ARCHITECTURE.md` when the dependency or a data flow is new.
7. **Validate.** `bash .claude/skills/validate/validate.sh A B make` (check-env catches a module redefining a global value).
