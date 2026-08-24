"""Things the desk can do, not just explain.

The commercial contact-centre agents resolve rather than answer: they issue the refund,
change the subscription, update the account. That is the capability gap between
explaining a process and completing it, and it is the largest one this system has.

The gap cannot be closed the same way here, and the reason is not technical. Those
systems act inside the account of the company that operates them. This system explains
Indian trade administration; it holds no authority over DGFT, CBIC or GSTN, and an
action that filed a real application with a real department on somebody's behalf would
be asserting an authority it does not have. A prototype that appeared to file a customs
declaration would be worse than one that could not, because a person would believe the
declaration was filed.

So the rule for every action here: **it must be within this system's own authority, and
it must be reversible.** What that leaves is real and useful:

  lodge_grievance      Creates a tracked grievance with a reference and an escalation
                       ladder. Within authority because the ladder is this system's.
  request_callback     Records that somebody wants to be rung back.
  remind_deadline      Sets a reminder before a scheme window closes.
  prepare_application  Assembles the checklist and the documents a scheme needs, ready
                       to carry to the department's own portal. It prepares; it does
                       not submit, and it says so.
  watch_record         Notifies the person when a cited record is superseded or
                       retired. This one is only possible *because* of the lifecycle
                       machinery already built, and it is the most useful of the five:
                       guidance changes, and the person who acted on the old version is
                       the one who needs to know.

Every action is offered only when the answer that triggered it actually supports it, is
confirmed by the person before it runs, and is written to the audit record. None of them
sends anything to a government system.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.core.logging import get_logger
from app.demo.db import connect

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS action_record (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT    NOT NULL,
    user_id      INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
    contact      TEXT    NOT NULL DEFAULT '',
    subject      TEXT    NOT NULL DEFAULT '',
    payload      TEXT    NOT NULL DEFAULT '',
    -- pending -> done | cancelled. Every action here is reversible by design.
    state        TEXT    NOT NULL DEFAULT 'pending',
    due_at       TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (state IN ('pending','done','cancelled'))
);
CREATE INDEX IF NOT EXISTS idx_action_user ON action_record(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_due ON action_record(state, due_at);

-- Somebody watching a record for change. The lifecycle already knows when a record is
-- superseded; this is the list of people that fact matters to.
CREATE TABLE IF NOT EXISTS record_watch (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id      TEXT    NOT NULL,
    item_title   TEXT    NOT NULL DEFAULT '',
    user_id      INTEGER REFERENCES app_user(id) ON DELETE CASCADE,
    contact      TEXT    NOT NULL DEFAULT '',
    notified_at  TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watch_unique
    ON record_watch(item_id, COALESCE(user_id, -1), contact);
"""


@dataclass(frozen=True)
class ActionOffer:
    kind: str
    label: str
    detail: str
    #: Everything needed to run it, so the confirmation step carries no hidden state.
    payload: dict

    def as_dict(self) -> dict:
        return {"kind": self.kind, "label": self.label, "detail": self.detail,
                "payload": self.payload, "requires_confirmation": True}


#: What each action does and does not do, in the words shown to the person.
CATALOGUE = {
    "lodge_grievance": ("Lodge a grievance",
                        "Creates a tracked reference with an escalation ladder."),
    "request_callback": ("Ask for a callback",
                         "Records your number so somebody can ring you."),
    "remind_deadline": ("Remind me before this closes",
                        "Sets a reminder ahead of the window closing."),
    "prepare_application": ("Prepare the paperwork",
                            "Assembles the checklist to carry to the department's "
                            "own portal. It does not submit anything."),
    "watch_record": ("Tell me if this changes",
                     "Notifies you if the cited record is superseded or retired."),
}


