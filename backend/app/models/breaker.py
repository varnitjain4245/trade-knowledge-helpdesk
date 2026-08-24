"""Circuit breaker for model clients (amendment §R).

Timeouts alone are most of the value, but when a model server is genuinely down every
request still pays its full timeout before degrading — 2 seconds of first-token timeout,
thirteen times a second at peak. The breaker converts that into fast degradation.

It never breaks the citation guarantee: the open state routes to extractive answering,
which is still retrieval-grounded and still bar-checked. It degrades prose quality,
never provenance (guardrail G4).
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Awaitable, Callable, TypeVar

from app.core.logging import get_logger

log = get_logger(__name__)
T = TypeVar("T")


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpen(Exception):
    """Raised instead of attempting a call the breaker believes will fail."""


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int,
        half_open_after_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._name = name
        self._threshold = failure_threshold
        self._cooldown = half_open_after_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._state = BreakerState.CLOSED

    @property
    def state(self) -> BreakerState:
        if self._state is BreakerState.OPEN and self._opened_at is not None:
            if self._clock() - self._opened_at >= self._cooldown:
                self._state = BreakerState.HALF_OPEN
        return self._state

    def _record_success(self) -> None:
        if self._state is not BreakerState.CLOSED:
            log.info("breaker.closed", breaker=self._name)
        self._failures = 0
        self._opened_at = None
        self._state = BreakerState.CLOSED

    def _record_failure(self) -> None:
        self._failures += 1
        # A failed half-open probe re-opens immediately rather than waiting for the
        # threshold again: one probe is the test, and it failed.
        if self._state is BreakerState.HALF_OPEN or self._failures >= self._threshold:
            self._state = BreakerState.OPEN
            self._opened_at = self._clock()
            log.warning("breaker.opened", breaker=self._name, failures=self._failures)

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Run ``fn`` under the breaker.

        Raises ``CircuitOpen`` without calling ``fn`` while open. Callers translate that
        into their degradation path — they must not treat it as a hard failure.
        """
        if self.state is BreakerState.OPEN:
            raise CircuitOpen(self._name)
        try:
            result = await fn()
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result
