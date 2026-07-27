from __future__ import annotations

import os
import tempfile
import time

from brium.metrics.engine import Metrics


def test_counter():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "metrics.db")
        m = Metrics(db)
        assert m.get_counter("pages") == 0
        m.incr("pages")
        assert m.get_counter("pages") == 1
        m.incr("pages", 5)
        assert m.get_counter("pages") == 6
        m.close()


def test_gauge():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "metrics.db")
        m = Metrics(db)
        assert m.get_gauge("index_size") is None
        m.gauge("index_size", 100)
        assert m.get_gauge("index_size") == 100
        m.gauge("index_size", 200)
        assert m.get_gauge("index_size") == 200
        m.close()


def test_latency():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "metrics.db")
        m = Metrics(db)
        assert m.avg_latency("search") == 0.0
        m.record_latency("search", 0.1)
        m.record_latency("search", 0.3)
        assert abs(m.avg_latency("search") - 0.2) < 0.01
        m.close()


def test_cache_tracking():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "metrics.db")
        m = Metrics(db)
        assert m.cache_hit_ratio() == 0.0
        m.cache_hit("search")
        m.cache_hit("search")
        m.cache_miss("search")
        assert abs(m.cache_hit_ratio() - 2.0 / 3.0) < 0.01
        assert abs(m.cache_hit_ratio("search") - 2.0 / 3.0) < 0.01
        m.close()


def test_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "metrics.db")
        m = Metrics(db)
        m.incr("pages", 10)
        m.gauge("index_size", 500)
        m.record_latency("search", 0.05)
        m.cache_hit("search")
        snap = m.snapshot()
        assert snap["counters"]["pages"] == 10
        assert snap["gauges"]["index_size"] == 500
        assert snap["cache"]["hits"] == 1
        assert "search" in snap["latency"]
        m.close()
