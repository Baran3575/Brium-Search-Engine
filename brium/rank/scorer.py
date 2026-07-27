from __future__ import annotations

import math
import time
from urllib.parse import urlparse

from brium.base.types import SearchResult
from brium.index.tokenizer import tokenize, bigrams
from brium.rank.classifier import (
    classify, detect_lang, is_stop_word,
    domain_tier, domain_authority, url_depth_penalty,
)
from brium.rank.booster import entity_boost, freshness_boost, lang_boost, title_start_boost, make_snippet
from brium.rank.diversifier import diversify
from brium.plugins.registry import Registry
from brium.storage.interface import StorageBackend, PostingRow

FRESHNESS_HALF_DAYS = 90.0
NEWS_FRESHNESS_HALF_DAYS = 7.0


class Scorer:
    def __init__(self, conn=None, ranker_name: str = "bm25",
                 storage: StorageBackend | None = None):
        self.conn = conn
        self._k1 = 1.2
        self._b = 0.4
        self._ranker_name = ranker_name
        self._storage = storage

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        if self._ranker_name != "bm25":
            ranker_cls = Registry.get_ranker(self._ranker_name)
            if ranker_cls:
                ranker = ranker_cls()
                conn = self.conn or (self._storage.conn if hasattr(self._storage, 'conn') else None)
                plugin_results = ranker.rank(query, conn, top_k)
                return [SearchResult(
                    url=r.url, title=r.title, score=r.score, snippet=r.snippet
                ) for r in plugin_results]

        terms = tokenize(query)
        terms = [t for t in terms if not is_stop_word(t)]
        if not terms:
            return []
        bgs = bigrams(terms)
        all_terms = list(set(terms + bgs))
        return self._rank(query, all_terms, len(terms), top_k)

    def _conn(self):
        return self.conn

    def _rank(self, raw_query: str, all_terms: list[str],
              query_term_count: int, top_k: int) -> list[SearchResult]:
        # Determine N and avgdl
        if self._storage:
            stats = self._storage.stats()
            N = stats.doc_count
            avgdl = stats.avg_text_len if stats.avg_text_len > 0 else 1.0
        elif self.conn:
            N = self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            avgdl = self.conn.execute("SELECT AVG(text_len) FROM docs").fetchone()[0] or 1.0
        else:
            return []

        if N == 0:
            return []
        now = time.time()
        query_type = classify(raw_query)
        query_lang = detect_lang(raw_query)

        # Get term IDs
        term_rows = []
        for t in set(all_terms):
            if self._storage:
                tid = self._storage.get_term_id(t)
            else:
                row = self.conn.execute("SELECT id FROM terms WHERE term=?", (t,)).fetchone()
                tid = row["id"] if row else None
            if tid is not None:
                term_rows.append((t, tid))

        if not term_rows:
            return []

        qtc = max(query_term_count, 1)
        doc_scores: dict[int, float] = {}

        for term, tid in term_rows:
            if self._storage:
                df = self._storage.term_df(tid)
                postings = self._storage.query_postings(tid)
            else:
                df = self.conn.execute(
                    "SELECT COUNT(*) FROM postings WHERE term_id=?", (tid,)
                ).fetchone()[0]
                rows = self.conn.execute(
                    """SELECT p.doc_id, p.freq, p.in_title, p.in_heading,
                              d.url, d.title, d.snippet,
                              d.text_len, d.incoming_links, d.crawled_at
                       FROM postings p JOIN docs d ON p.doc_id = d.id
                       WHERE p.term_id = ?""",
                    (tid,),
                ).fetchall()
                postings = [PostingRow(
                    doc_id=r["doc_id"], freq=r["freq"], in_title=r["in_title"],
                    in_heading=r["in_heading"], url=r["url"], title=r["title"],
                    snippet=r["snippet"], text_len=r["text_len"],
                    incoming_links=r["incoming_links"], crawled_at=r["crawled_at"],
                ) for r in rows]

            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

            for p in postings:
                tf = p.freq
                dl = p.text_len or 1
                domain = urlparse(p.url).netloc
                bm25 = idf * ((tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / avgdl)))
                title_boost = 1.0 + min(1.0, p.in_title / qtc)
                heading_boost = 1.0 + min(1.0, p.in_heading / qtc) * 0.5
                auth = domain_authority(domain, p.incoming_links, p.incoming_links)
                age_days = (now - p.crawled_at) / 86400
                half_life = NEWS_FRESHNESS_HALF_DAYS if domain_tier(domain) == 2 else FRESHNESS_HALF_DAYS
                freshness = freshness_boost(age_days, half_life)
                depth_penalty = url_depth_penalty(p.url)
                score = bm25 * title_boost * heading_boost * auth * freshness * depth_penalty
                doc_scores[p.doc_id] = doc_scores.get(p.doc_id, 0.0) + score

        sorted_docs = sorted(doc_scores.items(), key=lambda x: -x[1])[:top_k * 3]
        results = []

        for doc_id, score in sorted_docs:
            if self._storage:
                doc = self._storage.get_doc(doc_id)
            else:
                doc_row = self.conn.execute(
                    "SELECT url, title, snippet FROM docs WHERE id=?", (doc_id,)
                ).fetchone()
                doc = type('Doc', (), dict(doc_row))() if doc_row else None

            if doc is None:
                continue
            url = doc.url
            title = doc.title or ""
            snippet = doc.snippet or ""
            doc_lang = detect_lang(title + " " + snippet[:200])
            eb = entity_boost(raw_query, title, snippet)
            lb = lang_boost(doc_lang, query_lang)
            tsb = title_start_boost(title, raw_query)
            results.append(SearchResult(
                url=url, title=title,
                score=score * eb * lb * tsb,
                snippet=make_snippet(snippet, raw_query),
            ))

        results.sort(key=lambda r: -r.score)

        if query_type == "news" and len(results) >= 3:
            results = diversify(results)

        return results[:top_k]
