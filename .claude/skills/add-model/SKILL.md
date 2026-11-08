---
name: add-model
description: Add an LLM, embedding or decision model to llm-lab — Ollama pull list, LiteLLM models.yaml settings, evals config and docs/MODELS.md; or a vLLM model via VLLM_MODEL. Use when asked to add, swap or remove a served model.
---

# add-model

1. **Facts first.** From the model page (Ollama library or Hugging Face): exact tag, size on disk, type (chat, vision, reasoning, tools, embedding and its dimensions, decision), context length, license. Check it fits the VRAM in `docs/MODELS.md`. Never guess a tag or size.
2. **Ollama.** Add `"<tag> <size GB>"` to `models=(...)` in `scripts/ollama_pull_model.sh`, grouped with its type.
3. **LiteLLM.** In `modules/litellm/models.yaml`, add the tag under `models:` in its type block (`# ---- Chat`, `# ---- Embeddings`, …). Only override what differs from `defaults.<type>` (`keep_alive`, `max_tokens`, `model_info`). Non-Ollama backends go under `extra_models` with `api_base` = container name + port (e.g. `http://vllm:8000/v1`). `litellm-init` registers models at every `make litellm`; no compose change.
4. **vLLM instead.** One model per process: set `VLLM_MODEL`, `VLLM_MAX_MODEL_LEN` and `VLLM_EXTRA_ARGS` in `modules/vllm/example.env`, and add the repo to `scripts/vllm_pull_model.sh`.
5. **Evals.** To compare it, add it to `evals/models.yaml` with the same fields as its peers (prompt prefixes for embeddings).
6. **Docs.** `docs/MODELS.md`: a row in "Models at a glance" and a line in "Which model to use". Add to `docs/MODEL_EVAL_REPORT.md` only after a real eval run. Never invent numbers.
7. **Validate.** `bash .claude/skills/validate/validate.sh litellm shell`. Pulling the model and restarting LiteLLM (`scripts/ollama_pull_model.sh`, `make litellm`) is up to the user: it downloads GBs and loads the GPU.

Removing a model: reverse every step, and also check `modules/openwebui/example.env`, notebooks and langflow flows for the tag.
