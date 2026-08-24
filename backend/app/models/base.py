"""Shared model-client plumbing.

Every client is an interface plus an HTTP implementation, so the answer path can be unit
tested without a GPU (guardrail: LLD §5 DIP). Timeouts come from settings, never from
inline constants (guardrail G6).
"""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.models.breaker import CircuitBreaker


def make_client(base_url: str, timeout_ms: int) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout_ms / 1000.0),
        # No retries at this layer: the answer path's stage budget already defines what
        # happens on timeout, and a hidden retry would blow that budget silently.
        transport=httpx.AsyncHTTPTransport(retries=0),
    )


def make_breaker(name: str, settings: Settings) -> CircuitBreaker:
    return CircuitBreaker(
        name=name,
        failure_threshold=settings.circuit_breaker_failure_threshold,
        half_open_after_seconds=settings.circuit_breaker_half_open_seconds,
    )
