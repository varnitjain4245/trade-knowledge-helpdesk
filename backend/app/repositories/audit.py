"""Audit repository (append-only, guardrail G1).

There is no update or delete method on this interface **by design**, and the application
database role holds no such grant (migration 005). Two layers enforcing one rule: the
grant is the guarantee, the interface shape is what stops anyone writing code that would
need the grant restored.

``append`` does not commit. It runs inside the caller's transaction so a governance
action and its audit record land atomically — which is why an unaudited action is not a
reachable state rather than a discouraged one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.errors import PersistenceError


@dataclass(frozen=True)
class AuditEvent:
    action: str
    actor_kind: str          # 'user' | 'system' | 'public'
    subject_type: str
    subject_id: str
    detail: dict[str, Any]
    actor_user_id: int | None = None


@dataclass(frozen=True)
class AuditRecord:
    id: int
    action: str
    actor_user_id: int | None
    actor_kind: str
    subject_type: str
    subject_id: str
    detail: dict[str, Any]
    occurred_at: datetime


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuditEvent) -> None:
        """Insert within the caller's transaction; does not commit.

        Raises PersistenceError on failure — the caller must then roll back the action
        being audited. An unaudited governance action is not an acceptable outcome
        (REQ-014), so failing loudly here is the correct behaviour, not a nuisance.
        """
        try:
            self._session.execute(
                text(
                    """
                    INSERT INTO audit_record
                        (action, actor_user_id, actor_kind, subject_type, subject_id, detail)
                    VALUES (:action, :actor_user_id, :actor_kind, :subject_type,
                            :subject_id, CAST(:detail AS jsonb))
                    """
                ),
                {
                    "action": event.action,
                    "actor_user_id": event.actor_user_id,
                    "actor_kind": event.actor_kind,
                    "subject_type": event.subject_type,
                    "subject_id": event.subject_id,
                    "detail": json.dumps(event.detail, default=str),
                },
            )
        except SQLAlchemyError as exc:
            raise PersistenceError(f"could not audit {event.action}") from exc

    def for_subject(self, subject_type: str, subject_id: str) -> list[AuditRecord]:
        """Read-only, oldest first. Uses idx_audit_subject.

        Returns [] for an unknown subject — absence is not an error.
        """
        rows = self._session.execute(
            text(
                """
                SELECT id, action, actor_user_id, actor_kind, subject_type, subject_id,
                       detail, occurred_at
                  FROM audit_record
                 WHERE subject_type = :st AND subject_id = :sid
                 ORDER BY occurred_at
                """
            ),
            {"st": subject_type, "sid": subject_id},
        ).mappings().all()
        return [AuditRecord(**r) for r in rows]

    def query(
        self, action: str | None = None, actor_user_id: int | None = None,
        limit: int = 100, cursor: int | None = None,
    ) -> list[AuditRecord]:
        """Keyset pagination on id — the audit table is append-only, so ids are
        monotonic and a cursor cannot skip or duplicate rows the way an offset would."""
        rows = self._session.execute(
            text(
                """
                SELECT id, action, actor_user_id, actor_kind, subject_type, subject_id,
                       detail, occurred_at
                  FROM audit_record
                 WHERE (:action IS NULL OR action = :action)
                   AND (:actor IS NULL OR actor_user_id = :actor)
                   AND (:cursor IS NULL OR id < :cursor)
                 ORDER BY id DESC
                 LIMIT :limit
                """
            ),
            {"action": action, "actor": actor_user_id, "cursor": cursor, "limit": limit},
        ).mappings().all()
        return [AuditRecord(**r) for r in rows]
