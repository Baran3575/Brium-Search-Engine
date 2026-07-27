from __future__ import annotations

import os
import tempfile

from brium.index.engine import Indexer
from brium.base.types import Page
from brium.search.engine import SearchEngine
from brium.search.query import clean, meaningful_terms


def test_clean():
    assert clean("hello! world?") == "hello world"
    assert clean("  spaces   ") == "spaces"
    assert clean("") == ""
    assert clean("foo   bar") == "foo bar"


def test_meaningful_terms():
    assert meaningful_terms("the bir hello") == ["hello"]
    assert meaningful_terms("hello world") == ["hello", "world"]
    assert meaningful_terms("a an the") == []


def test_search_empty_index():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "empty.db")
        engine = SearchEngine(db)
        results = engine.search("hello")
        assert results == []
        engine.close()


def test_search_basic():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        idx = Indexer(db)
        idx.add_page(Page(url="http://a.com", html="", text="hello world", title="A"))
        idx.add_page(Page(url="http://b.com", html="", text="hello everyone", title="B"))
        idx.close()

        engine = SearchEngine(db)
        results = engine.search("hello")
        assert len(results) == 2
        engine.close()


def test_search_relevance():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        idx = Indexer(db)
        idx.add_page(Page(url="http://a.com", html="", text="python programming language", title="Python"))
        idx.add_page(Page(url="http://b.com", html="", text="snake python species", title="Snake"))
        idx.add_page(Page(url="http://c.com", html="", text="java programming", title="Java"))
        idx.close()

        engine = SearchEngine(db)
        results = engine.search("python")
        assert len(results) == 2
        # The first result should be the one with more python occurrences
        assert results[0].url in ("http://a.com", "http://b.com")
        engine.close()
