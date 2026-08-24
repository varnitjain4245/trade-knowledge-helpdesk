"""Watching the departments that publish the guidance this desk answers from.

A corpus is a snapshot. Trade guidance is not: DGFT issues notifications, public notices
and policy circulars continuously, CBIC issues customs circulars and instructions, and a
helpdesk whose knowledge was typed in once begins going wrong the day after it is
written. The lifecycle machinery already handles a record becoming superseded; what was
missing is anything that notices a superseding document exists.

This polls a feed, and turns each new entry into a record for review.

**Nothing ingested here can answer.** Every entry enters at ``pending_review``, the same
state a machine-drafted record enters at, for the same reason: a parser that could
publish into the answerable set would make every citation only as trustworthy as the
parser, and an HTML change on a government website would silently become a wrong answer
carrying an official-looking source. A curator promotes it or it never answers.

**A feed entry is a pointer, not a record.** An RSS summary is a headline and a link,
not the text of a circular. What is ingested is the announcement, marked as such, with
the link to the document. Presenting a two-line RSS blurb as though it were the
provision it announces would be exactly the unsourced assertion the rest of the system
refuses to make.

On sources: the two departments' published pages are recorded below, but no public RSS
endpoint for either was confirmed at the time of writing, so neither ships enabled with
a fabricated feed URL. An operator configures the real endpoint — or a departmental
mailing list bridged to one — and the connector uses it. Inventing a plausible feed URL
would produce a connector that silently fetched nothing.
"""

from __future__ import annotations

import hashlib
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx

from app.core.logging import get_logger
from app.demo.db import connect

log = get_logger(__name__)

