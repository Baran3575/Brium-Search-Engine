from __future__ import annotations

import logging

import requests

from brium.base.config import Config

log = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    def get(self, url: str, timeout: int = 10) -> requests.Response | None:
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            return None

    def close(self):
        self.session.close()
