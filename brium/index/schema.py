from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    snippet TEXT NOT NULL DEFAULT '',
    headings TEXT NOT NULL DEFAULT '',
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
    in_heading INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (term_id, doc_id),
    FOREIGN KEY (term_id) REFERENCES terms(id),
    FOREIGN KEY (doc_id) REFERENCES docs(id)
);
CREATE INDEX IF NOT EXISTS idx_postings_doc ON postings(doc_id);
"""

MIGRATIONS: list[str] = [
    "ALTER TABLE docs ADD COLUMN snippet TEXT DEFAULT ''",
    "ALTER TABLE docs ADD COLUMN headings TEXT DEFAULT ''",
    "ALTER TABLE docs ADD COLUMN incoming_links INTEGER DEFAULT 0",
    "ALTER TABLE docs ADD COLUMN crawled_at REAL DEFAULT 0",
    "ALTER TABLE postings ADD COLUMN in_heading INTEGER NOT NULL DEFAULT 0",
]
