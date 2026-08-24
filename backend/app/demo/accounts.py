"""Accounts, sessions, preferences and question history — backed by SQLite.

Previously held in memory, which meant an account vanished when the process restarted.
The interface is unchanged; only where the rows live has moved.

Three things are done properly rather than demo-properly, because a prototype that models
them wrongly gets copied:

* Passwords are salted and stretched with PBKDF2, never stored or recoverable.
* A wrong password and an unknown address take the same time and give the same message,
  so neither the clock nor the wording reveals whether an address is registered.
* Session tokens are random and stored hashed, so reading the database file does not hand
  anyone a working session.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.demo.db import connect, expiry_iso, hash_token, purge_expired_sessions

SESSION_DAYS = 14
PBKDF2_ROUNDS = 120_000
MIN_PASSWORD = 8


@dataclass
class Preferences:
    ui_language: str = "eng"
    answer_language: str = "eng"
    text_scale: float = 1.0
    read_aloud: bool = False
    entity_type: str | None = None
    activity: str | None = None
    sector: str | None = None
    turnover_cr: float | None = None


@dataclass
class QueryRecord:
    query: str
    outcome: str
    answer_text: str | None
    cited: str | None
    language: str
    at: datetime | str
    resolved: bool = False
    id: int | None = None


@dataclass
class User:
    id: int
    name: str
    email: str
    business_name: str
    preferences: Preferences = field(default_factory=Preferences)
    history: list[QueryRecord] = field(default_factory=list)


def _hash(password: str, salt: bytes) -> bytes:
    """PBKDF2 rather than a bare digest — a single SHA-256 pass over a password is
    reversible with a wordlist in minutes."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)


