"""Entity lifecycle state machines (guardrail G8).

Every entity with a lifecycle declares a ``_LEGAL`` transition map and goes through one
``assert_transition`` call site. Status is never assigned directly outside the lifecycle
service that owns it — a transition absent from these tables is unreachable by any code
path, which is what stops "just this once" assignments accumulating.
"""

from __future__ import annotations

from enum import StrEnum

from app.domain.errors import InvalidConversationTransition, InvalidStateTransition


class KnowledgeStatus(StrEnum):
    PROCESSING = "processing"
    FAILED = "failed"
    DUPLICATE_HOLD = "duplicate_hold"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    STALE = "stale"
    RETIRED = "retired"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


#: The answerable set. Nothing else, ever, anywhere (guardrail G2).
#: ``stale`` stays answerable by design (BR-9) and carries a review-pending flag on its
#: citations (BR-5) — silence is worse than dated guidance, provided the user is told.
ANSWERABLE: frozenset[KnowledgeStatus] = frozenset(
    {KnowledgeStatus.APPROVED, KnowledgeStatus.STALE}
)

_LEGAL_KNOWLEDGE: dict[KnowledgeStatus, frozenset[KnowledgeStatus]] = {
    KnowledgeStatus.PROCESSING: frozenset(
        {KnowledgeStatus.PENDING_REVIEW, KnowledgeStatus.FAILED, KnowledgeStatus.DUPLICATE_HOLD}
    ),
    KnowledgeStatus.DUPLICATE_HOLD: frozenset(
        {KnowledgeStatus.PENDING_REVIEW, KnowledgeStatus.REJECTED}
    ),
    KnowledgeStatus.PENDING_REVIEW: frozenset(
        {KnowledgeStatus.APPROVED, KnowledgeStatus.REJECTED}
    ),
    KnowledgeStatus.APPROVED: frozenset(
        {KnowledgeStatus.STALE, KnowledgeStatus.RETIRED, KnowledgeStatus.SUPERSEDED}
    ),
    KnowledgeStatus.STALE: frozenset(
        {KnowledgeStatus.APPROVED, KnowledgeStatus.RETIRED, KnowledgeStatus.SUPERSEDED}
    ),
    # Reversal of a supersession, reason required (PRD Detailed Feature Specifications).
    KnowledgeStatus.SUPERSEDED: frozenset({KnowledgeStatus.APPROVED}),
    # Terminal by policy — nothing is ever deleted (BR-10).
    KnowledgeStatus.RETIRED: frozenset(),
    KnowledgeStatus.REJECTED: frozenset(),
    # Resubmission.
    KnowledgeStatus.FAILED: frozenset({KnowledgeStatus.PROCESSING}),
}


def assert_knowledge_transition(current: KnowledgeStatus, target: KnowledgeStatus) -> None:
    if target not in _LEGAL_KNOWLEDGE[current]:
        raise InvalidStateTransition(current.value, target.value)


class ConversationState(StrEnum):
    ACTIVE_SELF_SERVE = "active_self_serve"
    ACTIVE_AGENT = "active_agent"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    SELF_RESOLVED = "self_resolved"
    AGENT_RESOLVED = "agent_resolved"
    CALLBACK_RECORDED = "callback_recorded"
    ABANDONED = "abandoned"


#: Exactly four, matching REQ-007's outcome set. Terminal states have no outgoing
#: transitions, which is how "exactly one recorded outcome" becomes structurally true
#: rather than a convention.
TERMINAL: frozenset[ConversationState] = frozenset(
    {
        ConversationState.SELF_RESOLVED,
        ConversationState.AGENT_RESOLVED,
        ConversationState.CALLBACK_RECORDED,
        ConversationState.ABANDONED,
    }
)

NON_TERMINAL: frozenset[ConversationState] = frozenset(ConversationState) - TERMINAL

_LEGAL_CONVERSATION: dict[ConversationState, frozenset[ConversationState]] = {
    ConversationState.ACTIVE_SELF_SERVE: frozenset(
        {
            ConversationState.SELF_RESOLVED,
            ConversationState.QUEUED,
            ConversationState.ABANDONED,
            ConversationState.CALLBACK_RECORDED,
        }
    ),
    ConversationState.ACTIVE_AGENT: frozenset(
        {
            ConversationState.AGENT_RESOLVED,
            ConversationState.ABANDONED,
            ConversationState.QUEUED,
        }
    ),
    ConversationState.QUEUED: frozenset(
        {
            ConversationState.ASSIGNED,
            ConversationState.CALLBACK_RECORDED,
            ConversationState.ABANDONED,
            ConversationState.ESCALATED,
        }
    ),
    ConversationState.ESCALATED: frozenset(
        {
            ConversationState.ASSIGNED,
            ConversationState.CALLBACK_RECORDED,
            ConversationState.ABANDONED,
        }
    ),
    ConversationState.ASSIGNED: frozenset(
        {
            ConversationState.AGENT_RESOLVED,
            ConversationState.QUEUED,
            ConversationState.ABANDONED,
        }
    ),
    ConversationState.SELF_RESOLVED: frozenset(),
    ConversationState.AGENT_RESOLVED: frozenset(),
    ConversationState.CALLBACK_RECORDED: frozenset(),
    ConversationState.ABANDONED: frozenset(),
}


def assert_conversation_transition(
    current: ConversationState, target: ConversationState
) -> None:
    if target not in _LEGAL_CONVERSATION[current]:
        raise InvalidConversationTransition(current.value, target.value)


class IngestionStage(StrEnum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    OCR = "ocr"
    METADATA = "metadata"
    DUPLICATE_CHECK = "duplicate_check"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    CLASSIFYING = "classifying"
    COMPLETE = "complete"
    FAILED = "failed"


#: Pipeline order. The orchestrator owns advancement; handlers never write their own
#: stage, which is what makes "state advances only on stage completion" enforceable.
INGESTION_ORDER: tuple[IngestionStage, ...] = (
    IngestionStage.EXTRACTING,
    IngestionStage.OCR,
    IngestionStage.METADATA,
    IngestionStage.DUPLICATE_CHECK,
    IngestionStage.CHUNKING,
    IngestionStage.EMBEDDING,
    IngestionStage.CLASSIFYING,
)


def stages_from(stage: IngestionStage) -> tuple[IngestionStage, ...]:
    """Stages remaining, so a re-delivered job resumes rather than restarting."""
    if stage in (IngestionStage.QUEUED, IngestionStage.FAILED):
        return INGESTION_ORDER
    if stage == IngestionStage.COMPLETE:
        return ()
    return INGESTION_ORDER[INGESTION_ORDER.index(stage) :]


class AnswerOutcome(StrEnum):
    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    CONFLICT = "conflict"
    BLOCKED_COVERAGE = "blocked_coverage"
    BLOCKED_FAIR_USE = "blocked_fair_use"