def offers_for(result, schemes: list[dict] | None = None) -> list[ActionOffer]:
    """Which actions this particular answer supports.

    Offered from what the answer contains, not from a fixed menu. An action offered
    against an answer that cannot support it is a button that fails after it is
    pressed, which teaches people not to press any of them.
    """
    outcome = getattr(result.outcome, "value", str(result.outcome))
    out: list[ActionOffer] = []

    if outcome in ("no_answer", "blocked_coverage", "conflict"):
        # Nothing was settled, so the useful actions are the ones that reach a person.
        out.append(ActionOffer("lodge_grievance", *CATALOGUE["lodge_grievance"], {}))
        out.append(ActionOffer("request_callback", *CATALOGUE["request_callback"], {}))
        return out

    for citation in getattr(result, "citations", [])[:2]:
        out.append(ActionOffer(
            "watch_record", *CATALOGUE["watch_record"],
            {"item_id": str(citation.item_id), "item_title": citation.item_title}))

    for scheme in (schemes or []):
        if not scheme.get("eligible"):
            continue
        out.append(ActionOffer(
            "prepare_application", *CATALOGUE["prepare_application"],
            {"scheme_code": scheme["code"], "scheme_name": scheme["name"]}))
        if scheme.get("window_closes"):
            out.append(ActionOffer(
                "remind_deadline", *CATALOGUE["remind_deadline"],
                {"scheme_code": scheme["code"], "scheme_name": scheme["name"],
                 "closes": scheme["window_closes"]}))
        break

    return out


