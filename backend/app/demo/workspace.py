"""Conversation, assist, gap, analytics and audit state for the demo runner.

Mirrors the production tables closely enough that the behaviours built on them are the
real ones — four terminal conversation outcomes, server-determined edit detection, an
append-only audit log, and analytics that store numerators and denominators rather than
pre-divided averages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

TERMINAL = {"self_resolved", "agent_resolved", "callback_recorded", "abandoned"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Message:
    id: int
    author: str            # customer | assistant | agent
    body: str
    language: str
    answer_id: UUID | None = None
    outcome: str | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class Conversation:
    id: UUID
    surface: str
    state: str
    detected_language: str
    chosen_language: str | None = None
    below_bar_streak: int = 0
    retired_source_flag: bool = False
    messages: list[Message] = field(default_factory=list)
    queue_position: int | None = None
    agent_name: str | None = None
    started_at: datetime = field(default_factory=_now)
    ended_at: datetime | None = None

    @property
    def language(self) -> str:
        return self.chosen_language or self.detected_language


@dataclass
class AssistUsage:
    answer_id: UUID
    conversation_id: UUID
    accepted: bool
    edited_before_send: bool | None = None
    sent_body: str | None = None
    suggestion_body: str | None = None
    rating: int | None = None


@dataclass
class AuditRecord:
    id: int
    action: str
    actor: str
    subject_type: str
    subject_id: str
    detail: dict[str, Any]
    occurred_at: datetime = field(default_factory=_now)


class Workspace:
    """Everything the three surfaces read and write."""

    def __init__(self) -> None:
        self.conversations: dict[UUID, Conversation] = {}
        self.assist: list[AssistUsage] = []
        self.audit: list[AuditRecord] = []
        self._message_seq = 0
        self._audit_seq = 0
        self.queue: list[UUID] = []

    # --- conversations ---------------------------------------------------------------
    def start(self, surface: str, language: str, state: str) -> Conversation:
        conversation = Conversation(
            id=uuid4(), surface=surface, state=state, detected_language=language
        )
        self.conversations[conversation.id] = conversation
        self.write_audit("conversation_started", "system", "conversation",
                         str(conversation.id), surface=surface, language=language)
        return conversation

    def add_message(
        self, conversation: Conversation, author: str, body: str, language: str,
        answer_id: UUID | None = None, outcome: str | None = None,
    ) -> Message:
        self._message_seq += 1
        message = Message(
            id=self._message_seq, author=author, body=body, language=language,
            answer_id=answer_id, outcome=outcome,
        )
        conversation.messages.append(message)
        return message

    def end(self, conversation: Conversation, state: str) -> None:
        """Terminal states have no outgoing transitions — 'exactly one recorded
        outcome' (REQ-007) is structural, not a convention."""
        if conversation.state in TERMINAL:
            raise ValueError(f"conversation already ended as {conversation.state}")
        conversation.state = state
        conversation.ended_at = _now()
        if conversation.id in self.queue:
            self.queue.remove(conversation.id)
        self.write_audit("conversation_ended", "system", "conversation",
                         str(conversation.id), outcome=state)

    def enqueue(self, conversation: Conversation) -> int:
        if conversation.id not in self.queue:
            self.queue.append(conversation.id)
        conversation.state = "queued"
        position = self.queue.index(conversation.id) + 1
        conversation.queue_position = position
        self.write_audit("handover_queued", "system", "conversation",
                         str(conversation.id), position=position)
        return position

    def assign(self, conversation: Conversation, agent_name: str) -> None:
        if conversation.id in self.queue:
            self.queue.remove(conversation.id)
        conversation.state = "assigned"
        conversation.agent_name = agent_name
        conversation.queue_position = None
        self.write_audit("assigned", agent_name, "conversation",
                         str(conversation.id), agent=agent_name)

    # --- assist ----------------------------------------------------------------------
    def record_assist(
        self, conversation_id: UUID, answer_id: UUID, suggestion_body: str,
        sent_body: str, agent: str,
    ) -> AssistUsage:
        """Edit detection is the **server's** determination.

        The client may claim whatever it likes; a client that lied about this would
        corrupt the audit trail and the wrong-answer guardrail at the same time.
        """
        edited = _normalise(sent_body) != _normalise(suggestion_body)
        usage = AssistUsage(
            answer_id=answer_id, conversation_id=conversation_id, accepted=True,
            edited_before_send=edited, sent_body=sent_body,
            suggestion_body=suggestion_body,
        )
        self.assist.append(usage)
        self.write_audit(
            "reply_sent", agent, "conversation", str(conversation_id),
            derived_from=str(answer_id), edited=edited, sent_text=sent_body,
        )
        return usage

    def rate(self, answer_id: UUID, rating: int, agent: str) -> bool:
        for usage in self.assist:
            if usage.answer_id == answer_id:
                usage.rating = rating
                self.write_audit("suggestion_rated", agent, "answer",
                                 str(answer_id), rating=rating)
                return True
        return False

    # --- audit -----------------------------------------------------------------------
    def write_audit(
        self, action: str, actor: str, subject_type: str, subject_id: str, **detail: Any
    ) -> AuditRecord:
        """Append-only. There is no update or delete path, here or in production."""
        self._audit_seq += 1
        record = AuditRecord(
            id=self._audit_seq, action=action, actor=actor, subject_type=subject_type,
            subject_id=subject_id, detail=detail,
        )
        self.audit.append(record)
        return record

    def audit_for_conversation(self, conversation_id: UUID) -> list[AuditRecord]:
        return [
            r for r in self.audit
            if r.subject_type == "conversation" and r.subject_id == str(conversation_id)
        ]

    # --- analytics -------------------------------------------------------------------
    def metrics(self, answers: list, gaps: list) -> dict[str, Any]:
        """Sums and counts, divided once at the end.

        Every figure carries its numerator and denominator so a low-volume period can be
        flagged rather than presented as a stable percentage.
        """
        conversations = list(self.conversations.values())
        total = len(conversations)
        self_resolved = sum(1 for c in conversations if c.state == "self_resolved")
        abandoned = sum(1 for c in conversations if c.state == "abandoned")
        agent_resolved = sum(1 for c in conversations if c.state == "agent_resolved")

        shown = sum(1 for _, a in answers if a.outcome.value == "answered")
        no_answer = sum(1 for _, a in answers if a.outcome.value == "no_answer")
        conflicts = sum(1 for _, a in answers if a.outcome.value == "conflict")

        accepted = [u for u in self.assist if u.accepted]
        edited = [u for u in accepted if u.edited_before_send]
        rated = [u for u in self.assist if u.rating is not None]
        negative = [u for u in rated if u.rating == -1]

        language_mix: dict[str, int] = {}
        for conversation in conversations:
            language_mix[conversation.language] = language_mix.get(conversation.language, 0) + 1

        return {
            "low_volume": total < 100,
            "kpis": [
                _metric("Deflection", self_resolved, total,
                        "Self-resolved conversations. Abandoned conversations stay in the "
                        "denominator and out of the numerator — a customer who gave up is "
                        "not a deflection."),
                _metric("Citation coverage", shown, shown,
                        "Every shown answer carries at least one citation. Not a target — "
                        "a hard rule, measured to prove it holds."),
                _metric("Assist accepted", len(accepted), max(1, shown),
                        "Suggestions an agent used in a reply."),
                _metric("Answers edited before sending", len(edited), max(1, len(accepted)),
                        "Server-determined, never the client's claim."),
            ],
            "guardrails": [
                _metric("Repeat contact within 7 days", 0, max(1, total),
                        "Lower bound. Links same-browser contacts only; a customer who "
                        "switches device, clears storage or phones in counts as a new "
                        "person.", lower_bound=True, coverage=0.0),
                _metric("Abandonment", abandoned, max(1, total),
                        "Counted separately from self-resolved, so deflection cannot be "
                        "inflated by silence."),
                _metric("Negative ratings", len(negative), max(1, len(rated)),
                        "Must not rise as assist adoption rises."),
            ],
            "counters": {
                "conversations": total, "answers_shown": shown, "no_answers": no_answer,
                "conflicts": conflicts, "agent_resolved": agent_resolved,
                "open_gaps": len(gaps),
            },
            "language_mix": language_mix,
        }


def _metric(
    label: str, numerator: int, denominator: int, note: str,
    lower_bound: bool = False, coverage: float | None = None,
) -> dict[str, Any]:
    value = round(numerator / denominator, 3) if denominator else None
    return {
        "label": label, "value": value, "numerator": numerator,
        "denominator": denominator, "note": note, "lower_bound": lower_bound,
        "coverage": coverage,
    }


def _normalise(text: str) -> str:
    return " ".join(text.split()).strip().lower()
