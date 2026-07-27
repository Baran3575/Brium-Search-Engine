from __future__ import annotations

import logging

from brium.base.types import Page
from brium.storage.interface import StorageBackend
from brium.storage.sqlite_backend import SQLiteBackend
from brium.index.tokenizer import tokenize, bigrams

log = logging.getLogger(__name__)


class Indexer:
    def __init__(self, db_path: str | None = None,
                 storage: StorageBackend | None = None):
        if storage is not None:
            self.store = storage
        elif db_path is not None:
            self.store = SQLiteBackend(db_path)
        else:
            raise ValueError("either db_path or storage must be provided")

    @property
    def conn(self):
        if isinstance(self.store, SQLiteBackend):
            return self.store.conn
        return None

    def add_page(self, page: Page) -> int:
        toks = tokenize(page.text)
        title_toks = tokenize(page.title)
        heading_toks = tokenize(" ".join(page.headings))
        return self.store.add_page(
            url=page.url,
            title=page.title,
            snippet=page.snippet,
            headings=" | ".join(page.headings),
            text_len=len(toks),
            tokens=toks,
            title_tokens=title_toks,
            heading_tokens=heading_toks,
            bigram_tokens=bigrams(toks),
            title_bigrams=bigrams(title_toks),
        )

    def doc_count(self) -> int:
        return self.store.doc_count()

    def total_terms(self) -> int:
        return self.store.total_terms()

    def close(self):
        self.store.close()
