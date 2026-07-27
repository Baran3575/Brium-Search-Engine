from __future__ import annotations

from brium.index.tokenizer import tokenize


def make_snippet(text: str, query: str) -> str:
    if not text or not query:
        return (text or "")[:200]
    qlow = query.lower()
    idx = text.lower().find(qlow)
    if idx < 0:
        return text[:200]
    start = max(0, idx - 60)
    end = min(len(text), idx + len(qlow) + 120)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


def freshness_boost(age_days: float, half_life: float) -> float:
    return 1.0 / (1.0 + age_days / half_life)


def entity_boost(raw_query: str, title: str, snippet: str) -> float:
    qlow = raw_query.lower()
    tlow = title.lower()
    first_bg = " ".join(qlow.split()[:2])
    phrase_in_title = qlow in tlow
    entity_in_title = first_bg in tlow
    phrase_in_snippet = qlow in snippet.lower()
    if phrase_in_title:
        return 3.0
    if entity_in_title:
        return 2.5
    if phrase_in_snippet:
        return 2.0
    return 1.0


def lang_boost(doc_lang: str, query_lang: str) -> float:
    return 1.3 if doc_lang == query_lang else 1.0


def title_start_boost(title: str, raw_query: str) -> float:
    if not title or not raw_query:
        return 1.0
    first_word = tokenize(title.split()[0]) if title.split() else []
    if not first_word:
        return 1.0
    query_words = tokenize(raw_query)
    return 1.2 if first_word[0] in query_words else 1.0
