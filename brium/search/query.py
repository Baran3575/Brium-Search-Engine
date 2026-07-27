from __future__ import annotations

import re

from brium.index.tokenizer import tokenize
from brium.rank.classifier import is_stop_word

_QUERY_CLEAN_RE = re.compile(r"[^\w\s]")


def clean(raw: str) -> str:
    return " ".join(_QUERY_CLEAN_RE.sub(" ", raw).split())


def meaningful_terms(raw: str) -> list[str]:
    return [t for t in tokenize(raw) if not is_stop_word(t) and len(t) > 1]
