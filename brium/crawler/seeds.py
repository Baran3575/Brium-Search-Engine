from __future__ import annotations

import logging
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

_WIKI_HEADERS = {
    "User-Agent": "Brium/0.1 (search engine; https://github.com/Baran3575/Brium-Search-Engine)"
}

DEFAULT_HOMEPAGES = [
    "https://en.wikipedia.org",
    "https://tr.wikipedia.org",
    "https://www.bbc.com/news",
    "https://www.aljazeera.com",
    "https://www.ntv.com.tr",
    "https://www.hurriyet.com.tr",
]


def _wiki_api(query: str, lang: str, limit: int = 5) -> list[str]:
    try:
        url = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=opensearch&search={quote(query)}&limit={limit}&namespace=0&format=json"
        )
        r = requests.get(url, headers=_WIKI_HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        return data[3] if len(data) > 3 else []
    except Exception:
        return []


def for_query(query: str) -> list[str]:
    seen: set[str] = set()
    seeds: list[str] = []

    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        words = query.lower().split()

    # 1. First bigram (most specific — usually the named entity)
    if len(words) >= 2:
        phrase = f"{words[0]} {words[1]}"
        for lang in ("tr", "en"):
            for url in _wiki_api(phrase, lang, 5):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # 2. Full query on Turkish + English Wikipedia
    for lang in ("tr", "en", "simple"):
        for url in _wiki_api(query, lang, 5):
            if url not in seen:
                seen.add(url)
                seeds.append(url)

    # 3. Remaining bigrams (ordered, not random)
    for i in range(1, len(words) - 1):
        if len(seeds) >= 15:
            break
        phrase = f"{words[i]} {words[i+1]}"
        for lang in ("tr", "en"):
            for url in _wiki_api(phrase, lang, 2):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # 4. Individual terms as fallback
    if not seeds:
        for term in words[:3]:
            for lang in ("tr", "en"):
                for url in _wiki_api(term, lang, 1):
                    if url not in seen:
                        seen.add(url)
                        seeds.append(url)

    return seeds[:15]
