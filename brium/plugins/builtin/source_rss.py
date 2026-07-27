from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import requests

from brium.plugins.base import BaseSource
from brium.plugins.registry import register_source
from brium.base.constants import NEWS_RSS
from brium.cache.engine import Cache

log = logging.getLogger(__name__)


@register_source
class RSSSource(BaseSource):
    name = "rss"

    def __init__(self, cache: Cache | None = None):
        self.cache = cache

    def discover(self, query: str = "") -> list[str]:
        cache_key = "all" if not query else f"q:{query}"
        if self.cache:
            cached = self.cache.get("rss", cache_key)
            if cached is not None:
                return cached.split("\n")

        seen: set[str] = set()
        seeds: list[str] = []
        for rss_url in NEWS_RSS:
            for link in self._parse(rss_url):
                if link not in seen:
                    seen.add(link)
                    seeds.append(link)

        if self.cache:
            self.cache.set("rss", cache_key, "\n".join(seeds), ttl_seconds=600)

        return seeds[:15]

    def _parse(self, url: str) -> list[str]:
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
            return links[:15]
        except Exception:
            return []
