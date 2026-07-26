from __future__ import annotations

import os
import tempfile
from brium.indexer.indexer import tokenize, Indexer
from brium.crawler.spider import Page


def test_tokenize():
    assert tokenize("Hello World!") == ["hello", "world"]
    assert tokenize("") == []
    assert tokenize("foo-bar") == ["foo", "bar"]


def test_indexer_add_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        idx = Indexer(db)
        idx.add_page(Page(url="http://a.com", html="", text="hello world", title="A"))
        idx.add_page(Page(url="http://b.com", html="", text="hello everyone", title="B"))
        assert idx.doc_count() == 2
        idx.close()

        from brium.search.engine import SearchEngine
        engine = SearchEngine(db)
        results = engine.search("hello")
        assert len(results) == 2
        results2 = engine.search("world")
        assert len(results2) == 1
        assert results2[0].url == "http://a.com"
        engine.close()
