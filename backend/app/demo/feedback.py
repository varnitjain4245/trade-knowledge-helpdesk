"""What the desk does with a rating.

Until now a rating was written to the audit log and read by nothing. That is the worst
version of a feedback control: it asks people to spend attention marking an answer
wrong, and then spends none of its own acting on it. A system that collects a signal it
never uses has taught its users that marking things wrong is pointless, which costs
more than never asking.

Three things happen to a negative rating here, in order of how quickly they take effect.

  Suppression, immediately. A record marked wrong for a query stops being cited for
  that query. Not for every query — the record may be perfectly good elsewhere, and
  retiring it wholesale on one person's judgement would let a single click remove a
  correct circular from the corpus.

  A curation task, immediately. The pairing goes to a queue with the question, the
  record and the reason, so a person decides whether the record is wrong, the retrieval
  is wrong, or the rater was.

  Nothing else, ever. Ratings do not edit records, do not change a record's lifecycle
  state, and do not adjust the answer bar. Every one of those is a change to what the
  desk asserts, and an unauthenticated thumbs-down is not evidence enough to make one.
  The suppression above is deliberately the weakest action that helps: it withholds a
  citation, it never rewrites one.

Suppression needs two independent negatives before it takes effect. One is noise — a
misread, a mis-click, somebody annoyed about something else. Two people telling the
desk the same pairing is wrong is a signal. The threshold is a tunable, not a truth.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.demo.db import connect

log = get_logger(__name__)

#: Distinct negative ratings on the same question/record pairing before it is withheld.
#: One is noise. See the module docstring.
SUPPRESS_AFTER = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS answer_feedback (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    query_key     TEXT    NOT NULL,
    item_id       TEXT    NOT NULL,
    item_title    TEXT    NOT NULL DEFAULT '',
    rating        INTEGER NOT NULL,
    note          TEXT    NOT NULL DEFAULT '',
    -- Who rated, so that one person clicking twice cannot manufacture a consensus.
    rater         TEXT    NOT NULL DEFAULT 'anonymous',
    at            TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (rating IN (-1, 1))
);
CREATE INDEX IF NOT EXISTS idx_feedback_pair ON answer_feedback(query_key, item_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_once
    ON answer_feedback(query_key, item_id, rater);

-- A pairing withheld from citation. Not a lifecycle state: the record stays approved
-- and answerable everywhere else, because being wrong for one question is not being
-- wrong.
CREATE TABLE IF NOT EXISTS suppressed_pair (
    query_key     TEXT    NOT NULL,
    item_id       TEXT    NOT NULL,
    reason        TEXT    NOT NULL DEFAULT '',
    negatives     INTEGER NOT NULL DEFAULT 0,
    -- A curator can clear a suppression; that is the only way one is lifted.
    cleared_at    TEXT,
    cleared_by    TEXT,
    at            TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (query_key, item_id)
);

CREATE TABLE IF NOT EXISTS curation_task (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    query         TEXT    NOT NULL,
    query_key     TEXT    NOT NULL,
    item_id       TEXT    NOT NULL,
    item_title    TEXT    NOT NULL DEFAULT '',
    reason        TEXT    NOT NULL DEFAULT '',
    negatives     INTEGER NOT NULL DEFAULT 1,
    -- open -> record_wrong | retrieval_wrong | rating_wrong
    state         TEXT    NOT NULL DEFAULT 'open',
    resolution    TEXT,
    resolved_by   TEXT,
    at            TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (state IN ('open','record_wrong','retrieval_wrong','rating_wrong'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_pair
    ON curation_task(query_key, item_id) WHERE state = 'open';
"""


def normalise(query: str) -> str:
    """The key a rating attaches to.

    Case and spacing only. Deliberately not stemming or stripping stopwords: an
    aggressive key would make "duty on cotton" and "duty on cotton yarn" the same
    question, so a rating about one would silently withhold a record from the other.
    An over-narrow key merely fails to generalise, which is the safer failure.
    """
    return " ".join(query.lower().split())


