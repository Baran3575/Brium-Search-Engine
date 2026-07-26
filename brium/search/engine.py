from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass

from brium.indexer.indexer import tokenize


@dataclass
class SearchResult:
    url: str
    title: str
    score: float
    snippet: str = ""


class SearchEngine:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._k1 = 1.5
        self._b = 0.75

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        terms = tokenize(query)
        if not terms:
            return []
        results = self._bm25(terms, top_k)
        return results

    def _bm25(self, terms: list[str], top_k: int) -> list[SearchResult]:
        N = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        if N == 0:
            return []
        avgdl = (
            self.conn.execute("SELECT AVG(text_len) FROM docs").fetchone()[0] or 1.0
        )
        term_ids = []
        for t in set(terms):
            row = self.conn.execute(
                "SELECT id FROM terms WHERE term = ?", (t,)
            ).fetchone()
            if row:
                term_ids.append((t, row["id"]))
        if not term_ids:
            return []
        doc_scores: dict[int, float] = {}
        for term, tid in term_ids:
            df = self.conn.execute(
                "SELECT COUNT(*) FROM postings WHERE term_id = ?", (tid,)
            ).fetchone()[0]
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            rows = self.conn.execute(
                """SELECT p.doc_id, p.freq, d.text_len
                   FROM postings p JOIN docs d ON p.doc_id = d.id
                   WHERE p.term_id = ?""",
                (tid,),
            ).fetchall()
            for r in rows:
                tf = r["freq"]
                dl = r["text_len"]
                score = idf * ((tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / avgdl)))
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
