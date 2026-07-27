from __future__ import annotations

import logging

from brium.base.constants import NEWS_RSS
from brium.discovery.wikipedia import wiki_search, wiki_related
from brium.discovery.rss import parse_rss
from brium.rank.classifier import classify

log = logging.getLogger(__name__)


def _news_seeds() -> list[str]:
    seen: set[str] = set()
    seeds: list[str] = []
    for rss_url in NEWS_RSS:
        for link in parse_rss(rss_url):
            if link not in seen:
                seen.add(link)
                seeds.append(link)
    return seeds[:15]


def for_query(query: str) -> list[str]:
    seen: set[str] = set()
    seeds: list[str] = []

    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        words = query.lower().split()

    # 1. First bigram — named entity
    if len(words) >= 2:
        phrase = f"{words[0]} {words[1]}"
        for lang in ("tr", "en"):
            for url in wiki_search(phrase, lang, 5):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # 2. Full query on Wikipedia
    for lang in ("tr", "en", "simple"):
        for url in wiki_search(query, lang, 5):
            if url not in seen:
                seen.add(url)
                seeds.append(url)

    # 3. Broader Wikipedia search results
    for lang in ("tr", "en"):
        for url in wiki_related(query, lang):
            if url not in seen:
                seen.add(url)
                seeds.append(url)

    # 4. RSS news
    for url in _news_seeds():
        if url not in seen:
            seen.add(url)
            seeds.append(url)

    # 5. Remaining bigrams
    for i in range(1, len(words) - 1):
        if len(seeds) >= 20:
            break
        phrase = f"{words[i]} {words[i+1]}"
        for lang in ("tr", "en"):
            for url in wiki_search(phrase, lang, 2):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # 6. Fallback individual terms
    if not seeds:
        for term in words[:3]:
            for lang in ("tr", "en"):
                for url in wiki_search(term, lang, 1):
                    if url not in seen:
                        seen.add(url)
                        seeds.append(url)

    return seeds[:25]
