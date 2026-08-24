"""Chunk repository — the single home of the answerable-set filter (guardrail G2).

`hybrid_search` is the only retrieval path in the system, and it always constrains
`knowledge_item.status IN ('approved','stale')`. There is no parameter to disable that
filter and no second query that reads chunks for answering.

This is what makes retirement immediate (BR-8): the status is read in the same statement
that searches vectors, so an item retired a second ago is already excluded — no cache
sweep, no index rebuild, no window.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.protocols import NewChunk, ScoredChunk

#: Hybrid retrieval: dense vectors for meaning, lexical for exact identifiers.
#: The domain is full of notification numbers and tariff codes, which vector search
#: handles poorly — dropping the lexical leg would make the system unable to find the
#: one thing a caller most often quotes verbatim.
_HYBRID_SQL = text(
    """
    WITH dense AS (
        SELECT ce.chunk_id,
               1 - (ce.embedding <=> CAST(:query_vector AS vector)) AS dense_score
        FROM chunk_embedding ce
        JOIN knowledge_item ki ON ki.id = ce.item_id
        WHERE ki.status IN ('approved','stale')
          AND ce.model_tag = :model_tag
        ORDER BY ce.embedding <=> CAST(:query_vector AS vector)
        LIMIT :candidates
    ),
    lexical AS (
        SELECT c.id AS chunk_id,
               ts_rank(c.lexeme, plainto_tsquery('simple', :query_text)) AS lexical_score
        FROM chunk c
        JOIN knowledge_item ki ON ki.id = c.item_id
        WHERE ki.status IN ('approved','stale')
          AND c.lexeme @@ plainto_tsquery('simple', :query_text)
        ORDER BY lexical_score DESC
        LIMIT :candidates
    ),
    fused AS (
        SELECT COALESCE(d.chunk_id, l.chunk_id) AS chunk_id,
               COALESCE(d.dense_score, 0)       AS dense_score,
               COALESCE(l.lexical_score, 0)     AS lexical_score
        FROM dense d
        FULL OUTER JOIN lexical l ON l.chunk_id = d.chunk_id
    )
    SELECT f.chunk_id, f.dense_score, f.lexical_score,
           c.body, c.heading_path,
           ki.id AS item_id, ki.title, ki.language, ki.issued_on,
           (ki.status = 'stale') AS item_is_stale,
           ia.display_name AS issuing_authority
    FROM fused f
    JOIN chunk c ON c.id = f.chunk_id
    JOIN knowledge_item ki ON ki.id = c.item_id
    JOIN issuing_authority ia ON ia.id = ki.issuing_authority_id
    -- Re-asserted here as well as in each CTE: this join is the one an optimiser could
    -- not remove, and the redundancy is deliberate on a correctness-critical filter.
    WHERE ki.status IN ('approved','stale')
      AND c.item_version = ki.current_version
    ORDER BY (f.dense_score + f.lexical_score) DESC
    LIMIT :candidates
    """
)


class ChunkRepository:
    def __init__(self, session: Session, model_tag: str) -> None:
        self._session = session
        self._model_tag = model_tag

    def hybrid_search(
        self, query_vector: list[float], query_text: str, candidates: int
    ) -> list[ScoredChunk]:
        """Retrieve candidates from the answerable set only.

        Read-committed is sufficient: an item retired mid-query is caught on the next
        query, and BR-8's guarantee is about the next answer, not one already in flight.

        Returns [] when nothing matches — an empty corpus is a legitimate state
        (REQ-023 cold start), never an error.
        """
        rows = self._session.execute(
            _HYBRID_SQL,
            {
                "query_vector": query_vector,
                "query_text": query_text,
                "candidates": candidates,
                "model_tag": self._model_tag,
            },
        ).mappings()

        return [
            ScoredChunk(
                chunk_id=row["chunk_id"],
                item_id=row["item_id"],
                body=row["body"],
                heading_path=row["heading_path"],
                item_title=row["title"],
                issuing_authority=row["issuing_authority"],
                issued_on=row["issued_on"],
                item_language=row["language"],
                item_is_stale=row["item_is_stale"],
                dense_score=float(row["dense_score"]),
                lexical_score=float(row["lexical_score"]),
            )
            for row in rows
        ]

    def replace_for_version(
        self, item_id: UUID, version: int, chunks: list[NewChunk]
    ) -> list[int]:
        """Replace an item's chunks for a version, inside the caller's transaction.

        Precondition: caller holds the item row lock.
        Postcondition: no window exists in which a committed reader sees an item with
        zero chunks — the delete and insert share one transaction, so readers see either
        the old set or the new one.
        """
        self._session.execute(
            text("DELETE FROM chunk WHERE item_id = :item_id"), {"item_id": item_id}
        )
        ids: list[int] = []
        for chunk in chunks:
            row = self._session.execute(
                text(
                    """
                    INSERT INTO chunk (item_id, item_version, ordinal, heading_path,
                                       body, char_start, char_end, token_count)
                    VALUES (:item_id, :version, :ordinal, :heading_path,
                            :body, :char_start, :char_end, :token_count)
                    RETURNING id
                    """
                ),
                {
                    "item_id": item_id,
                    "version": version,
                    "ordinal": chunk.ordinal,
                    "heading_path": chunk.heading_path,
                    "body": chunk.body,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "token_count": chunk.token_count,
                },
            ).scalar_one()
            ids.append(row)
        return ids

    def store_embeddings(
        self, item_id: UUID, chunk_ids: list[int], vectors: list[list[float]]
    ) -> None:
        """Upsert embeddings for chunks.

        Upsert rather than insert because a re-delivered ingestion job must be able to
        re-run the embedding stage without producing duplicates (guardrail: per-stage
        idempotency, amendment §O).
        """
        if len(chunk_ids) != len(vectors):
            raise ValueError("chunk/vector count mismatch")
        for chunk_id, vector in zip(chunk_ids, vectors, strict=True):
            self._session.execute(
                text(
                    """
                    INSERT INTO chunk_embedding (chunk_id, item_id, model_tag, embedding)
                    VALUES (:chunk_id, :item_id, :model_tag, CAST(:embedding AS vector))
                    ON CONFLICT (chunk_id) DO UPDATE
                      SET embedding = EXCLUDED.embedding,
                          model_tag = EXCLUDED.model_tag
                    """
                ),
                {
                    "chunk_id": chunk_id,
                    "item_id": item_id,
                    "model_tag": self._model_tag,
                    "embedding": vector,
                },
            )

    def bodies_for(self, chunk_ids: list[int]) -> dict[int, str]:
        """Chunk bodies by id. Used by the grounding verifier, which must compare
        generated text against the exact passages the generator was given."""
        if not chunk_ids:
            return {}
        rows = self._session.execute(
            text("SELECT id, body FROM chunk WHERE id = ANY(:ids)"), {"ids": chunk_ids}
        ).all()
        return {row[0]: row[1] for row in rows}
