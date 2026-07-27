from __future__ import annotations

import os
import sqlite3
import time
import logging
import threading

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics_counters (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS metrics_gauges (
    name TEXT PRIMARY KEY,
    value REAL NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics_latency (
    name TEXT NOT NULL,
    duration REAL NOT NULL,
    recorded_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_latency_name ON metrics_latency(name);
"""


class Metrics:
    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = os.path.join(os.getenv("BRIUM_DATA", "crawl_data"), "metrics.db")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self._lock = threading.Lock()
        self._cache_hits: dict[str, int] = {}
        self._cache_misses: dict[str, int] = {}

    # -- Counters --

    def incr(self, name: str, value: int = 1):
        with self._lock:
            self.conn.execute(
                "INSERT INTO metrics_counters (name, value) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET value = value + ?",
                (name, value, value),
            )
            self.conn.commit()

    def get_counter(self, name: str) -> int:
        row = self.conn.execute(
            "SELECT value FROM metrics_counters WHERE name=?", (name,)
        ).fetchone()
        return row[0] if row else 0

    # -- Gauges --

    def gauge(self, name: str, value: float):
        with self._lock:
            self.conn.execute(
                "INSERT INTO metrics_gauges (name, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET value=?, updated_at=?",
                (name, value, time.time(), value, time.time()),
            )
            self.conn.commit()

    def get_gauge(self, name: str) -> float | None:
        row = self.conn.execute(
            "SELECT value FROM metrics_gauges WHERE name=?", (name,)
        ).fetchone()
        return row[0] if row else None

    # -- Latency recording --

    def record_latency(self, name: str, duration: float):
        with self._lock:
            self.conn.execute(
                "INSERT INTO metrics_latency (name, duration, recorded_at) VALUES (?, ?, ?)",
                (name, duration, time.time()),
            )
            self.conn.execute(
                "DELETE FROM metrics_latency WHERE rowid NOT IN "
                "(SELECT rowid FROM metrics_latency ORDER BY rowid DESC LIMIT 1000)"
            )
            self.conn.commit()

    def avg_latency(self, name: str, window: int = 100) -> float:
        rows = self.conn.execute(
            "SELECT duration FROM metrics_latency WHERE name=? "
            "ORDER BY rowid DESC LIMIT ?", (name, window),
        ).fetchall()
        if not rows:
            return 0.0
        return sum(r[0] for r in rows) / len(rows)

    # -- Cache tracking --

    def cache_hit(self, namespace: str):
        self._cache_hits[namespace] = self._cache_hits.get(namespace, 0) + 1

    def cache_miss(self, namespace: str):
        self._cache_misses[namespace] = self._cache_misses.get(namespace, 0) + 1

    def cache_hit_ratio(self, namespace: str = "") -> float:
        if namespace:
            hits = self._cache_hits.get(namespace, 0)
            misses = self._cache_misses.get(namespace, 0)
        else:
            hits = sum(self._cache_hits.values())
            misses = sum(self._cache_misses.values())
        total = hits + misses
        return hits / total if total > 0 else 0.0

    # -- Snapshot --

    def snapshot(self) -> dict:
        counters = self.conn.execute(
            "SELECT name, value FROM metrics_counters ORDER BY name"
        ).fetchall()
        gauges = self.conn.execute(
            "SELECT name, value FROM metrics_gauges ORDER BY name"
        ).fetchall()

        cache_hits = sum(self._cache_hits.values())
        cache_misses = sum(self._cache_misses.values())

        return {
            "counters": {r["name"]: r["value"] for r in counters},
            "gauges": {r["name"]: r["value"] for r in gauges},
            "latency": {
                "search": self.avg_latency("search"),
                "crawl_page": self.avg_latency("crawl_page"),
            },
            "cache": {
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_ratio": self.cache_hit_ratio(),
            },
        }

    def close(self):
        self.conn.close()
