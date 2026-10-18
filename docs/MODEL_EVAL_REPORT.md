# Model evaluation report

Comparison of the models served by the LiteLLM gateway, by type: chat, embeddings and decision (classifier) models. Built with [DeepEval](https://deepeval.com/); code, datasets and how to rerun are in [evals/](../evals/README.md). Model settings and usage are in [MODELS.md](MODELS.md).

- **Date:** 2026-10-18
- **Setup:** LiteLLM v1.105.1 in front of Ollama v0.40.5, one GPU per model (`OLLAMA_SCHED_SPREAD` off) on an RTX 3060 (12 GB) + Tesla P4 (8 GB), 2 CPUs.
- **Method:** every request goes through the gateway. Sampling uses a fixed seed (42) with each model's own default temperature, one run per case.
- **Judge:** DeepEval's LLM metrics are judged by `gemma4:12b` with thinking off. It is also a candidate, so its own judged scores may be biased. The deterministic checks are not affected.
- **Size:** 11 chat cases, 54 retrieval queries over 50 documents, 36 classification cases. These are small sets: **a difference of one or two cases is noise.** Use the results as a first comparison, not a ranking.

## Summary

| Type | Result | Pick |
|---|---|---|
| Chat | All four are usable. `gemma4:12b` had no failed case; `llama3.2:3b` missed the arithmetic case and was weak at classification; `lfm2.5:8b` gave a wrong publication year; `qwen3-vl:8b` was correct but slowest because it thinks long. | `gemma4:12b` by default; `llama3.2:3b` only for simple, fast tasks |
| Embeddings | Effectively a tie: 96–100% Hit@1 for every model and variant. The cost differs a lot (0.6 GB to 4.7 GB). | `embeddinggemma:300m` by default; `qwen3-embedding:8b` when you need the best quality or long passages |
| Decisions | `nimble:9b` 94% vs `tev1:4b` 89% on 36 tickets (2 vs 4 errors, all on ambiguous tickets). Both answer in about 0.3 s with a useful confidence score. A chat model (`gemma4:12b`) scored 100% but takes 3.5 s per ticket and gives no probabilities. | `tev1:4b` by default, `nimble:9b` when mistakes cost more or inputs are longer |
| Decision models as judges | On 41 answers with a known verdict, `nimble:9b` ruled correctly on 40 and `tev1:4b` on 37, the same as the `gemma4:12b` LLM judge, in 0.1–0.5 s instead of 8.6 s. `tev1:4b` is weak on "say you don't know" answers. | `nimble:9b` as a fast judge for rubric checks; verify on your own data first |

## 1. Chat models

| Model | Deterministic checks | Judged cases (mean score) | Median latency in the eval | Generation speed (burst) | Median tokens |
|---|---|---|---|---|---|
| `gemma4:12b` | 6/6 | 5/5 (0.94) | 3.3 s | 80 tok/s | 224 |
| `qwen3-vl:8b` | 6/6 | 5/5 (0.92) | 39.1 s | 57 tok/s | 389 |
| `lfm2.5:8b` | 5/5 | 5/5 (0.82) | 3.3 s | 66 tok/s | 195 |
| `llama3.2:3b` | 4/5 | 5/5 (0.89) | 0.6 s | 45 tok/s | 19 |

The vision case (reading an invoice number from an image) ran only on the two vision models, so `lfm2.5:8b` and `llama3.2:3b` have 5 deterministic cases. Speeds are short bursts of 80–150 tokens with thinking off, measured on Ollama directly. `gemma4:12b` (80 tok/s) and `qwen3-vl:8b` (57 tok/s) were loaded by themselves; `lfm2.5:8b` and `llama3.2:3b` were measured while other models were resident, so their figures depend on which GPU they landed on (section 5).

| Case | `gemma4:12b` | `qwen3-vl:8b` | `lfm2.5:8b` | `llama3.2:3b` |
|---|---|---|---|---|
| Arithmetic (270 km) | pass | pass | pass | **fail (answered 240)** |
| Number sequence | pass | pass | pass | pass |
| JSON format | pass | pass | pass | pass |
| Exactly 3 bullets | pass | pass | pass | pass |
| Portuguese answer | pass | pass | pass | pass |
| Read invoice from image | pass | pass | n/a | n/a |
| Fact (Dom Casmurro, author and year) | 1.00 | 1.00 | **0.50 (said 1886, expected 1899)** | 1.00 |
| Explanation (answer relevancy) | 1.00 | 1.00 | 1.00 | 0.83 |
| RAG, answerable (faithfulness + correctness) | 1.00 | 1.00 | 1.00 | 1.00 |
| RAG, unanswerable (should say it doesn't know) | 1.00 | 1.00 | 1.00 | 1.00 |
| One-sentence summary | 0.70 | 0.60 | 0.60 | 0.60 |

**What this shows**
- **No model failed the RAG cases.** All four used the context and none invented a student discount.
- **`lfm2.5:8b` got a fact wrong** (1886 instead of 1899). The judge scored it 0.50, which still counts as a pass under the default threshold of 0.5, so a pass here does not mean the answer was right.
- **`llama3.2:3b` is the fastest but the least reliable.** It answered 240 for 60×2.5 + 80×1.5 (also in an earlier smoke test), and it answers in a median of 19 tokens because it does not think.
- **`qwen3-vl:8b` is slow in practice because it thinks.** A median of 389 tokens per answer and 39 s per case in the eval. Its raw speed is fine (57 tok/s alone), see section 5.
- **The summary case was low for everyone (0.60–0.70),** so it does not separate the models.
- **Self-judging:** `gemma4:12b` judged its own answers and got the highest judged mean (0.94 vs 0.82–0.92). The gap is small and the set is tiny, so I cannot tell how much of it is bias.

## 2. Embedding models

Retrieval task: 54 queries over 50 documents in English and Portuguese, including 20 "twin" distractor documents on the same topic and cross-lingual queries. Each query has one right document.

| Variant | Dimensions | Hit@1 | Hit@3 | Reciprocal rank | One query | 50 documents |
|---|---|---|---|---|---|---|
| `embeddinggemma:300m` | 768 | **1.00** | 1.00 | 1.00 | 56 ms | 1.7 s |
| `embeddinggemma:300m` + model-card prompts | 768 | 0.98 | 1.00 | 0.99 | 55 ms | 1.7 s |
| `qwen3-embedding:8b` | 4096 | 0.96 | 1.00 | 0.98 | 74 ms | 2.6 s |
| `qwen3-embedding:8b` + instruction | 4096 | **1.00** | 1.00 | 1.00 | 76 ms | 2.6 s |
| `nomic-embed-text-v2-moe` | 768 | 0.96 | 1.00 | 0.98 | 44 ms | 1.6 s |
| `nomic-embed-text-v2-moe` + `search_query:`/`search_document:` | 768 | 0.98 | 1.00 | 0.99 | 44 ms | 1.6 s |

**What this shows**
- **All variants find the right document in the top 3 every time.** The only misses were at rank 2, always to the same-topic twin document (for example the pancake query returned the crepe document).
- **The differences are one or two queries out of 54.** Do not read a ranking into 0.96 vs 1.00.
- **Prefixes and instructions:** `qwen3-embedding:8b` improved from 0.96 to 1.00 with its instruction and `nomic` from 0.96 to 0.98 with its prefixes. For `embeddinggemma:300m` the model-card prompts did not help (1.00 to 0.98). All of these are single-query changes.
- **Speed and size:** `embeddinggemma:300m` is 0.6 GB and `qwen3-embedding:8b` is 4.7 GB for the same score here. `nomic` is the fastest per query (44 ms).
- **What the test does not cover:** my passages are one or two sentences. It cannot show `qwen3-embedding:8b`'s advantage on long text (8K input), nor `nomic`'s 512-token limit. On large corpora the larger model may separate itself.

## 3. Decision models

Tasks on support tickets, with a chat model doing the same task as a baseline (prompted to reply with a label):
- **Routing:** 26 tickets into billing, technical, account or other (clear, Portuguese, ambiguous, one prompt injection, two long tickets).
- **Refund request:** 10 yes/no cases.

| Model | Type | Routing | Refund yes/no | All 36 | Median latency | Confidence when right / wrong |
|---|---|---|---|---|---|---|
| `nimble:9b` | decision | 92% | **100%** | **94%** | 0.32 s | 0.97 / 0.57 |
| `tev1:4b` | decision | 88% | 90% | 89% | 0.31 s | 0.94 / 0.57 |
| `gemma4:12b` | chat | 100% | 100% | **100%** | 3.5 s | none |
| `llama3.2:3b` | chat | 62% | 60% | 61% | 0.11 s | none |

By category (right/total): the decision models and `gemma4:12b` got every clear ticket (17/17) and every Portuguese ticket (9/9). They differ on the 7 ambiguous ones: `gemma4:12b` 7/7, `nimble:9b` 5/7, `tev1:4b` 3/7, `llama3.2:3b` 4/7.

**What this shows**
- **All the decision-model errors were on ambiguous tickets.** For example "login page loads forever" (labelled technical, both said account) and "I can't log in after the payment failed" (labelled billing, both said account). Those labels are debatable.
- **Confidence is useful.** `tev1:4b` answered 30 of 36 tickets with confidence of 0.8 or more and was right on all 30; its four errors all fell below 0.8. `nimble:9b` answered 34 with 0.8 or more and was right on 33. A threshold of about 0.8 sends the doubtful cases to a person or a larger model.
- **A chat model can be more accurate but not cheaper.** `gemma4:12b` got everything right here, but took about 3.5 s per ticket (11× slower), needs its thinking budget, and returns no probability. `llama3.2:3b` is fast but leaned toward "account" for tickets that were not, and fell for the prompt injection ("ignore previous instructions...").
- **Prompt injection:** both decision models and `gemma4:12b` resisted it; `llama3.2:3b` did not.
- **Tev1 vs Nimble:** 36 vs 34 correct is two cases. On this data they are close; `nimble:9b` costs 2× the disk and VRAM (9.5 GB vs 4.6 GB).
- **Long inputs, no conclusion.** Both models classified the 1.5K-token and 3.4K-token tickets correctly, but the real request was in the last sentence. Tev1's documented context is about 2K tokens, so for the 3.4K ticket it probably dropped the beginning and still found the answer. This test says nothing about understanding long text.

## 4. Decision models as judges

Can `tev1:4b` or `nimble:9b` replace `gemma4:12b` as the judge of other models' answers? To find out, I wrote 41 candidate answers whose right verdict is known (19 should pass, 22 should fail) and let each judge rule on them. They include real errors from section 1 (`lfm2.5:8b`'s 1886 instead of 1899, `llama3.2:3b`'s 240 instead of 270), contradicted or hallucinated RAG answers, off-topic answers, and summaries that are too long or invent a fact. Dataset: `evals/datasets/judge_validation.json`; code: `evals/judge_experiment.py`.

Three ways of judging were compared:
- **LLM judge:** the same DeepEval metrics as the chat eval (GEval, Faithfulness, Answer Relevancy) judged by `gemma4:12b` with thinking off.
- **Decision judge:** one yes/no question per answer ("does the answer state the same key facts as the reference?"), answered by a decision model through `/v1/systemone`. The score is the probability of "yes".
- **DeepEval native:** DeepEval's own Answer Relevancy and Faithfulness metrics with `eval_mode="system_one"`, so the decision model runs the whole metric with no LLM. DeepEval's built-in model class only accepts TypeSafe's models, so `evals/lib/system_one.py` adapts it to our gateway. These two metrics cover 14 of the 41 items.

| Judge | Right verdicts | Wrong answers accepted | Good answers rejected | Mean score good / bad | Median time per item |
|---|---|---|---|---|---|
| `gemma4:12b` LLM judge | 37/41 (90%) | 4/22 | 0/19 | 0.97 / 0.18 | 8.6 s |
| `tev1:4b` decision judge | 37/41 (90%) | 4/22 | 0/19 | 0.91 / 0.17 | **0.11 s** |
| `nimble:9b` decision judge | **40/41 (98%)** | 1/22 | 0/19 | 0.99 / 0.07 | 0.5 s |
| `tev1:4b` DeepEval native (14 items) | 13/14 (93%) | 1/7 | 0/7 | 0.90 / 0.20 | 0.3 s |
| `nimble:9b` DeepEval native (14 items) | 13/14 (93%) | 1/7 | 0/7 | 0.98 / 0.21 | 0.9 s |

By kind of check (right verdicts):

| Judge | Correctness vs a reference (13) | Faithfulness (8) | Abstention (8) | Relevancy (6) | Summary rules (6) |
|---|---|---|---|---|---|
| `gemma4:12b` LLM judge | 12 | 6 | 8 | 5 | 6 |
| `tev1:4b` decision judge | **13** | **8** | 5 | **6** | 5 |
| `nimble:9b` decision judge | **13** | 7 | **8** | **6** | **6** |

**What this shows**
- **Both decision models matched or beat the LLM judge here, at a fraction of the time.** The whole set took 10 s with `tev1:4b`, 34 s with `nimble:9b` and 369 s with the `gemma4:12b` judge.
- **The LLM judge missed the dangerous cases.** It gave a contradicted answer ("yes, within 30 days") a score of 1.00, and it gave the 1886 error, a hallucinated "store credit" and a non-answer exactly 0.50, which passes at DeepEval's default threshold. This is the same pass that `lfm2.5:8b`'s wrong year got in section 1. Both decision judges scored the 1886 error 0.02 and 0.00.
- **`tev1:4b` is good at facts and weak at nuance.** It was perfect on correctness (13/13), faithfulness (8/8) and relevancy (6/6), but accepted 3 of the 4 wrong abstention answers (5/8), such as inventing a student discount (score 0.53) or "if they email support" (0.67). It also accepted a two-sentence summary where one sentence was required (0.60). Its scores on these cases hover near 0.5, so treat anything between 0.3 and 0.7 as "unsure".
- **`nimble:9b` is the more dependable judge.** Its single miss was the hallucinated "store credit within 60 days" (0.72). Its accuracy barely moves with the pass threshold (39–41 of 41 from 0.4 to 0.9), while `tev1:4b` ranges from 35 to 41 and `gemma4:12b` from 35 to 39. I did not tune any threshold; 0.5 is the default.
- **DeepEval's native mode works, with a gap.** Both models passed the contradicted answer in the native Faithfulness metric (scores 0.59 and 0.93), although their own yes/no question rejected it (0.08 and 0.00). The metric's built-in questions are less strict than a rubric written for the task, so the rubric route was the more accurate here.

**Limits of this experiment**
- **Small and written by me.** 41 items means one item is 2.4 points, so `tev1:4b` and `gemma4:12b` are tied and only `nimble:9b`'s lead is more than noise. The items are mostly clear-cut and in English, and the decision rubrics were written specifically for each kind of check while the LLM judge used DeepEval's general prompts, which favours the decision judges.
- **No hard cases yet.** Subtle errors, long answers and ambiguous rubrics are not covered. Test with 50 or more answers labelled from your own data before replacing the judge.
- **The chat eval in section 1 still uses the LLM judge.** Nothing was changed there.

## 5. Speed and memory on this server

| Model | Generation speed |
|---|---|
| `gemma4:12b` alone | 80 tok/s (45 with another model loaded) |
| `lfm2.5:8b` (other models loaded) | 66 tok/s |
| `qwen3-vl:8b` alone | 57 tok/s |
| `qwen3-vl:8b` with `gemma4:12b` and `llama3.2:3b` loaded | **9.5 tok/s** |
| `llama3.2:3b` (alone and with others) | 45 tok/s |

- **Spread over both GPUs was slower:** `gemma4:12b` generated 4000 tokens at 22 tok/s spread and 44 tok/s on one card, so spreading is left off ([MODELS.md](MODELS.md)).
- **Co-loaded models slow each other down.** With `gemma4:12b` and `llama3.2:3b` resident, `qwen3-vl:8b` dropped from 57 to 9.5 tok/s. That is consistent with part of it being pushed to the CPU because neither card had enough free VRAM, but I could not see the placement from outside. Check the `PROCESSOR` column of `ollama ps` while you work.
- **A second model probably lands on the Tesla P4.** Ollama keeps a model on one GPU when it fits, so once the RTX 3060 is occupied the next one most likely goes to the slower P4. This is inferred from the speeds (for example `llama3.2:3b` at 45 tok/s, even when alone), not observed: `nvidia-smi` on the server would confirm it.
- **The latencies in sections 1 and 3 include these effects,** because the eval alternates between models and the judge. Use the "alone" figures to compare model speed.

## 6. Recommendations

- **Default chat model:** `gemma4:12b`.
- **Keep `llama3.2:3b` only for simple, fast tasks;** do not rely on it for arithmetic, classification or injection-prone input.
- **Be careful with `lfm2.5:8b` for factual questions:** it was wrong once on a simple fact.
- **Use `qwen3-vl:8b` for images, not as a general model,** and expect long thinking.
- **Embeddings:** start with `embeddinggemma:300m`. Switch to `qwen3-embedding:8b` for long documents or if quality on your own data is better.
- **Classification:** use `tev1:4b` with a confidence threshold of about 0.8, and `nimble:9b` when errors are costly or inputs are longer. Add a "none of the above" option and send low-confidence cases to a bigger model or a person.
- **Judging:** try `nimble:9b` as a fast judge for rubric-style checks (it needs no thinking budget and is not one of the models being judged), and keep an LLM judge for open-ended criteria. Use `tev1:4b` only for quick screening and treat scores between 0.3 and 0.7 as unsure.
- **Avoid loading several large models at once** when speed matters.

## 7. Limits of this report and next steps

- **Small datasets.** Add cases from your real data before choosing between close models.
- **Judge issues found and fixed.** The first chat run used JSON mode for the judge, which made `gemma4:12b` think until it ran out of tokens and return empty answers, so two judged metrics errored for every model. The judge now runs with thinking off, and judge errors are reported separately. The judged scores above come from the fixed run.
- **Parser fix.** The chat baseline first misread Portuguese answers ("não") as invalid. It now accepts "sim/não".
- **Not evaluated:** tool calling, long-context quality, the decision models' `score` questions, multi-turn chat, and answer quality in languages other than English and Portuguese.
- **Self-judging:** use a different judge model (`JUDGE_MODEL`) for a fairer chat comparison, or one of the decision judges from section 4.

## Reproduce

```sh
cd evals
.venv/bin/python run_embeddings.py     # about 1 minute
.venv/bin/python run_decisions.py      # about 10 minutes
.venv/bin/python run_chat.py           # about 30 minutes
.venv/bin/python judge_experiment.py   # about 7 minutes: which judge to trust
```

Raw results are saved in `evals/results/*.json` (git-ignored).
