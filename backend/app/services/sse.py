"""Server-sent event channel (amendment §B).

One channel per **conversation**, not per answer. A channel per answer would multiply
connections across a long conversation and break the ``Last-Event-ID`` replay contract,
which is per channel.

The contract this service owes the client, stated once because both sides depend on it:
``answer.final`` or ``answer.error`` **always** arrives on a terminal path. A client that
receives tokens and then neither must discard its draft — that is the frontend's
behaviour when this guarantee is not met, and the guarantee is why it almost never is.

Reconnection replays **state, not backlog**: current conversation state, current queue
position, and ``answer.final`` for anything that completed while disconnected. Token
events are never replayed — a partial draft has no value once the final answer exists,
and replaying it would reopen the window the provisional-region design closes.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Event:
    """One SSE frame. ``id`` is monotonic per channel, for Last-Event-ID."""

    id: int
    name: str
    data: dict[str, Any]

    def render(self) -> str:
        return f"id: {self.id}\nevent: {self.name}\ndata: {json.dumps(self.data)}\n\n"


#: Event names. Kept as constants so a typo is an import error rather than a message
#: nobody receives — the failure mode of stringly-typed event buses.
ANSWER_TOKEN = "answer.token"
ANSWER_GROUNDING = "answer.grounding"
ANSWER_FINAL = "answer.final"
ANSWER_ERROR = "answer.error"
CONVERSATION_STATE = "conversation.state"
QUEUE_POSITION = "queue.position"
CONVERSATION_ASSIGNED = "conversation.assigned"
ASSIGNMENT_OFFERED = "assignment.offered"
ASSIGNMENT_REVOKED = "assignment.revoked"
KNOWLEDGE_RETIRED_SOURCE = "knowledge.retired_source"
PRESENCE_EXPIRED = "presence.expired"

#: Replayed on reconnect. Token events are deliberately absent (see module docstring).
REPLAYABLE = frozenset({ANSWER_FINAL, CONVERSATION_STATE, QUEUE_POSITION,
                        CONVERSATION_ASSIGNED, KNOWLEDGE_RETIRED_SOURCE})


@dataclass
class _Channel:
    next_id: int = 1
    subscribers: set[asyncio.Queue[Event]] = field(default_factory=set)
    #: Last replayable event per name — state, not a log. Bounded by design: a channel
    #: cannot grow without limit no matter how long a conversation runs.
    replay_state: dict[str, Event] = field(default_factory=dict)


class SseChannelService:
    def __init__(self) -> None:
        self._channels: dict[str, _Channel] = defaultdict(_Channel)

    @staticmethod
    def conversation_key(conversation_id: UUID) -> str:
        return f"conversation:{conversation_id}"

    @staticmethod
    def agent_key(agent_id: int) -> str:
        return f"agent:{agent_id}"

    def publish(self, key: str, name: str, data: dict[str, Any]) -> Event:
        channel = self._channels[key]
        event = Event(id=channel.next_id, name=name, data=data)
        channel.next_id += 1

        if name in REPLAYABLE:
            channel.replay_state[name] = event

        for queue in list(channel.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # A subscriber that cannot keep up is dropped rather than allowed to
                # block the publisher. It will reconnect and replay state, which is
                # exactly the case the replay contract exists for.
                channel.subscribers.discard(queue)
                log.warning("sse.subscriber_dropped", channel=key)
        return event

    async def subscribe(
        self, key: str, last_event_id: int | None = None
    ) -> tuple[asyncio.Queue[Event], list[Event]]:
        """Attach to a channel and receive the state replay.

        The replay is ordered by event id so a client applying it sequentially reaches
        the same state the server holds.
        """
        channel = self._channels[key]
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=256)
        channel.subscribers.add(queue)

        replay = [
            event
            for event in channel.replay_state.values()
            if last_event_id is None or event.id > last_event_id
        ]
        replay.sort(key=lambda e: e.id)
        return queue, replay

    def unsubscribe(self, key: str, queue: asyncio.Queue[Event]) -> None:
        self._channels[key].subscribers.discard(queue)

    def subscriber_count(self, key: str) -> int:
        return len(self._channels[key].subscribers)