class Actions:
    def __init__(self, database_path: str) -> None:
        self._path = database_path
        conn = connect(self._path)
        try:
            with conn:
                conn.executescript(_SCHEMA)
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        return connect(self._path)

    def run(self, kind: str, payload: dict, *, user_id: int | None = None,
            contact: str = "", grievances=None) -> dict:  # noqa: ANN001
        """Execute a confirmed action. Never reaches a government system."""
        if kind not in CATALOGUE:
            raise ValueError(f"not an action this desk can take: {kind}")

        import json

        if kind == "lodge_grievance":
            if grievances is None:
                raise RuntimeError("grievance service unavailable")
            lodged = grievances.lodge(
                (payload.get("subject") or "Unresolved query")[:80],
                payload.get("detail") or payload.get("subject") or "Unresolved query",
                category=payload.get("category", "general"),
                user_id=user_id, contact=contact)
            self._record(kind, user_id, contact, lodged["reference"], payload, "done")
            return {"kind": kind, "done": True, "reference": lodged["reference"],
                    "message": f"Lodged as {lodged['reference']}."}

        if kind == "watch_record":
            conn = self._conn()
            try:
                with conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO record_watch(item_id, item_title,"
                        " user_id, contact) VALUES (?,?,?,?)",
                        (payload.get("item_id", ""), payload.get("item_title", ""),
                         user_id, contact))
            finally:
                conn.close()
            self._record(kind, user_id, contact,
                         payload.get("item_title", ""), payload, "done")
            return {"kind": kind, "done": True,
                    "message": ("You will be told if this record is superseded or "
                                "retired.")}

        if kind == "remind_deadline":
            closes = payload.get("closes")
            try:
                due = date.fromisoformat(closes) - timedelta(days=14)
            except (TypeError, ValueError):
                raise ValueError("that scheme has no closing date to remind you about")
            self._record(kind, user_id, contact, payload.get("scheme_name", ""),
                         payload, "pending", due_at=due.isoformat())
            return {"kind": kind, "done": True, "remind_on": due.isoformat(),
                    "message": f"Reminder set for {due.isoformat()}, two weeks before "
                               f"the window closes."}

        if kind == "request_callback":
            if not contact.strip():
                raise ValueError("a phone number is needed for a callback")
            self._record(kind, user_id, contact, "Callback requested", payload,
                         "pending")
            return {"kind": kind, "done": True,
                    "message": "Recorded. Somebody will ring you."}

        # prepare_application
        checklist = _checklist(payload.get("scheme_code", ""))
        self._record(kind, user_id, contact, payload.get("scheme_name", ""),
                     {**payload, "checklist": checklist}, "done")
        return {
            "kind": kind, "done": True, "checklist": checklist,
            "submitted": False,
            "message": ("Checklist prepared. This desk does not submit applications — "
                        "take this to the department's own portal."),
        }

    def _record(self, kind: str, user_id: int | None, contact: str, subject: str,
                payload: dict, state: str, due_at: str | None = None) -> None:
        import json
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO action_record(kind, user_id, contact, subject,"
                    " payload, state, due_at) VALUES (?,?,?,?,?,?,?)",
                    (kind, user_id, contact, subject, json.dumps(payload), state,
                     due_at))
        finally:
            conn.close()

    def watchers_for(self, item_id: str) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM record_watch WHERE item_id = ? AND notified_at IS NULL",
                (str(item_id),)).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def notify_watchers(self, item_id: str, what_changed: str) -> int:
        """Called when a record's lifecycle changes. Returns how many were told."""
        watchers = self.watchers_for(item_id)
        if not watchers:
            return 0
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    "UPDATE record_watch SET notified_at = datetime('now')"
                    " WHERE item_id = ? AND notified_at IS NULL", (str(item_id),))
        finally:
            conn.close()
        log.info("actions.watchers_notified", item_id=item_id,
                 count=len(watchers), change=what_changed)
        return len(watchers)

    def for_user(self, user_id: int) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT id, kind, subject, state, due_at, created_at FROM action_record"
                " WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
                (user_id,)).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT kind, count(*) c FROM action_record GROUP BY kind").fetchall()
            watches = conn.execute(
                "SELECT count(*) c FROM record_watch").fetchone()["c"]
        finally:
            conn.close()
        return {"by_kind": {r["kind"]: r["c"] for r in rows},
                "total": sum(r["c"] for r in rows), "record_watches": watches,
                "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def _checklist(scheme_code: str) -> list[str]:
    """Documents a scheme application needs.

    Generic on purpose. A scheme-specific list invented here would be exactly the sort
    of unsourced assertion the rest of the system refuses to make; a real deployment
    reads this from the scheme notification.
    """
    return [
        "Importer Exporter Code (IEC), if the scheme is export-linked",
        "Udyam registration certificate, for an MSME claim",
        "GST registration certificate",
        "PAN of the enterprise",
        "Bank account details with a cancelled cheque",
        "Audited financial statements for the relevant year",
        "The scheme's own application form from the department's portal",
    ]


def demo() -> None:
    """Self-check: actions stay inside authority and nothing is ever submitted."""
    import tempfile
    from pathlib import Path
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as tmp:
        actions = Actions(str(Path(tmp) / "a.db"))

        # An answer with citations offers a watch; a refusal offers a way to a person.
        answered = SimpleNamespace(
            outcome="answered",
            citations=[SimpleNamespace(item_id="i-1", item_title="IEC record")])
        kinds = [o.kind for o in offers_for(answered)]
        assert "watch_record" in kinds
        assert "lodge_grievance" not in kinds

        refused = SimpleNamespace(outcome="no_answer", citations=[])
        assert [o.kind for o in offers_for(refused)] == [
            "lodge_grievance", "request_callback"]

        # An eligible scheme with a window adds preparation and a reminder.
        with_scheme = offers_for(answered, schemes=[
            {"code": "MEI", "name": "MSME export incentive", "eligible": True,
             "window_closes": "2027-03-31"}])
        assert {"prepare_application", "remind_deadline"} <= {
            o.kind for o in with_scheme}
        # An ineligible scheme must not be offered at all.
        assert "prepare_application" not in {o.kind for o in offers_for(
            answered, schemes=[{"code": "X", "name": "X", "eligible": False}])}

        # The rule the whole module exists for.
        prepared = actions.run("prepare_application",
                               {"scheme_code": "MEI", "scheme_name": "MSME"})
        assert prepared["submitted"] is False
        assert "does not submit" in prepared["message"]
        assert len(prepared["checklist"]) >= 5

        watched = actions.run("watch_record",
                              {"item_id": "i-1", "item_title": "IEC record"},
                              contact="9876543210")
        assert watched["done"]
        assert len(actions.watchers_for("i-1")) == 1
        # Watching twice must not queue two notifications.
        actions.run("watch_record", {"item_id": "i-1", "item_title": "IEC record"},
                    contact="9876543210")
        assert len(actions.watchers_for("i-1")) == 1

        assert actions.notify_watchers("i-1", "superseded") == 1
        assert actions.notify_watchers("i-1", "superseded") == 0, "notified twice"

        reminder = actions.run("remind_deadline",
                               {"scheme_code": "MEI", "scheme_name": "MSME",
                                "closes": "2027-03-31"})
        assert reminder["remind_on"] == "2027-03-17"

        for bad, payload in (("request_callback", {}), ("remind_deadline", {}),
                             ("file_customs_declaration", {})):
            try:
                actions.run(bad, payload)
            except (ValueError, RuntimeError):
                pass
            else:
                raise AssertionError(f"{bad} should have been refused")

        assert actions.summary()["total"] >= 4
        print("actions: checks passed, nothing is submitted to any department")


if __name__ == "__main__":
    demo()
