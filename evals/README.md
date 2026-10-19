# Model evals

Evaluations of the models served by the LiteLLM gateway, built on [DeepEval](https://deepeval.com/). They compare models of the same type: chat, embeddings and decision (classifier) models. Results and conclusions are in [../docs/MODEL_EVAL_REPORT.md](../docs/MODEL_EVAL_REPORT.md).

The evals only call the gateway (`/v1/chat/completions`, `/v1/embeddings`, `/v1/systemone`), so they work with any model registered in LiteLLM. They load models into Ollama, so run them when the GPU is free.

## Setup

```sh
cd evals
uv venv --python 3.12 .venv          # or: python3.12 -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt   # or: .venv/bin/pip install -r requirements.txt
cp example.env .env                   # then set LITELLM_BASE_URL and LITELLM_API_KEY (JUDGE_MODEL defaults to tev1:4b)
```

`.env` is git-ignored. Models and their prompt prefixes are listed in `models.yaml`.

## Run

```sh
.venv/bin/python run_embeddings.py   # about 1 minute
.venv/bin/python run_decisions.py    # tev1, plus chat baselines (--no-baselines to skip them)
.venv/bin/python run_chat.py         # slowest: reasoning models + tev1 judge (--no-judge for deterministic cases only)
.venv/bin/python judge_experiment.py # how accurate the tev1 judge is on answers with a known verdict (--judges tev1:4b,nimble:9b compares more; --llm adds the old gemma4 baseline)
```

Each script prints a summary and saves its raw results in `results/*.json` (git-ignored). Useful flags: `--models`, `--cases` (chat), `--out`.

## What is evaluated

| Type | Scenario (dataset) | DeepEval metrics | Judge needed |
|---|---|---|---|
| Chat | 14 cases: arithmetic, sequence, JSON format, bullet count, Portuguese, image reading (vision models only), two factual QA, explanation, RAG answerable, RAG with a conflicting question, two RAG unanswerable, summary | Custom `CheckMetric` (number, JSON, contains, bullets) for 6 cases; `DecisionJudgeMetric` (narrow yes/no checks ruled by `tev1:4b`, plus a sentence-count rule) for 8 | Yes, for 8 cases |
| Embeddings | Retrieval: 54 queries over 50 documents (English and Portuguese, same-topic distractors, cross-lingual) | Custom `RankMetric`: Hit@1, Hit@3, Reciprocal rank | No |
| Decisions | 26 ticket-routing cases (4 teams, Portuguese, ambiguous, prompt injection, two long inputs) and 10 refund yes/no cases | Custom `ExactMatchMetric`; confidence and latency recorded | No |

The decision scenarios also run two chat models on the same tickets, to show what a dedicated decision model adds.

### How the judge works

The judge is a decision model, `tev1:4b` (`JUDGE_MODEL`), not a chat model. It answers yes/no questions through `/v1/systemone` and returns a probability for each. A judged case is a list of **narrow checks**, each `[question, expected answer]`, for example for Dom Casmurro: "Does the answer say that it was published in 1899?" (yes) and "Does the answer give a year other than 1899, or an author other than Machado de Assis?" (no). The case score is the lowest probability among its checks, and it passes at 0.5, so one failed check fails the case. A few reasons for this shape:

- A decision model answers one small question reliably and hedges on a compound one, so every check asks about one fact.
- Each case asks for the facts it needs *and* asks whether a wrong or invented fact is there, so it is not weaker than a general "is this correct?" prompt.
- What code can verify is checked by code, not by the model (`sentences`: at most N sentences).
- The judge is not one of the chat models, so it cannot favour its own answers.

Generic rubrics (`correctness`, `faithfulness`, `abstention`, `relevancy`, `summary`) live in `lib/judge_metrics.py`; a case can use one with `"kind"` or define its own `"checks"` in `datasets/chat.json`.

`judge_experiment.py` is a separate check: it measures how accurate each judge is on 84 candidate answers with a known verdict (`datasets/judge_validation.json`: 41 clear-cut, 27 harder, 16 held-out that were never used to tune the checks). It compares a decision model asked one compound question, the same model asked the narrow checks, the checks written for each chat case, and DeepEval's `eval_mode="system_one"` (adapter in `lib/system_one.py`). `--llm` adds the old `gemma4:12b` judge as a baseline.

## Layout

```text
models.yaml        models to evaluate, grouped by type, with embedding prefixes
datasets/          chat.json, embeddings.json, decisions.json, images/
lib/config.py      environment, registry and dataset loading
lib/llm.py         gateway client (chat, embeddings, systemone)
lib/judge.py       DeepEvalBaseLLM that judges through a chat model (only the gemma4:12b baseline of judge_experiment.py)
lib/metrics.py     custom DeepEval metrics and the evaluate() wrapper
lib/system_one.py  DeepEval System One adapter: lets a decision model served by LiteLLM decide metric steps
lib/judge_metrics.py  DeepEval metric whose judge is a decision model (narrow yes/no checks); the chat judge
run_*.py           one runner per model type
judge_experiment.py  accuracy of each judge against answers with a known verdict
```

## Limits to keep in mind

- **Small datasets.** A difference of one or two cases is noise. Treat results as a sanity check and a first comparison, then add cases from your own data.
- **The judge is a 4B classifier.** `tev1:4b` is weak at nuance (see the report): treat a judged score near 0.5 as "unsure", and re-check the judge with `judge_experiment.py` when you change a check. A judge error is reported separately and never counted against the model.
- **Judged scores are not comparable with the first report.** That run used `gemma4:12b` with DeepEval's general prompts; the cases and the scoring (lowest check wins) changed.
- **Partial reruns:** `--models` and `--cases` re-run only those and merge into the existing `results/*.json`.
- **One run per case.** Sampling uses a fixed seed (`SEED` in `lib/config.py`) but the models keep their own default temperature, so results can vary between runs.
- **Latency includes thinking time** for reasoning models, and depends on which models are already loaded in VRAM.
