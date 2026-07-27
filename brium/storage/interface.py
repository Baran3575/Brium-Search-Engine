from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchDoc:
    id: int
    url: str
    title: str
    snippet: str
    headings: str
    text_len: int
    incoming_links: int
    crawled_at: float


@dataclass
class IndexStats:
    doc_count: int
    avg_text_len: float
    total_terms: int


@dataclass
class PostingRow:
    doc_id: int
    freq: int
    in_title: int
    in_heading: int
    url: str
    title: str
    snippet: str
    text_len: int
    incoming_links: int
    crawled_at: float


class StorageBackend(ABC):
    @abstractmethod
    def add_page(self, url: str, title: str, snippet: str, headings: str,
                 text_len: int, tokens: list[str], title_tokens: list[str],
                 heading_tokens: list[str], bigram_tokens: list[str],
                 title_bigrams: list[str]) -> int:
        ...

    @abstractmethod
    def doc_count(self) -> int:
        ...

    @abstractmethod
    def total_terms(self) -> int:
        ...

    @abstractmethod
    def stats(self) -> IndexStats:
        ...

    @abstractmethod
    def get_doc(self, doc_id: int) -> SearchDoc | None:
        ...

    @abstractmethod
    def get_doc_by_url(self, url: str) -> SearchDoc | None:
        ...

    @abstractmethod
    def get_term_id(self, term: str) -> int | None:
        ...

    @abstractmethod
    def term_df(self, term_id: int) -> int:
        ...

    @abstractmethod
    def query_postings(self, term_id: int) -> list[PostingRow]:
        ...

    @abstractmethod
    def close(self):
        ...
