from __future__ import annotations

import time
from collections import defaultdict
from urllib.parse import urlparse


class RateLimiter:
    def __init__(self, max_requests: int = 3, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._history: defaultdict[str, list[float]] = defaultdict(list)

    def is_limited(self, url: str) -> bool:
        domain = urlparse(url).netloc
        now = time.time()
        ts_list = self._history[domain]
        ts_list[:] = [t for t in ts_list if now - t < self._window]
        if len(ts_list) >= self._max:
            return True
        ts_list.append(now)
        return False
