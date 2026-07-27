from __future__ import annotations

import sqlite3

from brium.algorithm.ranker import Ranker, SearchResult


class SearchEngine:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ranker = Ranker(self.conn)

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        return self._ranker.search(query, top_k)

    def close(self):
        self.conn.close()
