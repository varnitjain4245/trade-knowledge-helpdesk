"""Test doubles for the answer path.

Repositories and model clients are faked so the orchestration in AnswerService can be
tested in milliseconds. That matters because the orchestration is where the subtle
upstream findings live — conflict-before-bar, grounding suppression, persist-before-
return — and those tests must run on every commit, not only when a database is available.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.core.config import Settings
from app.repositories.protocols import ScoredChunk
from app.services.authz import Actor, Role

ITEM_A = UUID("11111111-1111-1111-1111-111111111111")
ITEM_B = UUID("22222222-2222-2222-2222-222222222222")


def chunk(
    chunk_id: int, item_id: UUID, body: str, score: float = 0.9, stale: bool = False
) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id, item_id=item_id, body=body, heading_path="3.2 Licensing",
        item_title="Notification 12/2024", issuing_authority="DGFT",
        issued_on=date(2024, 4, 1), item_language="eng", item_is_stale=stale,
        dense_score=score, lexical_score=0.0, rerank_score=score,
    )


class FakeRetrieval:
    def __init__(self, results: list[ScoredChunk]) -> None:
        self.results = results
        self.calls = 0

    def hybrid_search(self, vector, text, candidates):  # noqa: ANN001
        self.calls += 1
        return list(self.results)


class FakeEmbedder:
    async def embed(self, texts):  # noqa: ANN001
        return [[0.1] * 8 for _ in texts]


class FakeReranker:
    def __init__(self, scores: list[float] | None = None, fail: bool = False) -> None:
        self.scores = scores
        self.fail = fail

    async def rerank(self, query, passages):  # noqa: ANN001
        if self.fail:
            raise TimeoutError("rerank timed out")
        return self.scores if self.scores is not None else [0.9] * len(passages)


class FakeGenerator:
    def __init__(self, text: str, fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.called = False

    async def generate(self, query, context, language) -> AsyncIterator[str]:  # noqa: ANN001
        self.called = True
        if self.fail:
            raise TimeoutError("generation timed out")
        yield self.text


class FakeExtractive:
    def __init__(self) -> None:
        self.called = False

    async def generate(self, query, context, language) -> AsyncIterator[str]:  # noqa: ANN001
        self.called = True
        if context:
            yield context[0].body


class FakeAnswers:
    def __init__(self) -> None:
        self.recorded: list = []
        self.fail = False

    def record(self, answer):  # noqa: ANN001
        if self.fail:
            from app.domain.errors import PersistenceError

            raise PersistenceError("disk on fire")
        self.recorded.append(answer)
        return uuid4()


class FakeGaps:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def record_gap(self, **kw):  # noqa: ANN003
        self.entries.append(kw)


class FakeCache:
    def __init__(self) -> None:
        self.store: dict = {}

    def get(self, query, language):  # noqa: ANN001
        return self.store.get((query, language))

    def put(self, query, language, payload):  # noqa: ANN001
        self.store[(query, language)] = payload


class FakeThresholds:
    def __init__(self, **values: float) -> None:
        self.values = {"answer_bar": 0.70, **values}

    def get(self, name: str) -> float:
        return self.values[name]


class FakeLanguages:
    def __init__(self, enabled=("eng", "hin")) -> None:
        self._enabled = frozenset(enabled)

    def enabled_codes(self):
        return self._enabled


class FakeCoverage:
    def __init__(self, open_: bool = True) -> None:
        self.open = open_

    def is_public_answer_open(self) -> bool:
        return self.open


class FakeFairUse:
    def __init__(self, allow: bool = True) -> None:
        self._allow = allow

    def allow(self, token):  # noqa: ANN001
        return (True, None) if self._allow else (False, 1800)


class FakeGeneration:
    def current(self) -> int:
        return 7


class FakeDetector:
    def __init__(self, language: str = "eng") -> None:
        self.language = language

    def detect(self, text: str) -> str:
        return self.language


class FakeMasker:
    def mask(self, text: str):  # noqa: ANN001
        from app.services.masking import MaskResult

        return MaskResult(text=text, entities_masked=0, min_confidence=1.0, withheld=False)


@pytest.fixture
def settings() -> Settings:
    return Settings(generation_enabled=True)


@pytest.fixture
def agent_actor() -> Actor:
    return Actor(user_id=1, roles=frozenset({Role.AGENT}))


@pytest.fixture
def public_actor() -> Actor:
    return Actor.public("tok-abc")
