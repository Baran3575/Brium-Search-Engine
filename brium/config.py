from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    data_dir: str = field(default_factory=lambda: os.getenv("BRIUM_DATA", "crawl_data"))
    user_agent: str = "Brium/0.1"
    max_pages: int = int(os.getenv("BRIUM_MAX_PAGES", "10000"))
    max_depth: int = int(os.getenv("BRIUM_MAX_DEPTH", "5"))
    request_delay: float = float(os.getenv("BRIUM_DELAY", "0.5"))
    index_db: str = ""
    # ponytail: global lock, per-account locks if throughput matters

    def __post_init__(self):
        if not self.index_db:
            self.index_db = os.path.join(self.data_dir, "index.db")
