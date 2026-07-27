from __future__ import annotations

import os
import tempfile

from brium.storage.sqlite_backend import SQLiteBackend
from brium.index.tokenizer import tokenize, bigrams


def _make_tokens(text: str):
    toks = tokenize(text)
    return toks, bigrams(toks)


def test_sqlite_add_and_count():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        s = SQLiteBackend(db)
        toks, bgs = _make_tokens("hello world")
        doc_id = s.add_page(
            url="http://a.com", title="A", snippet="hello world",
            headings="", text_len=len(toks),
            tokens=toks, title_tokens=tokenize("A"),
            heading_tokens=[], bigram_tokens=bgs, title_bigrams=[],
        )
        assert doc_id > 0
        assert s.doc_count() == 1
        s.close()


def test_sqlite_get_doc():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        s = SQLiteBackend(db)
        toks, bgs = _make_tokens("hello world example")
        s.add_page(url="http://a.com", title="Test Title", snippet="hello world example",
                   headings="h1 | h2", text_len=len(toks),
                   tokens=toks, title_tokens=tokenize("Test Title"),
                   heading_tokens=tokenize("h1 h2"), bigram_tokens=bgs,
                   title_bigrams=bigrams(tokenize("Test Title")),
        )
        doc = s.get_doc_by_url("http://a.com")
        assert doc is not None
        assert doc.title == "Test Title"
        assert doc.text_len == 3
        s.close()


def test_sqlite_term_id():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        s = SQLiteBackend(db)
        toks, bgs = _make_tokens("hello world")
        s.add_page(url="http://a.com", title="A", snippet="hello world",
                   headings="", text_len=len(toks),
                   tokens=toks, title_tokens=tokenize("A"),
                   heading_tokens=[], bigram_tokens=bgs, title_bigrams=[],
        )
        tid = s.get_term_id("hello")
        assert tid is not None
        assert tid > 0
        assert s.get_term_id("nonexistent") is None
        s.close()


def test_sqlite_stats():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        s = SQLiteBackend(db)
        stats = s.stats()
        assert stats.doc_count == 0
        toks, bgs = _make_tokens("hello world")
        s.add_page(url="http://a.com", title="A", snippet="hello world",
                   headings="", text_len=len(toks),
                   tokens=toks, title_tokens=tokenize("A"),
                   heading_tokens=[], bigram_tokens=bgs, title_bigrams=[],
        )
        stats2 = s.stats()
        assert stats2.doc_count == 1
        assert stats2.total_terms == 2
        s.close()


def test_sqlite_postings():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        s = SQLiteBackend(db)
        toks, bgs = _make_tokens("hello world hello")
        s.add_page(url="http://a.com", title="Hello Page", snippet="hello world hello",
                   headings="", text_len=len(toks),
                   tokens=toks, title_tokens=tokenize("Hello Page"),
                   heading_tokens=[], bigram_tokens=bgs, title_bigrams=[],
        )
        tid = s.get_term_id("hello")
        postings = s.query_postings(tid)
        assert len(postings) == 1
        assert postings[0].freq == 2
        assert postings[0].in_title >= 1
        s.close()
