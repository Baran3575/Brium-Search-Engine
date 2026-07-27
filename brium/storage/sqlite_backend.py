from __future__ import annotations

import os
import sqlite3
import time
import logging
from collections import Counter

from brium.storage.interface import StorageBackend, SearchDoc, IndexStats, PostingRow
from brium.index.schema import SCHEMA_SQL, MIGRATIONS

log = logging.getLogger(__name__)


class SQLiteBackend(StorageBackend):
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        for migration in MIGRATIONS:
            try:
                self.conn.execute(migration)
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def add_page(self, url: str, title: str, snippet: str, headings: str,
                 text_len: int, tokens: list[str], title_tokens: list[str],
                 heading_tokens: list[str], bigram_tokens: list[str],
                 title_bigrams: list[str]) -> int:
        now = time.time()
        freq = Counter(tokens)
        title_freq = Counter(title_tokens)
        heading_freq = Counter(heading_tokens)

        cur = self.conn.execute(
            "INSERT OR IGNORE INTO docs (url, title, snippet, headings, text_len, crawled_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (url, title[:500], snippet[:1000], headings[:500], text_len, now),
        )
        doc_id = cur.lastrowid
        if doc_id == 0:
            doc_id = self.conn.execute(
                "SELECT id FROM docs WHERE url=?", (url,)
            ).fetchone()[0]
            self.conn.execute(
                "UPDATE docs SET text_len=?, snippet=?, headings=?, crawled_at=? WHERE id=?",
                (text_len, snippet[:1000], headings[:500], now, doc_id),
            )
            self.conn.execute("DELETE FROM postings WHERE doc_id=?", (doc_id,))

        for term, count in freq.items():
            self.conn.execute("INSERT OR IGNORE INTO terms (term) VALUES (?)", (term,))
            tid = self.conn.execute(
                "SELECT id FROM terms WHERE term=?", (term,)
            ).fetchone()["id"]
            self.conn.execute(
                "INSERT OR REPLACE INTO postings (term_id, doc_id, freq, in_title, in_heading) "
                "VALUES (?, ?, ?, ?, ?)",
                (tid, doc_id, count, title_freq.get(term, 0), heading_freq.get(term, 0)),
            )

        for bg in bigram_tokens:
            self.conn.execute("INSERT OR IGNORE INTO terms (term) VALUES (?)", (bg,))
            tid = self.conn.execute(
                "SELECT id FROM terms WHERE term=?", (bg,)
            ).fetchone()["id"]
            self.conn.execute(
                "INSERT OR REPLACE INTO postings (term_id, doc_id, freq, in_title, in_heading) "
                "VALUES (?, ?, 1, 0, 0)",
                (tid, doc_id),
            )

        for bg in title_bigrams:
            self.conn.execute("INSERT OR IGNORE INTO terms (term) VALUES (?)", (bg,))
            tid = self.conn.execute(
                "SELECT id FROM terms WHERE term=?", (bg,)
            ).fetchone()["id"]
            existing = self.conn.execute(
                "SELECT freq FROM postings WHERE term_id=? AND doc_id=?", (tid, doc_id)
            ).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE postings SET in_title = in_title + 1 WHERE term_id=? AND doc_id=?",
                    (tid, doc_id),
                )
            else:
                self.conn.execute(
                    "INSERT INTO postings (term_id, doc_id, freq, in_title, in_heading) "
                    "VALUES (?, ?, 1, 1, 0)",
                    (tid, doc_id),
                )

        self.conn.commit()
        return doc_id

    def doc_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]

    def total_terms(self) -> int:
        return self.conn.execute("SELECT SUM(text_len) FROM docs").fetchone()[0] or 0

    def stats(self) -> IndexStats:
        row = self.conn.execute(
            "SELECT COUNT(*) AS doc_count, AVG(text_len) AS avg_len "
            "FROM docs"
        ).fetchone()
        return IndexStats(
            doc_count=row["doc_count"],
            avg_text_len=row["avg_len"] or 0.0,
            total_terms=self.total_terms(),
        )

    def get_doc(self, doc_id: int) -> SearchDoc | None:
        row = self.conn.execute(
            "SELECT id, url, title, snippet, headings, text_len, "
            "incoming_links, crawled_at FROM docs WHERE id=?", (doc_id,)
        ).fetchone()
        if row is None:
            return None
        return SearchDoc(**dict(row))

    def get_doc_by_url(self, url: str) -> SearchDoc | None:
        row = self.conn.execute(
            "SELECT id, url, title, snippet, headings, text_len, "
            "incoming_links, crawled_at FROM docs WHERE url=?", (url,)
        ).fetchone()
        if row is None:
            return None
        return SearchDoc(**dict(row))

    def get_term_id(self, term: str) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM terms WHERE term=?", (term,)
        ).fetchone()
        return row["id"] if row else None

    def term_df(self, term_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM postings WHERE term_id=?", (term_id,)
        ).fetchone()
        return row[0]

    def query_postings(self, term_id: int) -> list[PostingRow]:
        rows = self.conn.execute(
            """SELECT p.doc_id, p.freq, p.in_title, p.in_heading,
                      d.url, d.title, d.snippet,
                      d.text_len, d.incoming_links, d.crawled_at
               FROM postings p JOIN docs d ON p.doc_id = d.id
               WHERE p.term_id = ?""",
            (term_id,),
        ).fetchall()
        return [PostingRow(**dict(r)) for r in rows]

    def close(self):
        self.conn.close()
