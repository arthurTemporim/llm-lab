"""Evaluate the embedding models on a retrieval task (DeepEval custom metrics Hit@1, Hit@3, MRR).

    python run_embeddings.py [--models "qwen3-embedding:8b,embeddinggemma:300m"]

Each query has one right document among 30. Documents and queries are embedded through LiteLLM,
ranked by cosine similarity, and the rank of the right document feeds the DeepEval metrics.
"""
import argparse
import json
import statistics
from collections import defaultdict
from datetime import date

import numpy as np
from deepeval.test_case import LLMTestCase

from lib import config
from lib.llm import embed
from lib.metrics import RankMetric, run_metrics


def evaluate_variant(variant: dict, data: dict) -> dict:
    model, label = variant["name"], variant["label"]
    docs = data["documents"]
    queries = data["queries"]
    doc_texts = [variant.get("doc_prefix", "") + d["text"] for d in docs]
    query_texts = [variant.get("query_prefix", "") + q["text"] for q in queries]

    embed(model, ["warm-up"])
    doc_vectors, doc_seconds = embed(model, doc_texts)
    query_vectors, query_seconds = embed(model, query_texts)
    single = [embed(model, [query_texts[i]])[1] for i in range(5)]

    d = np.array(doc_vectors)
    q = np.array(query_vectors)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    similarity = q @ d.T

    ids = [doc["id"] for doc in docs]
    texts = {doc["id"]: doc["text"] for doc in docs}
    cases, details = [], []
    for i, query in enumerate(queries):
        order = [ids[j] for j in np.argsort(-similarity[i])]
        rank = order.index(query["gold"]) + 1
        gold_score = float(similarity[i][ids.index(query["gold"])])
        top_wrong = float(max(similarity[i][j] for j in range(len(ids)) if ids[j] != query["gold"]))
        cases.append(
            LLMTestCase(
                input=query["text"],
                actual_output=texts[order[0]],
                expected_output=texts[query["gold"]],
                retrieval_context=[texts[x] for x in order[:3]],
                additional_metadata={"rank": rank, "type": query["type"]},
            )
        )
        details.append(
            {"id": query["id"], "type": query["type"], "rank": rank, "top1": order[0], "gold": query["gold"], "margin": round(gold_score - top_wrong, 3)}
        )

    rows = run_metrics(cases, [RankMetric("hit@1"), RankMetric("hit@3"), RankMetric("mrr")])
    by_metric = defaultdict(list)
    by_type = defaultdict(list)
    for row, detail in zip(rows, details):
        for metric in row["metrics"]:
            by_metric[metric["name"]].append(metric["score"])
        by_type[detail["type"]].append(detail["rank"] == 1)

    return {
        "label": label,
        "model": model,
        "dimensions": int(d.shape[1]),
        "hit@1": round(statistics.mean(by_metric["Hit@1"]), 3),
        "hit@3": round(statistics.mean(by_metric["Hit@3"]), 3),
        "mrr": round(statistics.mean(by_metric["Reciprocal rank"]), 3),
        "mean_margin": round(statistics.mean(x["margin"] for x in details), 3),
        "hit@1_by_type": {t: f"{sum(v)}/{len(v)}" for t, v in by_type.items()},
        "docs_batch_s": round(doc_seconds, 2),
        "queries_batch_s": round(query_seconds, 2),
        "single_query_ms": round(statistics.median(single) * 1000),
        "misses": [x for x in details if x["rank"] > 1],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", help="comma-separated labels from models.yaml")
    parser.add_argument("--out", default="results/embeddings.json")
    args = parser.parse_args()

    variants = config.models()["embeddings"]
    if args.models:
        variants = [v for v in variants if v["label"] in args.models.split(",")]
    data = config.dataset("embeddings")
    print(f"Gateway: {config.BASE_URL} | {len(data['documents'])} documents, {len(data['queries'])} queries")

    results = []
    for variant in variants:
        result = evaluate_variant(variant, data)
        results.append(result)
        print(
            f"{result['label']:<34} dim={result['dimensions']:<5} hit@1={result['hit@1']:.2f} hit@3={result['hit@3']:.2f} "
            f"mrr={result['mrr']:.2f} margin={result['mean_margin']:+.3f} single={result['single_query_ms']}ms"
        )

    out = config.ROOT / args.out
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"date": str(date.today()), "results": results}, indent=1, ensure_ascii=False))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
