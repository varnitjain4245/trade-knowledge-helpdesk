"""Knowledge item repository (lld-backend.md §6.3).

Two things are load-bearing here:

* ``get_for_update`` refuses to run outside a transaction. A silent unlocked read would
  reintroduce the lost-update race that pass 1 §7.1 chose pessimistic locking to prevent,
  and it would fail only under concurrency — the worst kind of bug to leave discoverable.
* ``mark_stale`` is a conditional bulk update, so re-running it the same day changes
  nothing. The staleness sweep may be retried (amendment §O) and an incremental version
  would double-transition items.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.errors import VersionConflict
from app.domain.state import KnowledgeStatus


@dataclass
class KnowledgeItem:
    id: UUID
    status: KnowledgeStatus
    title: str
    language: str
    current_version: int
    issuing_authority_id: int | None
    issued_on: date | None
    review_due_on: date | None
    supersedes_id: UUID | None
    superseded_by_id: UUID | None
    approved_by: int | None
    approved_at: datetime | None
    status_reason: str | None
    updated_at: datetime


_COLUMNS = """
    id, status, title, language, current_version, issuing_authority_id, issued_on,
    review_due_on, supersedes_id, superseded_by_id, approved_by, approved_at,
    status_reason, updated_at
"""


def _row_to_item(row) -> KnowledgeItem:  # type: ignore[no-untyped-def]
    return KnowledgeItem(
        id=row["id"],
        status=KnowledgeStatus(row["status"]),
        title=row["title"],
        language=row["language"],
        current_version=row["current_version"],
        issuing_authority_id=row["issuing_authority_id"],
        issued_on=row["issued_on"],
        review_due_on=row["review_due_on"],
        supersedes_id=row["supersedes_id"],
        superseded_by_id=row["superseded_by_id"],
        approved_by=row["approved_by"],
        approved_at=row["approved_at"],
        status_reason=row["status_reason"],
        updated_at=row["updated_at"],
    )


class KnowledgeItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, item_id: UUID) -> KnowledgeItem | None:
        """Returns None when absent — never raises for a missing row."""
        row = self._session.execute(
            text(f"SELECT {_COLUMNS} FROM knowledge_item WHERE id = :id"),
            {"id": item_id},
        ).mappings().first()
        return _row_to_item(row) if row else None

    def get_for_update(self, item_id: UUID) -> KnowledgeItem | None:
        """SELECT ... FOR UPDATE.

        Precondition: the caller holds an open transaction.
        Postcondition: the row is locked until that transaction ends.

        Raises RuntimeError outside a transaction rather than degrading to an unlocked
        read, because the degraded version is silently wrong.
        """
        if not self._session.in_transaction():
            raise RuntimeError("get_for_update requires an open transaction")
        row = self._session.execute(
            text(f"SELECT {_COLUMNS} FROM knowledge_item WHERE id = :id FOR UPDATE"),
            {"id": item_id},
        ).mappings().first()
        return _row_to_item(row) if row else None

    def save(self, item: KnowledgeItem, expected_version: int | None = None) -> None:
        """Write within the caller's transaction; does not commit.

        When ``expected_version`` is given this is the optimistic check behind
        ``If-Match``: a mismatch raises VersionConflict carrying both versions, so the
        client can show what changed rather than auto-merging.
        """
        if expected_version is not None:
            current = self._session.execute(
                text("SELECT current_version FROM knowledge_item WHERE id = :id"),
                {"id": item.id},
            ).scalar_one_or_none()
            if current is None:
                raise VersionConflict(expected_version, -1)
            if current != expected_version:
                raise VersionConflict(expected_version, current)

        self._session.execute(
            text(
                """
                UPDATE knowledge_item
                   SET status = :status, title = :title,
                       issuing_authority_id = :issuing_authority_id,
                       issued_on = :issued_on, review_due_on = :review_due_on,
                       supersedes_id = :supersedes_id,
                       superseded_by_id = :superseded_by_id,
                       approved_by = :approved_by, approved_at = :approved_at,
                       status_reason = :status_reason,
                       current_version = :current_version,
                       updated_at = now()
                 WHERE id = :id
                """
            ),
            {
                "id": item.id,
                "status": item.status.value,
                "title": item.title,
                "issuing_authority_id": item.issuing_authority_id,
                "issued_on": item.issued_on,
                "review_due_on": item.review_due_on,
                "supersedes_id": item.supersedes_id,
                "superseded_by_id": item.superseded_by_id,
                "approved_by": item.approved_by,
                "approved_at": item.approved_at,
                "status_reason": item.status_reason,
                "current_version": item.current_version,
            },
        )

    def due_for_review(self, within_days: int) -> list[KnowledgeItem]:
        """Approved and stale items whose review date falls inside the window.

        Read-only; uses idx_ki_review_due. Serves REQ-010's 30-day list.
        """
        rows = self._session.execute(
            text(
                f"""
                SELECT {_COLUMNS} FROM knowledge_item
                 WHERE status IN ('approved','stale')
                   AND review_due_on IS NOT NULL
                   AND review_due_on <= CURRENT_DATE + CAST(:days || ' days' AS interval)
                 ORDER BY review_due_on
                """
            ),
            {"days": within_days},
        ).mappings().all()
        return [_row_to_item(r) for r in rows]

    def mark_stale(self, as_of: date) -> int:
        """Bulk transition approved -> stale where the review date has passed.

        Idempotent: re-running the same day changes nothing, because the predicate
        excludes rows already stale. That matters — the sweep is retried on failure.
        """
        result = self._session.execute(
            text(
                """
                UPDATE knowledge_item
                   SET status = 'stale', updated_at = now()
                 WHERE status = 'approved'
                   AND review_due_on IS NOT NULL
                   AND review_due_on < :as_of
                """
            ),
            {"as_of": as_of},
        )
        return result.rowcount or 0

    def find_by_sha256(self, digest: bytes) -> UUID | None:
        """Exact-duplicate short-circuit before the expensive near-duplicate check."""
        return self._session.execute(
            text(
                """
                SELECT ki.id FROM knowledge_item ki
                  JOIN source_document sd ON sd.id = ki.source_document_id
                 WHERE sd.sha256 = :digest
                 LIMIT 1
                """
            ),
            {"digest": digest},
        ).scalar_one_or_none()

    def must_have_topics_uncovered(self) -> list[str]:
        """Must-have topics with no answerable item — drives the REQ-023 coverage floor.

        Returns display names so the console can name what is missing rather than
        reporting a bare count, which nobody can act on.
        """
        rows = self._session.execute(
            text(
                """
                SELECT t.display_name
                  FROM taxonomy_topic t
                 WHERE t.is_must_have AND t.is_active
                   AND NOT EXISTS (
                       SELECT 1 FROM item_classification ic
                         JOIN knowledge_item ki ON ki.id = ic.item_id
                        WHERE ic.topic_id = t.id
                          AND ki.status IN ('approved','stale')
                   )
                 ORDER BY t.display_name
                """
            )
        ).scalars().all()
        return list(rows)

    def append_version(
        self, item_id: UUID, version: int, title: str, body: str,
        issuing_authority_id: int | None, issued_on: date | None,
        edited_by: int, change_note: str | None,
    ) -> None:
        """Append an immutable version snapshot (REQ-009)."""
        self._session.execute(
            text(
                """
                INSERT INTO knowledge_item_version
                    (item_id, version, title, body, issuing_authority_id, issued_on,
                     edited_by, change_note)
                VALUES (:item_id, :version, :title, :body, :authority, :issued_on,
                        :edited_by, :note)
                """
            ),
            {
                "item_id": item_id, "version": version, "title": title, "body": body,
                "authority": issuing_authority_id, "issued_on": issued_on,
                "edited_by": edited_by, "note": change_note,
            },
        )
