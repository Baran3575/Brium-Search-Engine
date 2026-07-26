from __future__ import annotations

import os
import re
import sqlite3
import logging
import time
from collections import Counter
from urllib.parse import urlparse

from brium.crawler.spider import Page

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]


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
                text_len INTEGER NOT NULL DEFAULT 0,
                incoming_links INTEGER NOT NULL DEFAULT 0,
                crawled_at REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS postings (
                term_id INTEGER NOT NULL,
                doc_id INTEGER NOT NULL,
                freq INTEGER NOT NULL DEFAULT 0,
                in_title INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (term_id, doc_id),
                FOREIGN KEY (term_id) REFERENCES terms(id),
                FOREIGN KEY (doc_id) REFERENCES docs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_postings_doc ON postings(doc_id);
        """)
        # Add columns if missing (schema migration)
        for col, typ in [("incoming_links", "INTEGER DEFAULT 0"), ("crawled_at", "REAL DEFAULT 0")]:
            try:
                self.conn.execute(f"ALTER TABLE docs ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        try:
            self.conn.execute("ALTER TABLE postings ADD COLUMN in_title INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def add_page(self, page: Page) -> int:
        toks = tokenize(page.text)
        title_toks = tokenize(page.title)
        domain = urlparse(page.url).netloc
        url_toks = tokenize(domain + " " + page.url)
        total_tokens = len(toks)
        freq = Counter(toks)
        title_freq = Counter(title_toks)
        now = time.time()

        cur = self.conn.execute(
            "INSERT OR IGNORE INTO docs (url, title, text_len, crawled_at) VALUES (?, ?, ?, ?)",
            (page.url, page.title[:500], total_tokens, now),
        )
        doc_id = cur.lastrowid
        if doc_id == 0:
            doc_id = self.conn.execute("SELECT id FROM docs WHERE url = ?", (page.url,)).fetchone()[0]
            self.conn.execute("UPDATE docs SET text_len = ?, crawled_at = ? WHERE id = ?",
                              (total_tokens, now, doc_id))
            # Clear old postings for re-crawl
            self.conn.execute("DELETE FROM postings WHERE doc_id = ?", (doc_id,))
        else:
            self._update_incoming_links(page.url, doc_id)

        for term, count in freq.items():
            self.conn.execute("INSERT OR IGNORE INTO terms (term) VALUES (?)", (term,))
            term_id = self.conn.execute("SELECT id FROM terms WHERE term = ?", (term,)).fetchone()[0]
            in_title = title_freq.get(term, 0)
            self.conn.execute(
                "INSERT OR REPLACE INTO postings (term_id, doc_id, freq, in_title) VALUES (?, ?, ?, ?)",
                (term_id, doc_id, count, in_title),
            )

        # index bigrams from body text
        for bg in bigrams(toks):
            self.conn.execute("INSERT OR IGNORE INTO terms (term) VALUES (?)", (bg,))
            tid = self.conn.execute("SELECT id FROM terms WHERE term = ?", (bg,)).fetchone()[0]
            self.conn.execute(
                "INSERT OR REPLACE INTO postings (term_id, doc_id, freq, in_title) VALUES (?, ?, ?, 0)",
                (tid, doc_id, 1),
            )
        # index bigrams from title
        for bg in bigrams(title_toks):
            self.conn.execute("INSERT OR IGNORE INTO terms (term) VALUES (?)", (bg,))
            tid = self.conn.execute("SELECT id FROM terms WHERE term = ?", (bg,)).fetchone()[0]
            existing = self.conn.execute(
                "SELECT freq FROM postings WHERE term_id=? AND doc_id=?", (tid, doc_id)
            ).fetchone()
            if existing:
                self.conn.execute("UPDATE postings SET in_title = in_title + 1 WHERE term_id=? AND doc_id=?", (tid, doc_id))
            else:
                self.conn.execute(
                    "INSERT INTO postings (term_id, doc_id, freq, in_title) VALUES (?, ?, 1, 1)",
                    (tid, doc_id),
                )

        self.conn.commit()
        return doc_id

    def _update_incoming_links(self, url: str, doc_id: int):
        for other_url, in self.conn.execute("SELECT url FROM docs WHERE id != ?", (doc_id,)).fetchall():
            pass  # ponytail: incoming_links tracked via link table; skip full recompute for now

    def record_links(self, from_doc_id: int, to_urls: list[str]):
        for url in set(to_urls):
            row = self.conn.execute("SELECT id FROM docs WHERE url = ?", (url,)).fetchone()
            if row:
                self.conn.execute("UPDATE docs SET incoming_links = incoming_links + 1 WHERE id = ?", (row["id"],))

    def doc_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]

    def total_terms(self) -> int:
        return self.conn.execute("SELECT SUM(text_len) FROM docs").fetchone()[0] or 0

    def close(self):
        self.conn.close()
