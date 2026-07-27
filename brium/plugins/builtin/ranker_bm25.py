from __future__ import annotations

import math
import time
from urllib.parse import urlparse

from brium.plugins.base import BaseRanker, RankerResult
from brium.plugins.registry import register_ranker
from brium.index.tokenizer import tokenize, bigrams
from brium.rank.classifier import (
    classify, detect_lang, is_stop_word,
    domain_tier, domain_authority, url_depth_penalty,
)
from brium.rank.booster import entity_boost, freshness_boost, lang_boost, title_start_boost, make_snippet
from brium.rank.diversifier import diversify


@register_ranker
class BM25Ranker(BaseRanker):
    name = "bm25"
    _k1 = 1.2
    _b = 0.4
    _news_freshness_half = 7.0
    _freshness_half = 90.0

    def rank(self, raw_query: str, conn, top_k: int = 20) -> list[RankerResult]:
        terms = tokenize(raw_query)
        terms = [t for t in terms if not is_stop_word(t)]
        if not terms:
            return []
        bgs = bigrams(terms)
        all_terms = list(set(terms + bgs))
        return self._score(raw_query, all_terms, len(terms), conn, top_k)

    def _score(self, raw_query: str, all_terms: list[str],
               query_term_count: int, conn, top_k: int) -> list[RankerResult]:
        N = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
        if N == 0:
            return []
        avgdl = conn.execute("SELECT AVG(text_len) FROM docs").fetchone()[0] or 1.0
        now = time.time()
        query_type = classify(raw_query)
        query_lang = detect_lang(raw_query)

        term_rows = []
        for t in set(all_terms):
            row = conn.execute("SELECT id FROM terms WHERE term = ?", (t,)).fetchone()
            if row:
                term_rows.append((t, row["id"]))

        if not term_rows:
            return []

        qtc = max(query_term_count, 1)
        doc_scores: dict[int, float] = {}

        for term, tid in term_rows:
            df = conn.execute(
                "SELECT COUNT(*) FROM postings WHERE term_id = ?", (tid,)
            ).fetchone()[0]
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            rows = conn.execute(
                """SELECT p.doc_id, p.freq, p.in_title, p.in_heading,
                          d.url, d.title, d.snippet,
                          d.text_len, d.incoming_links, d.crawled_at
                   FROM postings p JOIN docs d ON p.doc_id = d.id
                   WHERE p.term_id = ?""",
                (tid,),
            ).fetchall()
            for r in rows:
                tf = r["freq"]
                dl = r["text_len"]
                domain = urlparse(r["url"]).netloc
                bm25 = idf * ((tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * dl / avgdl)))
                title_boost = 1.0 + min(1.0, r["in_title"] / qtc)
                heading_boost = 1.0 + min(1.0, r["in_heading"] / qtc) * 0.5
                auth = domain_authority(domain, r["incoming_links"], r["incoming_links"])
                age_days = (now - r["crawled_at"]) / 86400
                half_life = self._news_freshness_half if domain_tier(domain) == 2 else self._freshness_half
                freshness = freshness_boost(age_days, half_life)
                depth_penalty = url_depth_penalty(r["url"])
                score = bm25 * title_boost * heading_boost * auth * freshness * depth_penalty
                doc_scores[r["doc_id"]] = doc_scores.get(r["doc_id"], 0.0) + score

        sorted_docs = sorted(doc_scores.items(), key=lambda x: -x[1])[:top_k * 3]
        results = []
        for doc_id, score in sorted_docs:
            doc = conn.execute(
                "SELECT url, title, snippet FROM docs WHERE id = ?", (doc_id,)
            ).fetchone()
            url = doc["url"]
            title = doc["title"] or ""
            snippet = doc["snippet"] or ""
            doc_lang = detect_lang(title + " " + snippet[:200])
            eb = entity_boost(raw_query, title, snippet)
            lb = lang_boost(doc_lang, query_lang)
            tsb = title_start_boost(title, raw_query)
            results.append(RankerResult(
                url=url, title=title,
                score=score * eb * lb * tsb,
                snippet=make_snippet(snippet, raw_query),
            ))

        results.sort(key=lambda r: -r.score)
        if query_type == "news" and len(results) >= 3:
            results = diversify(results)  # type: ignore[arg-type]
        return results[:top_k]
