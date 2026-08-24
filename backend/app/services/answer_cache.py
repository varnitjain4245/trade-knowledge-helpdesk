"""Answer cache, keyed on the knowledge generation (guardrail G3).

A cache hit that cannot be validated is not a hit. When the generation counter cannot be
read — a database outage with Redis still up — every lookup returns a miss and the
request fails on retrieval rather than serving an answer that might cite a retired
circular. That behaviour is required by hld-backend.md §21 and was left to chance until
the Stage 6 review (P1-1).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from app.core.logging import get_logger

log = get_logger(__name__)


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None: ...
    def setex(self, key: str, ttl_seconds: int, value: str) -> None: ...


class InMemoryCacheBackend:
    """Used in tests and in single-process local runs.

    Deliberately not an LRU: the generation key already bounds growth to one knowledge
    generation's worth of distinct queries, and adding eviction here would obscure
    whether a miss came from invalidation or from eviction.
    """

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self._data[key] = value


class AnswerCache:
    def __init__(
        self, backend: CacheBackend, ttl_seconds: int, generation_counter: Any
    ) -> None:
        self._backend = backend
        self._ttl = ttl_seconds
        self._generation = generation_counter

    @staticmethod
    def _normalise(query: str) -> str:
        """Whitespace and case folded so trivially different phrasings share a key.

        Nothing more aggressive: stripping punctuation would collide "notification 12/2024"
        with "notification 122024", and in this domain those are different documents.
        """
        return " ".join(query.lower().split())

    def _key(self, query: str, language: str, generation: int) -> str:
        digest = hashlib.sha256(
            f"{self._normalise(query)}|{language}|{generation}".encode()
        ).hexdigest()
        return f"answer:{digest}"

    def get(self, query: str, language: str) -> dict[str, Any] | None:
        """Look up a cached answer.

        Returns None on a miss **and** when the generation cannot be read. The second
        case is the safety property: a bypass is always correct, whereas a hit against an
        unknown knowledge state is not.
        """
        generation = self._generation.current()
        if generation is None:
            log.warning("answer_cache.bypassed", reason="generation_unreadable")
            return None
        raw = self._backend.get(self._key(query, language, generation))
        return json.loads(raw) if raw else None

    def put(self, query: str, language: str, payload: dict[str, Any]) -> None:
        generation = self._generation.current()
        if generation is None:
            return  # Nothing to key on; skip rather than write an unverifiable entry.
        self._backend.setex(
            self._key(query, language, generation), self._ttl, json.dumps(payload, default=str)
        )
