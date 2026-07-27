from __future__ import annotations

import time
import logging
from collections import deque

from brium.base.config import Config
from brium.base.types import Page
from brium.fetch.http_client import HttpClient
from brium.crawl.parser import parse_html

log = logging.getLogger(__name__)


class Crawler:
    def __init__(self, config: Config, on_page=None):
        self.config = config
        self.on_page = on_page
        self.seen: set[str] = set()
        self.queue: deque[tuple[str, int]] = deque()
        self.client = HttpClient(config)

    def seed(self, urls: list[str]):
        for u in urls:
            if u not in self.seen:
                self.seen.add(u)
                self.queue.append((u, 0))

    def crawl(self, max_pages: int | None = None) -> int:
        limit = max_pages or self.config.max_pages
        count = 0
        while self.queue and count < limit:
            url, depth = self.queue.popleft()
            if depth > self.config.max_depth:
                continue
            try:
                resp = self.client.get(url)
                if resp is None:
                    continue
                if "text/html" not in (resp.headers.get("content-type", "")):
                    continue
                page = parse_html(url, resp.text)
                if page is None:
                    continue
                if self.on_page:
                    self.on_page(page)
                count += 1
                if depth < self.config.max_depth:
                    self._enqueue_links(page.links, depth + 1)
            except Exception:
                log.exception("crawl error: %s", url)
            time.sleep(self.config.request_delay)
        return count

    def _enqueue_links(self, links: list[str], depth: int):
        for link in links:
            if link not in self.seen:
                self.seen.add(link)
                self.queue.append((link, depth))

    def close(self):
        self.client.close()
