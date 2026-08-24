"""SQLite storage for accounts, preferences, sessions and question history.

SQLite rather than a server database because this is a single-process deployment and a
file is the honest fit — but the schema is written as it would be for PostgreSQL, with
real constraints and indexes, so nothing here teaches a habit that would have to be
unlearned when it moves.

Two decisions worth naming:

* **Foreign keys are enforced.** SQLite leaves them off unless asked, and a database that
  silently accepts an orphaned row is worse than no constraint at all, because it looks
  like it is protecting you.
* **A session is a random token stored as a hash.** Anyone who reads the database file
  still cannot present themselves as a signed-in user, which is the point of hashing a
  credential at rest.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_user (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    business_name   TEXT    NOT NULL DEFAULT '—',
    salt            BLOB    NOT NULL,
    password_hash   BLOB    NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (length(email) > 4),
    CHECK (is_active IN (0, 1))
);

-- One row per user. Split from app_user because preferences change often and
-- credentials should not be rewritten every time somebody changes a font size.
CREATE TABLE IF NOT EXISTS preference (
    user_id         INTEGER PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
    ui_language     TEXT    NOT NULL DEFAULT 'eng',
    answer_language TEXT    NOT NULL DEFAULT 'eng',
    text_scale      REAL    NOT NULL DEFAULT 1.0,
    read_aloud      INTEGER NOT NULL DEFAULT 0,
    entity_type     TEXT,
    activity        TEXT,
    sector          TEXT,
    turnover_cr     REAL,
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (text_scale BETWEEN 0.5 AND 2.0),
    CHECK (read_aloud IN (0, 1))
);

CREATE TABLE IF NOT EXISTS session (
    token_hash      BLOB    PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_user ON session(user_id);
CREATE INDEX IF NOT EXISTS idx_session_expiry ON session(expires_at);

CREATE TABLE IF NOT EXISTS query_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    query           TEXT    NOT NULL,
    outcome         TEXT    NOT NULL,
    answer_text     TEXT,
    cited           TEXT,
    language        TEXT    NOT NULL DEFAULT 'eng',
    -- Whether the person said it settled their question. The service can only measure
    -- whether it produced an answer; this is the part only they can report.
    resolved        INTEGER NOT NULL DEFAULT 0,
    asked_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (resolved IN (0, 1))
);
-- Serves the dashboard, which reads one user's most recent questions.
CREATE INDEX IF NOT EXISTS idx_history_user_time
    ON query_history(user_id, asked_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_cited ON query_history(cited);

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def hash_token(token: str) -> bytes:
    """Session tokens are stored hashed, never in the clear."""
    return hashlib.sha256(token.encode()).digest()


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # SQLite ignores foreign keys unless asked, and a constraint that is declared but not
    # enforced is worse than none — it reads as protection that is not there.
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL lets a read proceed while a write is in flight, which matters as soon as the
    # dashboard is being read while an answer is being recorded.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO schema_meta(key, value) VALUES ('version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn


def purge_expired_sessions(conn: sqlite3.Connection) -> int:
    """Remove sessions past their expiry.

    Called on startup and on each sign-in. An expired row left in place is a credential
    that still exists, and the check that rejects it is one bug away from not running.
    """
    cur = conn.execute("DELETE FROM session WHERE expires_at < ?", (_now_iso(),))
    conn.commit()
    return cur.rowcount or 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def expiry_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
