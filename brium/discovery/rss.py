from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import requests

from brium.cache.engine import Cache

log = logging.getLogger(__name__)

_cache: Cache | None = None


def set_cache(cache: Cache | None):
    global _cache
    _cache = cache


def parse_rss(url: str) -> list[str]:
    if _cache:
        cached = _cache.get("rss", url)
        if cached is not None:
            return cached.split("\n") if cached else []

    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        links: list[str] = []
        for item in root.iter("item"):
            link = item.findtext("link", "")
            if link:
                links.append(link)
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            for link_el in entry.iter("{http://www.w3.org/2005/Atom}link"):
                href = link_el.get("href", "")
                if href:
                    links.append(href)
        result = links[:15]
        if _cache:
            _cache.set("rss", url, "\n".join(result), ttl_seconds=600)
        return result
    except Exception:
        return []
