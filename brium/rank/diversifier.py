from __future__ import annotations

from urllib.parse import urlparse

from brium.base.types import SearchResult


def diversify(results: list[SearchResult]) -> list[SearchResult]:
    seen_domains: set[str] = set()
    diverse: list[SearchResult] = []
    deferred: list[SearchResult] = []
    for r in results:
        domain = urlparse(r.url).netloc
        if domain not in seen_domains:
            seen_domains.add(domain)
            diverse.append(r)
        else:
            deferred.append(r)
    return diverse + deferred
