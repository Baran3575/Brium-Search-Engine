from __future__ import annotations

from urllib.parse import urlparse

from brium.base.constants import (
    NEWS_DOMAINS, WIKI_DOMAINS, NEWS_TRIGGERS,
    TURKISH_CHARS, TURKISH_LEXICON, TR_STOP_WORDS, EN_STOP_WORDS,
)


def detect_lang(text: str) -> str:
    text_lower = text.lower()
    tr_char_count = sum(1 for c in text_lower if c in TURKISH_CHARS)
    if tr_char_count >= 2:
        return "tr"
    words = set(text_lower.split())
    tr_lex_overlap = len(words & TURKISH_LEXICON)
    if tr_lex_overlap >= 1:
        return "tr"
    return "en"


def is_stop_word(word: str) -> bool:
    return word.lower() in TR_STOP_WORDS or word.lower() in EN_STOP_WORDS


def classify(query: str) -> str:
    q = query.lower()
    for trigger in NEWS_TRIGGERS:
        if trigger in q:
            return "news"
    words = q.split()
    if len(words) <= 3 and any(c.isupper() for c in query if c.isalpha()):
        return "entity"
    return "general"


def domain_tier(domain: str) -> int:
    domain = domain.lower()
    for d in NEWS_DOMAINS:
        if domain == d or domain.endswith("." + d):
            return 2
    for d in WIKI_DOMAINS:
        if domain == d or domain.endswith("." + d):
            return 1
    return 0


def domain_authority(domain: str, _: int = 0, incoming_links: int = 0) -> float:
    tier = domain_tier(domain)
    base = {2: 1.3, 1: 1.2}.get(tier, 1.0)
    link_boost = 1.0 + min(0.5, incoming_links * 0.02)
    return base * link_boost


def url_depth_penalty(url: str) -> float:
    path = urlparse(url).path.strip("/")
    if not path:
        return 1.0
    depth = len(path.split("/"))
    if depth <= 1:
        return 1.0
    return max(0.7, 1.0 - (depth - 1) * 0.03)
