"""Cross-encoder reranker.

Reranking is where confidence becomes meaningful. Raw vector distance is a poor
confidence signal, and using it would make the answer bar meaningless — so this client
is on the critical path for REQ-005, not just for result ordering.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings
from app.models.base import make_breaker, make_client
from app.models.breaker import CircuitBreaker


class RerankClient(Protocol):
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        """Score each passage against the query. Returns scores in input order."""
        ...


class HttpRerankClient:
    def __init__(self, settings: Settings, breaker: CircuitBreaker | None = None) -> None:
        self._http = make_client(settings.rerank_endpoint, settings.timeout_rerank_ms)
        self._breaker = breaker or make_breaker("rerank", settings)

    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []

        async def _call() -> list[float]:
            response = await self._http.post(
                "/rerank", json={"query": query, "passages": passages}
            )
            response.raise_for_status()
            scores = response.json()["scores"]
            if len(scores) != len(passages):
                raise ValueError("rerank score count does not match passage count")
            return [float(s) for s in scores]

        return await self._breaker.call(_call)

    async def aclose(self) -> None:
        await self._http.aclose()
