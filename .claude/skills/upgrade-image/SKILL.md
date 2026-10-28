---
name: upgrade-image
description: Bump a pinned image version in an llm-lab module — release notes, every service sharing the image, Dockerfiles and scripts that repeat the tag, related versions, README Overview. Use when asked to upgrade, update or pin a module's version.
---

# upgrade-image

1. **Find every use of the tag.** `grep -rn '<image>' modules scripts docs` — services that share the image (`litellm-init` and `litellm`), `docker-compose.gpu.yml` variants (CPU and CUDA tags move together), Dockerfiles, scripts (`scripts/vllm_pull_model.sh`), `LANGFUSE_VERSION` in `example.env`.
2. **Read the release notes** between the current and the target version: breaking changes, renamed env vars, migrations, new minimum versions. Summarize what matters to this lab; don't guess.
3. **Related versions.** Langfuse ↔ ClickHouse, Hatchet engine ↔ worker SDKs, Docling worker ↔ manager, Postgres major (needs dump and restore: stop and ask).
4. **Edit.** Exact pinned tag (never `latest` or a floating tag). Apply renamed env vars to `example.env`; if an existing `.env` would break, add a migration guard in `scripts/check_env.sh`.
5. **Docs.** The README `Overview` image row of the module. Image versions appear nowhere else (see `docs/CONVENTIONS.md`); reports keep the version they ran with.
6. **Validate.** `bash .claude/skills/validate/validate.sh <module>`. Pulling and restarting (`make <module>`) is up to the user.

Report: old → new version, notable changes from the release notes, any manual step (migration, `.env` edit).
