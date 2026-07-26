from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass

from brium.indexer.indexer import tokenize, bigrams


@dataclass
class SearchResult:
    url: str
    title: str
    score: float
    snippet: str = ""


FRESHNESS_HALF_DAYS = 90.0


class SearchEngine:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._k1 = 1.5
        self._b = 0.75

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        terms = tokenize(query)
        if not terms:
            return []
        bgs = bigrams(terms)
        all_terms = list(set(terms + bgs))
        results = self._ranked(all_terms, len(terms), top_k)
        return results

    def _ranked(self, all_terms: list[str], query_term_count: int, top_k: int) -> list[SearchResult]:
        N = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        if N == 0:
            return []
        avgdl = self.conn.execute("SELECT AVG(text_len) FROM docs").fetchone()[0] or 1.0
        now = time.time()

        term_rows = []
        for t in set(all_terms):
            row = self.conn.execute("SELECT id FROM terms WHERE term = ?", (t,)).fetchone()
            if row:
                term_rows.append((t, row["id"]))

        if not term_rows:
            return []

        qtc = max(query_term_count, 1)
        doc_scores: dict[int, float] = {}
        for term, tid in term_rows:
            df = self.conn.execute("SELECT COUNT(*) FROM postings WHERE term_id = ?", (tid,)).fetchone()[0]
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            rows = self.conn.execute(
                """SELECT p.doc_id, p.freq, p.in_title, d.text_len, d.incoming_links, d.crawled_at
                   FROM postings p JOIN docs d ON p.doc_id = d.id
                   WHERE p.term_id = ?""",
                (tid,),
            ).fetchall()
            for r in rows:
                tf = r["freq"]
                dl = r["text_len"]
                bm25 = idf * ((tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / avgdl)))
                title_boost = 1.0 + min(1.0, r["in_title"] / qtc)
                auth_boost = 1.0 + math.log1p(r["incoming_links"]) * 0.15
                age_days = (now - r["crawled_at"]) / 86400
                freshness = 1.0 / (1.0 + age_days / FRESHNESS_HALF_DAYS)
                score = bm25 * title_boost * auth_boost * (0.5 + 0.5 * freshness)
                doc_scores[r["doc_id"]] = doc_scores.get(r["doc_id"], 0.0) + score

        sorted_docs = sorted(doc_scores.items(), key=lambda x: -x[1])[:top_k]
        results = []
        for doc_id, score in sorted_docs:
            doc = self.conn.execute(
                "SELECT url, title FROM docs WHERE id = ?", (doc_id,)
            ).fetchone()
            results.append(SearchResult(url=doc["url"], title=doc["title"], score=score))
        return results

    def close(self):
        self.conn.close()
