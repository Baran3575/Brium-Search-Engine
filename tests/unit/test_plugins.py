from __future__ import annotations

from brium.plugins.registry import Registry
from brium.plugins.base import BaseRanker, BaseSource


def test_registry_has_builtins():
    assert "bm25" in Registry.list_rankers()
    assert "wikipedia" in Registry.list_sources()
    assert "rss" in Registry.list_sources()


def test_get_ranker():
    ranker_cls = Registry.get_ranker("bm25")
    assert ranker_cls is not None
    assert ranker_cls.name == "bm25"
    instance = ranker_cls()
    assert hasattr(instance, "rank")


def test_get_source():
    source_cls = Registry.get_source("wikipedia")
    assert source_cls is not None
    assert source_cls.name == "wikipedia"
    instance = source_cls()
    assert hasattr(instance, "discover")


def test_custom_ranker_registration():

    @Registry.register_ranker
    class TestRanker(BaseRanker):
        name = "test"

        def rank(self, raw_query, conn, top_k=20):
            return []

    assert "test" in Registry.list_rankers()
    assert Registry.get_ranker("test") is TestRanker


def test_custom_source_registration():

    @Registry.register_source
    class TestSource(BaseSource):
        name = "test"

        def discover(self, query):
            return ["http://test.com"]

    assert "test" in Registry.list_sources()
    assert Registry.get_source("test") is TestSource
