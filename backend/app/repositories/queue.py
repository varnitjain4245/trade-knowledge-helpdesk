"""Queue repository (lld-backend-pass2.md §6.6).

``claim_next`` is the **only** dequeue path in the system. A plain read would let two
assignment workers pick the same conversation and assign it twice; ``FOR UPDATE SKIP
LOCKED`` lets them proceed in parallel on *different* entries instead, which is both
correct and faster than serialising on the queue head.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class QueueEntry:
    conversation_id: UUID
    language: str
    enqueued_at: datetime
    attempts: int
    escalated: bool


class QueueRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def enqueue(self, conversation_id: UUID, language: str) -> QueueEntry:
        """Idempotent on conversation_id (primary key).

        Re-enqueueing an already-queued conversation returns the existing entry rather
        than duplicating it, which is what makes agent release and heartbeat expiry safe
        to retry — both paths re-enqueue and both can run twice.
        """
        row = self._session.execute(
            text(
                """
                INSERT INTO queue_entry (conversation_id, language)
                VALUES (:cid, :lang)
                ON CONFLICT (conversation_id) DO UPDATE SET language = queue_entry.language
                RETURNING conversation_id, language, enqueued_at, attempts, escalated
                """
            ),
            {"cid": conversation_id, "lang": language},
        ).mappings().one()
        return QueueEntry(**row)

    def claim_next(self) -> QueueEntry | None:
        """SELECT ... FOR UPDATE SKIP LOCKED, oldest first, excluding escalated entries.

        Precondition: caller holds an open transaction; the claim is held until that
        transaction ends.
        Returns None on an empty queue — never blocks, never raises.
        """
        if not self._session.in_transaction():
            raise RuntimeError("claim_next requires an open transaction")
        row = self._session.execute(
            text(
                """
                SELECT conversation_id, language, enqueued_at, attempts, escalated
                  FROM queue_entry
                 WHERE NOT escalated
                 ORDER BY enqueued_at
                 FOR UPDATE SKIP LOCKED
                 LIMIT 1
                """
            )
        ).mappings().first()
        return QueueEntry(**row) if row else None

    def record_attempt(self, conversation_id: UUID, escalate: bool) -> None:
        """Increment the attempt count, optionally escalating.

        The entry is **never deleted here**. REQ-008 requires that a conversation which
        cannot be assigned stays open and becomes visible to a supervisor rather than
        disappearing — losing it silently is the failure this method exists to prevent.
        """
        self._session.execute(
            text(
                """
                UPDATE queue_entry
                   SET attempts = attempts + 1,
                       last_attempt_at = now(),
                       escalated = escalated OR :escalate
                 WHERE conversation_id = :cid
                """
            ),
            {"cid": conversation_id, "escalate": escalate},
        )

    def delete(self, conversation_id: UUID) -> None:
        """Remove an entry. Called only on successful assignment or a terminal outcome."""
        self._session.execute(
            text("DELETE FROM queue_entry WHERE conversation_id = :cid"),
            {"cid": conversation_id},
        )

    def depth(self) -> dict[str, int]:
        """Queue depth by language — the operational signal behind the alert rules."""
        rows = self._session.execute(
            text("SELECT language, count(*) FROM queue_entry WHERE NOT escalated GROUP BY language")
        ).all()
        return {row[0]: row[1] for row in rows}

    def escalations(self) -> list[QueueEntry]:
        rows = self._session.execute(
            text(
                """
                SELECT conversation_id, language, enqueued_at, attempts, escalated
                  FROM queue_entry WHERE escalated ORDER BY enqueued_at
                """
            )
        ).mappings().all()
        return [QueueEntry(**r) for r in rows]
