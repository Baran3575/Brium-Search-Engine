from __future__ import annotations

import logging

from brium.plugins.base import BaseRanker, BaseSource

log = logging.getLogger(__name__)


class Registry:
    rankers: dict[str, type[BaseRanker]] = {}
    sources: dict[str, type[BaseSource]] = {}

    @classmethod
    def register_ranker(cls, ranker_cls: type[BaseRanker]):
        name = getattr(ranker_cls, "name", ranker_cls.__name__)
        cls.rankers[name] = ranker_cls
        log.debug("registered ranker: %s", name)
        return ranker_cls

    @classmethod
    def register_source(cls, source_cls: type[BaseSource]):
        name = getattr(source_cls, "name", source_cls.__name__)
        cls.sources[name] = source_cls
        log.debug("registered source: %s", name)
        return source_cls

    @classmethod
    def get_ranker(cls, name: str) -> type[BaseRanker] | None:
        return cls.rankers.get(name)

    @classmethod
    def get_source(cls, name: str) -> type[BaseSource] | None:
        return cls.sources.get(name)

    @classmethod
    def list_rankers(cls) -> list[str]:
        return list(cls.rankers.keys())

    @classmethod
    def list_sources(cls) -> list[str]:
        return list(cls.sources.keys())


def register_ranker(cls):
    Registry.register_ranker(cls)
    return cls


def register_source(cls):
    Registry.register_source(cls)
    return cls
