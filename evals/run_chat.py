"""Evaluate the chat models: deterministic checks plus yes/no checks ruled by a decision model.

    python run_chat.py [--models gemma4:12b,llama3.2:3b] [--cases math-distance,...] [--no-judge]

The judge (JUDGE_MODEL, default tev1:4b) answers narrow yes/no questions through /v1/systemone; see
lib/judge_metrics.py. Questions that code can verify (one sentence, a number) are checked by code.
"""
import argparse
import json
import statistics
import time
from datetime import date

from deepeval.test_case import LLMTestCase

from lib import config
from lib.judge_metrics import DecisionJudgeMetric
from lib.llm import chat, image_part
from lib.metrics import CheckMetric, run_metrics


def build_messages(case: dict) -> list:
    if "context" in case:
        text = (
            "Answer the question using only the context. If the context does not contain the answer, say so.\n\n"
            f"Context:\n{case['context']}\n\nQuestion: {case['question']}"
        )
    else:
        text = case["prompt"]
    if "image" in case:
        content = [{"type": "text", "text": text}, image_part(config.ROOT / "datasets" / case["image"])]
        return [{"role": "user", "content": content}]
    return [{"role": "user", "content": text}]


def build_metrics(case: dict, judge: str) -> list:
    if "check" in case:
        return [CheckMetric(case["check"], name=f"Check: {case['check']['type']}")]
    metrics = []
    for spec in case["metrics"]:
        if spec["type"] != "decision":
            raise ValueError(f"unknown metric {spec['type']}")
        metrics.append(DecisionJudgeMetric(judge, kind=spec.get("kind"), checks=spec.get("checks"), local=spec.get("local"), name=spec["name"]))
    return metrics


def evaluate_model(model: str, vision: bool, cases: list, judge: str) -> dict:
    print(f"\n=== {model}")
    warm = chat(model, [{"role": "user", "content": "Say OK."}], max_tokens=512)
    print(f"  warm-up (includes model load): {warm['latency']:.1f}s")
    results = []
    for case in cases:
        if case.get("requires") == "vision" and not vision:
            results.append({"id": case["id"], "category": case["category"], "skipped": "no vision support"})
            print(f"  {case['id']:<36} skipped (no vision)")
            continue
        entry = {"id": case["id"], "category": case["category"]}
        try:
            answer = chat(model, build_messages(case))
        except RuntimeError as error:
            entry.update(error=str(error), score=0.0, passed=False)
            results.append(entry)
            print(f"  {case['id']:<36} ERROR {error}")
            continue
        entry.update(
            output=answer["content"][:400],
            latency=round(answer["latency"], 1),
            completion_tokens=answer["completion_tokens"],
            finish_reason=answer["finish_reason"],
            thinking_chars=len(answer["reasoning"]),
        )
        test_case = LLMTestCase(
            input=case.get("question") or case["prompt"],
            actual_output=answer["content"],
            expected_output=case.get("expected"),
            retrieval_context=[case["context"]] if "context" in case else None,
        )
        rows = run_metrics([test_case], build_metrics(case, judge))
        metrics = rows[0]["metrics"]
        entry["metrics"] = metrics
        entry["judged"] = "check" not in case
        if not metrics or any(m.get("error") or m["score"] is None for m in metrics):
            # The judge failed, so this says nothing about the model: keep it out of the scores.
            entry.update(judge_error=True, score=None, passed=None)
            flag = "JUDGE ERROR"
        else:
            entry["score"] = round(sum(m["score"] for m in metrics) / len(metrics), 3)
            entry["passed"] = all(m["success"] for m in metrics)
            flag = "PASS" if entry["passed"] else "FAIL"
        results.append(entry)
        score = "n/a" if entry["score"] is None else f"{entry['score']:.2f}"
        print(f"  {case['id']:<36} {flag} score={score} {entry['latency']}s tokens={entry['completion_tokens']}")
    return {"model": model, "warmup_latency": round(warm["latency"], 1), "cases": results}


def summarize(result: dict) -> dict:
    run = [c for c in result["cases"] if "skipped" not in c]
    checks = [c for c in run if not c.get("judged", False)]
    judged = [c for c in run if c.get("judged", False) and not c.get("judge_error")]
    latencies = [c["latency"] for c in run if "latency" in c]
    tokens = [c["completion_tokens"] for c in run if c.get("completion_tokens") is not None]
    return {
        "model": result["model"],
        "checks_passed": f"{sum(c['passed'] for c in checks)}/{len(checks)}",
        "judged_mean": round(statistics.mean(c["score"] for c in judged), 2) if judged else None,
        "judged_passed": f"{sum(c['passed'] for c in judged)}/{len(judged)}",
        "median_latency_s": round(statistics.median(latencies), 1) if latencies else None,
        "median_tokens": statistics.median(tokens) if tokens else None,
        "judge_errors": sum(1 for c in run if c.get("judge_error")),
        "truncated": sum(1 for c in run if c.get("finish_reason") == "length"),
        "warmup_s": result["warmup_latency"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", help="comma-separated subset of models.yaml chat models")
    parser.add_argument("--cases", help="comma-separated case ids")
    parser.add_argument("--no-judge", action="store_true", help="only run the deterministic cases")
    parser.add_argument("--out", default="results/chat.json")
    args = parser.parse_args()

    registry = config.models()["chat"]
    if args.models:
        wanted = args.models.split(",")
        registry = [m for m in registry if m["name"] in wanted]
    cases = config.dataset("chat")["cases"]
    if args.cases:
        cases = [c for c in cases if c["id"] in args.cases.split(",")]
    if args.no_judge:
        cases = [c for c in cases if "check" in c]

    judge = config.JUDGE_MODEL
    print(f"Judge: {judge} (decision model, yes/no checks) | gateway: {config.BASE_URL}")
    started = time.time()
    out = config.ROOT / args.out
    out.parent.mkdir(exist_ok=True)

    # --models / --cases re-run only part of the evaluation: merge into the previous results file
    previous = json.loads(out.read_text())["results"] if (args.cases or args.models) and out.exists() else []
    order = [c["id"] for c in config.dataset("chat")["cases"]]
    results = []
    for m in registry:
        new = evaluate_model(m["name"], m.get("vision", False), cases, judge)
        old = next((r for r in previous if r["model"] == m["name"]), None)
        if old and args.cases:  # replace only the re-run cases, keep the others from the previous run
            kept = {c["id"]: c for c in old["cases"]}
            kept.update({c["id"]: c for c in new["cases"]})
            new["cases"] = [kept[i] for i in order if i in kept]
        results.append(new)
        merged = results + [r for r in previous if r["model"] not in {x["model"] for x in results}]
        summary = [summarize(r) for r in merged]
        payload = {"date": str(date.today()), "judge": config.JUDGE_MODEL, "seconds": round(time.time() - started), "summary": summary, "results": merged}
        out.write_text(json.dumps(payload, indent=1, ensure_ascii=False))  # keep partial runs
    print("\nSummary")
    for row in summary:
        print(row)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
