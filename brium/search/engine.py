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
        self._k1 = 1.2
        self._b = 0.4

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        terms = tokenize(query)
        if not terms:
            return []
        bgs = bigrams(terms)
        all_terms = list(set(terms + bgs))
        return self._ranked(query, all_terms, len(terms), top_k)

    def _ranked(self, raw_query: str, all_terms: list[str],
                query_term_count: int, top_k: int) -> list[SearchResult]:
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
            df = self.conn.execute(
                "SELECT COUNT(*) FROM postings WHERE term_id = ?", (tid,)
            ).fetchone()[0]
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            rows = self.conn.execute(
                """SELECT p.doc_id, p.freq, p.in_title, p.in_heading,
                          d.text_len, d.incoming_links, d.crawled_at, d.snippet
                   FROM postings p JOIN docs d ON p.doc_id = d.id
                   WHERE p.term_id = ?""",
                (tid,),
            ).fetchall()
            for r in rows:
                tf = r["freq"]
                dl = r["text_len"]
                bm25 = idf * ((tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / avgdl)))
                title_boost = 1.0 + min(1.0, r["in_title"] / qtc)
                heading_boost = 1.0 + min(1.0, r["in_heading"] / qtc) * 0.5
                auth_boost = 1.0 + math.log1p(r["incoming_links"]) * 0.15
                age_days = (now - r["crawled_at"]) / 86400
                freshness = 1.0 / (1.0 + age_days / FRESHNESS_HALF_DAYS)
                score = bm25 * title_boost * heading_boost * auth_boost * (0.5 + 0.5 * freshness)
                doc_scores[r["doc_id"]] = doc_scores.get(r["doc_id"], 0.0) + score

        sorted_docs = sorted(doc_scores.items(), key=lambda x: -x[1])[:top_k]
        results = []
        for doc_id, score in sorted_docs:
            doc = self.conn.execute(
                "SELECT url, title, snippet FROM docs WHERE id = ?", (doc_id,)
            ).fetchone()
            title = doc["title"] or ""
            snippet = doc["snippet"] or ""

            # Entity boost: check title + snippet for query phrases
            qlow = raw_query.lower()
            tlow = title.lower()
            # First bigram (usually the named entity)
            first_bg = " ".join(qlow.split()[:2])
            # Full query phrase anywhere in page (snippet covers early content)
            phrase_in_title = qlow in tlow
            entity_in_title = first_bg in tlow
            phrase_in_snippet = qlow in snippet.lower()
            entity_boost = 1.0
            if phrase_in_title:
                entity_boost = 3.0
            elif entity_in_title:
                entity_boost = 2.5
            elif phrase_in_snippet:
                entity_boost = 2.0

            results.append(SearchResult(
                url=doc["url"], title=title,
                score=score * entity_boost, snippet=_make_snippet(snippet, raw_query),
            ))
        results.sort(key=lambda r: -r.score)
        return results[:top_k]

    def close(self):
        self.conn.close()


def _make_snippet(text: str, query: str) -> str:
    if not text or not query:
        return (text or "")[:200]
    qlow = query.lower()
    idx = text.lower().find(qlow)
    if idx < 0:
        return text[:200]
    start = max(0, idx - 60)
    end = min(len(text), idx + len(qlow) + 120)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix
