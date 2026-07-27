from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type);
"""


@dataclass
class Task:
    id: int = 0
    task_type: str = ""
    payload: dict = field(default_factory=dict)
    status: str = "pending"
    priority: int = 0
    error: str = ""


class Queue:
    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = os.path.join(os.getenv("BRIUM_DATA", "crawl_data"), "queue.db")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def enqueue(self, task_type: str, payload: dict | None = None,
                priority: int = 0) -> int:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO tasks (task_type, payload, priority, created_at) VALUES (?, ?, ?, ?)",
                (task_type, json.dumps(payload or {}), priority, time.time()),
            )
            self.conn.commit()
            return cur.lastrowid

    def dequeue(self, task_types: list[str] | None = None) -> Task | None:
        with self._lock:
            if task_types:
                placeholders = ",".join("?" for _ in task_types)
                sql = (
                    f"SELECT id, task_type, payload, status, priority, error "
                    f"FROM tasks WHERE status='pending' AND task_type IN ({placeholders}) "
                    f"ORDER BY priority DESC, created_at ASC LIMIT 1"
                )
                row = self.conn.execute(sql, task_types).fetchone()
            else:
                sql = (
                    "SELECT id, task_type, payload, status, priority, error "
                    "FROM tasks WHERE status='pending' "
                    "ORDER BY priority DESC, created_at ASC LIMIT 1"
                )
                row = self.conn.execute(sql).fetchone()
            if row is None:
                return None
            self.conn.execute(
                "UPDATE tasks SET status='running', started_at=? WHERE id=?",
                (time.time(), row["id"]),
            )
            self.conn.commit()
            return Task(
                id=row["id"],
                task_type=row["task_type"],
                payload=json.loads(row["payload"]) if row["payload"] else {},
                status="running",
                priority=row["priority"],
                error=row["error"] or "",
            )

    def complete(self, task_id: int):
        with self._lock:
            self.conn.execute(
                "UPDATE tasks SET status='completed', completed_at=? WHERE id=?",
                (time.time(), task_id),
            )
            self.conn.commit()

    def fail(self, task_id: int, error: str = ""):
        with self._lock:
            self.conn.execute(
                "UPDATE tasks SET status='failed', completed_at=?, error=? WHERE id=?",
                (time.time(), error[:500], task_id),
            )
            self.conn.commit()

    def retry_failed(self, max_retries: int = 3) -> int:
        with self._lock:
            count = self.conn.execute(
                "UPDATE tasks SET status='pending', started_at=NULL, completed_at=NULL "
                "WHERE status='failed' AND (json_extract(payload, '$.retries') IS NULL "
                "OR json_extract(payload, '$.retries') < ?)",
                (max_retries,),
            ).rowcount
            if count:
                self.conn.commit()
            return count

    def size(self, status: str = "pending") -> int:
        with self._lock:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status=?", (status,)
            ).fetchone()
            return row[0]

    def pending_count(self) -> int:
        return self.size("pending")

    def close(self):
        self.conn.close()
