"""Answer service unit scenarios (lld-backend.md §8.1).

Numbering follows the LLD so a reviewer can check coverage against the design directly.
"""

from __future__ import annotations

import pytest

from app.domain.errors import LanguageNotEnabled, PersistenceError
from app.domain.state import AnswerOutcome
from app.services.answer import AnswerRequest, AnswerResult, AnswerService
from app.services.conflict import ConflictDetector
from app.services.grounding import GroundingVerifier

from tests.conftest import (ITEM_A, ITEM_B, FakeAnswers, FakeCache, FakeCoverage,
                       FakeDetector, FakeEmbedder, FakeExtractive, FakeFairUse,
                       FakeGaps, FakeGeneration, FakeGenerator, FakeLanguages,
                       FakeMasker, FakeReranker, FakeRetrieval, FakeThresholds, chunk)

SUPPORTED = "An export licence is required for restricted goods."
PASSAGE = "An export licence is required for restricted goods under notification 12/2024."


def build(settings, *, results, generator=None, reranker=None, thresholds=None,
          coverage=None, fair_use=None, answers=None, gaps=None, cache=None,
          languages=None, extractive=None):
    return AnswerService(
        settings=settings,
        retrieval=FakeRetrieval(results),
        reranker=reranker or FakeReranker(),
        generator=generator or FakeGenerator(SUPPORTED),
        extractive=extractive or FakeExtractive(),
        verifier=GroundingVerifier(min_coverage=settings.grounding_min_coverage),
        conflict_detector=ConflictDetector(min_score=0.7),
        thresholds=thresholds or FakeThresholds(),
        answers=answers or FakeAnswers(),
        cache=cache or FakeCache(),
        gaps=gaps or FakeGaps(),
        masker=FakeMasker(),
        language_registry=languages or FakeLanguages(),
        coverage_gate=coverage or FakeCoverage(),
        fair_use=fair_use or FakeFairUse(),
        generation_counter=FakeGeneration(),
        detector=FakeDetector(),
        embedder=FakeEmbedder(),
    )


async def test_1_grounded_answer_above_bar(settings, agent_actor):
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)])
    result = await svc.answer(AnswerRequest(query="Do I need a licence?"), agent_actor)
    assert result.outcome is AnswerOutcome.ANSWERED
    assert result.citations and result.citations[0].passage == PASSAGE
    assert result.stale_sources is False


async def test_2_ungrounded_draft_is_discarded_not_shown(settings, agent_actor):
    """The generated text must appear NOWHERE in the response."""
    invented = "The duty rate is 45 percent and refunds take ninety days."
    generator = FakeGenerator(invented)
    extractive = FakeExtractive()
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)],
                generator=generator, extractive=extractive)
    result = await svc.answer(AnswerRequest(query="rate?"), agent_actor)
    assert generator.called and extractive.called
    assert result.answer_text is not None
    assert invented not in result.answer_text, "ungrounded draft leaked into the answer"
    assert result.answer_text == PASSAGE
    assert result.citations


async def test_3_grounding_fails_and_fallback_below_bar_gives_no_answer(settings, agent_actor):
    weak = chunk(1, ITEM_A, PASSAGE, score=0.30)
    svc = build(settings, results=[weak], reranker=FakeReranker([0.30]),
                generator=FakeGenerator("Entirely invented content about tariffs."))
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert result.outcome is AnswerOutcome.NO_ANSWER
    assert not result.citations
    assert result.handover_offered


async def test_5_below_bar_returns_no_answer_and_logs_gap(settings, agent_actor):
    gaps = FakeGaps()
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE, score=0.2)],
                reranker=FakeReranker([0.2]), gaps=gaps)
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert result.outcome is AnswerOutcome.NO_ANSWER
    assert result.related_reading, "related reading is offered as reading, not as an answer"
    assert gaps.entries and gaps.entries[0]["cause"] == "below_bar"