@dataclass(frozen=True)
class Outcome:
    recorded: bool
    negatives: int
    suppressed: bool
    task_opened: bool
    message: str

    def as_dict(self) -> dict:
        return {
            "recorded": self.recorded, "negatives": self.negatives,
            "suppressed": self.suppressed, "task_opened": self.task_opened,
            "message": self.message,
        }


class FeedbackStore:
    def __init__(self, database_path: str) -> None:
        self._path = database_path
        conn = self._conn()
        try:
            with conn:
                conn.executescript(_SCHEMA)
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        return connect(self._path)

    # --- writing -----------------------------------------------------------------
    def rate(self, query: str, item_id: str, rating: int, *, item_title: str = "",
             note: str = "", rater: str = "anonymous") -> Outcome:
        if rating not in (-1, 1):
            raise ValueError("a rating is -1 or 1")

        key = normalise(query)
        conn = self._conn()
        try:
            with conn:
                try:
                    conn.execute(
                        "INSERT INTO answer_feedback(query_key, item_id, item_title,"
                        " rating, note, rater) VALUES (?,?,?,?,?,?)",
                        (key, item_id, item_title, rating, note, rater),
                    )
                except sqlite3.IntegrityError:
                    # Same person, same pairing, already rated. Updating rather than
                    # inserting is what stops one rater counting twice toward a
                    # suppression.
                    conn.execute(
                        "UPDATE answer_feedback SET rating = ?, note = ?,"
                        " at = datetime('now')"
                        " WHERE query_key = ? AND item_id = ? AND rater = ?",
                        (rating, note, key, item_id, rater),
                    )

                negatives = conn.execute(
                    "SELECT count(*) c FROM answer_feedback"
                    " WHERE query_key = ? AND item_id = ? AND rating = -1",
                    (key, item_id),
                ).fetchone()["c"]

                suppressed = False
                task_opened = False
                if rating == -1:
                    task_opened = self._open_task(
                        conn, query, key, item_id, item_title, negatives)
                    if negatives >= SUPPRESS_AFTER:
                        conn.execute(
                            "INSERT INTO suppressed_pair(query_key, item_id, reason,"
                            " negatives) VALUES (?,?,?,?)"
                            " ON CONFLICT(query_key, item_id) DO UPDATE SET"
                            " negatives = excluded.negatives, cleared_at = NULL,"
                            " cleared_by = NULL",
                            (key, item_id,
                             f"{negatives} independent raters marked this wrong", negatives),
                        )
                        suppressed = True
                elif negatives == 0:
                    # A positive rating on a pairing nobody has faulted lifts a stale
                    # suppression. It never lifts one that still has negatives standing.
                    conn.execute(
                        "UPDATE suppressed_pair SET cleared_at = datetime('now'),"
                        " cleared_by = 'positive rating' WHERE query_key = ?"
                        " AND item_id = ? AND cleared_at IS NULL",
                        (key, item_id),
                    )
        finally:
            conn.close()

        if suppressed:
            log.info("feedback.suppressed", item_id=item_id, negatives=negatives)
            message = ("Recorded. This record will no longer be cited for this "
                       "question, and a curator has been asked to look at it.")
        elif rating == -1:
            message = ("Recorded, and a curator has been asked to look at it. One "
                       "report is not enough to withhold a record on its own.")
        else:
            message = "Recorded. Thank you."

        return Outcome(True, negatives, suppressed, task_opened, message)

    @staticmethod
    def _open_task(conn: sqlite3.Connection, query: str, key: str, item_id: str,
                   item_title: str, negatives: int) -> bool:
        existing = conn.execute(
            "SELECT id FROM curation_task WHERE query_key = ? AND item_id = ?"
            " AND state = 'open'", (key, item_id),
        ).fetchone()
        if existing:
            conn.execute("UPDATE curation_task SET negatives = ? WHERE id = ?",
                         (negatives, existing["id"]))
            return False
        conn.execute(
            "INSERT INTO curation_task(query, query_key, item_id, item_title, reason,"
            " negatives) VALUES (?,?,?,?,?,?)",
            (query, key, item_id, item_title,
             "Marked as not answering the question asked.", negatives),
        )
        return True

    def resolve_task(self, task_id: int, state: str, resolution: str = "",
                     by: str = "curator") -> bool:
        if state not in ("record_wrong", "retrieval_wrong", "rating_wrong"):
            raise ValueError(f"not a resolution: {state}")
        conn = self._conn()
        try:
            with conn:
                row = conn.execute(
                    "SELECT query_key, item_id FROM curation_task WHERE id = ?",
                    (task_id,)).fetchone()
                if row is None:
                    return False
                conn.execute(
                    "UPDATE curation_task SET state = ?, resolution = ?,"
                    " resolved_by = ? WHERE id = ?",
                    (state, resolution, by, task_id))
                if state == "rating_wrong":
                    # The raters were mistaken: lift the suppression, and clear the
                    # negatives so the same votes cannot re-suppress it tomorrow.
                    conn.execute(
                        "UPDATE suppressed_pair SET cleared_at = datetime('now'),"
                        " cleared_by = ? WHERE query_key = ? AND item_id = ?",
                        (by, row["query_key"], row["item_id"]))
                    conn.execute(
                        "DELETE FROM answer_feedback WHERE query_key = ?"
                        " AND item_id = ? AND rating = -1",
                        (row["query_key"], row["item_id"]))
        finally:
            conn.close()
        return True

    # --- reading -----------------------------------------------------------------
    def suppressed_for(self, query: str) -> frozenset[str]:
        """Item ids withheld for this question. Read on the retrieval path."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT item_id FROM suppressed_pair WHERE query_key = ?"
                " AND cleared_at IS NULL", (normalise(query),),
            ).fetchall()
        finally:
            conn.close()
        return frozenset(r["item_id"] for r in rows)

    def tasks(self, state: str = "open", limit: int = 50) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM curation_task WHERE state = ?"
                " ORDER BY negatives DESC, at DESC LIMIT ?", (state, limit),
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        conn = self._conn()
        try:
            def one(sql: str, *args) -> int:
                return conn.execute(sql, args).fetchone()["c"]

            up = one("SELECT count(*) c FROM answer_feedback WHERE rating = 1")
            down = one("SELECT count(*) c FROM answer_feedback WHERE rating = -1")
            return {
                "ratings": up + down,
                "positive": up,
                "negative": down,
                "satisfaction": round(up / (up + down), 3) if up + down else None,
                "suppressed_pairs": one(
                    "SELECT count(*) c FROM suppressed_pair WHERE cleared_at IS NULL"),
                "open_tasks": one(
                    "SELECT count(*) c FROM curation_task WHERE state = 'open'"),
                "acted_on": one(
                    "SELECT count(*) c FROM curation_task WHERE state != 'open'"),
                "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        finally:
            conn.close()


def demo() -> None:
    """Self-check: one rating is noise, two suppress, and a curator can overrule."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        store = FeedbackStore(str(Path(tmp) / "f.db"))
        q, item = "how do I sell abroad", "item-ecommerce"

        first = store.rate(q, item, -1, rater="alice")
        assert first.negatives == 1 and not first.suppressed
        assert first.task_opened
        assert store.suppressed_for(q) == frozenset()

        # The same person again must not manufacture a second opinion.
        again = store.rate(q, item, -1, rater="alice")
        assert again.negatives == 1, again.negatives
        assert not again.suppressed
        assert not again.task_opened, "the task already exists"

        second = store.rate(q, item, -1, rater="bob")
        assert second.negatives == 2 and second.suppressed
        assert store.suppressed_for(q) == frozenset({item})

        # Suppression is per question, never corpus-wide.
        assert store.suppressed_for("something else entirely") == frozenset()

        # A curator overruling the raters lifts it, and the old votes cannot
        # re-suppress it afterwards.
        task = store.tasks()[0]
        assert task["negatives"] == 2
        assert store.resolve_task(task["id"], "rating_wrong", "Record is correct.")
        assert store.suppressed_for(q) == frozenset()
        assert store.rate(q, item, -1, rater="carol").negatives == 1

        s = store.summary()
        assert s["negative"] == 1 and s["acted_on"] == 1
        print("feedback: checks passed, one rating is noise and two withhold")


if __name__ == "__main__":
    demo()
