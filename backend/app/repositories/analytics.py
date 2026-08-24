"""Analytics and gap repositories.

Two rules here are load-bearing and both exist to stop the figures lying:

* ``range`` returns **only days actually computed** and never fabricates zero rows. A
  fabricated zero is indistinguishable from a real quiet day, and REQ-012 requires
  missing intervals to be named rather than averaged across.
* Rollups store sums and counts, never pre-divided averages. A mean of daily means is
  simply wrong when volumes differ between days.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_COUNTERS = (
    "conversations_started", "self_resolved", "agent_resolved", "abandoned",
    "callback_recorded", "answers_shown", "no_answers", "conflicts",
    "assist_suggested", "assist_accepted", "assist_edited",
    "ratings_positive", "ratings_negative", "resolution_count",
    "handover_after_failed_self_serve", "handover_direct",
)


@dataclass
class DailyRow:
    day: date
    language: str
    surface: str
    resolution_seconds_sum: int
    counters: dict[str, int]


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def range(
        self, start: date, end: date, language: str | None = None,
        surface: str | None = None,
    ) -> list[DailyRow]:
        """Rows for days that were actually computed. Never fabricates zeroes.

        Callers MUST cross-check against ``computed_days`` and surface the difference.
        """
        rows = self._session.execute(
            text(
                f"""
                SELECT day, language, surface, resolution_seconds_sum,
                       {", ".join(_COUNTERS)}
                  FROM analytics_daily
                 WHERE day BETWEEN :start AND :end
                   AND (:language IS NULL OR language = :language)
                   AND (:surface IS NULL OR surface = CAST(:surface AS conversation_surface))
                 ORDER BY day
                """
            ),
            {"start": start, "end": end, "language": language, "surface": surface},
        ).mappings().all()
        return [
            DailyRow(
                day=r["day"], language=r["language"], surface=r["surface"],
                resolution_seconds_sum=r["resolution_seconds_sum"],
                counters={c: r[c] for c in _COUNTERS},
            )
            for r in rows
        ]

    def computed_days(self, start: date, end: date) -> set[date]:
        rows = self._session.execute(
            text("SELECT day FROM analytics_gap_day WHERE day BETWEEN :s AND :e"),
            {"s": start, "e": end},
        ).scalars().all()
        return set(rows)

    def upsert_day(self, row: DailyRow) -> None:
        """Full recompute, never increment.

        Idempotent by construction: running the rollup twice for a day produces the same
        figures. An incremental rollup that ran twice would double-count, and the failure
        would be invisible in the output — which is exactly the class of bug that makes
        people stop trusting a dashboard.
        """
        assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in _COUNTERS)
        self._session.execute(
            text(
                f"""
                INSERT INTO analytics_daily
                    (day, language, surface, resolution_seconds_sum, {", ".join(_COUNTERS)},
                     computed_at)
                VALUES (:day, :language, CAST(:surface AS conversation_surface),
                        :resolution_seconds_sum, {", ".join(f":{c}" for c in _COUNTERS)}, now())
                ON CONFLICT (day, language, surface) DO UPDATE
                  SET resolution_seconds_sum = EXCLUDED.resolution_seconds_sum,
                      {assignments},
                      computed_at = now()
                """
            ),
            {
                "day": row.day, "language": row.language, "surface": row.surface,
                "resolution_seconds_sum": row.resolution_seconds_sum,
                **row.counters,
            },
        )

    def mark_day_computed(self, day: date) -> None:
        self._session.execute(
            text(
                """
                INSERT INTO analytics_gap_day (day, computed_at) VALUES (:day, now())
                ON CONFLICT (day) DO UPDATE SET computed_at = now()
                """
            ),
            {"day": day},
        )

    def raw_day(self, day: date) -> list[dict[str, Any]]:
        """Recompute a day's counters from source rows.

        Deliberately one query per day over the partitioned tables: the partition bound
        makes this cheap, and recomputing from source is what makes ``upsert_day``
        idempotent rather than merely repeatable.
        """
        rows = self._session.execute(
            text(
                """
                SELECT c.detected_language AS language,
                       c.surface::text      AS surface,
                       count(*)                                                    AS conversations_started,
                       count(*) FILTER (WHERE c.state = 'self_resolved')           AS self_resolved,
                       count(*) FILTER (WHERE c.state = 'agent_resolved')          AS agent_resolved,
                       count(*) FILTER (WHERE c.state = 'abandoned')               AS abandoned,
                       count(*) FILTER (WHERE c.state = 'callback_recorded')       AS callback_recorded,
                       COALESCE(sum(EXTRACT(EPOCH FROM (c.ended_at - c.started_at)))
                                FILTER (WHERE c.state IN ('self_resolved','agent_resolved')), 0)
                                                                                   AS resolution_seconds_sum,
                       count(*) FILTER (WHERE c.state IN ('self_resolved','agent_resolved'))
                                                                                   AS resolution_count
                  FROM conversation c
                 WHERE c.started_at >= :day AND c.started_at < :day + 1
                 GROUP BY c.detected_language, c.surface
                """
            ),
            {"day": day},
        ).mappings().all()
        return [dict(r) for r in rows]

    def answer_counters_for_day(self, day: date) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT query_language AS language,
                       count(*) FILTER (WHERE outcome = 'answered')  AS answers_shown,
                       count(*) FILTER (WHERE outcome = 'no_answer') AS no_answers,
                       count(*) FILTER (WHERE outcome = 'conflict')  AS conflicts
                  FROM answer_record
                 WHERE created_at >= :day AND created_at < :day + 1
                 GROUP BY query_language
                """
            ),
            {"day": day},
        ).mappings().all()
        return [dict(r) for r in rows]

    def repeat_contact(self, start: date, end: date, within_days: int = 7) -> tuple[int, int, int]:
        """Repeat-contact guardrail — returns (repeats, keyed_conversations, total).

        A **lower bound**, always. It links contacts sharing a pseudonymous browser key,
        so a customer who switches device, clears storage or phones in counts as a new
        person. The caller must publish the caveat and the key coverage alongside the
        figure; a bare percentage here would be read as exact and would understate
        exactly the failure this guardrail exists to catch.
        """
        repeats = self._session.execute(
            text(
                """
                SELECT count(*) FROM (
                    SELECT c.customer_key_hash
                      FROM conversation c
                     WHERE c.customer_key_hash IS NOT NULL
                       AND c.started_at::date BETWEEN :start AND :end
                     GROUP BY c.customer_key_hash
                    HAVING count(*) > 1
                       AND max(c.started_at) - min(c.started_at)
                           <= CAST(:within || ' days' AS interval)
                ) repeat_customers
                """
            ),
            {"start": start, "end": end, "within": within_days},
        ).scalar_one()

        keyed, total = self._session.execute(
            text(
                """
                SELECT count(*) FILTER (WHERE customer_key_hash IS NOT NULL), count(*)
                  FROM conversation
                 WHERE started_at::date BETWEEN :start AND :end
                """
            ),
            {"start": start, "end": end},
        ).one()
        return repeats, keyed, total


class GapRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self, query_text: str, query_language: str, cause: str,
        embedding: list[float] | None, conversation_id: UUID | None,
        answer_id: UUID | None,
    ) -> int:
        """Record a gap. ``query_text`` must already be masked by the caller."""
        return self._session.execute(
            text(
                """
                INSERT INTO gap_entry
                    (query_text, query_language, cause, embedding, conversation_id, answer_id)
                VALUES (:q, :lang, :cause, CAST(:emb AS vector), :cid, :aid)
                RETURNING id
                """
            ),
            {
                "q": query_text, "lang": query_language, "cause": cause,
                "emb": embedding, "cid": conversation_id, "aid": answer_id,
            },
        ).scalar_one()

    def unclustered(self, limit: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            text(
                """
                SELECT id, created_at, query_text, query_language, embedding
                  FROM gap_entry
                 WHERE group_id IS NULL AND embedding IS NOT NULL
                 ORDER BY created_at LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]

    def nearest_open_group(self, embedding: list[float]) -> tuple[int, float] | None:
        """Nearest **open** group only.

        Resolved groups are excluded so a new entry never silently re-opens a manager's
        decision. If the question genuinely recurs it forms a fresh group — which is the
        visible signal that the resolution did not work.
        """
        row = self._session.execute(
            text(
                """
                SELECT id, 1 - (centroid <=> CAST(:emb AS vector)) AS similarity
                  FROM gap_group
                 WHERE resolution = 'open'
                 ORDER BY centroid <=> CAST(:emb AS vector)
                 LIMIT 1
                """
            ),
            {"emb": embedding},
        ).first()
        return (row[0], float(row[1])) if row else None

    def create_group(
        self, centroid: list[float], label: str, language: str
    ) -> int:
        import json

        return self._session.execute(
            text(
                """
                INSERT INTO gap_group (centroid, label, entry_count, language_spread)
                VALUES (CAST(:centroid AS vector), :label, 1, CAST(:spread AS json))
                RETURNING id
                """
            ),
            {"centroid": centroid, "label": label, "spread": json.dumps({language: 1})},
        ).scalar_one()

    def attach_to_group(
        self, entry_id: int, created_at: Any, group_id: int, embedding: list[float],
        language: str,
    ) -> None:
        """Attach an entry and update the group's running centroid and spread.

        The centroid moves by incremental mean rather than a full recompute: the group
        may hold thousands of entries and re-averaging them hourly would make the
        clustering job's cost grow without bound.
        """
        self._session.execute(
            text(
                "UPDATE gap_entry SET group_id = :gid WHERE id = :id AND created_at = :ts"
            ),
            {"gid": group_id, "id": entry_id, "ts": created_at},
        )
        self._session.execute(
            text(
                """
                UPDATE gap_group
                   SET entry_count = entry_count + 1,
                       centroid = CAST(:emb AS vector) * (1.0 / (entry_count + 1))
                                  + centroid * (entry_count::float / (entry_count + 1)),
                       language_spread = jsonb_set(
                           language_spread::jsonb, ARRAY[:lang],
                           to_jsonb(COALESCE((language_spread::jsonb ->> :lang)::int, 0) + 1),
                           true),
                       updated_at = now()
                 WHERE id = :gid
                """
            ),
            {"emb": embedding, "lang": language, "gid": group_id},
        )

    def get_group_for_update(self, group_id: int) -> dict[str, Any] | None:
        if not self._session.in_transaction():
            raise RuntimeError("get_group_for_update requires an open transaction")
        row = self._session.execute(
            text(
                """
                SELECT id, label, entry_count, language_spread, resolution,
                       resolved_item_id, resolution_owner
                  FROM gap_group WHERE id = :id FOR UPDATE
                """
            ),
            {"id": group_id},
        ).mappings().first()
        return dict(row) if row else None

    def resolve_group(
        self, group_id: int, resolution: str, resolved_by: int,
        item_id: UUID | None, owner: int | None,
    ) -> None:
        self._session.execute(
            text(
                """
                UPDATE gap_group
                   SET resolution = :res, resolved_item_id = :item, resolution_owner = :owner,
                       resolved_by = :by, resolved_at = now(), updated_at = now()
                 WHERE id = :id
                """
            ),
            {"res": resolution, "item": item_id, "owner": owner, "by": resolved_by, "id": group_id},
        )

    def open_groups(self, min_size: int, limit: int) -> list[dict[str, Any]]:
        """Ranked actionable queue.

        ``min_size`` filters the *view*, not the clustering — a group that later grows
        past the threshold appears with its full history rather than starting from the
        moment it crossed.
        """
        rows = self._session.execute(
            text(
                """
                SELECT id, label, entry_count, language_spread, updated_at
                  FROM gap_group
                 WHERE resolution = 'open' AND entry_count >= :min_size
                 ORDER BY entry_count DESC LIMIT :limit
                """
            ),
            {"min_size": min_size, "limit": limit},
        ).mappings().all()
        return [dict(r) for r in rows]
