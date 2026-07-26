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

    # Full query — exact article match on major wikis
    for lang in ("en", "tr", "simple"):
        for url in _wiki_api(query, lang, 3):
            if url not in seen:
                seen.add(url)
                seeds.append(url)

    # Individual terms — limit to 1 result per term per lang, Turkish first
    terms = [t for t in query.lower().split() if len(t) > 2]
    for term in terms[:3]:
        for lang in ("tr", "en"):
            for url in _wiki_api(term, lang, 1):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # Fallback direct URL guess if still nothing
    if not seeds:
        for lang in ("en", "tr"):
            slug = query.strip().lower().replace(" ", "_")
            url = f"https://{lang}.wikipedia.org/wiki/{quote(slug, safe='')}"
            if url not in seen:
                seen.add(url)
                seeds.append(url)

    return seeds[:15]
