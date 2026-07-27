from __future__ import annotations

import logging
from urllib.parse import quote

import requests

from brium.cache.engine import Cache

log = logging.getLogger(__name__)

WIKI_HEADERS = {
    "User-Agent": "Brium/0.1 (search engine; https://github.com/Baran3575/Brium-Search-Engine)"
}

_cache: Cache | None = None


def set_cache(cache: Cache | None):
    global _cache
    _cache = cache


def wiki_search(query: str, lang: str, limit: int = 5) -> list[str]:
    cache_key = f"search:{lang}:{query}"
    if _cache:
        cached = _cache.get("wikipedia", cache_key)
        if cached is not None:
            return cached.split("\n") if cached else []

    try:
        url = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=opensearch&search={quote(query)}&limit={limit}&namespace=0&format=json"
        )
        r = requests.get(url, headers=WIKI_HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        result = data[3] if len(data) > 3 else []
        if _cache:
            _cache.set("wikipedia", cache_key, "\n".join(result), ttl_seconds=3600)
        return result
    except Exception:
        return []


def wiki_related(query: str, lang: str = "tr") -> list[str]:
    cache_key = f"related:{lang}:{query}"
    if _cache:
        cached = _cache.get("wikipedia", cache_key)
        if cached is not None:
            return cached.split("\n") if cached else []

    try:
        url = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quote(query)}"
            f"&srlimit=5&format=json"
        )
        r = requests.get(url, headers=WIKI_HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("search", [])
        result = [f"https://{lang}.wikipedia.org/wiki/{quote(p['title'].replace(' ', '_'), safe='')}"
                  for p in pages]
        if _cache:
            _cache.set("wikipedia", cache_key, "\n".join(result), ttl_seconds=3600)
        return result
    except Exception:
        return []
