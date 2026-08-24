"""Grievance lodging, tracking and automatic escalation.

An answer settles a question. A grievance is what remains when the desk cannot: a
consignment held without explanation, a payment overdue past its statutory period, a
platform refusing a return. Those need an identifier the person keeps, a time by which
somebody must respond, and a route upward when nobody does.

The escalation ladder follows the CPGRAMS pattern used across Indian public grievance
redress: a nodal officer first, a sub-nodal officer, then an appellate authority. The
part that matters is that rising a level is *not* an action anybody has to remember to
take. A grievance past its due time escalates when it is next read, so an unattended
grievance becomes more visible over time rather than less — silence is the failure mode
a redress system exists to prevent, and a queue that relies on someone noticing has
already lost to it.

Escalation is monotonic. A level never falls, and each rise is written to an
append-only event log, so "this waited three weeks at level zero" stays answerable
after the fact.
"""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.demo.db import connect

#: Hours allowed at each level before the grievance rises to the next. Short, because
#: this is a demonstrable prototype: a real deployment sets these from the service
#: standard the department publishes, which is a policy decision, not a code one.
SLA_HOURS = {0: 48, 1: 72, 2: 120}

LADDER = {
    0: ("Nodal Officer", "Directorate General of Foreign Trade"),
    1: ("Sub-Nodal Officer", "Department of Commerce"),
    2: ("Appellate Authority", "Ministry of Commerce & Industry"),
}

CATEGORIES = (
    "customs_clearance",
    "licensing",
    "gst_refund",
    "delayed_payment",
    "ecommerce",
    "scheme_benefit",
    "general",
)

OPEN_STATUSES = ("lodged", "acknowledged", "under_review")


@dataclass(frozen=True)
class Grievance:
    id: int
    reference: str
    subject: str
    detail: str
    category: str
    status: str
    level: int
    assigned_to: str
    authority: str
    due_at: str
    overdue: bool
    resolution: str | None
    lodged_at: str
    events: list[dict]

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "reference": self.reference,
            "subject": self.subject,
            "detail": self.detail,
            "category": self.category,
            "status": self.status,
            "level": self.level,
            "level_name": LADDER[self.level][0],
            "assigned_to": self.assigned_to,
            "authority": self.authority,
            "due_at": self.due_at,
            "overdue": self.overdue,
            "resolution": self.resolution,
            "lodged_at": self.lodged_at,
            "events": self.events,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _due(level: int, frm: datetime | None = None) -> str:
    return ((frm or _now()) + timedelta(hours=SLA_HOURS[level])).isoformat(timespec="seconds")


def _reference() -> str:
    """A reference the person can read back over a phone line.

    Deliberately not the row id: an id discloses how many grievances exist and how
    recently this one was filed, and is guessable, which would let anyone enumerate
    other people's grievances through the tracking endpoint.
    """
    return "MOCI-" + _now().strftime("%Y%m") + "-" + secrets.token_hex(3).upper()


