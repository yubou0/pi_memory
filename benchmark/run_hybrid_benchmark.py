#!/usr/bin/env python3
"""
Hybrid Memory Retrieval Benchmark.

這支腳本保留原本 run_benchmark.py 作為 pure BM25 baseline，
並另外使用 memory.hybrid.hybrid_search() 評估 BM25 + embedding 的效果。
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from memory.hybrid import hybrid_search


def load_jsonl(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def dcg(gains: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float:
    gains = [1.0 if rid in relevant else 0.0 for rid in ranked_ids[:k]]
    ideal = [1.0] * min(len(relevant), k)
    idcg = dcg(ideal)
    return (dcg(gains) / idcg) if idcg > 0 else 0.0


def avg(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.6)
    parser.add_argument("--per-query", action="store_true")
    parser.add_argument("--corpus", default="corpus.jsonl")
    parser.add_argument("--queries", default="queries.jsonl")
    args = parser.parse_args()

    k = args.k
    alpha = args.alpha

    corpus = load_jsonl(HERE / args.corpus)
    queries = load_jsonl(HERE / args.queries)

    docs = [
        {
            "id": row["id"],
            "text": " ".join([row["summary"], *row.get("tags", [])]),
        }
        for row in corpus
    ]

    recalls, rrs, ndcgs = [], [], []
    rows = []

    for q in queries:
        relevant = set(q["relevant_ids"])
        hits = hybrid_search(q["query"], docs, k=k, alpha=alpha)
        ranked_ids = [h["id"] for h in hits]

        hit_set = set(ranked_ids) & relevant
        recall = len(hit_set) / len(relevant) if relevant else 0.0

        rr = 0.0
        for rank, rid in enumerate(ranked_ids, start=1):
            if rid in relevant:
                rr = 1.0 / rank
                break

        nd = ndcg_at_k(ranked_ids, relevant, k)

        recalls.append(recall)
        rrs.append(rr)
        ndcgs.append(nd)
        rows.append((q["query"], ranked_ids[:k], sorted(relevant), recall, rr, nd))

    print(f"\n=== Hybrid Memory Retrieval Benchmark (k={k}, alpha={alpha}, {len(queries)} queries) ===\n")

    if args.per_query:
        for query, got, rel, rc, rr, nd in rows:
            mark = "✓" if rc > 0 else "✗"
            print(f"{mark} {query}")
            print(f"    got@{k}: {got}")
            print(f"    gold : {rel}   Recall={rc:.2f} RR={rr:.2f} nDCG={nd:.2f}\n")

    print(f"Recall@{k} : {avg(recalls):.3f}")
    print(f"MRR       : {avg(rrs):.3f}")
    print(f"nDCG@{k}  : {avg(ndcgs):.3f}")


if __name__ == "__main__":
    main()