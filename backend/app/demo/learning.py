"""Self-updating knowledge.

Replaces the manual gap queue. When the desk cannot answer, the question is logged and a
record is drafted automatically, so the same question is answerable the next time it is
asked.

The design constraint that shapes everything here: **a machine-drafted record must never
be indistinguishable from a published circular.** The product's whole claim is that you
can see where an answer came from. An auto-drafted record is therefore answerable but
carries its own authority line — "Machine-drafted, pending verification" — so a reader
knows the provenance differs from a DGFT notification, and a knowledge manager can
confirm or replace it.

Auto-drafting is off for anything the desk should not be inventing. A question about a
specific duty rate, a deadline or a monetary threshold is logged for a human rather than
drafted, because a plausible-sounding number is precisely the harm the citation rule
exists to prevent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger(__name__)

MACHINE_AUTHORITY = "Machine-drafted — pending verification"

#: A question turning on a specific figure is not drafted. Getting a rate or a ceiling
#: wrong is worse than saying nothing, and a model asked for one will supply it anyway.
_FIGURE_QUESTION = re.compile(
    r"\b(rate|rates|duty|tariff|percent|per cent|%|ceiling|limit|fee|"
    r"deadline|due date|last date|penalty|fine|threshold|amount|crore|lakh)\b",
    re.IGNORECASE,
)


@dataclass
class LearningEntry:
    query: str
    language: str
    cause: str
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "logged"          # logged | drafted | declined | verified
    drafted_title: str | None = None
    decline_reason: str | None = None
    times_asked: int = 1


class LearningLog:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.entries: list[LearningEntry] = []

    def _find(self, query: str) -> LearningEntry | None:
        key = " ".join(query.lower().split())
        for entry in self.entries:
            if " ".join(entry.query.lower().split()) == key:
                return entry
        return None

    def record(self, query: str, language: str, cause: str) -> LearningEntry:
        existing = self._find(query)
        if existing:
            existing.times_asked += 1
            return existing
        entry = LearningEntry(query=query, language=language, cause=cause)
        self.entries.append(entry)
        return entry

    def should_draft(self, entry: LearningEntry) -> tuple[bool, str]:
        if entry.status != "logged":
            return False, "already handled"
        if entry.cause == "conflict":
            return False, "sources disagree — a human must decide which applies"
        if _FIGURE_QUESTION.search(entry.query):
            return False, (
                "asks for a specific figure — drafting one would invent a number, "
                "which is the failure the citation rule exists to prevent"
            )
        if len(entry.query.split()) < 3:
            return False, "too short to draft against"
        return True, ""

    async def draft(self, entry: LearningEntry) -> dict | None:
        """Draft a record for a question the corpus could not answer.

        Returns the record to add, or None where drafting was declined or failed. The
        model is told to refuse rather than speculate, and a refusal is respected — a
        drafted record nobody can rely on is worse than an honest gap.
        """
        allowed, reason = self.should_draft(entry)
        if not allowed:
            entry.status = "declined"
            entry.decline_reason = reason
            return None

        if not self._settings.groq_api_key:
            entry.status = "declined"
            entry.decline_reason = "no drafting service configured"
            return None

        prompt = (
            "A trade helpdesk for India's commerce and industry administration could not "
            "answer this question from its records:\n\n"
            f"  {entry.query}\n\n"
            "Write a short reference note that would answer it, covering only settled "
            "procedure and well-established definitions. Two or three sentences.\n\n"
            "Rules:\n"
            "- State no specific rate, fee, ceiling, deadline or monetary figure. If the "
            "question cannot be answered without one, reply with exactly: DECLINE\n"
            "- If the question is outside Indian trade, commerce, MSME, customs, GST or "
            "e-commerce administration, reply with exactly: DECLINE\n"
            "- Write plainly, as guidance to a business owner. No preamble.\n\n"
            "Also give a short title on the first line, then the note on the following "
            "lines. Do not label them."
        )

        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.groq_api_key}",
                        "User-Agent": "scc-knowledge-platform/0.1",
                    },
                    json={
                        "model": self._settings.groq_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "max_tokens": 320,
                    },
                )
                response.raise_for_status()
                text = response.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as exc:
            log.warning("learning.draft_failed", error=str(exc))
            entry.decline_reason = "the drafting service was unavailable"
            return None

        if "DECLINE" in text.upper()[:40] or len(text) < 40:
            entry.status = "declined"
            entry.decline_reason = (
                "the drafting model declined — the question needs a figure or falls "
                "outside this domain"
            )
            return None

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        title = lines[0].lstrip("#*- ").strip(' "')[:160]
        body = " ".join(lines[1:]).strip() or title

        entry.status = "drafted"
        entry.drafted_title = title
        return {
            "title": title,
            "authority": MACHINE_AUTHORITY,
            "passages": [body],
            "language": entry.language,
            "topic": "auto_drafted",
        }

    def summary(self) -> dict:
        return {
            "logged": sum(1 for e in self.entries if e.status == "logged"),
            "drafted": sum(1 for e in self.entries if e.status == "drafted"),
            "declined": sum(1 for e in self.entries if e.status == "declined"),
            "verified": sum(1 for e in self.entries if e.status == "verified"),
            "total": len(self.entries),
        }
