"""Domain exception hierarchies (guardrail G9).

One base per domain, each mapped to a ``problem+json`` code in exactly one table per
surface (``app.api.errors``). An exception without a mapping is an incomplete change.

Note what is deliberately *not* here: ``no_answer``, ``conflict``, ``blocked_coverage``,
``blocked_fair_use``, assist-unavailable and no-agent-available are **not** exceptions.
Guardrail G5 makes them legitimate results returned at 200. Modelling them as errors is
how "I don't know" starts reading as "broken".
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base for every domain error. Carries a stable ``code`` for problem+json."""

    code: str = "domain.error"
    http_status: int = 400

    def __init__(self, detail: str = "", **extra: Any) -> None:
        super().__init__(detail or self.code)
        self.detail = detail or self.code
        self.extra = extra


# --------------------------------------------------------------------------------------
# Knowledge domain
# --------------------------------------------------------------------------------------
class KnowledgeDomainError(DomainError):
    code = "knowledge.error"


class ItemNotFound(KnowledgeDomainError):
    code = "knowledge.item_not_found"
    http_status = 404


class InvalidStateTransition(KnowledgeDomainError):
    code = "knowledge.invalid_transition"
    http_status = 409

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"cannot transition from {current!r} to {target!r}",
            current=current,
            target=target,
        )


class VersionConflict(KnowledgeDomainError):
    code = "knowledge.version_conflict"
    http_status = 409

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"version {expected} is stale; current is {actual}",
            expected_version=expected,
            current_version=actual,
        )


class NearDuplicateRequiresDecision(KnowledgeDomainError):
    code = "knowledge.duplicate_decision_required"
    http_status = 409


class IncompleteCitationMetadata(KnowledgeDomainError):
    """An item cannot become answerable without authority and issue date (BR-2)."""

    code = "knowledge.citation_incomplete"
    http_status = 422


class ReviewDateRequired(KnowledgeDomainError):
    code = "knowledge.review_date_required"
    http_status = 422


# --------------------------------------------------------------------------------------
# Answer domain
# --------------------------------------------------------------------------------------
class AnswerDomainError(DomainError):
    code = "answer.error"


class LanguageNotEnabled(AnswerDomainError):
    code = "answer.language_not_enabled"
    http_status = 422

    def __init__(self, language: str, enabled: list[str]) -> None:
        super().__init__(
            f"language {language!r} is not enabled", language=language, enabled=enabled
        )


class ModelUnavailable(AnswerDomainError):
    """The agent surface keeps working; the conversation is never blocked (REQ-006)."""

    code = "answer.assist_unavailable"
    http_status = 503


class GroundingFailed(AnswerDomainError):
    """Internal only. Never surfaces — it triggers the extractive path."""

    code = "answer.grounding_failed"
    http_status = 500


# --------------------------------------------------------------------------------------
# Ingestion
# --------------------------------------------------------------------------------------
class IngestionError(DomainError):
    code = "ingestion.error"


class RetryableStageError(IngestionError):
    """Transient: model server unreachable, I/O blip. Retried with backoff."""

    code = "ingestion.stage_retryable"
    http_status = 503


class FatalStageError(IngestionError):
    """Terminal: unreadable file, unsupported type. Never retried."""

    code = "ingestion.stage_fatal"
    http_status = 422


class DocumentTooLarge(IngestionError):
    code = "ingestion.too_large"
    http_status = 413


class ExtractionFailed(FatalStageError):
    code = "ingestion.extraction_failed"
    http_status = 422


# --------------------------------------------------------------------------------------
# Conversation
# --------------------------------------------------------------------------------------
class ConversationDomainError(DomainError):
    code = "conversation.error"


class ConversationNotFound(ConversationDomainError):
    code = "conversation.not_found"
    http_status = 404


class InvalidConversationTransition(ConversationDomainError):
    code = "conversation.invalid_transition"
    http_status = 409

    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"cannot transition from {current!r} to {target!r}",
            current=current,
            target=target,
        )


class ConversationAlreadyTerminal(ConversationDomainError):
    code = "conversation.already_ended"
    http_status = 409


class NotAssignedAgent(ConversationDomainError):
    code = "conversation.not_assigned"
    http_status = 403


class SuggestionNotInConversation(ConversationDomainError):
    code = "assist.foreign_answer"
    http_status = 403


# --------------------------------------------------------------------------------------
# Assignment
# --------------------------------------------------------------------------------------
class AssignmentError(DomainError):
    code = "assignment.error"


class AssignmentRaceLost(AssignmentError):
    """Internal; retried once, never surfaced to a caller."""

    code = "assignment.race_lost"
    http_status = 409


class PolicyReturnedUnknownAgent(AssignmentError):
    """LSP contract violation (lld-backend-pass2.md §5). Fail loudly, never assign."""

    code = "assignment.policy_contract_violation"
    http_status = 500


# --------------------------------------------------------------------------------------
# Authorisation / administration / privacy
# --------------------------------------------------------------------------------------
class PermissionDenied(DomainError):
    code = "auth.forbidden"
    http_status = 403


class UserNotFound(DomainError):
    code = "admin.user_not_found"
    http_status = 404


class LastAdministratorRemoval(DomainError):
    """A system whose last administrator can be removed can be locked permanently."""

    code = "admin.last_administrator"
    http_status = 409


class GroupNotFound(DomainError):
    code = "gaps.group_not_found"
    http_status = 404


class ResolutionIncomplete(DomainError):
    code = "gaps.resolution_incomplete"
    http_status = 422


class GroupAlreadyResolved(DomainError):
    code = "gaps.already_resolved"
    http_status = 409


class PeriodTooLarge(DomainError):
    code = "analytics.period_too_large"
    http_status = 422


class DeletionAlreadyExecuted(DomainError):
    code = "privacy.already_executed"
    http_status = 409


class PersistenceError(DomainError):
    """An action that could not be recorded must not be reported as done (REQ-014)."""

    code = "persistence.failed"
    http_status = 500
