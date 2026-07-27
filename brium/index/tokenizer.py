from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9çğıöşü]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
