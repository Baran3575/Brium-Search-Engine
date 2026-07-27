from __future__ import annotations

import os
import tempfile

from brium.index.tokenizer import tokenize, bigrams
from brium.index.engine import Indexer
from brium.index.storage import Storage
from brium.base.types import Page


def test_tokenize():
    assert tokenize("Hello World!") == ["hello", "world"]
    assert tokenize("") == []
    assert tokenize("foo-bar") == ["foo", "bar"]
    assert tokenize("Türkiye'nin") == ["türkiye", "nin"]


def test_bigrams():
    assert bigrams(["a", "b", "c"]) == ["a_b", "b_c"]
    assert bigrams(["hello"]) == []
    assert bigrams([]) == []


def test_storage_init():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        s = Storage(db)
        tables = s.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r["name"] for r in tables}
        assert "docs" in names
        assert "terms" in names
        assert "postings" in names
        s.close()


def test_indexer_add_page():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        idx = Indexer(db)
        page = Page(
            url="http://example.com/test",
            html="<html><body>hello world</body></html>",
            text="hello world",
            title="Test Page",
        )
        doc_id = idx.add_page(page)
        assert doc_id > 0
        assert idx.doc_count() == 1
        idx.close()


def test_indexer_doc_count():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        idx = Indexer(db)
        idx.add_page(Page(url="http://a.com", html="", text="page one", title="A"))
        idx.add_page(Page(url="http://b.com", html="", text="page two", title="B"))
        idx.add_page(Page(url="http://c.com", html="", text="page three", title="C"))
        assert idx.doc_count() == 3
        idx.close()


def test_indexer_update():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        idx = Indexer(db)
        idx.add_page(Page(url="http://a.com", html="", text="hello world", title="A"))
        assert idx.doc_count() == 1
        # Update same URL
        idx.add_page(Page(url="http://a.com", html="", text="updated content", title="A Updated"))
        assert idx.doc_count() == 1
        idx.close()
