from __future__ import annotations

import re
from urllib.parse import urlparse

NEWS_DOMAINS: set[str] = {
    "ntv.com.tr", "hurriyet.com.tr", "sozcu.com.tr", "cumhuriyet.com.tr",
    "milliyet.com.tr", "haberturk.com", "t24.com.tr", "dw.com",
    "bbc.com", "bbc.co.uk", "aljazeera.com", "reuters.com",
    "apnews.com", "cnn.com", "cnnturk.com", "trthaber.com",
    "aa.com.tr", "dunya.com", "sabah.com.tr", "takvim.com.tr",
    "ensonhaber.com", "mynet.com", "haberler.com", "memurlar.net",
}

WIKI_DOMAINS: set[str] = {
    "wikipedia.org",
}

NEWS_TRIGGERS: set[str] = {
    "haber", "news", "son dakika", "breaking", "gündem",
    "olay", "oluyor", "açıklama", "canlı", "yayın",
}


def classify(query: str) -> str:
    q = query.lower()
    # News query = contains news trigger words
    for trigger in NEWS_TRIGGERS:
        if trigger in q:
            return "news"
    # Entity query = first bigram capitalized in natural language
    words = q.split()
    if len(words) >= 2 and words[0][0].isupper() if any(c.isupper() for c in query) else False:
        return "entity"
    # Short queries with proper nouns
    if len(words) <= 2 and any(w[0].isupper() for w in words if w):
        return "entity"
    return "general"


def domain_tier(domain: str) -> int:
    domain = domain.lower()
    for d in NEWS_DOMAINS:
        if domain == d or domain.endswith("." + d):
            return 2  # news
    for d in WIKI_DOMAINS:
        if domain == d or domain.endswith("." + d):
            return 1  # knowledge
    return 0  # general


def is_news_domain(domain: str) -> bool:
    return domain_tier(domain) == 2


def domain_authority(domain: str, doc_count: int, incoming_links: int) -> float:
    tier = domain_tier(domain)
    base = 1.0
    if tier == 2:
        base = 1.3  # news sites trusted
    elif tier == 1:
        base = 1.2  # wikipedia trusted
    link_boost = 1.0 + min(0.5, incoming_links * 0.02)
    return base * link_boost
