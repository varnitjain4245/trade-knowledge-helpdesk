"""Audit writer — a decorator over the masker (guardrail G1).

Masking is applied *by construction* on the way in, not by a rule call sites are asked
to remember. That is the whole reason this is a decorator rather than a helper function:
an audit write cannot bypass masking, because there is no path that reaches the
repository without passing through here.
"""

from __future__ import annotations

from typing import Any

from app.repositories.audit import AuditEvent, AuditRepository
from app.services.masking import CallSite, Masker

#: Detail fields that may contain customer content and are masked before storage.
#: A field not listed here is assumed to be operational metadata (ids, statuses, counts).
_MASKED_FIELDS = frozenset({"query", "query_text", "sent_text", "answer_text", "reason",
                            "note", "body", "contact_detail", "label"})


class AuditWriter:
    def __init__(self, repository: AuditRepository, masker: Masker) -> None:
        self._repository = repository
        self._masker = masker

    def write(
        self, action: str, subject_type: str, subject_id: str,
        actor_user_id: int | None = None, actor_kind: str = "user",
        **detail: Any,
    ) -> None:
        """Record an action inside the caller's transaction.

        Never commits: the audit record and the action it describes must land together,
        which is what makes an unaudited governance action unreachable rather than
        merely discouraged.
        """
        self._repository.append(
            AuditEvent(
                action=action,
                actor_user_id=actor_user_id,
                actor_kind=actor_kind,
                subject_type=subject_type,
                subject_id=str(subject_id),
                detail=self._mask_detail(detail),
            )
        )

    def _mask_detail(self, detail: dict[str, Any]) -> dict[str, Any]:
        masked: dict[str, Any] = {}
        for key, value in detail.items():
            if key in _MASKED_FIELDS and isinstance(value, str):
                result = self._masker.mask_for(value, CallSite.AUDIT_DETAIL)
                masked[key] = result.text
                if result.withheld:
                    masked[f"{key}_withheld"] = True
            else:
                masked[key] = value
        return masked