#: Where each department publishes. ``feed_url`` is empty until an operator supplies a
#: real one; the page URL is recorded so the source is documented either way.
SOURCES: dict[str, dict] = {
    "dgft_regulatory": {
        "authority": "Directorate General of Foreign Trade",
        "page": "https://www.dgft.gov.in/CP/?opt=regulatory-updates",
        "feed_url": "",
        "topic": "trade_policy",
        "kinds": ["Notification", "Public Notice", "Policy Circular", "Trade Notice"],
    },
    "cbic_customs": {
        "authority": "Central Board of Indirect Taxes and Customs",
        "page": "https://beta.cbic.gov.in/Customs-Circulars-Instructions",
        "feed_url": "",
        "topic": "customs_procedure",
        "kinds": ["Circular", "Instruction"],
    },
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feed_entry (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT    NOT NULL,
    guid         TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    link         TEXT    NOT NULL DEFAULT '',
    summary      TEXT    NOT NULL DEFAULT '',
    published    TEXT    NOT NULL DEFAULT '',
    -- new -> drafted | ignored. Never 'approved': see the module docstring.
    state        TEXT    NOT NULL DEFAULT 'new',
    seen_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (state IN ('new','drafted','ignored'))
);
-- The guid is what makes a poll idempotent. Without it every poll re-ingests the whole
-- feed and the review queue fills with duplicates of things already handled.
CREATE UNIQUE INDEX IF NOT EXISTS idx_feed_guid ON feed_entry(source, guid);
CREATE INDEX IF NOT EXISTS idx_feed_state ON feed_entry(state, seen_at DESC);
"""


@dataclass(frozen=True)
class Entry:
    source: str
    guid: str
    title: str
    link: str
    summary: str
    published: str

    def as_record(self, authority: str, topic: str) -> dict:
        """A record a curator can review. Marked as an announcement, not a provision."""
        return {
            "title": self.title[:180],
            "authority": authority,
            "issued": (self.published or date.today().isoformat())[:10],
            "topic": topic,
            "status": "pending_review",
            "passages": [
                f"{self.title}. {self.summary}".strip()
                + f" Announced by {authority}."
                + (f" Full text: {self.link}" if self.link else "")
                + " This entry records the announcement only; the operative text is in"
                  " the document itself and must be read into the record before it is"
                  " approved."
            ],
            "source_link": self.link,
        }


def _text(node, *names: str) -> str:  # noqa: ANN001
    for name in names:
        found = node.find(name)
        if found is not None and (found.text or "").strip():
            return (found.text or "").strip()
        # Atom puts the URL in an attribute rather than the element text.
        if found is not None and found.get("href"):
            return found.get("href", "")
    return ""


def parse_feed(xml_text: str, source: str) -> list[Entry]:
    """Parse RSS 2.0 or Atom. Both, because departments use both.

    A malformed feed returns nothing rather than raising: a government site serving a
    broken document should not take a helpdesk down with it.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("feeds.unparseable", source=source, error=str(exc))
        return []

    atom = "{http://www.w3.org/2005/Atom}"
    items = root.findall(".//item") or root.findall(f".//{atom}entry")

    entries: list[Entry] = []
    for item in items:
        title = _text(item, "title", f"{atom}title")
        if not title:
            continue
        link = _text(item, "link", f"{atom}link")
        summary = _text(item, "description", "summary", f"{atom}summary",
                        f"{atom}content")
        published = _text(item, "pubDate", "date", f"{atom}published", f"{atom}updated")
        guid = _text(item, "guid", "id", f"{atom}id") or link or \
            hashlib.sha256(title.encode()).hexdigest()[:32]
        entries.append(Entry(source=source, guid=guid, title=title, link=link,
                             summary=summary[:600], published=published))
    return entries


class FeedWatcher:
    def __init__(self, database_path: str, sources: dict | None = None) -> None:
        self._path = database_path
        self.sources = sources if sources is not None else SOURCES
        conn = connect(self._path)
        try:
            with conn:
                conn.executescript(_SCHEMA)
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        return connect(self._path)

    @property
    def configured(self) -> list[str]:
        return [k for k, v in self.sources.items() if v.get("feed_url")]

    async def poll(self, source: str) -> dict:
        """Fetch one source and store entries not seen before."""
        if source not in self.sources:
            raise KeyError(f"unknown source: {source}")
        url = self.sources[source].get("feed_url")
        if not url:
            raise RuntimeError(
                f"No feed URL configured for {source}. Set one from "
                f"{self.sources[source]['page']} rather than guessing an endpoint."
            )
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "scc-knowledge-platform/0.1"})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("feeds.unreachable", source=source, error=str(exc))
            return {"source": source, "reachable": False, "new": 0, "error": str(exc)}

        return {"source": source, "reachable": True,
                **self.store(parse_feed(response.text, source))}

    def store(self, entries: list[Entry]) -> dict:
        """Insert entries not already seen. Returns how many were genuinely new."""
        new = 0
        conn = self._conn()
        try:
            with conn:
                for entry in entries:
                    cur = conn.execute(
                        "INSERT OR IGNORE INTO feed_entry(source, guid, title, link,"
                        " summary, published) VALUES (?,?,?,?,?,?)",
                        (entry.source, entry.guid, entry.title, entry.link,
                         entry.summary, entry.published))
                    new += cur.rowcount
        finally:
            conn.close()
        if new:
            log.info("feeds.new_entries", count=new)
        return {"seen": len(entries), "new": new}

    def pending(self, limit: int = 50) -> list[dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM feed_entry WHERE state = 'new'"
                " ORDER BY seen_at DESC LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def to_records(self, limit: int = 20) -> list[dict]:
        """Turn pending entries into records for the curation queue."""
        out = []
        for row in self.pending(limit):
            meta = self.sources.get(row["source"], {})
            entry = Entry(row["source"], row["guid"], row["title"], row["link"],
                          row["summary"], row["published"])
            out.append(entry.as_record(meta.get("authority", "Unknown"),
                                       meta.get("topic", "trade_policy")))
        return out

    def mark(self, source: str, guid: str, state: str) -> bool:
        if state not in ("drafted", "ignored"):
            raise ValueError("a feed entry is marked drafted or ignored")
        conn = self._conn()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE feed_entry SET state = ? WHERE source = ? AND guid = ?",
                    (state, source, guid))
        finally:
            conn.close()
        return cur.rowcount > 0

    def summary(self) -> dict:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT state, count(*) c FROM feed_entry GROUP BY state").fetchall()
        finally:
            conn.close()
        return {
            "sources": {k: {"authority": v["authority"], "page": v["page"],
                            "configured": bool(v.get("feed_url"))}
                        for k, v in self.sources.items()},
            "configured_sources": self.configured,
            "entries": {r["state"]: r["c"] for r in rows},
            "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": ("Feed entries enter at pending_review and record the announcement "
                     "only. The operative text must be read into the record before a "
                     "curator approves it."),
        }


