# Model evals

Evaluations of the models served by the LiteLLM gateway, built on [DeepEval](https://deepeval.com/). They compare models of the same type: chat, embeddings and decision (classifier) models. Results and conclusions are in [../docs/MODEL_EVAL_REPORT.md](../docs/MODEL_EVAL_REPORT.md).

The evals only call the gateway (`/v1/chat/completions`, `/v1/embeddings`, `/v1/systemone`), so they work with any model registered in LiteLLM. They load models into Ollama, so run them when the GPU is free.

## Setup

```sh
cd evals
uv venv --python 3.12 .venv          # or: python3.12 -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt   # or: .venv/bin/pip install -r requirements.txt
cp example.env .env                   # then set LITELLM_BASE_URL and LITELLM_API_KEY
```

`.env` is git-ignored. Models and their prompt prefixes are listed in `models.yaml`.

## Run

```sh
.venv/bin/python run_embeddings.py   # about 1 minute
.venv/bin/python run_decisions.py    # tev1 + nimble, plus chat baselines (--no-baselines to skip them)
.venv/bin/python run_chat.py         # slowest: reasoning models + LLM judge (--no-judge for deterministic cases only)
.venv/bin/python judge_experiment.py # which judge to trust: gemma4 vs tev1 vs nimble on answers with a known verdict (about 7 minutes)
```

Each script prints a summary and saves its raw results in `results/*.json` (git-ignored). Useful flags: `--models`, `--cases` (chat), `--out`.

## What is evaluated

| Type | Scenario (dataset) | DeepEval metrics | Judge needed |
|---|---|---|---|
| Chat | 11 cases: arithmetic, sequence, JSON format, bullet count, Portuguese, image reading (vision models only), factual QA, explanation, RAG answerable, RAG unanswerable, summary | Custom `CheckMetric` (number, JSON, contains, bullets) for 6 cases; `GEval` (Correctness, Abstention, Summary quality), `AnswerRelevancyMetric` and `FaithfulnessMetric` for 5 | Yes, for 5 cases |
| Embeddings | Retrieval: 54 queries over 50 documents (English and Portuguese, same-topic distractors, cross-lingual) | Custom `RankMetric`: Hit@1, Hit@3, Reciprocal rank | No |
| Decisions | 26 ticket-routing cases (4 teams, Portuguese, ambiguous, prompt injection, two long inputs) and 10 refund yes/no cases | Custom `ExactMatchMetric`; confidence and latency recorded | No |

The decision scenarios also run two chat models on the same tickets, to show what a dedicated decision model adds.

`judge_experiment.py` is a separate check: it measures how accurate each judge is on 41 candidate answers with a known verdict (`datasets/judge_validation.json`), comparing the LLM judge with decision models used through a yes/no rubric and through DeepEval's `eval_mode="system_one"` (adapter in `lib/system_one.py`, metric in `lib/judge_metrics.py`).

## Layout

```text
models.yaml        models to evaluate, grouped by type, with embedding prefixes
datasets/          chat.json, embeddings.json, decisions.json, images/
lib/config.py      environment, registry and dataset loading
lib/llm.py         gateway client (chat, embeddings, systemone)
lib/judge.py       DeepEvalBaseLLM that judges through LiteLLM (JUDGE_MODEL)
lib/metrics.py     custom DeepEval metrics and the evaluate() wrapper
lib/system_one.py  DeepEval System One adapter: lets a decision model served by LiteLLM decide metric steps
lib/judge_metrics.py  DeepEval metric whose judge is a decision model (yes/no rubric)
run_*.py           one runner per model type
judge_experiment.py  accuracy of each judge against answers with a known verdict
```

## Limits to keep in mind

- **Small datasets.** A difference of one or two cases is noise. Treat results as a sanity check and a first comparison, then add cases from your own data.
- **The judge is also a candidate.** `JUDGE_MODEL` defaults to `gemma4:12b`, which is also evaluated as a chat model, so its judged scores can be biased in its own favour. Deterministic checks do not have this problem. Use a different judge for a fairer comparison.
- **The judge runs with thinking off** (`JUDGE_REASONING_EFFORT=none`). With thinking on, reasoning models can use their whole token budget and return an empty answer, which shows up as a judge error (reported separately, never counted against the model).
- **Partial reruns:** `--models` and `--cases` re-run only those and merge into the existing `results/*.json`.
- **One run per case.** Sampling uses a fixed seed (`SEED` in `lib/config.py`) but the models keep their own default temperature, so results can vary between runs.
- **Latency includes thinking time** for reasoning models, and depends on which models are already loaded in VRAM.
