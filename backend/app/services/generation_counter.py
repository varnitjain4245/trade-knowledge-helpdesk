"""Knowledge generation counter (guardrail G3, resolves hld-review High-1).

The Stage 4 review found a real contradiction: the design required retirement to take
effect immediately, then reintroduced a window through an answer cache. The resolution is
this counter.

Every approval, edit, retirement, supersession and reversal bumps it **inside the same
transaction as the state change**. Cache keys include the generation, so a bump makes
every prior key unreachable atomically — no invalidation scan to get wrong, no per-key
bookkeeping, no window.

The cost is that any knowledge change flushes the whole cache. At the stated change rate
(a handful of items a day) that is negligible, and per-item invalidation would reintroduce
exactly the reasoning errors this design eliminates.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class GenerationCounter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def current(self) -> int | None:
        """Read the counter.

        Returns **None** when it cannot be read — the database being unavailable is the
        case the amendment §M cache bypass depends on. Returning a stale or default
        value here would serve cached answers against an unverifiable knowledge state,
        which is precisely what hld-backend.md §21 forbids.
        """
        try:
            return self._session.execute(
                text("SELECT generation FROM knowledge_generation WHERE id = TRUE")
            ).scalar_one()
        except SQLAlchemyError:
            return None

    def bump(self) -> int:
        """Increment within the caller's transaction; does not commit.

        Called from every lifecycle transition. Being in the same transaction is the
        whole point: the cache cannot observe a retirement that has not committed, nor
        miss one that has.
        """
        return self._session.execute(
            text(
                """
                UPDATE knowledge_generation SET generation = generation + 1
                 WHERE id = TRUE RETURNING generation
                """
            )
        ).scalar_one()
