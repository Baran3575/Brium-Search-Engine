from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote, urlparse

import requests

from brium.algorithm.classifier import classify

log = logging.getLogger(__name__)

_WIKI_HEADERS = {
    "User-Agent": "Brium/0.1 (search engine; https://github.com/Baran3575/Brium-Search-Engine)"
}

TURKISH_NEWS_SITES = [
    "https://www.ntv.com.tr",
    "https://www.hurriyet.com.tr",
    "https://www.sozcu.com.tr",
    "https://www.cumhuriyet.com.tr",
    "https://www.milliyet.com.tr",
    "https://www.haberturk.com",
    "https://t24.com.tr",
    "https://trthaber.com",
]

NEWS_RSS = {
    "https://www.ntv.com.tr/gundem.rss",
    "https://www.hurriyet.com.tr/rss/anasayfa",
    "https://www.sozcu.com.tr/rss/gundem.xml",
    "https://www.cumhuriyet.com.tr/rss/son-dakika.xml",
    "https://www.trthaber.com/feed.rss",
    "https://www.bbc.com/turkce/index.xml",
}

DEFAULT_HOMEPAGES = [
    "https://en.wikipedia.org",
    "https://tr.wikipedia.org",
    "https://www.bbc.com/news",
    "https://www.aljazeera.com",
    *TURKISH_NEWS_SITES,
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


def _news_search_urls(query: str) -> list[str]:
    q = quote(query)
    urls = []
    for site in TURKISH_NEWS_SITES:
        parsed = urlparse(site)
        domain = parsed.netloc
        urls.append(f"{site}/arama?q={q}")
        urls.append(f"https://www.google.com/search?q=site:{domain}+{q}&tbm=nws")
    return urls


def _parse_rss(url: str) -> list[str]:
    try:
        r = requests.get(url, headers=_WIKI_HEADERS, timeout=8)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        links = []
        for item in root.iter("item"):
            link = item.findtext("link", "")
            if link:
                links.append(link)
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            link = entry.findtext("{http://www.w3.org/2005/Atom}link")
            if link:
                links.append(link)
        return links[:10]
    except Exception:
        return []


def _news_seeds(query: str) -> list[str]:
    seen: set[str] = set()
    seeds: list[str] = []

    # RSS feeds (latest news from all sources)
    for rss_url in NEWS_RSS:
        for link in _parse_rss(rss_url):
            if link not in seen:
                seen.add(link)
                seeds.append(link)

    if not seeds:
        seeds.extend(_news_search_urls(query))

    return seeds[:10]


def for_query(query: str) -> list[str]:
    seen: set[str] = set()
    seeds: list[str] = []
    query_type = classify(query)

    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        words = query.lower().split()

    # 1. Wikipedia: first bigram (named entity) — always try
    if len(words) >= 2:
        phrase = f"{words[0]} {words[1]}"
        for lang in ("tr", "en"):
            for url in _wiki_api(phrase, lang, 5):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # 2. Wikipedia: full query
    for lang in ("tr", "en", "simple"):
        for url in _wiki_api(query, lang, 5):
            if url not in seen:
                seen.add(url)
                seeds.append(url)

    # 3. News seeds (always, but more for news-type queries)
    news_urls = _news_seeds(query)
    for url in news_urls:
        if url not in seen:
            seen.add(url)
            seeds.append(url)
        if query_type == "news" and len(seeds) < 20:
            pass  # keep adding

    # 4. Wikipedia: remaining bigrams
    for i in range(1, len(words) - 1):
        if len(seeds) >= 15:
            break
        phrase = f"{words[i]} {words[i+1]}"
        for lang in ("tr", "en"):
            for url in _wiki_api(phrase, lang, 2):
                if url not in seen:
                    seen.add(url)
                    seeds.append(url)

    # 5. Individual term fallback
    if not seeds:
        for term in words[:3]:
            for lang in ("tr", "en"):
                for url in _wiki_api(term, lang, 1):
                    if url not in seen:
                        seen.add(url)
                        seeds.append(url)

    return seeds[:20]
