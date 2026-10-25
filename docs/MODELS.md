# Models

The models served through the LiteLLM gateway (backed by Ollama): what each one is for, how it is configured, and how to call it. Measured comparisons are in [MODEL_EVAL_REPORT.md](MODEL_EVAL_REPORT.md) (run by [evals/](../evals/README.md)). Pull them with `scripts/ollama_pull_model.sh`; the LiteLLM settings are in `modules/litellm/models.yaml`.

- **Gateway:** LiteLLM v1.105.1 at `http://<host>:4000`. Models are registered from Ollama at startup (`litellm-init`).
- **Backend:** Ollama v0.40.5 on a server with an RTX 3060 (12 GB) + Tesla P4 (8 GB) = about 20 GB of VRAM, 48 GB RAM.
- **Keys:** examples use `$LITELLM_KEY`. Never commit a real key.

## Models at a glance

| Model | Type | Size on disk | Context (as configured) | Use it for | Reference |
|---|---|---|---|---|---|
| `gemma4:12b` | chat, vision, reasoning, tools | 8.0 GB | 16K (model: 256K) | Default assistant: answers, reasoning, images | [Ollama](https://ollama.com/library/gemma4) |
| `qwen3-vl:8b` | chat, vision, reasoning, tools | 6.2 GB | 16K (model: 256K) | Reading images and documents | [Ollama](https://ollama.com/library/qwen3-vl) |
| `lfm2.5:8b` | chat, reasoning, tools (mixture of experts) | 5.2 GB | 16K (model: 128K) | Fast tool calling and light agents | [Ollama](https://ollama.com/library/lfm2.5) |
| `llama3.2:3b` | chat, tools | 2.0 GB | 16K (model: 128K) | Quick, cheap text tasks without thinking | [Ollama](https://ollama.com/library/llama3.2) |
| `qwen3-embedding:8b` | embedding (4096 dims) | 4.7 GB | 8K input | Best-quality multilingual search and RAG | [Ollama](https://ollama.com/library/qwen3-embedding) |
| `nomic-embed-text-v2-moe` | embedding (768 dims) | 1.0 GB | 512 tokens | Small, fast embeddings for short texts | [Ollama](https://ollama.com/library/nomic-embed-text-v2-moe) |
| `embeddinggemma:300m` | embedding (768 dims) | 0.6 GB | 2K input | Smallest embedding model, good default | [Ollama](https://ollama.com/library/embeddinggemma) |
| `tev1:4b` | decision (classifier) | 4.6 GB | about 2K tokens | Routing, moderation and yes/no gates on short inputs | [Ollama](https://ollama.com/library/tev1) |
| `nimble:9b` | decision (classifier) | 9.5 GB | 8K tokens | Same tasks with longer inputs | [Ollama](https://ollama.com/library/nimble), [independent test](https://blog.devgenius.io/evaluating-a-decision-model-nimble-9b-and-its-base-model-qwen3-5-9b-a845c2bbd7f0) |

Other references: [LiteLLM decision API](https://docs.litellm.ai/docs/decisions), [Ollama 0.35 release (`/v1/systemone`)](https://github.com/ollama/ollama/releases/tag/v0.35.0), [Ollama FAQ (concurrency, memory)](https://docs.ollama.com/faq), [DeepEval](https://deepeval.com/).

## Which model to use

**Chat**
- **Start with `gemma4:12b`.** It is the most capable one here, handles images, and its thinking can be left on for hard questions.
- **`qwen3-vl:8b`** when the job is reading screenshots, scans or charts.
- **`lfm2.5:8b`** for tool calling and quick turns. It is a small mixture-of-experts model, so it answers sooner than the other reasoning models. In the evals it got one simple fact wrong (a book's publication year), so double-check factual answers.
- **`llama3.2:3b`** when speed matters more than depth (short rewrites, simple extraction). It does not think, so it answers in about a second, but in the evals it failed an arithmetic check, classified only 61% of tickets correctly and fell for a prompt injection.
- Reasoning models spend tokens on thinking: leave `max_tokens` at the default (8192) or higher.

**Embeddings**
- **`qwen3-embedding:8b`** for the best retrieval quality, multilingual content or long passages. It is the heaviest (4096-dimension vectors).
- **`embeddinggemma:300m`** as the light default: tiny, fast, 768 dimensions. In the retrieval eval all three models found the right passage in the top 3 every time (96–100% first place), so the larger one is only worth it for long passages or if it wins on your own data.
- **`nomic-embed-text-v2-moe`** for short passages only (512-token limit). Add its `search_query: ` / `search_document: ` prefixes.
- Never mix vectors from different models in one index.

**Decision models** (`/v1/systemone`)
- Use them when the answer is a choice, a yes/no or a score and you want probabilities: ticket routing, intent detection, moderation, cheap gates in front of a larger LLM.
- **`tev1:4b`** is the default (half the size, fast). Keep inputs under about 1,500 words. It scored 89% on 36 labelled tickets, and all of its errors had confidence below 0.8.
- **`nimble:9b`** when inputs are longer (up to about 6,000 words) or accuracy matters most (94% on the same tickets, two more cases right).
- They also work as fast judges for yes/no checks ("does the answer say 1899?"): in the evals `tev1:4b` ruled correctly on 82 of 84 test answers in about 0.2 s each when each question covered one fact. It is weak on answers that say "the context does not contain this". Verify on your own data first.
- Do not use them to generate text. Include a "none of the above" option and use `confidence` as a threshold to send doubtful cases to a chat model or a person.

## Configuration

Every entry points at the Ollama server and retries twice (`num_retries: 2`). The decision models use the `typesafe/` provider with a dummy `api_key` (`ollama`), because Ollama needs none.

| Model | LiteLLM route | `mode` | `num_ctx` | `max_tokens` | `timeout` | `keep_alive` |
|---|---|---|---|---|---|---|
| `gemma4:12b` | `ollama_chat/` | chat | 16384 | 8192 | 300 s | 15m |
| `qwen3-vl:8b` | `ollama_chat/` | chat | 16384 | 8192 | 300 s | 3m |
| `lfm2.5:8b` | `ollama_chat/` | chat | 16384 | 8192 | 300 s | 5m |
| `llama3.2:3b` | `ollama_chat/` | chat | 16384 | 4096 | 300 s | 5m |
| `qwen3-embedding:8b` | `ollama/` | embedding | Ollama default | n/a | 120 s | 5m |
| `nomic-embed-text-v2-moe` | `ollama/` | embedding | Ollama default | n/a | 120 s | 10m |
| `embeddinggemma:300m` | `ollama/` | embedding | Ollama default | n/a | 120 s | 10m |
| `tev1:4b` | `typesafe/` | decisions | about 2K (Ollama) | n/a | 120 s | 15m |
| `nimble:9b` | `typesafe/` | decisions | 8K (Ollama) | n/a | 120 s | 2m |

- **`num_ctx` 16384:** fits the 20 GB of VRAM and is far above Ollama's small default. The models support more, but a larger value costs VRAM.
- **`max_tokens`:** reasoning tokens count against it. With 16 tokens the reasoning models returned empty answers.
- **`keep_alive`:** how long an idle model stays in VRAM. It overrides the module's `OLLAMA_KEEP_ALIVE`. Big or rarely used models have short values so VRAM is freed.
- **Sampling** is not set in LiteLLM. The Ollama Modelfile of each model already carries its recommended values: `gemma4:12b` temperature 1, top_k 64, top_p 0.95; `qwen3-vl:8b` temperature 1, top_k 20, top_p 0.95; `lfm2.5:8b` temperature 0.2, top_k 80, repeat_penalty 1.05.

## How to use them

Set the key once: `export LITELLM_KEY=<your key>`

### Chat

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gemma4:12b","messages":[{"role":"user","content":"Hello"}]}'
```

Reasoning models return their thinking in `message.reasoning_content` and the answer in `content`. Images go in the message as `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}` (`gemma4:12b`, `qwen3-vl:8b`).

### Embeddings

```bash
curl http://localhost:4000/v1/embeddings \
  -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen3-embedding:8b","input":["hello world"]}'
```

| Model | Dimensions | Notes |
|---|---|---|
| `qwen3-embedding:8b` | 4096 (32–4096 possible) | Optional query instruction: `Instruct: <task>\nQuery: <text>`. Documents are embedded as plain text |
| `nomic-embed-text-v2-moe` | 768 (can truncate to 256) | Prefix `search_query: ` for queries and `search_document: ` for documents. 512 tokens maximum |
| `embeddinggemma:300m` | 768 | Plain text works. The model card also describes prompts (`task: search result \| query: ...`, `title: none \| text: ...`) |

### Decisions

```bash
curl http://localhost:4000/v1/systemone \
  -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" \
  -d '{
    "model": "tev1:4b",
    "state": "I was charged twice. Please refund the extra payment.",
    "questions": {
      "team": {"type": "choice", "instructions": "Which team should handle this ticket?",
               "criteria": {"billing": "Payments and refunds", "technical": "Bugs and integrations", "other": "None of the above"}},
      "refund": {"type": "noul", "instructions": "Does the customer explicitly ask for a refund?"},
      "urgency": {"type": "score", "instructions": "How urgent is this ticket?", "criteria": ["Routine", "Soon", "Urgent"]}
    }
  }'
```

- **Question types:** `choice` (2–26 options; returns `choice`, `probabilities`, `confidence`), `noul` (yes/no; returns a probability of true) and `score` (a rubric of 2–26 levels). Up to 64 questions and 64 KiB per request. No streaming.
- **Behaviour:** they answer only with the options you give, each question is scored independently, and `confidence` measures how concentrated the probabilities are, not whether the answer is right.
- **Size of input:** `usage.input_tokens` in the response shows it. As a rule, 2K tokens is about 1,500 English words and 8K tokens about 6,000. The limit covers the state, the questions and the built-in prompt. Portuguese and code use more tokens per word.

## Memory and speed on this server

- **Eviction, not splitting:** when a model does not fit next to the loaded ones, Ollama unloads idle models to make room instead of splitting it onto the CPU. In a test, loading `nimble:9b` unloaded `gemma4:12b` and `tev1:4b`, so the next call to either pays a reload of about 7–15 s.
- **Early CPU spill:** with `keep_alive` at 30m and four models resident, `llama3.2:3b` once loaded only 1.1 of 4.5 GB in VRAM. Short `keep_alive` values avoid that pile-up. Check `ollama ps` (or `/api/ps`) for the CPU share.
- **Both GPUs:** by default Ollama keeps a model on one GPU when it fits, which leaves the other idle. `OLLAMA_SCHED_SPREAD=1` spreads every model across both cards, but it was slower here: `gemma4:12b` generated 4000 tokens at 22 tok/s spread and 44 tok/s without it (80-token burst: 49 vs 80 tok/s), because the Tesla P4 sets the pace. It is left off.
- **Optional Ollama settings** (commented in `modules/ollama/example.env`): `OLLAMA_FLASH_ATTENTION=1` with `OLLAMA_KV_CACHE_TYPE=q8_0` halves the context memory; `OLLAMA_MAX_LOADED_MODELS=2` caps resident models.
- **Mixed GPUs:** the Tesla P4 is slower than the RTX 3060. A model split across both runs at the slower card's pace.
- **Cold start:** the first request after a model unloads takes 15–40 s (the decision models up to 40 s).

## Known limitations

- **`typesafe/` provider:** LiteLLM's docs recommend `bespoke` for Nimble, but v1.105.1 does not list it. `typesafe/` with Ollama as `api_base` works here but is not the documented path. Check again after a LiteLLM upgrade.
- **Removed on purpose:** `llama3.2-vision:11b` (Ollama 0.40.5 cannot load the `mllama` architecture), `embeddinggemma-2:740m` (an Apple MLX build that fails on Linux) and the duplicate `llama3.2:latest` (same digest as `llama3.2:3b`; the Ollama copy shares the same blob).
- **Not covered by the evals:** tool calling, long-context quality and the decision `score` question type.
