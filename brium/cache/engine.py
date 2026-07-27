from __future__ import annotations

import os
import sqlite3
import time
import logging

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    expires_at REAL NOT NULL,
    PRIMARY KEY (namespace, key)
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
"""


class Cache:
    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = os.path.join(os.getenv("BRIUM_DATA", "crawl_data"), "cache.db")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def get(self, namespace: str, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value, expires_at FROM cache WHERE namespace=? AND key=?",
            (namespace, key),
        ).fetchone()
        if row is None:
            return None
        value, expires_at = row
        if time.time() > expires_at:
            self.conn.execute(
                "DELETE FROM cache WHERE namespace=? AND key=?",
                (namespace, key),
            )
            self.conn.commit()
            return None
        return value

    def set(self, namespace: str, key: str, value: str, ttl_seconds: int = 300):
        expires_at = time.time() + ttl_seconds
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (namespace, key, value, expires_at) VALUES (?, ?, ?, ?)",
            (namespace, key, value, expires_at),
        )
        self.conn.commit()

    def delete(self, namespace: str, key: str):
        self.conn.execute(
            "DELETE FROM cache WHERE namespace=? AND key=?",
            (namespace, key),
        )
        self.conn.commit()

    def clear_expired(self) -> int:
        now = time.time()
        deleted = self.conn.execute(
            "DELETE FROM cache WHERE expires_at <= ?", (now,)
        ).rowcount
        if deleted:
            self.conn.commit()
        return deleted

    def clear_namespace(self, namespace: str):
        self.conn.execute("DELETE FROM cache WHERE namespace=?", (namespace,))
        self.conn.commit()

    def close(self):
        self.conn.close()
