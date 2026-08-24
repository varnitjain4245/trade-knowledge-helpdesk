"""Request deadlines.

Per-stage timeouts bound one stage; this bounds the whole request. Without it, several
stages running slow-but-under-timeout add up past the p95 target with nothing to notice
(found while verifying the stage timeouts against the §4.6 budget — recorded as an
upstream gap).

The rule when a deadline passes: take the shortest **safe** exit, never the fastest one.
Concretely that means falling back to extractive answering or to no-answer — never
skipping the grounding check to save time, because a fast unverified answer is the one
outcome this system must not produce (guardrail G4).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Deadline:
    """A monotonic budget for one request."""

    budget_ms: int
    started_at: float

    @classmethod
    def start(cls, budget_ms: int) -> Deadline:
        return cls(budget_ms=budget_ms, started_at=time.monotonic())

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_at) * 1000)

    @property
    def remaining_ms(self) -> int:
        return max(0, self.budget_ms - self.elapsed_ms)

    @property
    def expired(self) -> bool:
        return self.remaining_ms == 0

    def clamp(self, stage_timeout_ms: int) -> float:
        """Seconds available for a stage: its own ceiling, or what is left, whichever
        is smaller. A stage is never given longer than the request has remaining."""
        return min(stage_timeout_ms, self.remaining_ms) / 1000.0

    def allows(self, stage_cost_ms: int) -> bool:
        """Whether a stage with this expected cost should still be attempted.

        Used before generation specifically: starting a 2.5 s generation with 400 ms
        left produces a truncated answer nobody wanted, when the extractive fallback
        would have produced a complete cited one in the time available.
        """
        return self.remaining_ms >= stage_cost_ms