class Accounts:
    def __init__(self, path: str = "data/scc.db") -> None:
        self._conn: sqlite3.Connection = connect(path)
        purge_expired_sessions(self._conn)

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    # --- registration and sign-in ----------------------------------------------------
    def create(self, name: str, email: str, password: str, business_name: str) -> User:
        email = email.strip().lower()
        if len(password) < MIN_PASSWORD:
            raise ValueError(f"Choose a password of at least {MIN_PASSWORD} characters.")
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("That does not look like an email address.")

        salt = os.urandom(16)
        try:
            with self._conn:
                cur = self._conn.execute(
                    "INSERT INTO app_user(name, email, business_name, salt, password_hash) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (name.strip(), email, business_name.strip() or "—", salt,
                     _hash(password, salt)),
                )
                user_id = cur.lastrowid
                self._conn.execute(
                    "INSERT INTO preference(user_id) VALUES (?)", (user_id,)
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account already exists for that email address.") from exc

        return self.get(user_id)  # type: ignore[return-value]

    def authenticate(self, email: str, password: str) -> User | None:
        row = self._conn.execute(
            "SELECT id, salt, password_hash, is_active FROM app_user WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()

        if row is None:
            # Hash anyway. Returning early would make an unknown address measurably
            # faster than a wrong password, which is enough to enumerate registrations.
            _hash(password, os.urandom(16))
            return None
        if not hmac.compare_digest(row["password_hash"], _hash(password, row["salt"])):
            return None
        if not row["is_active"]:
            return None
        return self.get(row["id"])

    def start_session(self, user: User) -> str:
        purge_expired_sessions(self._conn)
        token = secrets.token_urlsafe(32)
        with self._conn:
            self._conn.execute(
                "INSERT INTO session(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (hash_token(token), user.id, expiry_iso(SESSION_DAYS)),
            )
        return token

    def end_session(self, token: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM session WHERE token_hash = ?", (hash_token(token),)
            )

    def user_for(self, token: str | None) -> User | None:
        if not token:
            return None
        row = self._conn.execute(
            "SELECT user_id FROM session WHERE token_hash = ? AND expires_at > datetime('now')",
            (hash_token(token),),
        ).fetchone()
        return self.get(row["user_id"]) if row else None

    # --- reading ---------------------------------------------------------------------
    def get(self, user_id: int) -> User | None:
        row = self._conn.execute(
            "SELECT id, name, email, business_name FROM app_user WHERE id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()
        if row is None:
            return None

        pref = self._conn.execute(
            "SELECT ui_language, answer_language, text_scale, read_aloud, entity_type, "
            "activity, sector, turnover_cr FROM preference WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        return User(
            id=row["id"], name=row["name"], email=row["email"],
            business_name=row["business_name"],
            preferences=Preferences(
                ui_language=pref["ui_language"], answer_language=pref["answer_language"],
                text_scale=pref["text_scale"], read_aloud=bool(pref["read_aloud"]),
                entity_type=pref["entity_type"], activity=pref["activity"],
                sector=pref["sector"], turnover_cr=pref["turnover_cr"],
            ) if pref else Preferences(),
            history=self._history(user_id),
        )

    def _history(self, user_id: int, limit: int = 200) -> list[QueryRecord]:
        rows = self._conn.execute(
            "SELECT id, query, outcome, answer_text, cited, language, resolved, asked_at "
            "FROM query_history WHERE user_id = ? ORDER BY asked_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            QueryRecord(
                id=r["id"], query=r["query"], outcome=r["outcome"],
                answer_text=r["answer_text"], cited=r["cited"], language=r["language"],
                resolved=bool(r["resolved"]), at=r["asked_at"],
            )
            for r in rows
        ]

    # --- writing ---------------------------------------------------------------------
    def save_preferences(self, user: User, changes: dict[str, Any]) -> None:
        allowed = {
            "ui_language", "answer_language", "text_scale", "read_aloud",
            "entity_type", "activity", "sector", "turnover_cr",
        }
        # Column names are taken from a fixed set rather than from the request, so a
        # field name can never reach the SQL text.
        fields = {k: v for k, v in changes.items() if k in allowed and v is not None}
        if not fields:
            return
        if "read_aloud" in fields:
            fields["read_aloud"] = int(bool(fields["read_aloud"]))

        assignments = ", ".join(f"{k} = ?" for k in fields)
        with self._conn:
            self._conn.execute(
                f"UPDATE preference SET {assignments}, updated_at = datetime('now') "
                "WHERE user_id = ?",
                (*fields.values(), user.id),
            )
        for key, value in fields.items():
            setattr(user.preferences, key, bool(value) if key == "read_aloud" else value)

    def record_query(
        self, user: User, query: str, outcome: str, answer_text: str | None,
        cited: str | None, language: str,
    ) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO query_history(user_id, query, outcome, answer_text, cited, "
                "language) VALUES (?, ?, ?, ?, ?, ?)",
                (user.id, query, outcome, answer_text, cited, language),
            )

    def mark_resolved(self, user: User, history_id: int) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE query_history SET resolved = 1 WHERE id = ? AND user_id = ?",
                (history_id, user.id),
            )
        return bool(cur.rowcount)

    # --- dashboard -------------------------------------------------------------------
    def dashboard(self, user: User) -> dict[str, Any]:
        """What this person asked, and how much of it the desk settled.

        Per-person rather than a slice of the aggregate: a business wants to know whether
        *its* questions were answered, and the site-wide rate says nothing about that.
        """
        totals = self._conn.execute(
            """
            SELECT count(*) AS total,
                   sum(outcome = 'answered')  AS answered,
                   sum(outcome = 'no_answer') AS unanswered,
                   sum(outcome = 'conflict')  AS conflicts,
                   sum(resolved)              AS resolved
              FROM query_history WHERE user_id = ?
            """,
            (user.id,),
        ).fetchone()

        total = totals["total"] or 0
        answered = totals["answered"] or 0
        resolved = totals["resolved"] or 0

        top = self._conn.execute(
            "SELECT cited, count(*) AS n FROM query_history "
            "WHERE user_id = ? AND cited IS NOT NULL "
            "GROUP BY cited ORDER BY n DESC LIMIT 5",
            (user.id,),
        ).fetchall()

        recent = self._history(user.id, limit=25)

        return {
            "total": total,
            "answered": answered,
            "unanswered": totals["unanswered"] or 0,
            "conflicts": totals["conflicts"] or 0,
            "resolved": resolved,
            "answer_rate": round(answered / total, 3) if total else None,
            "resolution_rate": round(resolved / total, 3) if total else None,
            "top_records": [(r["cited"], r["n"]) for r in top],
            "recent": [
                {
                    "id": h.id, "query": h.query, "outcome": h.outcome,
                    "cited": h.cited, "language": h.language, "resolved": h.resolved,
                    "at": str(h.at)[5:16].replace("-", "/"),
                    "answer": (h.answer_text or "")[:220],
                }
                for h in recent
            ],
        }

    def stats(self) -> dict[str, int]:
        row = self._conn.execute(
            "SELECT (SELECT count(*) FROM app_user) AS users, "
            "(SELECT count(*) FROM query_history) AS questions, "
            "(SELECT count(*) FROM session WHERE expires_at > datetime('now')) AS sessions"
        ).fetchone()
        return {"users": row["users"], "questions": row["questions"],
                "active_sessions": row["sessions"]}
