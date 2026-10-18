"""Can a decision model (tev1, nimble) be the judge of other models' answers?

    python judge_experiment.py [--judges gemma4:12b,tev1:4b,nimble:9b]

datasets/judge_validation.json holds candidate answers with a known verdict (good = should pass,
bad = should fail). Every judge rules on all of them and is scored against the known verdict:
  - "LLM judge":        the DeepEval metrics used by run_chat.py, judged by gemma4:12b (thinking off)
  - "decision judge":   one yes/no question per answer, answered by a decision model (/v1/systemone)
  - "DeepEval native":  DeepEval's own Answer Relevancy and Faithfulness metrics with
                        eval_mode="system_one", so the decision model runs the whole metric
"""
import argparse
import json
import statistics
import time
from collections import defaultdict
from datetime import date

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from lib import config
from lib.judge import LiteLLMJudge
from lib.judge_metrics import DecisionJudgeMetric
from lib.metrics import run_metrics
from lib.system_one import LiteLLMSystemOne

P = SingleTurnParams
GEVAL = {
    "correctness": ("Correctness", "Decide whether the actual output states the same key facts as the expected output (same names, numbers and years). A wrong or missing fact must score low.", [P.INPUT, P.ACTUAL_OUTPUT, P.EXPECTED_OUTPUT]),
    "abstention": ("Abstention", "The context says nothing about the question. A good answer states that the information is not in the context (or that it does not know) and does not invent it. Score low if the answer claims the thing exists or does not exist.", [P.INPUT, P.ACTUAL_OUTPUT, P.RETRIEVAL_CONTEXT]),
    "summary": ("Summary quality", "The output must be a single sentence that keeps the key facts (a 4 km bike lane on River Avenue, starting in March, about 2.3 million dollars) and invents nothing that is not in the text.", [P.INPUT, P.ACTUAL_OUTPUT]),
}
NATIVE_KINDS = {"relevancy", "faithfulness"}


def llm_metric(kind: str, judge):
    common = {"model": judge, "async_mode": False, "include_reason": True}
    if kind in GEVAL:
        name, criteria, params = GEVAL[kind]
        return GEval(name=name, criteria=criteria, evaluation_params=params, model=judge, async_mode=False)
    return AnswerRelevancyMetric(**common) if kind == "relevancy" else FaithfulnessMetric(**common)


def native_metric(kind: str, decision_model: str):
    system_one = LiteLLMSystemOne(decision_model)
    cls = AnswerRelevancyMetric if kind == "relevancy" else FaithfulnessMetric
    return cls(eval_mode="system_one", system_one_model=system_one, async_mode=False, include_reason=True)


def run_judge(name: str, items: list, make_metric) -> dict:
    print(f"\n=== {name}")
    rows = []
    for item in items:
        if make_metric is None:
            continue
        test_case = LLMTestCase(
            input=item["input"],
            actual_output=item["actual_output"],
            expected_output=item.get("expected"),
            retrieval_context=[item["context"]] if "context" in item else None,
        )
        started = time.perf_counter()
        try:
            metric = make_metric(item["kind"])
            if metric is None:
                continue
            outcome = run_metrics([test_case], [metric])[0]["metrics"][0]
        except Exception as error:  # a judge that cannot rule is a result, not a crash
            outcome = {"score": None, "success": None, "error": f"{type(error).__name__}: {error}"[:200]}
        seconds = time.perf_counter() - started
        error = outcome.get("error") or (outcome["score"] is None and "no score") or None
        row = {"id": item["id"], "kind": item["kind"], "label": item["label"], "score": outcome["score"], "passed": None if error else bool(outcome["success"]), "error": error or None, "seconds": round(seconds, 2)}
        rows.append(row)
        verdict = "ERROR" if error else ("pass" if row["passed"] else "fail")
        right = "" if error else ("ok" if (row["passed"] == (item["label"] == "good")) else "WRONG")
        score = "  n/a" if row["score"] is None else f"{row['score']:.2f}"
        print(f"  {item['id']:<8} want={item['label']:<5} got={verdict:<5} score={score} {seconds:5.1f}s {right}")
    return {"judge": name, "rows": rows}


def summarize(result: dict, only_kinds=None) -> dict:
    rows = [r for r in result["rows"] if only_kinds is None or r["kind"] in only_kinds]
    ok = [r for r in rows if r["error"] is None]
    right = [r for r in ok if r["passed"] == (r["label"] == "good")]
    bad = [r for r in ok if r["label"] == "bad"]
    good = [r for r in ok if r["label"] == "good"]
    by_kind = defaultdict(list)
    for r in ok:
        by_kind[r["kind"]].append(r["passed"] == (r["label"] == "good"))
    return {
        "judge": result["judge"],
        "items": len(rows),
        "errors": len(rows) - len(ok),
        "accuracy": round(len(right) / len(ok), 3) if ok else None,
        "false_pass": f"{sum(r['passed'] for r in bad)}/{len(bad)}",  # a wrong answer accepted: the dangerous mistake
        "false_fail": f"{sum(not r['passed'] for r in good)}/{len(good)}",  # a good answer rejected
        "mean_score_good": round(statistics.mean(r["score"] for r in good), 2) if good else None,
        "mean_score_bad": round(statistics.mean(r["score"] for r in bad), 2) if bad else None,
        "median_seconds": round(statistics.median(r["seconds"] for r in rows), 2) if rows else None,
        "by_kind": {k: f"{sum(v)}/{len(v)}" for k, v in by_kind.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/judge_experiment.json")
    parser.add_argument("--no-native", action="store_true", help="skip DeepEval's native system_one metrics")
    args = parser.parse_args()

    items = config.dataset("judge_validation")["items"]
    llm = LiteLLMJudge()
    print(f"{len(items)} candidate answers | LLM judge: {llm.get_model_name()} | gateway: {config.BASE_URL}")

    out = config.ROOT / args.out
    out.parent.mkdir(exist_ok=True)
    results = []

    def save():
        out.write_text(json.dumps({"date": str(date.today()), "results": results}, indent=1, ensure_ascii=False))

    results.append(run_judge(f"{config.JUDGE_MODEL} (LLM judge, DeepEval metrics)", items, lambda kind: llm_metric(kind, llm)))
    save()
    for model in ("tev1:4b", "nimble:9b"):
        results.append(run_judge(f"{model} (decision judge)", items, lambda kind, m=model: DecisionJudgeMetric(m, kind)))
        save()
    if not args.no_native:
        for model in ("tev1:4b", "nimble:9b"):
            results.append(
                run_judge(f"{model} (DeepEval native system_one)", [i for i in items if i["kind"] in NATIVE_KINDS], lambda kind, m=model: native_metric(kind, m))
            )
            save()

    print("\nSummary (all 41 items; native rows cover the 14 relevancy/faithfulness items)")
    for r in results:
        print(summarize(r))
    print("\nSame 14 relevancy/faithfulness items for every judge")
    for r in results:
        print(summarize(r, NATIVE_KINDS))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
