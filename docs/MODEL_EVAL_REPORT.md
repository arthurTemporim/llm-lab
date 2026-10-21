# Model evaluation report

Comparison of the models served by the LiteLLM gateway, by type: chat, embeddings and decision (classifier) models. Built with [DeepEval](https://deepeval.com/); code, datasets and how to rerun are in [evals/](../evals/README.md). Model settings and usage are in [MODELS.md](MODELS.md).

- **Date:** 2026-10-18
- **Setup:** LiteLLM v1.105.1 in front of Ollama v0.40.5, one GPU per model (`OLLAMA_SCHED_SPREAD` off) on an RTX 3060 (12 GB) + Tesla P4 (8 GB), 2 CPUs.
- **Method:** every request goes through the gateway. Sampling uses a fixed seed (42) with each model's own default temperature, one run per case.
- **Judge:** the judged chat cases are ruled by `tev1:4b`, a decision model, with narrow yes/no checks (section 4). It is not one of the chat models, so it cannot favour its own answers. The deterministic checks do not use a judge.
- **Size:** 14 chat cases, 54 retrieval queries over 50 documents, 36 classification cases, 84 answers with a known verdict for testing the judge. These are small sets: **a difference of one or two cases is noise.** Use the results as a first comparison, not a ranking.
- **Changes since the first run of this report:** the judge changed from `gemma4:12b` (DeepEval's general prompts) to `tev1:4b` (narrow yes/no checks), and the chat set grew from 11 to 14 cases, so **judged scores are not comparable with the first version.** Everything was run twice on the same day and every accuracy figure and pass/fail verdict was identical; only timings differ, and the tables show the second run.

## Summary

| Type | Result | Pick |
|---|---|---|
| Chat | `gemma4:12b` passed every case. `qwen3-vl:8b` is correct but 10× slower because it thinks. `lfm2.5:8b` gave a wrong publication year, `llama3.2:3b` missed the arithmetic, an independence date detail and the summary. | `gemma4:12b` by default; `llama3.2:3b` only for simple, fast tasks |
| Embeddings | Effectively a tie: 96–100% Hit@1 for every model and variant. The cost differs a lot (0.6 GB to 4.7 GB). | `embeddinggemma:300m` by default; `qwen3-embedding:8b` when you need the best quality or long passages |
| Decisions | `nimble:9b` 94% vs `tev1:4b` 89% on 36 tickets (2 vs 4 errors, all on ambiguous tickets). `tev1:4b` answers in 0.1 s and `nimble:9b` in 0.3 s, both with a useful confidence score. A chat model (`gemma4:12b`) scored 100% but takes 3.5 s per ticket and gives no probabilities. | `tev1:4b` by default, `nimble:9b` when mistakes cost more or inputs are longer |
| `tev1:4b` as judge | With narrow yes/no checks it ruled correctly on 82 of 84 answers with a known verdict (98%) in 0.1–0.25 s each, and 36 of 36 on the checks written for the chat cases. It caught the wrong year that the old `gemma4:12b` judge let pass. It is weak when an answer says "the context does not contain this". | `tev1:4b` as the judge, with narrow checks; read scores between 0.3 and 0.7 as unsure |

## 1. Chat models

| Model | Deterministic checks | Judged cases passed (mean score) | Median latency in the eval | Generation speed (burst) | Median tokens |
|---|---|---|---|---|---|
| `gemma4:12b` | 6/6 | 8/8 (0.85) | 3.8 s | 80 tok/s | 237 |
| `qwen3-vl:8b` | 6/6 | 7/8 (0.84) | 41.3 s | 57 tok/s | 387 |
| `lfm2.5:8b` | 5/5 | 6/8 (0.72) | 7.2 s | 66 tok/s | 207 |
| `llama3.2:3b` | 4/5 | 5/8 (0.63) | 0.7 s | 45 tok/s | 22 |

The vision case (reading an invoice number from an image) ran only on the two vision models, so `lfm2.5:8b` and `llama3.2:3b` have 5 deterministic cases. The judged score of a case is the lowest probability among its yes/no checks, and a case passes at 0.5. The generation speeds are short-burst measurements taken earlier on Ollama directly (80–150 tokens, thinking off) and were not repeated for this version. `lfm2.5:8b` is slower than in the first version of this report (3.3 to 7.2 s), probably because the judge model is loaded between cases and evicts the others; `llama3.2:3b` went from 0.6 to 1.6 s in one run and back to 0.7 s in the next, so latencies depend on what is loaded at that moment.

| Case | `gemma4:12b` | `qwen3-vl:8b` | `lfm2.5:8b` | `llama3.2:3b` |
|---|---|---|---|---|
| Arithmetic (270 km) | pass | pass | pass | **fail (answered 240)** |
| Number sequence | pass | pass | pass | pass |
| JSON format | pass | pass | pass | pass |
| Exactly 3 bullets | pass | pass | pass | pass |
| Portuguese answer | pass | pass | pass | pass |
| Read invoice from image | pass | pass | n/a | n/a |
| Fact: Dom Casmurro (author and year) | 0.99 | 0.98 | **0.04 (said 1886, expected 1899)** | 0.99 |
| Fact in Portuguese: Brazilian independence (1822, Dom Pedro I) | 0.99 | 0.99 | 0.99 | **0.09 (did not name Dom Pedro)** |
| Explanation (two sentences, vector database) | 0.84 | 0.85 | 0.87 | 0.86 |
| RAG, answerable (faithfulness + correctness) | 0.91 | 0.95 | 0.91 | 0.94 |
| RAG, question the context rules out (Canada) | 0.74 | **0.61 \*** | **0.63 \*** | **0.46 \*** |
| RAG, unanswerable: student discount | 0.73 | 0.70 | 0.75 | 0.82 |
| RAG, unanswerable: Pro plan seats | 0.68 | 0.74 | 0.62 | 0.71 |
| One-sentence summary | 0.89 | 0.93 | 0.95 | **0.20 (left out the cost)** |

\* See below: these are probably judge errors.

**What this shows**
- **`gemma4:12b` passed every case.** `llama3.2:3b` failed four: the arithmetic (240), the independence case (a correct date but no mention of who proclaimed it), the summary (no cost) and the Canada case.
- **The new judge catches the wrong fact the old one let through.** `lfm2.5:8b`'s 1886 now scores 0.04 and fails. With the `gemma4:12b` judge the same answer scored 0.50 and passed.
- **The summary case now separates the models** (0.20 for `llama3.2:3b` against 0.89–0.95). With the old judge everyone got 0.60–0.70.
- **The Canada case is a judge weakness, not a model failure.** The question asks for the express shipping cost to Canada, and the context says international shipping is not available. `qwen3-vl:8b`, `lfm2.5:8b` and `llama3.2:3b` all answered that the context has no such information, which is right, and all three passed the correctness check (0.95, 0.93, 0.69). Only the faithfulness check failed them: `tev1:4b` read "the context does not contain the answer" as contradicting the context ("Does the answer contradict the context?" answered yes with 0.73, 0.66 and 0.77). Even `gemma4:12b`'s correct one-line answer scored only 0.50 on faithfulness. Read this case as a pass for all four on correctness and ignore the faithfulness result until the check is reworded.
- **`qwen3-vl:8b` is slow in practice because it thinks.** A median of 387 tokens per answer and 41 s per case in the eval. Its raw speed is fine (57 tok/s alone), see section 5.
- **Judged scores sit lower than before** (0.63–0.85 against 0.82–0.94) because the score is now the lowest of several checks, not an average of general ratings. They are not comparable with the first version of this report.

## 2. Embedding models

Retrieval task: 54 queries over 50 documents in English and Portuguese, including 20 "twin" distractor documents on the same topic and cross-lingual queries. Each query has one right document.

| Variant | Dimensions | Hit@1 | Hit@3 | Reciprocal rank | One query | 50 documents |
|---|---|---|---|---|---|---|
| `embeddinggemma:300m` | 768 | **1.00** | 1.00 | 1.00 | 30 ms | 0.9 s |
| `embeddinggemma:300m` + model-card prompts | 768 | 0.98 | 1.00 | 0.99 | 32 ms | 0.8 s |
| `qwen3-embedding:8b` | 4096 | 0.98 | 1.00 | 0.99 | 68 ms | 2.8 s |
| `qwen3-embedding:8b` + instruction | 4096 | **1.00** | 1.00 | 1.00 | 70 ms | 2.7 s |
| `nomic-embed-text-v2-moe` | 768 | 0.96 | 1.00 | 0.98 | 38 ms | 1.7 s |
| `nomic-embed-text-v2-moe` + `search_query:`/`search_document:` | 768 | 0.98 | 1.00 | 0.99 | 44 ms | 1.6 s |

**What this shows**
- **All variants find the right document in the top 3 every time.** The only misses were at rank 2, always to the same-topic twin document (the `detail vs twin` query h01 for four of the six variants, and one paraphrase query for plain `nomic`).
- **The differences are one or two queries out of 54.** Do not read a ranking into 0.96 vs 1.00. Plain `qwen3-embedding:8b` scored 0.96 in the first version of this report and 0.98 in both later runs, which is the size of the noise.
- **Prefixes and instructions:** `qwen3-embedding:8b` improved from 0.98 to 1.00 with its instruction and `nomic` from 0.96 to 0.98 with its prefixes. For `embeddinggemma:300m` the model-card prompts did not help (1.00 to 0.98). All of these are single-query changes.
- **Speed and size:** `embeddinggemma:300m` is 0.6 GB and `qwen3-embedding:8b` is 4.7 GB for the same score here, and it is the fastest per query (30 ms).
- **What the test does not cover:** my passages are one or two sentences. It cannot show `qwen3-embedding:8b`'s advantage on long text (8K input), nor `nomic`'s 512-token limit. On large corpora the larger model may separate itself.

## 3. Decision models

Tasks on support tickets, with a chat model doing the same task as a baseline (prompted to reply with a label):
- **Routing:** 26 tickets into billing, technical, account or other (clear, Portuguese, ambiguous, one prompt injection, two long tickets).
- **Refund request:** 10 yes/no cases.

| Model | Type | Routing | Refund yes/no | All 36 | Median latency | Confidence when right / wrong |
|---|---|---|---|---|---|---|
| `nimble:9b` | decision | 92% | **100%** | **94%** | 0.34 s | 0.97 / 0.57 |
| `tev1:4b` | decision | 88% | 90% | 89% | 0.09 s | 0.94 / 0.57 |
| `gemma4:12b` | chat | 100% | 100% | **100%** | 3.5 s | none |
| `llama3.2:3b` | chat | 62% | 60% | 61% | 0.12 s | none |

`nimble:9b` is no longer part of `run_decisions.py`; its row is from the earlier run on the same day (raw results in `evals/results/prev2/`). The two runs of `tev1:4b`, `gemma4:12b` and `llama3.2:3b` agree exactly.

By category (right/total): the decision models and `gemma4:12b` got every clear ticket (17/17) and every Portuguese ticket (9/9). They differ on the 7 ambiguous ones: `gemma4:12b` 7/7, `nimble:9b` 5/7, `tev1:4b` 3/7, `llama3.2:3b` 4/7.

**What this shows**
- **All the decision-model errors were on ambiguous tickets.** For example "login page loads forever" (labelled technical, both said account) and "I can't log in after the payment failed" (labelled billing, both said account). `tev1:4b` also missed "the invoice PDF download button does nothing" (technical, it said billing) and "how long do refunds usually take?" (not a refund request, it said yes). Those labels are debatable. The accuracy figures are identical to the first run.
- **Confidence is useful.** `tev1:4b` answered 30 of 36 tickets with confidence of 0.8 or more and was right on all 30; its four errors all fell below 0.8. `nimble:9b` answered 34 with 0.8 or more and was right on 33. A threshold of about 0.8 sends the doubtful cases to a person or a larger model.
- **A chat model can be more accurate but not cheaper.** `gemma4:12b` got everything right here, but took about 3.5 s per ticket (10–40× slower than the decision models), needs its thinking budget, and returns no probability. `llama3.2:3b` is fast but leaned toward "account" for tickets that were not, and fell for the prompt injection ("ignore previous instructions...").
- **Prompt injection:** both decision models and `gemma4:12b` resisted it; `llama3.2:3b` did not.
- **Tev1 vs Nimble:** 34 vs 32 correct out of 36 is two cases. On this data they are close; `nimble:9b` costs 2× the disk and VRAM (9.5 GB vs 4.6 GB).
- **Long inputs, no conclusion.** Both models classified the 1.5K-token and 3.4K-token tickets correctly, but the real request was in the last sentence. Tev1's documented context is about 2K tokens, so for the 3.4K ticket it probably dropped the beginning and still found the answer. This test says nothing about understanding long text.

## 4. `tev1:4b` as the judge

The judged chat cases are ruled by `tev1:4b`. This section checks how far to trust it, using 84 candidate answers whose right verdict is known (45 should fail, 39 should pass). They include real errors from section 1 (`lfm2.5:8b`'s 1886 instead of 1899, `llama3.2:3b`'s 240 instead of 270), contradicted or hallucinated RAG answers, partial answers, wrong units, swapped facts, answers that say "not in the context" and then guess, off-topic answers, and summaries that are too long or invent a fact. Dataset: `evals/datasets/judge_validation.json`; code: `evals/judge_experiment.py`.

The judge answers yes/no questions through `/v1/systemone` and returns a probability for each. A case passes when the lowest probability among its checks is at least 0.5. Three ways of asking were compared:
- **Single question:** one compound question per kind of check ("does the answer state the same key facts as the reference, and nothing invented?").
- **Narrow checks:** two to four small questions per kind that must all hold ("does the answer contain the key facts?" and "does it give a different name, number or year?"), plus code for rules a program can verify (a summary must be one sentence).
- **Case checks:** the questions written for each case in `chat.json` (for example "does the answer say it was published in 1899?"). This is what the chat eval uses. It can only be tested on the 36 answers whose question appears in the chat set.

| `tev1:4b` judge | Right verdicts | Wrong answers accepted | Good answers rejected | Mean score good / bad | Median time per item |
|---|---|---|---|---|---|
| Single question (84 items) | 78/84 (93%) | 6/45 | 0/39 | 0.91 / 0.18 | 0.11 s |
| **Narrow checks (84 items)** | **82/84 (98%)** | 2/45 | 0/39 | 0.83 / 0.13 | 0.17 s |
| Case checks (36 items) | **36/36** | 0/20 | 0/16 | 0.82 / 0.12 | 0.24 s |
| DeepEval native `system_one` (30 relevancy/faithfulness items) | 28/30 (93%) | 2/15 | 0/15 | 0.91 / 0.20 | 0.23 s |

By kind of check (right verdicts, `tev1:4b`):

| Judge | Correctness (29) | Faithfulness (18) | Abstention (15) | Relevancy (12) | Summary rules (10) |
|---|---|---|---|---|---|
| Single question | 29 | 18 | 10 | 12 | 9 |
| Narrow checks | 29 | 17 | 14 | 12 | 10 |

**What this shows**
- **Narrow checks beat the single question, mostly on "say you don't know" answers and on summaries.** The single question accepted 5 wrong abstention answers (an invented 20% discount, an invented seat count, an "email support" workaround and two "not stated, but..." guesses) and a two-sentence summary. The narrow checks miss two answers: "ship free over $50, and returns are free too" (score 0.56) and "not in the policy, but you can cancel a monthly plan at any time" (0.63).
- **Case checks gave no error on the 36 answers they cover.** The questions of each case were written before the first run and not changed after it (the generic faithfulness, abstention and summary rubrics that some cases also use were), so this one is mostly not tuned to the data. It is still only 36 answers on 5 questions.
- **The narrow checks were tuned on these same answers, so 98% is optimistic.** My first version of them (three or four checks per kind, including "does the answer leave out a fact?") was worse than the single question: 61/68 against 62/68. Each extra question that hovers near 0.5, such as "Eight bits." against the reference "8", lets one noisy check fail a good answer, because the lowest check wins. I diagnosed that on the first 68 answers, dropped or rewrote the noisy questions, and added 16 answers I had not looked at. **On those 16 held-out answers the single question and the narrow checks both got 16/16**, so the held-out set cannot tell them apart: it is too easy.
- **Fewer, concrete questions work better than many.** A 4B classifier answers "does the answer say 1899?" reliably and hedges on "does the answer leave out a fact?".
- **Compared with the old judge.** `gemma4:12b` with DeepEval's general prompts ruled correctly on 57 of the first 68 answers (84%), accepting 11 of 36 wrong ones, in about 4 s each. The same 41 answers that gave 37/41 in the first version of this report gave 36/41 in a later run, which is the noise level. It was not run on the 16 held-out answers. `nimble:9b` was tested too in the earlier run and is not the judge: with the same checks it got 79/84 on narrow checks (it rejected 4 good answers) and 35/36 on case checks. That run was not repeated.
- **DeepEval's native mode still trails the task-specific questions** (93% on its 30 items).

**Where `tev1:4b` is weak**
- **Answers that say "the context does not contain this".** It reads them as contradicting the context (section 1, Canada case) and also lets some "not stated, but..." guesses through.
- **Scores near 0.5.** Anything between 0.3 and 0.7 should be read as "unsure". The chat eval reports the score for that reason.
- **Number words and other languages.** "Eight" was not matched with "8" until the question said so, and "Brasília" in a Portuguese answer scored 0.42 on the first wording.

**Limits of this experiment**
- **Small and written by me.** 84 answers means one is 1.2 points. They are mostly short and in English, and the checks were written for these kinds of check.
- **No long or subtle answers.** Test with 50 or more answers labelled from your own data before relying on it for something that matters.

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
- **Judging:** use `tev1:4b` with narrow yes/no checks (one fact per question, what code can check is checked by code), and read scores between 0.3 and 0.7 as unsure. Do not use it to judge answers that say "the context does not contain this"; check those by hand or with a larger model.
- **Avoid loading several large models at once** when speed matters.

## 7. Limits of this report and next steps

- **Small datasets.** Add cases from your real data before choosing between close models.
- **Judge changes.** The first version of this report used `gemma4:12b` with thinking off as the judge, after JSON mode had made it think until it ran out of tokens. It is now `tev1:4b` with yes/no checks. Judge errors are still reported separately, and there were none in this run.
- **Parser fix.** The chat baseline first misread Portuguese answers ("não") as invalid. It now accepts "sim/não".
- **Not evaluated:** tool calling, long-context quality, the decision models' `score` questions, multi-turn chat, and answer quality in languages other than English and Portuguese.
- **Self-judging** is gone: the judge is not one of the chat models.
- **Canada case:** the faithfulness check of `rag-shipping-conflict` rejects correct answers (section 1). I left it as it is so the results match the datasets; rewording it or dropping that check is the next fix.
- **Section 5 was not repeated.** The speed and memory figures are from the earlier measurement.

## Reproduce

```sh
cd evals
.venv/bin/python run_embeddings.py     # about 1 minute
.venv/bin/python run_decisions.py      # about 4 minutes
.venv/bin/python run_chat.py           # about 16 minutes (the thinking model is most of it)
.venv/bin/python judge_experiment.py   # about 1 minute: how far to trust the tev1 judge
```

Raw results are saved in `evals/results/*.json` (git-ignored).
