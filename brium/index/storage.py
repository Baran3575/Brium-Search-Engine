from __future__ import annotations

import os
import sqlite3
import logging

from brium.index.schema import SCHEMA_SQL, MIGRATIONS

log = logging.getLogger(__name__)


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript(SCHEMA_SQL)
        for migration in MIGRATIONS:
            try:
                self.conn.execute(migration)
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def close(self):
        self.conn.close()