async def test_6_conflict_when_both_sources_above_bar(settings, agent_actor):
    a = chunk(1, ITEM_A, "An export licence is required for restricted goods.", 0.95)
    b = chunk(2, ITEM_B, "An export licence is not required; goods are freely exportable.", 0.93)
    svc = build(settings, results=[a, b], reranker=FakeReranker([0.95, 0.93]))
    result = await svc.answer(AnswerRequest(query="licence?"), agent_actor)
    assert result.outcome is AnswerOutcome.CONFLICT
    assert len(result.conflicting_sources) == 2
    assert result.answer_text is None, "a conflict is not an answer"


async def test_7_conflict_detected_even_when_both_sources_are_below_the_bar(
    settings, agent_actor
):
    """BR-6's ordering assertion.

    The naive implementation checks the answer bar first and returns no_answer here.
    This test is what catches that inversion.
    """
    a = chunk(1, ITEM_A, "An export licence is required for restricted goods.", 0.72)
    b = chunk(2, ITEM_B, "An export licence is not required; goods are freely exportable.", 0.71)
    svc = build(settings, results=[a, b], reranker=FakeReranker([0.72, 0.71]),
                thresholds=FakeThresholds(answer_bar=0.99))
    result = await svc.answer(AnswerRequest(query="licence?"), agent_actor)
    assert result.outcome is AnswerOutcome.CONFLICT, (
        "conflict must be detected before the answer bar is applied"
    )


async def test_9_stale_source_answers_with_review_pending(settings, agent_actor):
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE, stale=True)])
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert result.outcome is AnswerOutcome.ANSWERED, "stale items still answer (BR-9)"
    assert result.stale_sources and result.citations[0].review_pending


async def test_10_no_match_returns_no_answer(settings, agent_actor):
    gaps = FakeGaps()
    svc = build(settings, results=[], gaps=gaps)
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert result.outcome is AnswerOutcome.NO_ANSWER
    assert not result.related_reading
    assert gaps.entries[0]["cause"] == "no_match"


async def test_11_rerank_timeout_caps_confidence_below_bar(settings, agent_actor):
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE, score=0.99)],
                reranker=FakeReranker(fail=True))
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert result.outcome is AnswerOutcome.NO_ANSWER, (
        "an unranked candidate set must not produce an answer"
    )


async def test_12_generation_timeout_falls_back_to_extractive(settings, agent_actor):
    extractive = FakeExtractive()
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)],
                generator=FakeGenerator("", fail=True), extractive=extractive)
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert extractive.called
    assert result.outcome is AnswerOutcome.ANSWERED
    assert result.citations


async def test_13_persistence_failure_means_no_answer_is_returned(settings, agent_actor):
    answers = FakeAnswers()
    answers.fail = True
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)], answers=answers)
    with pytest.raises(PersistenceError):
        await svc.answer(AnswerRequest(query="q"), agent_actor)


async def test_14_language_not_enabled_rejects_before_retrieval(settings, agent_actor):
    retrieval_probe = FakeRetrieval([chunk(1, ITEM_A, PASSAGE)])
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)],
                languages=FakeLanguages(enabled=("hin",)))
    svc._retrieval = retrieval_probe
    with pytest.raises(LanguageNotEnabled):
        await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert retrieval_probe.calls == 0, "no retrieval should be attempted"


async def test_15_public_blocked_when_coverage_floor_undeclared(settings, public_actor):
    generator = FakeGenerator(SUPPORTED)
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)],
                coverage=FakeCoverage(open_=False), generator=generator)
    result = await svc.answer(AnswerRequest(query="q"), public_actor)
    assert result.outcome is AnswerOutcome.BLOCKED_COVERAGE
    assert not generator.called, "no model call should be made behind a closed gate"
    assert result.handover_offered


async def test_16_fair_use_block_still_offers_handover(settings, public_actor):
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)],
                fair_use=FakeFairUse(allow=False))
    result = await svc.answer(AnswerRequest(query="q"), public_actor)
    assert result.outcome is AnswerOutcome.BLOCKED_FAIR_USE
    assert result.handover_offered, "limiting must never remove the path to a human"
    assert result.retry_after_seconds == 1800


