from __future__ import annotations

import re
import time
import logging
from collections import deque
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

from brium.config import Config

log = logging.getLogger(__name__)


@dataclass
class Page:
    url: str
    html: str
    text: str
    title: str
    links: list[str] = field(default_factory=list)


class Crawler:
    def __init__(self, config: Config, on_page=None):
        self.config = config
        self.on_page = on_page  # callback(page: Page) -> None
        self.seen: set[str] = set()
        self.queue: deque[tuple[str, int]] = deque()  # (url, depth)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

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
                page = self._fetch(url)
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

    def _fetch(self, url: str) -> Page | None:
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException:
            return None
        if "text/html" not in (resp.headers.get("content-type", "")):
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        title = soup.title.string.strip() if soup.title else ""
        text = soup.get_text(separator=" ", strip=True)
        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                links.append(href)
        return Page(url=url, html=resp.text, text=text, title=title, links=links)

    def _enqueue_links(self, links: list[str], depth: int):
        for link in links:
            if link not in self.seen:
                self.seen.add(link)
                self.queue.append((link, depth))

    def close(self):
        self.session.close()