def demo() -> None:
    """Self-check: parsing, idempotence, and the rule that nothing arrives answerable."""
    import asyncio
    import tempfile
    from pathlib import Path

    rss = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>Notification 42/2026 — Amendment to export policy of onions</title>
        <link>https://example.gov.in/n42</link><guid>n-42-2026</guid>
        <description>Export policy amended.</description>
        <pubDate>2026-08-20</pubDate></item>
      <item><title>Public Notice 11/2026 — RoDTEP rate revision</title>
        <link>https://example.gov.in/pn11</link><guid>pn-11-2026</guid>
        <description>Rates revised.</description><pubDate>2026-08-18</pubDate></item>
    </channel></rss>"""

    entries = parse_feed(rss, "dgft_regulatory")
    assert len(entries) == 2
    assert entries[0].guid == "n-42-2026"

    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Circular 7/2026 — Bill of entry timelines</title>
        <link href="https://example.gov.in/c7"/><id>c-7-2026</id>
        <summary>Timelines clarified.</summary>
        <updated>2026-08-19</updated></entry></feed>"""
    atom_entries = parse_feed(atom, "cbic_customs")
    assert len(atom_entries) == 1
    assert atom_entries[0].link == "https://example.gov.in/c7"

    # A broken feed must not raise; a department's bad XML is not this desk's outage.
    assert parse_feed("<not xml", "dgft_regulatory") == []

    with tempfile.TemporaryDirectory() as tmp:
        watcher = FeedWatcher(str(Path(tmp) / "f.db"))

        assert watcher.store(entries) == {"seen": 2, "new": 2}
        # Polling again must add nothing: that is what the guid index is for.
        assert watcher.store(entries) == {"seen": 2, "new": 0}
        assert watcher.store(atom_entries)["new"] == 1

        records = watcher.to_records()
        assert len(records) == 3
        for record in records:
            # The rule the module exists to hold.
            assert record["status"] == "pending_review"
            assert record["status"] not in ("approved", "stale")
            assert "announcement only" in record["passages"][0]
            assert record["authority"] in (
                "Directorate General of Foreign Trade",
                "Central Board of Indirect Taxes and Customs")

        assert watcher.mark("dgft_regulatory", "n-42-2026", "drafted")
        assert not watcher.mark("dgft_regulatory", "nope", "drafted")
        assert len(watcher.pending()) == 2

        try:
            watcher.mark("dgft_regulatory", "pn-11-2026", "approved")
        except ValueError:
            pass
        else:
            raise AssertionError("a feed entry must never be markable as approved")

        # No fabricated endpoint: an unconfigured source refuses rather than pretending.
        assert watcher.configured == []
        try:
            asyncio.run(watcher.poll("dgft_regulatory"))
        except RuntimeError as exc:
            assert "No feed URL configured" in str(exc)
        else:
            raise AssertionError("must refuse to poll an unconfigured source")

        try:
            asyncio.run(watcher.poll("not_a_source"))
        except KeyError:
            pass
        else:
            raise AssertionError("unknown source must be refused")

    print("feeds: checks passed, ingestion is idempotent and never answerable")


if __name__ == "__main__":
    demo()
