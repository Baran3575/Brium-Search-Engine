from __future__ import annotations

import sqlite3
import sys
import json
from dataclasses import dataclass
from pathlib import Path

from brium.search.engine import SearchEngine
from brium.indexer.indexer import Indexer
from brium.crawler.spider import Page


@dataclass
class Qrel:
    query: str
    relevant_urls: set[str]


BUILTIN_TESTS: list[Qrel] = [
    Qrel("example domain", {"https://example.com"}),
    Qrel("iana", {"https://www.iana.org/"}),
]


def precision_at_k(results: list, relevant: set[str], k: int) -> float:
    top = results[:k]
    if not top:
        return 0.0
    hits = sum(1 for r in top if r.url in relevant)
    return hits / len(top)


def recall_at_k(results: list, relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = results[:k]
    hits = sum(1 for r in top if r.url in relevant)
    return hits / len(relevant)


def mrr(results: list, relevant: set[str]) -> float:
    for i, r in enumerate(results):
        if r.url in relevant:
            return 1.0 / (i + 1)
    return 0.0


def load_qrels(path: str | None) -> list[Qrel]:
    if path is None:
        return BUILTIN_TESTS
    p = Path(path)
    if not p.exists():
        print(f"qrels file not found: {path}", file=sys.stderr)
        return BUILTIN_TESTS

    qrels: list[Qrel] = []
    if p.suffix == ".json":
        data = json.loads(p.read_text())
        for item in data:
            qrels.append(Qrel(item["query"], set(item["relevant_urls"])))
    elif p.suffix == ".txt":
        for line in p.read_text().strip().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                qrels.append(Qrel(parts[0], set(parts[1].split(","))))
    return qrels or BUILTIN_TESTS


def main():
    import argparse

    parser = argparse.ArgumentParser("brium-benchmark")
    parser.add_argument("--data-dir", default="crawl_data")
    parser.add_argument("--qrels", help="path to qrels file (json or txt)")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    db_path = f"{args.data_dir}/index.db"
    if not Path(db_path).exists():
        print(f"Index not found at {db_path}. Run 'brium crawl' first.", file=sys.stderr)
        sys.exit(1)
    engine = SearchEngine(db_path)
    qrels = load_qrels(args.qrels)

    if not qrels:
        print("No test queries loaded")
        return

    print(f"Loaded {len(qrels)} test queries")
    print(f"{'Query':<30} {'P@5':<8} {'P@10':<8} {'R@10':<8} {'MRR':<8} {'Results':<8}")
    print("-" * 70)

    total_p5 = total_p10 = total_r10 = total_mrr = 0.0
    for qrel in qrels:
        results = engine.search(qrel.query, args.top_k)
        p5 = precision_at_k(results, qrel.relevant_urls, 5)
        p10 = precision_at_k(results, qrel.relevant_urls, 10)
        r10 = recall_at_k(results, qrel.relevant_urls, 10)
        mr = mrr(results, qrel.relevant_urls)
        total_p5 += p5
        total_p10 += p10
        total_r10 += r10
        total_mrr += mr
        print(f"{qrel.query:<30} {p5:<8.3f} {p10:<8.3f} {r10:<8.3f} {mr:<8.3f} {len(results):<8}")

    n = len(qrels)
    print("-" * 70)
    print(f"{'AVERAGE':<30} {total_p5/n:<8.3f} {total_p10/n:<8.3f} {total_r10/n:<8.3f} {total_mrr/n:<8.3f}")


if __name__ == "__main__":
    main()
