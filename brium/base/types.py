from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Page:
    url: str
    html: str
    text: str
    title: str
    headings: list[str] = field(default_factory=list)
    snippet: str = ""
    links: list[str] = field(default_factory=list)


@dataclass
class SearchResult:
    url: str
    title: str
    score: float
    snippet: str = ""
