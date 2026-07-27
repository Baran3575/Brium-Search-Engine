from __future__ import annotations

import logging
from urllib.parse import quote

import requests

from brium.plugins.base import BaseSource
from brium.plugins.registry import register_source
from brium.cache.engine import Cache

log = logging.getLogger(__name__)

_WIKI_HEADERS = {
    "User-Agent": "Brium/0.1 (search engine; https://github.com/Baran3575/Brium-Search-Engine)"
}


@register_source
class WikipediaSource(BaseSource):
    name = "wikipedia"

    def __init__(self, cache: Cache | None = None):
        self.cache = cache

    def discover(self, query: str) -> list[str]:
        if self.cache:
            cached = self.cache.get("wikipedia", query)
            if cached is not None:
                return cached.split("\n")

        results: list[str] = []
        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            words = query.lower().split()

        # First bigram
        if len(words) >= 2:
            phrase = f"{words[0]} {words[1]}"
            for lang in ("tr", "en"):
                results.extend(self._search(phrase, lang, 5))

        # Full query
        for lang in ("tr", "en", "simple"):
            results.extend(self._search(query, lang, 5))

        # Related search
        for lang in ("tr", "en"):
            results.extend(self._related(query, lang))

        # Remaining bigrams
        for i in range(1, len(words) - 1):
            if len(results) >= 20:
                break
            phrase = f"{words[i]} {words[i+1]}"
            for lang in ("tr", "en"):
                results.extend(self._search(phrase, lang, 2))

        # Fallback terms
        if not results:
            for term in words[:3]:
                for lang in ("tr", "en"):
                    results.extend(self._search(term, lang, 1))

        if self.cache:
            self.cache.set("wikipedia", query, "\n".join(results), ttl_seconds=3600)

        return results[:25]

    def _search(self, q: str, lang: str, limit: int) -> list[str]:
        try:
            url = (
                f"https://{lang}.wikipedia.org/w/api.php"
                f"?action=opensearch&search={quote(q)}&limit={limit}&namespace=0&format=json"
            )
            r = requests.get(url, headers=_WIKI_HEADERS, timeout=5)
            r.raise_for_status()
            data = r.json()
            return data[3] if len(data) > 3 else []
        except Exception:
            return []

    def _related(self, q: str, lang: str) -> list[str]:
        try:
            url = (
                f"https://{lang}.wikipedia.org/w/api.php"
                f"?action=query&list=search&srsearch={quote(q)}"
                f"&srlimit=5&format=json"
            )
            r = requests.get(url, headers=_WIKI_HEADERS, timeout=5)
            r.raise_for_status()
            data = r.json()
            pages = data.get("query", {}).get("search", [])
            return [f"https://{lang}.wikipedia.org/wiki/{quote(p['title'].replace(' ', '_'), safe='')}"
                    for p in pages]
        except Exception:
            return []
