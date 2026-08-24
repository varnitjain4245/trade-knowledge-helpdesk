"""Repository protocols and shared value objects.

Interfaces are split by consumer, not by table (ISP, LLD §5): the ingestion worker needs
chunk *writes* and never touches answers; the answer path needs chunk *reads* and never
writes items. A single combined repository would force the hot path to depend on write
methods it must never call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ScoredChunk:
    """A retrieval candidate, carrying everything a citation needs (BR-2)."""

    chunk_id: int
    item_id: UUID
    body: str
    heading_path: str | None
    item_title: str
    issuing_authority: str
    issued_on: date
    item_language: str
    item_is_stale: bool
    dense_score: float
    lexical_score: float
    rerank_score: float | None = None

    @property
    def score(self) -> float:
        """Rerank score when present, otherwise the fused retrieval score.

        Falling back to the fused score matters: when rerank times out the answer path
        still needs an ordering, but it also caps confidence below the answer bar so a
        badly-ranked answer is never shown (LLD §4.6).
        """
        if self.rerank_score is not None:
            return self.rerank_score
        return self.dense_score + self.lexical_score


@dataclass(frozen=True)
class NewChunk:
    ordinal: int
    heading_path: str | None
    body: str
    char_start: int
    char_end: int
    token_count: int


class UnitOfWork(Protocol):
    """A transaction scope.

    Repositories never commit. The caller owns the transaction, which is what lets a
    lifecycle change, its generation bump and its audit record land atomically — the
    property that makes cache invalidation correct and audit unmissable.
    """

    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, *exc: object) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
