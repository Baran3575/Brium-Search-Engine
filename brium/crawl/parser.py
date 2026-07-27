from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from brium.base.types import Page


def parse_html(url: str, html: str) -> Page | None:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title else ""
    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        txt = h.get_text(strip=True)
        if txt:
            headings.append(txt)
    text = soup.get_text(separator=" ", strip=True)
    snippet = " ".join(text.split()[:200])
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        parsed = urlparse(href)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            links.append(href)
    return Page(
        url=url, html=html, text=text, title=title,
        headings=headings, snippet=snippet, links=links,
    )