class Grievances:
    def __init__(self, database_path: str) -> None:
        self._path = database_path

    def _conn(self) -> sqlite3.Connection:
        return connect(self._path)

    # --- writing -----------------------------------------------------------------
    def lodge(
        self,
        subject: str,
        detail: str,
        *,
        category: str = "general",
        user_id: int | None = None,
        contact: str = "",
        language: str = "eng",
    ) -> dict:
        subject = subject.strip()
        detail = detail.strip()
        if not subject or not detail:
            raise ValueError("a grievance needs both a subject and a description")
        if category not in CATEGORIES:
            category = "general"

        reference = _reference()
        conn = self._conn()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO grievance(reference, user_id, contact, subject, detail,"
                    " category, language, due_at) VALUES (?,?,?,?,?,?,?,?)",
                    (reference, user_id, contact.strip(), subject, detail,
                     category, language, _due(0)),
                )
                gid = cur.lastrowid
                conn.execute(
                    "INSERT INTO grievance_event(grievance_id, kind, note, actor)"
                    " VALUES (?,?,?,?)",
                    (gid, "lodged", f"Assigned to {LADDER[0][0]}, {LADDER[0][1]}",
                     "citizen"),
                )
        finally:
            conn.close()
        return self.track(reference).as_dict()

    def update_status(self, reference: str, status: str, note: str = "",
                      actor: str = "officer") -> dict | None:
        if status not in ("acknowledged", "under_review", "resolved", "closed"):
            raise ValueError(f"not a status a grievance can be moved to: {status}")
        conn = self._conn()
        try:
            with conn:
                row = conn.execute(
                    "SELECT id FROM grievance WHERE reference = ?", (reference,)
                ).fetchone()
                if row is None:
                    return None
                conn.execute(
                    "UPDATE grievance SET status = ?, resolution = COALESCE(?, resolution),"
                    " updated_at = datetime('now') WHERE id = ?",
                    (status, note or None, row["id"]),
                )
                conn.execute(
                    "INSERT INTO grievance_event(grievance_id, kind, note, actor)"
                    " VALUES (?,?,?,?)",
                    (row["id"], status, note, actor),
                )
        finally:
            conn.close()
        g = self.track(reference)
        return g.as_dict() if g else None

    # --- escalation --------------------------------------------------------------
    def escalate_overdue(self) -> int:
        """Raise every open grievance past its due time. Returns how many moved.

        Called on read rather than from a scheduler, because a prototype with no
        always-on worker would otherwise show an escalation ladder that never moves.
        The condition is on the stored due instant, so the outcome is the same either
        way — a cron job would find exactly these rows.
        """
        now = _now().isoformat(timespec="seconds")
        moved = 0
        conn = self._conn()
        try:
            with conn:
                rows = conn.execute(
                    "SELECT id, reference, level FROM grievance"
                    f" WHERE status IN {OPEN_STATUSES} AND due_at < ? AND level < 2",
                    (now,),
                ).fetchall()
                for row in rows:
                    level = row["level"] + 1
                    officer, authority = LADDER[level]
                    conn.execute(
                        "UPDATE grievance SET level = ?, assigned_to = ?, due_at = ?,"
                        " status = 'under_review', updated_at = datetime('now')"
                        " WHERE id = ?",
                        (level, officer, _due(level), row["id"]),
                    )
                    conn.execute(
                        "INSERT INTO grievance_event(grievance_id, kind, note, actor)"
                        " VALUES (?,?,?,?)",
                        (row["id"], "escalated",
                         f"No response within {SLA_HOURS[level - 1]}h. "
                         f"Raised to {officer}, {authority}.",
                         "system"),
                    )
                    moved += 1
        finally:
            conn.close()
        return moved

    # --- reading -----------------------------------------------------------------
    def track(self, reference: str) -> Grievance | None:
        self.escalate_overdue()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM grievance WHERE reference = ?", (reference.strip().upper(),)
            ).fetchone()
            if row is None:
                return None
            events = [
                {"kind": e["kind"], "note": e["note"], "actor": e["actor"], "at": e["at"]}
                for e in conn.execute(
                    "SELECT kind, note, actor, at FROM grievance_event"
                    " WHERE grievance_id = ? ORDER BY at, id",
                    (row["id"],),
                )
            ]
        finally:
            conn.close()
        return self._row_to_grievance(row, events)

    def for_user(self, user_id: int) -> list[dict]:
        self.escalate_overdue()
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM grievance WHERE user_id = ? ORDER BY lodged_at DESC",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()
        return [self._row_to_grievance(r, []).as_dict() for r in rows]

    def queue(self, limit: int = 50) -> list[dict]:
        """The officer's view: open grievances, most overdue first."""
        self.escalate_overdue()
        conn = self._conn()
        try:
            rows = conn.execute(
                f"SELECT * FROM grievance WHERE status IN {OPEN_STATUSES}"
                " ORDER BY due_at LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [self._row_to_grievance(r, []).as_dict() for r in rows]

    def summary(self) -> dict:
        self.escalate_overdue()
        now = _now().isoformat(timespec="seconds")
        conn = self._conn()
        try:
            total = conn.execute("SELECT count(*) c FROM grievance").fetchone()["c"]
            open_ = conn.execute(
                f"SELECT count(*) c FROM grievance WHERE status IN {OPEN_STATUSES}"
            ).fetchone()["c"]
            resolved = conn.execute(
                "SELECT count(*) c FROM grievance WHERE status = 'resolved'"
            ).fetchone()["c"]
            overdue = conn.execute(
                f"SELECT count(*) c FROM grievance WHERE status IN {OPEN_STATUSES}"
                " AND due_at < ?", (now,)
            ).fetchone()["c"]
            escalated = conn.execute(
                "SELECT count(*) c FROM grievance WHERE level > 0"
            ).fetchone()["c"]
        finally:
            conn.close()
        return {
            "total": total, "open": open_, "resolved": resolved,
            "overdue": overdue, "escalated": escalated,
            "resolution_rate": round(resolved / total, 3) if total else 0.0,
        }

    @staticmethod
    def _row_to_grievance(row: sqlite3.Row, events: list[dict]) -> Grievance:
        due = row["due_at"]
        return Grievance(
            id=row["id"], reference=row["reference"], subject=row["subject"],
            detail=row["detail"], category=row["category"], status=row["status"],
            level=row["level"], assigned_to=row["assigned_to"],
            authority=LADDER[row["level"]][1], due_at=due,
            overdue=(row["status"] in OPEN_STATUSES
                     and due < _now().isoformat(timespec="seconds")),
            resolution=row["resolution"], lodged_at=row["lodged_at"], events=events,
        )


def demo() -> None:
    """Self-check: lodge, escalate on a breached clock, and confirm level is monotonic."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "g.db")
        g = Grievances(db)

        first = g.lodge("Consignment held at Nhava Sheva",
                        "Bill of entry filed on the 3rd, no assessment since.",
                        category="customs_clearance", contact="9876543210")
        assert first["level"] == 0 and first["status"] == "lodged"
        assert first["reference"].startswith("MOCI-")

        # Breach the clock by hand, exactly as the passage of time would.
        conn = connect(db)
        with conn:
            conn.execute("UPDATE grievance SET due_at = ? WHERE reference = ?",
                         ("2020-01-01T00:00:00", first["reference"]))
        conn.close()

        moved = g.escalate_overdue()
        assert moved == 1, moved
        after = g.track(first["reference"]).as_dict()
        assert after["level"] == 1, after["level"]
        assert after["assigned_to"] == "Sub-Nodal Officer"
        assert any(e["kind"] == "escalated" for e in after["events"])

        # Escalation must never run twice on a clock it has already reset.
        assert g.escalate_overdue() == 0
        assert g.track(first["reference"]).level == 1

        # A resolved grievance stops escalating even if its clock is long past.
        g.update_status(first["reference"], "resolved", "Assessment completed.")
        conn = connect(db)
        with conn:
            conn.execute("UPDATE grievance SET due_at = '2020-01-01T00:00:00'")
        conn.close()
        assert g.escalate_overdue() == 0
        assert g.track(first["reference"]).level == 1

        s = g.summary()
        assert s == {**s, "total": 1, "resolved": 1, "open": 0}
        print("grievances: all checks passed")


if __name__ == "__main__":
    demo()
