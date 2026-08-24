"""Assignment and assist-usage repositories.

``assignment`` is the authoritative record of who holds what; ``agent_presence`` is only
an advisory fast path over it (pass 2 §7.2).

``AssistUsageRepository`` is insert-only except for the rating columns, matching the
grant in migration 005. An assist record must not be rewritten after the fact — it is
evidence for the wrong-answer-versus-adoption guardrail, and evidence that can be edited
is not evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class Assignment:
    id: int
    conversation_id: UUID
    agent_id: int
    language_matched: bool
    wait_seconds: int
    assigned_at: datetime
    ended_at: datetime | None
    end_state: str | None


class AssignmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, conversation_id: UUID, agent_id: int, language_matched: bool,
        wait_seconds: int,
    ) -> Assignment:
        row = self._session.execute(
            text(
                """
                INSERT INTO assignment
                    (conversation_id, agent_id, language_matched, wait_seconds)
                VALUES (:cid, :agent_id, :matched, :wait)
                RETURNING id, conversation_id, agent_id, language_matched, wait_seconds,
                          assigned_at, ended_at, end_state
                """
            ),
            {
                "cid": conversation_id, "agent_id": agent_id,
                "matched": language_matched, "wait": wait_seconds,
            },
        ).mappings().one()
        return Assignment(**row)

    def close(self, conversation_id: UUID, agent_id: int, end_state: str) -> None:
        self._session.execute(
            text(
                """
                UPDATE assignment SET ended_at = now(), end_state = :end_state
                 WHERE conversation_id = :cid AND agent_id = :agent_id
                   AND ended_at IS NULL
                """
            ),
            {"cid": conversation_id, "agent_id": agent_id, "end_state": end_state},
        )

    def open_for_agent(self, agent_id: int) -> Assignment | None:
        """The authoritative answer to "is this agent free". Uses idx_assignment_agent_open."""
        row = self._session.execute(
            text(
                """
                SELECT id, conversation_id, agent_id, language_matched, wait_seconds,
                       assigned_at, ended_at, end_state
                  FROM assignment WHERE agent_id = :agent_id AND ended_at IS NULL
                 ORDER BY assigned_at DESC LIMIT 1
                """
            ),
            {"agent_id": agent_id},
        ).mappings().first()
        return Assignment(**row) if row else None

    def current_for_conversation(self, conversation_id: UUID) -> Assignment | None:
        row = self._session.execute(
            text(
                """
                SELECT id, conversation_id, agent_id, language_matched, wait_seconds,
                       assigned_at, ended_at, end_state
                  FROM assignment WHERE conversation_id = :cid AND ended_at IS NULL
                 ORDER BY assigned_at DESC LIMIT 1
                """
            ),
            {"cid": conversation_id},
        ).mappings().first()
        return Assignment(**row) if row else None


class AssistUsageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self, conversation_id: UUID, agent_id: int, answer_id: UUID, accepted: bool,
        edited_before_send: bool | None = None, sent_message_id: int | None = None,
    ) -> int:
        """Insert-only, within the caller's transaction.

        ``edited_before_send`` is the server's determination, never the client's claim —
        a client that lied would corrupt the REQ-014 audit trail and the wrong-answer
        guardrail simultaneously.
        """
        return self._session.execute(
            text(
                """
                INSERT INTO assist_usage
                    (conversation_id, agent_id, answer_id, accepted, edited_before_send,
                     sent_message_id)
                VALUES (:cid, :agent_id, :answer_id, :accepted, :edited, :msg_id)
                RETURNING id
                """
            ),
            {
                "cid": conversation_id, "agent_id": agent_id, "answer_id": answer_id,
                "accepted": accepted, "edited": edited_before_send,
                "msg_id": sent_message_id,
            },
        ).scalar_one()

    def rate(self, answer_id: UUID, agent_id: int, rating: int) -> None:
        """Set a rating once. The only UPDATE the application role is granted here."""
        if rating not in (-1, 1):
            raise ValueError("rating must be -1 or 1")
        self._session.execute(
            text(
                """
                UPDATE assist_usage SET rating = :rating, rated_at = now()
                 WHERE answer_id = :answer_id AND agent_id = :agent_id
                   AND rating IS NULL
                """
            ),
            {"answer_id": answer_id, "agent_id": agent_id, "rating": rating},
        )