async def test_15b_agent_bypasses_the_coverage_gate(settings, agent_actor):
    """REQ-023: agent assist is live from the first approved item."""
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)], coverage=FakeCoverage(open_=False))
    result = await svc.answer(AnswerRequest(query="q"), agent_actor)
    assert result.outcome is AnswerOutcome.ANSWERED


async def test_17_answered_result_without_citations_is_unrepresentable():
    """BR-1 as a constructor invariant — the server half of the frontend's type rule."""
    with pytest.raises(ValueError, match="at least one citation"):
        AnswerResult(outcome=AnswerOutcome.ANSWERED, answer_text="something", citations=[])


async def test_cache_hit_skips_the_model(settings, agent_actor):
    cache = FakeCache()
    generator = FakeGenerator(SUPPORTED)
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)], cache=cache, generator=generator)
    first = await svc.answer(AnswerRequest(query="Do I need a licence?"), agent_actor)
    assert first.outcome is AnswerOutcome.ANSWERED

    generator2 = FakeGenerator("SHOULD NOT BE CALLED")
    svc2 = build(settings, results=[chunk(1, ITEM_A, PASSAGE)], cache=cache, generator=generator2)
    second = await svc2.answer(AnswerRequest(query="Do I need a licence?"), agent_actor)
    assert second.outcome is AnswerOutcome.ANSWERED
    assert not generator2.called
    assert second.citations[0].passage == PASSAGE


async def test_6b_weak_tangential_source_does_not_veto_a_strong_answer(
    settings, agent_actor
):
    """A conflict needs two *comparable* sources.

    Regression for a false conflict found while exercising the demo corpus: a weak
    passage containing a negation blocked a strong, well-supported answer to an
    unrelated question. Withholding a good answer is the opposite of BR-6's intent.
    """
    strong = chunk(1, ITEM_A, "An export licence is required for restricted goods.", 0.95)
    tangent = chunk(2, ITEM_B, "Handicraft wood items are freely exportable, no licence.", 0.42)
    svc = build(settings, results=[strong, tangent], reranker=FakeReranker([0.95, 0.42]))
    result = await svc.answer(AnswerRequest(query="licence for restricted goods?"), agent_actor)
    assert result.outcome is AnswerOutcome.ANSWERED
    assert result.citations[0].item_id == ITEM_A


async def test_cache_hit_round_trips_citation_types(settings, agent_actor):
    """A cached citation must come back with real date and UUID types.

    Regression for a bug found by running the demo: the cache stores JSON, so
    ``issued_on`` returned as a string and the response serialiser crashed with
    ``'str' object has no attribute 'isoformat'`` — on the cache-hit path only, which is
    where it was least likely to be caught. The unit tests passed throughout, because
    they never asserted on the *types* of a rehydrated citation.
    """
    import json
    from datetime import date as date_type
    from uuid import UUID as uuid_type

    cache = FakeCache()
    svc = build(settings, results=[chunk(1, ITEM_A, PASSAGE)], cache=cache)
    await svc.answer(AnswerRequest(query="Do I need a licence?"), agent_actor)

    # Force the cache through a real JSON round trip, as Redis does.
    for key, payload in list(cache.store.items()):
        cache.store[key] = json.loads(json.dumps(payload, default=str))

    svc2 = build(settings, results=[chunk(1, ITEM_A, PASSAGE)], cache=cache,
                 generator=FakeGenerator("SHOULD NOT BE CALLED"))
    cached = await svc2.answer(AnswerRequest(query="Do I need a licence?"), agent_actor)

    citation = cached.citations[0]
    assert isinstance(citation.issued_on, date_type), "issued_on must rehydrate as a date"
    assert isinstance(citation.item_id, uuid_type), "item_id must rehydrate as a UUID"
    assert citation.issued_on.isoformat() == "2024-04-01"
