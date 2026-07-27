from __future__ import annotations

import logging
import threading
import functools

from brium.plugins.safe.metadata import (
    CURRENT_API_VERSION, SUPPORTED_API_VERSIONS, PluginMetadata,
)

log = logging.getLogger(__name__)


def check_compatibility(plugin_api_version: str) -> bool:
    if plugin_api_version not in SUPPORTED_API_VERSIONS:
        log.warning("incompatible plugin API version: %s (supported: %s)",
                     plugin_api_version, SUPPORTED_API_VERSIONS)
        return False
    return True


def isolate(fn=None, *, timeout: float = 10.0):
    if fn is None:
        return functools.partial(isolate, timeout=timeout)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = None
        error = None

        def target():
            nonlocal result, error
            try:
                result = fn(*args, **kwargs)
            except Exception as e:
                error = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Thread is still running after timeout
            log.warning("plugin call timed out after %.1fs: %s", timeout, fn.__name__)
            raise TimeoutError(f"plugin timed out after {timeout}s")

        if error is not None:
            log.warning("plugin error in %s: %s", fn.__name__, error)
            raise error

        return result

    return wrapper
