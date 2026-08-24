"""Presence repository (lld-backend-pass2.md §6.6, §7.2).

Presence is an **advisory fast path**; open assignments are authoritative. That split is
deliberate and ratified (amendment §N): the fast path is the one that can be wrong, and
an hourly reconciliation repairs drift. Without it, a crash between the presence write
and the assignment insert leaks agents who are permanently "busy" with a conversation
nobody holds.

``available_agents`` puts heartbeat freshness **in the predicate**, not in a later check.
The ``state`` column alone is a lie the moment a browser closes without notice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class AgentPresence:
    agent_id: int
    state: str
    last_heartbeat: datetime
    current_conversation_id: UUID | None


@dataclass(frozen=True)
class AvailableAgent:
    agent_id: int
    languages: frozenset[str]


class PresenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def heartbeat(self, agent_id: int, state: str) -> None:
        """Upsert presence. Called every 20 s by the console; TTL is 60 s, so three
        missed beats are tolerated before an agent is treated as gone — enough for a
        slow network, not enough to hold a conversation for a closed browser."""
        self._session.execute(
            text(
                """
                INSERT INTO agent_presence (agent_id, state, last_heartbeat, updated_at)
                VALUES (:agent_id, :state, now(), now())
                ON CONFLICT (agent_id) DO UPDATE
                  SET state = EXCLUDED.state,
                      last_heartbeat = now(),
                      updated_at = now()
                """
            ),
            {"agent_id": agent_id, "state": state},
        )

    def available_agents(self, fresh_within: timedelta) -> list[AvailableAgent]:
        """Agents who can take work right now.

        Read-committed; results are a snapshot and MUST be re-verified under lock by the
        assignment engine. Trusting this list without the re-check is the classic
        double-assignment bug.
        """
        rows = self._session.execute(
            text(
                """
                SELECT p.agent_id,
                       COALESCE(array_agg(al.language) FILTER (WHERE al.language IS NOT NULL),
                                '{}') AS languages
                  FROM agent_presence p
                  LEFT JOIN agent_language al ON al.agent_id = p.agent_id
                  JOIN app_user u ON u.id = p.agent_id AND u.is_active
                 WHERE p.state = 'available'
                   AND p.current_conversation_id IS NULL
                   AND p.last_heartbeat > now() - CAST(:ttl || ' seconds' AS interval)
                 GROUP BY p.agent_id
                """
            ),
            {"ttl": int(fresh_within.total_seconds())},
        ).all()
        return [AvailableAgent(row[0], frozenset(row[1])) for row in rows]

    def get_for_update(self, agent_id: int) -> AgentPresence | None:
        """SELECT ... FOR UPDATE. Precondition: open transaction.

        The assignment engine re-checks ``state`` and ``current_conversation_id`` after
        acquiring this lock, because the candidate list it ranked was a snapshot another
        worker may already have invalidated.
        """
        if not self._session.in_transaction():
            raise RuntimeError("get_for_update requires an open transaction")
        row = self._session.execute(
            text(
                """
                SELECT agent_id, state, last_heartbeat, current_conversation_id
                  FROM agent_presence WHERE agent_id = :agent_id FOR UPDATE
                """
            ),
            {"agent_id": agent_id},
        ).mappings().first()
        return AgentPresence(**row) if row else None

    def claim(self, agent_id: int, conversation_id: UUID) -> None:
        """Mark an agent busy with a conversation. Caller must hold the presence lock."""
        self._session.execute(
            text(
                """
                UPDATE agent_presence
                   SET state = 'busy', current_conversation_id = :cid, updated_at = now()
                 WHERE agent_id = :agent_id
                """
            ),
            {"agent_id": agent_id, "cid": conversation_id},
        )

    def release(self, agent_id: int, state: str = "available") -> None:
        self._session.execute(
            text(
                """
                UPDATE agent_presence
                   SET state = :state, current_conversation_id = NULL, updated_at = now()
                 WHERE agent_id = :agent_id
                """
            ),
            {"agent_id": agent_id, "state": state},
        )

    def lapsed(self, ttl: timedelta) -> list[AgentPresence]:
        """Agents whose heartbeat stopped. Read-only."""
        rows = self._session.execute(
            text(
                """
                SELECT agent_id, state, last_heartbeat, current_conversation_id
                  FROM agent_presence
                 WHERE state <> 'offline'
                   AND last_heartbeat < now() - CAST(:ttl || ' seconds' AS interval)
                """
            ),
            {"ttl": int(ttl.total_seconds())},
        ).mappings().all()
        return [AgentPresence(**r) for r in rows]

    def drifted(self) -> list[int]:
        """Agents whose presence disagrees with the authoritative assignment table.

        Two directions of drift, both repaired by the hourly reconciliation job:
        presence claims a conversation with no open assignment, or presence is free
        while an open assignment exists. Without this the fast path leaks agents.
        """
        rows = self._session.execute(
            text(
                """
                SELECT p.agent_id
                  FROM agent_presence p
                  LEFT JOIN assignment a
                    ON a.agent_id = p.agent_id AND a.ended_at IS NULL
                 WHERE (p.current_conversation_id IS NOT NULL AND a.id IS NULL)
                    OR (p.current_conversation_id IS NULL AND a.id IS NOT NULL)
                """
            )
        ).scalars().all()
        return list(rows)
