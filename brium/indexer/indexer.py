from __future__ import annotations

import os
import re
import math
import sqlite3
import logging
from collections import Counter

from brium.crawler.spider import Page

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Indexer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                text_len INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS postings (
                term_id INTEGER NOT NULL,
                doc_id INTEGER NOT NULL,
                freq INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (term_id, doc_id),
                FOREIGN KEY (term_id) REFERENCES terms(id),
                FOREIGN KEY (doc_id) REFERENCES docs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_postings_doc ON postings(doc_id);
        """)
        self.conn.commit()

    def add_page(self, page: Page) -> int:
        toks = tokenize(page.text)
        total_tokens = len(toks)
        freq = Counter(toks)
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO docs (url, title, text_len) VALUES (?, ?, ?)",
            (page.url, page.title[:500], total_tokens),
        )
        doc_id = cur.lastrowid
        if doc_id == 0:
            doc_id = self.conn.execute("SELECT id FROM docs WHERE url = ?", (page.url,)).fetchone()[0]
            # update text_len for re-crawls
            self.conn.execute("UPDATE docs SET text_len = ? WHERE id = ?", (total_tokens, doc_id))
        for term, count in freq.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO terms (term) VALUES (?)", (term,)
            )
            term_id = self.conn.execute(
                "SELECT id FROM terms WHERE term = ?", (term,)
            ).fetchone()[0]
            self.conn.execute(
                "INSERT OR REPLACE INTO postings (term_id, doc_id, freq) VALUES (?, ?, ?)",
                (term_id, doc_id, count),
            )
        self.conn.commit()
        return doc_id

    def doc_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]

    def total_terms(self) -> int:
        return self.conn.execute("SELECT SUM(text_len) FROM docs").fetchone()[0] or 0

    def close(self):
        self.conn.close()
