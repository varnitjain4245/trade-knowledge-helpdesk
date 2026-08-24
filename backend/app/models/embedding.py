"""Multilingual embedding client.

The model is the mechanism behind REQ-001's central promise: a Tamil query must land
near a Hindi or English passage of the same meaning, which is what makes "search all
knowledge regardless of item language" true.

``model_tag`` travels with every vector. A model change is a re-embed, never a silent
mix of two vector spaces — that failure is invisible in testing and corrupts retrieval.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.core.config import Settings
from app.models.base import make_breaker, make_client
from app.models.breaker import CircuitBreaker


class EmbeddingClient(Protocol):
    model_tag: str

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch. Returns one vector per input, in order.

        Raises ``httpx.HTTPError`` on transport failure and ``CircuitOpen`` while the
        breaker is open. Callers decide the degradation; this client never guesses.
        """
        ...


class HttpEmbeddingClient:
    def __init__(self, settings: Settings, breaker: CircuitBreaker | None = None) -> None:
        self.model_tag = settings.embedding_model_tag
        self._dims = settings.embedding_dimensions
        self._http = make_client(settings.embedding_endpoint, settings.timeout_embed_ms)
        self._breaker = breaker or make_breaker("embedding", settings)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        async def _call() -> list[list[float]]:
            response = await self._http.post("/embed", json={"inputs": texts})
            response.raise_for_status()
            vectors = response.json()["embeddings"]
            if len(vectors) != len(texts):
                raise httpx.HTTPError(
                    f"embedding count mismatch: {len(vectors)} for {len(texts)} inputs"
                )
            for vector in vectors:
                if len(vector) != self._dims:
                    # A wrong-dimension vector would be rejected by the column type
                    # anyway; failing here names the cause instead of surfacing a
                    # database error three layers up.
                    raise httpx.HTTPError(
                        f"expected {self._dims} dimensions, got {len(vector)}"
                    )
            return vectors

        return await self._breaker.call(_call)

    async def aclose(self) -> None:
        await self._http.aclose()
