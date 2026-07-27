from __future__ import annotations

import os
import tempfile
import time

from brium.cache.engine import Cache


def test_cache_set_get():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "cache.db")
        c = Cache(db)
        c.set("ns1", "key1", "value1", 60)
        assert c.get("ns1", "key1") == "value1"
        assert c.get("ns1", "nonexistent") is None
        c.close()


def test_cache_ttl():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "cache.db")
        c = Cache(db)
        c.set("ns1", "key1", "value1", 1)
        assert c.get("ns1", "key1") == "value1"
        time.sleep(1.5)
        assert c.get("ns1", "key1") is None
        c.close()


def test_cache_delete():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "cache.db")
        c = Cache(db)
        c.set("ns1", "key1", "value1", 60)
        c.delete("ns1", "key1")
        assert c.get("ns1", "key1") is None
        c.close()


def test_cache_clear_expired():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "cache.db")
        c = Cache(db)
        c.set("ns1", "k1", "v1", 0)
        c.set("ns1", "k2", "v2", 60)
        time.sleep(0.1)
        deleted = c.clear_expired()
        assert deleted >= 1
        assert c.get("ns1", "k2") == "v2"
        c.close()


def test_cache_clear_namespace():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "cache.db")
        c = Cache(db)
        c.set("ns1", "k1", "v1", 60)
        c.set("ns2", "k1", "v1", 60)
        c.clear_namespace("ns1")
        assert c.get("ns1", "k1") is None
        assert c.get("ns2", "k1") == "v1"
        c.close()
