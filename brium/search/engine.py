from __future__ import annotations

from brium.base.types import SearchResult
from brium.rank.scorer import Scorer
from brium.storage.interface import StorageBackend
from brium.storage.sqlite_backend import SQLiteBackend


class SearchEngine:
    def __init__(self, db_path: str | None = None, ranker_name: str = "bm25",
                 storage: StorageBackend | None = None):
        if storage is not None:
            self._storage = storage
        elif db_path is not None:
            self._storage = SQLiteBackend(db_path)
        else:
            raise ValueError("either db_path or storage must be provided")

        self._scorer = Scorer(
            conn=self._storage.conn if hasattr(self._storage, 'conn') else None,
            ranker_name=ranker_name,
            storage=self._storage,
        )

    @property
    def conn(self):
        if hasattr(self._storage, 'conn'):
            return self._storage.conn
        return None

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        return self._scorer.search(query, top_k)

    def close(self):
        self._storage.close()
