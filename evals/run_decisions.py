"""Evaluate the decision models (/v1/systemone) and compare them with chat models doing the same task.

    python run_decisions.py [--no-baselines]

Tasks: team routing (choice, 4 options) and refund request (yes/no) on labelled support tickets.
DeepEval's ExactMatch metric scores each prediction; confidence and latency are recorded as well.
"""
import argparse
import json
import re
import statistics
from collections import defaultdict
from datetime import date

from deepeval.test_case import LLMTestCase

from lib import config
from lib.llm import chat, systemone
from lib.metrics import ExactMatchMetric, run_metrics


def decide_choice(model: str, text: str, spec: dict) -> dict:
    questions = {"team": {"type": "choice", "instructions": spec["instructions"], "criteria": spec["criteria"]}}
    data, seconds = systemone(model, text, questions)
    answer = data["answers"]["team"]
    return {"pred": answer["choice"], "confidence": answer["confidence"], "latency": seconds, "input_tokens": data["usage"]["input_tokens"]}


def decide_noul(model: str, text: str, spec: dict) -> dict:
    questions = {"refund": {"type": "noul", "instructions": spec["instructions"]}}
    data, seconds = systemone(model, text, questions)
    probability = data["answers"]["refund"]["noul"]
    return {"pred": str(probability > 0.5).lower(), "confidence": max(probability, 1 - probability), "latency": seconds, "input_tokens": data["usage"]["input_tokens"]}


def chat_choice(model: str, text: str, spec: dict) -> dict:
    options = "\n".join(f"- {name}: {desc}" for name, desc in spec["criteria"].items())
    prompt = f"Classify the support ticket into exactly one team.\n{options}\nReply with only the team name.\n\nTicket: {text}"
    answer = chat(model, [{"role": "user", "content": prompt}])
    content = answer["content"].lower()
    found = sorted((content.find(name), name) for name in spec["criteria"] if name in content)
    return {"pred": found[0][1] if found else content.strip()[:20], "confidence": None, "latency": answer["latency"], "input_tokens": None}


def chat_noul(model: str, text: str, spec: dict) -> dict:
    prompt = f"{spec['instructions']} Answer only yes or no.\n\nTicket: {text}"
    answer = chat(model, [{"role": "user", "content": prompt}])
    content = answer["content"].strip().lower()
    # the model may answer in the ticket's language (sim / não)
    pred = "true" if re.match(r"\W*(yes|sim)\b", content) else "false" if re.match(r"\W*(no|não|nao)\b", content) else content[:20]
    return {"pred": pred, "confidence": None, "latency": answer["latency"], "input_tokens": None}


def evaluate_model(name: str, kind: str, data: dict) -> dict:
    print(f"\n=== {name} ({kind})")
    runner = {"decision": (decide_choice, decide_noul), "chat": (chat_choice, chat_noul)}[kind]
    warm_text = "Warm-up ticket: please ignore."
    runner[0](name, warm_text, data["choice"])
    tasks = [("choice", runner[0], data["choice"]), ("noul", runner[1], data["noul"])]

    rows = []
    for task, function, spec in tasks:
        for case in spec["cases"]:
            gold = str(case["gold"]).lower()
            try:
                result = function(name, case["text"], spec)
                error = None
            except RuntimeError as exc:
                result = {"pred": "ERROR", "confidence": None, "latency": None, "input_tokens": None}
                error = str(exc)[:200]
            rows.append({"task": task, "id": case["id"], "category": case["category"], "gold": gold, "error": error, **result})

    test_cases = [
        LLMTestCase(input=r["id"], actual_output=r["pred"], expected_output=r["gold"], additional_metadata={"confidence": r["confidence"]})
        for r in rows
    ]
    scored = run_metrics(test_cases, [ExactMatchMetric()])
    for row, outcome in zip(rows, scored):
        row["correct"] = outcome["success"]
        print(f"  {row['id']:<5} {row['category']:<22} gold={row['gold']:<10} pred={row['pred']:<10} {'ok' if row['correct'] else 'WRONG'}")

    def accuracy(subset):
        return round(sum(r["correct"] for r in subset) / len(subset), 3) if subset else None

    by_category = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    confident = [r["confidence"] for r in rows if r["confidence"] is not None]
    correct_conf = [r["confidence"] for r in rows if r["confidence"] is not None and r["correct"]]
    wrong_conf = [r["confidence"] for r in rows if r["confidence"] is not None and not r["correct"]]
    latencies = [r["latency"] for r in rows if r["latency"] is not None]
    return {
        "model": name,
        "kind": kind,
        "accuracy_choice": accuracy([r for r in rows if r["task"] == "choice"]),
        "accuracy_noul": accuracy([r for r in rows if r["task"] == "noul"]),
        "accuracy_all": accuracy(rows),
        "accuracy_by_category": {c: f"{sum(r['correct'] for r in v)}/{len(v)}" for c, v in by_category.items()},
        "mean_confidence": round(statistics.mean(confident), 3) if confident else None,
        "confidence_when_correct": round(statistics.mean(correct_conf), 3) if correct_conf else None,
        "confidence_when_wrong": round(statistics.mean(wrong_conf), 3) if wrong_conf else None,
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "errors": [r["id"] for r in rows if r["error"]],
        "wrong": [{k: r[k] for k in ("id", "category", "gold", "pred", "confidence")} for r in rows if not r["correct"]],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-baselines", action="store_true", help="skip the chat-model baselines")
    parser.add_argument("--models", help="comma-separated model names to re-run; the others are kept from the previous results")
    parser.add_argument("--out", default="results/decisions.json")
    args = parser.parse_args()

    registry = config.models()["decisions"]
    data = config.dataset("decisions")
    n_choice, n_noul = len(data["choice"]["cases"]), len(data["noul"]["cases"])
    print(f"Gateway: {config.BASE_URL} | {n_choice} routing cases + {n_noul} refund cases")

    out = config.ROOT / args.out
    out.parent.mkdir(exist_ok=True)
    plan = [(m["name"], "decision") for m in registry["models"]]
    if not args.no_baselines:
        plan += [(m["name"], "chat") for m in registry["chat_baselines"]]

    previous = json.loads(out.read_text())["results"] if args.models and out.exists() else []
    if args.models:
        plan = [(n, k) for n, k in plan if n in args.models.split(",")]
    results = []
    for name, kind in plan:
        results.append(evaluate_model(name, kind, data))
        rerun = {(r["model"], r["kind"]) for r in results}
        merged = results + [r for r in previous if (r["model"], r["kind"]) not in rerun]
        out.write_text(json.dumps({"date": str(date.today()), "results": merged}, indent=1, ensure_ascii=False))  # keep partial runs
    results = merged
    print("\nSummary")
    for r in results:
        print({k: r[k] for k in ("model", "kind", "accuracy_choice", "accuracy_noul", "accuracy_all", "confidence_when_correct", "confidence_when_wrong", "median_latency_s")})
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
