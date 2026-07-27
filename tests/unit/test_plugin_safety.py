from __future__ import annotations

import time

from brium.plugins.safe.metadata import PluginMetadata, CURRENT_API_VERSION, SUPPORTED_API_VERSIONS
from brium.plugins.safe.sandbox import isolate, check_compatibility


def test_metadata_defaults():
    m = PluginMetadata()
    assert m.name == "unknown"
    assert m.version == "0.1.0"
    assert m.api_version == CURRENT_API_VERSION


def test_check_compatibility():
    assert check_compatibility("1.0") is True
    assert check_compatibility("2.0") is False
    assert check_compatibility("0.9") is False


def test_current_in_supported():
    assert CURRENT_API_VERSION in SUPPORTED_API_VERSIONS


def test_isolate_success():
    @isolate(timeout=2)
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_isolate_exception():
    @isolate(timeout=2)
    def broken():
        raise ValueError("oops")

    try:
        broken()
        assert False, "should have raised"
    except ValueError as e:
        assert "oops" in str(e)


def test_isolate_timeout():
    @isolate(timeout=0.5)
    def slow():
        time.sleep(5)
        return 42

    try:
        slow()
        assert False, "should have raised"
    except TimeoutError:
        pass


def test_isolate_preserves_signature():
    @isolate(timeout=2)
    def greet(name: str) -> str:
        return f"hello {name}"

    assert greet.__name__ == "greet"
    assert greet("world") == "hello world"
