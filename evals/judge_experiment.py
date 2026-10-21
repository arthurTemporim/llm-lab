"""Can a decision model (tev1, optionally nimble) be the judge of other models' answers?

    python judge_experiment.py [--no-native] [--llm] [--judges tev1:4b,nimble:9b]

datasets/judge_validation.json holds candidate answers with a known verdict (good = should pass,
bad = should fail). Every judge rules on all of them and is scored against the known verdict:
  - "LLM judge":        (only with --llm) DeepEval's general metrics, judged by gemma4:12b. The judge
                        run_chat.py used before tev1; a baseline, not used as a judge anywhere else.
  - "single question":  one compound yes/no question per answer, answered by a decision model
                        (/v1/systemone). The first version of the decision judge.
  - "narrow checks":    a few small yes/no questions per kind of check that must all hold, plus code for
                        the rules a program can verify (one sentence).
  - "case checks":      the checks written for one case in datasets/chat.json, which is what
                        run_chat.py uses. Only the answers to those questions can be ruled this way.
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
LLM_JUDGE = "gemma4:12b"  # the previous judge, kept as the baseline


def case_metrics(model: str):
    """Maps a question of datasets/chat.json to the judge metrics of that case."""
    cases = {}
    for case in config.dataset("chat")["cases"]:
        specs = [s for s in case.get("metrics", []) if s["type"] == "decision"]
        if specs:
            cases[case.get("question") or case["prompt"]] = specs

    def make(item):
        if item["input"] not in cases:
            return None
        return [DecisionJudgeMetric(model, kind=s.get("kind"), checks=s.get("checks"), local=s.get("local"), name=s["name"]) for s in cases[item["input"]]]

    return make


def llm_metric(kind: str, judge):
    common = {"model": judge, "async_mode": False, "include_reason": True}
    if kind in GEVAL:
        name, criteria, params = GEVAL[kind]
        return GEval(name=name, criteria=criteria, evaluation_params=params, model=judge, async_mode=False)
    return AnswerRelevancyMetric(**common) if kind == "relevancy" else FaithfulnessMetric(**common)


def native_metric(item: dict, decision_model: str):
    kind = item["kind"]
    system_one = LiteLLMSystemOne(decision_model)
    cls = AnswerRelevancyMetric if kind == "relevancy" else FaithfulnessMetric
    return cls(eval_mode="system_one", system_one_model=system_one, async_mode=False, include_reason=True)


def run_judge(name: str, items: list, make_metric, reuse: dict | None = None) -> dict:
    """make_metric(item) returns the metrics to run on the item (a metric, a list, or None to skip it).
    reuse maps item id -> a row of a previous run that is kept as is."""
    print(f"\n=== {name}")
    rows = []
    for item in items:
        if reuse and item["id"] in reuse:
            rows.append(reuse[item["id"]])
            continue
        test_case = LLMTestCase(
            input=item["input"],
            actual_output=item["actual_output"],
            expected_output=item.get("expected"),
            retrieval_context=[item["context"]] if "context" in item else None,
        )
        started = time.perf_counter()
        try:
            metrics = make_metric(item)
            if metrics is None:
                continue
            metrics = metrics if isinstance(metrics, list) else [metrics]
            outcomes = [run_metrics([test_case], [m])[0]["metrics"][0] for m in metrics]
            failed = [o for o in outcomes if o.get("error") or o["score"] is None]
            # a case passes when every one of its metrics passes; the score is the lowest one
            outcome = failed[0] if failed else {"score": min(o["score"] for o in outcomes), "success": all(o["success"] for o in outcomes)}
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
    parser.add_argument("--judges", default="tev1:4b", help="comma-separated decision models to compare (default: tev1:4b)")
    parser.add_argument("--llm", action="store_true", help="also run the gemma4:12b LLM judge as a baseline (slow, heavy on the server CPU)")
    parser.add_argument("--reuse-llm", action="store_true", help="keep the gemma4:12b rows already in the output file and judge only the new items")
    args = parser.parse_args()

    items = config.dataset("judge_validation")["items"]
    llm = LiteLLMJudge(LLM_JUDGE)
    native_items = [i for i in items if i["kind"] in NATIVE_KINDS]
    print(f"{len(items)} candidate answers | LLM judge: {llm.get_model_name()} | gateway: {config.BASE_URL}")

    out = config.ROOT / args.out
    out.parent.mkdir(exist_ok=True)
    results = []

    def save():
        out.write_text(json.dumps({"date": str(date.today()), "results": results}, indent=1, ensure_ascii=False))

    judges = args.judges.split(",")
    llm_name = f"{LLM_JUDGE} (LLM judge, DeepEval metrics)"
    if args.llm:
        reuse = None
        if args.reuse_llm and out.exists():
            old = next((r for r in json.loads(out.read_text())["results"] if r["judge"] == llm_name), None)
            reuse = {row["id"]: row for row in old["rows"]} if old else None
        results.append(run_judge(llm_name, items, lambda item: llm_metric(item["kind"], llm), reuse))
        save()
    for model in judges:
        results.append(run_judge(f"{model} (single question)", items, lambda item, m=model: DecisionJudgeMetric(m, item["kind"], variant="single")))
        save()
        results.append(run_judge(f"{model} (narrow checks)", items, lambda item, m=model: DecisionJudgeMetric(m, item["kind"])))
        save()
        results.append(run_judge(f"{model} (case checks)", items, case_metrics(model)))
        save()
    if not args.no_native:
        for model in judges:
            results.append(run_judge(f"{model} (DeepEval native system_one)", native_items, lambda item, m=model: native_metric(item, m)))
            save()

    print(f"\nSummary (all {len(items)} items; native rows cover the {len(native_items)} relevancy/faithfulness items)")
    for r in results:
        print(summarize(r))
    print(f"\nSame {len(native_items)} relevancy/faithfulness items for every judge")
    for r in results:
        print(summarize(r, NATIVE_KINDS))
    groups = {
        "the first 41 clear-cut items (comparable with the first report)": [i["id"] for i in items[:41]],
        "the 27 harder items": [i["id"] for i in items[41:68]],
        "the 16 held-out items (written after the rubrics, never used to tune them)": [i["id"] for i in items if i["id"].startswith("t-")],
    }
    for label, ids in groups.items():
        print(f"\nOnly {label}")
        for r in results:
            print(summarize({"judge": r["judge"], "rows": [row for row in r["rows"] if row["id"] in set(ids)]}))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
