"""Answer repository (append-only, guardrail G1).

The application role holds no UPDATE or DELETE on ``answer_record`` or
``answer_citation``, and this interface exposes no method that could express one. Two
enforcement layers for the same rule, deliberately: the grant is the guarantee, the
interface shape is what stops someone writing code that would need the grant restored.

``record`` raises rather than swallowing on failure. REQ-014 requires that an answer
shown was recorded, so the caller must **not** return an answer whose persistence failed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.errors import PersistenceError
from app.domain.state import AnswerOutcome


@dataclass(frozen=True)
class CitationRow:
    chunk_id: int
    item_id: UUID
    rank: int
    rerank_score: float


@dataclass(frozen=True)
class AnswerToRecord:
    conversation_id: UUID | None
    query_text: str            # already masked by the caller (pass 3 §6.5)
    query_language: str
    answer_language: str | None
    outcome: AnswerOutcome
    answer_text: str | None
    confidence: Decimal | None
    stale_sources: bool
    generation: int
    latency_ms: int
    citations: list[CitationRow]


class AnswerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, answer: AnswerToRecord) -> UUID:
        """Insert the answer and its citations in one transaction, then commit.

        Raises PersistenceError on failure — the caller must then not return the answer
        to the user.
        """
        answer_id = uuid4()
        try:
            self._session.execute(
                text(
                    """
                    INSERT INTO answer_record
                        (id, conversation_id, query_text, query_language, answer_language,
                         outcome, answer_text, confidence, stale_sources, generation,
                         latency_ms)
                    VALUES (:id, :conversation_id, :query_text, :query_language,
                            :answer_language, :outcome, :answer_text, :confidence,
                            :stale_sources, :generation, :latency_ms)
                    """
                ),
                {
                    "id": answer_id,
                    "conversation_id": answer.conversation_id,
                    "query_text": answer.query_text,
                    "query_language": answer.query_language,
                    "answer_language": answer.answer_language,
                    "outcome": answer.outcome.value,
                    "answer_text": answer.answer_text,
                    "confidence": answer.confidence,
                    "stale_sources": answer.stale_sources,
                    "generation": answer.generation,
                    "latency_ms": answer.latency_ms,
                },
            )
            for citation in answer.citations:
                self._session.execute(
                    text(
                        """
                        INSERT INTO answer_citation
                            (answer_id, chunk_id, item_id, rank, rerank_score)
                        VALUES (:answer_id, :chunk_id, :item_id, :rank, :score)
                        """
                    ),
                    {
                        "answer_id": answer_id,
                        "chunk_id": citation.chunk_id,
                        "item_id": citation.item_id,
                        "rank": citation.rank,
                        "score": citation.rerank_score,
                    },
                )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise PersistenceError("could not record answer") from exc
        return answer_id

    def conversations_citing(self, item_id: UUID, only_open: bool = True) -> list[UUID]:
        """Conversations that cited an item. Serves BR-12's retirement flagging.

        Read-only; uses idx_answer_citation_item.
        """
        sql = """
            SELECT DISTINCT ar.conversation_id
              FROM answer_citation ac
              JOIN answer_record ar ON ar.id = ac.answer_id
             WHERE ac.item_id = :item_id
               AND ar.conversation_id IS NOT NULL
        """
        if only_open:
            sql += """
               AND EXISTS (
                   SELECT 1 FROM conversation c
                    WHERE c.id = ar.conversation_id
                      AND c.state NOT IN ('self_resolved','agent_resolved',
                                          'callback_recorded','abandoned')
               )
            """
        rows = self._session.execute(text(sql), {"item_id": item_id}).scalars().all()
        return list(rows)

    def for_conversation(self, conversation_id: UUID) -> list[dict]:
        """Every answer attempted in a conversation, with why each was rejected.

        REQ-008 requires the receiving agent to see what was *tried*, not only what
        succeeded — an agent who repeats a failed attempt wastes the customer's time.
        """
        rows = self._session.execute(
            text(
                """
                SELECT id, outcome, confidence, answer_text, answer_language,
                       stale_sources, created_at
                  FROM answer_record
                 WHERE conversation_id = :cid
                 ORDER BY created_at
                """
            ),
            {"cid": conversation_id},
        ).mappings().all()
        return [dict(r) for r in rows]
