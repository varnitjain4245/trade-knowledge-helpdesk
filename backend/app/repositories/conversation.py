"""Conversation and message repositories (lld-backend-pass2.md §6.6).

``get_for_update`` exists because turn ordering and ``below_bar_streak`` are both
order-dependent: two rapid customer messages must not interleave their state updates, or
the two-consecutive-below-bar rule (REQ-007) silently miscounts.

``idle_longer_than`` streams rather than materialises — the inactivity sweep may touch
many rows and must not hold them all in memory.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.state import ConversationState


@dataclass
class Conversation:
    id: UUID
    surface: str
    state: ConversationState
    detected_language: str
    chosen_language: str | None
    below_bar_streak: int
    retired_source_flag: bool
    started_at: datetime
    last_activity_at: datetime
    ended_at: datetime | None

    @property
    def language(self) -> str:
        """Explicit choice wins over detection (REQ-001)."""
        return self.chosen_language or self.detected_language


_COLS = """
    id, surface, state, detected_language, chosen_language, below_bar_streak,
    retired_source_flag, started_at, last_activity_at, ended_at
"""


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, conversation_id: UUID, surface: str, state: ConversationState,
        detected_language: str, customer_token_hash: bytes | None,
        customer_key_hash: bytes | None,
    ) -> Conversation:
        row = self._session.execute(
            text(
                f"""
                INSERT INTO conversation
                    (id, surface, state, detected_language, customer_token_hash,
                     customer_key_hash)
                VALUES (:id, :surface, :state, :lang, :token_hash, :key_hash)
                RETURNING {_COLS}
                """
            ),
            {
                "id": conversation_id, "surface": surface, "state": state.value,
                "lang": detected_language, "token_hash": customer_token_hash,
                "key_hash": customer_key_hash,
            },
        ).mappings().one()
        return Conversation(**{**row, "state": ConversationState(row["state"])})

    def get(self, conversation_id: UUID) -> Conversation | None:
        row = self._session.execute(
            text(f"SELECT {_COLS} FROM conversation WHERE id = :id"),
            {"id": conversation_id},
        ).mappings().first()
        return Conversation(**{**row, "state": ConversationState(row["state"])}) if row else None

    def get_for_update(self, conversation_id: UUID) -> Conversation | None:
        """Row lock for turn ordering. Precondition: open transaction."""
        if not self._session.in_transaction():
            raise RuntimeError("get_for_update requires an open transaction")
        row = self._session.execute(
            text(f"SELECT {_COLS} FROM conversation WHERE id = :id FOR UPDATE"),
            {"id": conversation_id},
        ).mappings().first()
        return Conversation(**{**row, "state": ConversationState(row["state"])}) if row else None

    def save(self, conversation: Conversation) -> None:
        self._session.execute(
            text(
                """
                UPDATE conversation
                   SET state = :state, chosen_language = :chosen,
                       below_bar_streak = :streak,
                       retired_source_flag = :retired,
                       last_activity_at = :last_activity,
                       ended_at = :ended_at
                 WHERE id = :id
                """
            ),
            {
                "id": conversation.id, "state": conversation.state.value,
                "chosen": conversation.chosen_language,
                "streak": conversation.below_bar_streak,
                "retired": conversation.retired_source_flag,
                "last_activity": conversation.last_activity_at,
                "ended_at": conversation.ended_at,
            },
        )

    def idle_longer_than(
        self, limit: timedelta, states: frozenset[ConversationState]
    ) -> Iterator[Conversation]:
        """Stream conversations idle past the boundary. Uses idx_conv_active_inactivity."""
        result = self._session.execute(
            text(
                f"""
                SELECT {_COLS} FROM conversation
                 WHERE state = ANY(:states)
                   AND last_activity_at < now() - CAST(:seconds || ' seconds' AS interval)
                """
            ),
            {"states": [s.value for s in states], "seconds": int(limit.total_seconds())},
        ).mappings()
        for row in result:
            yield Conversation(**{**row, "state": ConversationState(row["state"])})

    def by_customer_key(self, key_hash: bytes) -> list[UUID]:
        """Conversations sharing a pseudonymous customer key.

        Serves both the repeat-contact guardrail and erasure. Only links contacts from
        the same browser — which is why every figure derived from it is a lower bound
        and every erasure reports its resolved scope before executing.
        """
        rows = self._session.execute(
            text("SELECT id FROM conversation WHERE customer_key_hash = :key"),
            {"key": key_hash},
        ).scalars().all()
        return list(rows)

    def flag_retired_source(self, conversation_id: UUID) -> None:
        """BR-12: the handling agent is told an item they cited has been retired."""
        self._session.execute(
            text("UPDATE conversation SET retired_source_flag = TRUE WHERE id = :id"),
            {"id": conversation_id},
        )


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self, conversation_id: UUID, author: str, body: str, language: str,
        agent_id: int | None = None, answer_id: UUID | None = None,
    ) -> int:
        """Append a turn.

        The body is stored **unmasked**: this is the live transcript an agent needs to
        do their job. REQ-015 scopes masking to content stored *for analytics, gap
        entries or reuse*, and the transcript is protected by retention and access
        control instead (pass 3 §6.5).
        """
        return self._session.execute(
            text(
                """
                INSERT INTO message (conversation_id, author, agent_id, body, language,
                                     answer_id)
                VALUES (:cid, :author, :agent_id, :body, :language, :answer_id)
                RETURNING id
                """
            ),
            {
                "cid": conversation_id, "author": author, "agent_id": agent_id,
                "body": body, "language": language, "answer_id": answer_id,
            },
        ).scalar_one()

    def recent(self, conversation_id: UUID, limit: int) -> list[dict]:
        """Most recent turns, oldest first — follow-up context for the answer path."""
        rows = self._session.execute(
            text(
                """
                SELECT author, body, language, created_at FROM (
                    SELECT author, body, language, created_at
                      FROM message WHERE conversation_id = :cid
                     ORDER BY created_at DESC LIMIT :limit
                ) recent ORDER BY created_at
                """
            ),
            {"cid": conversation_id, "limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]

    def all_for(self, conversation_id: UUID) -> list[dict]:
        rows = self._session.execute(
            text(
                """
                SELECT id, author, agent_id, body, language, answer_id, created_at
                  FROM message WHERE conversation_id = :cid ORDER BY created_at
                """
            ),
            {"cid": conversation_id},
        ).mappings().all()
        return [dict(r) for r in rows]
