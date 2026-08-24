"""Answer service — the sole producer of answers on every surface.

Endorsed explicitly by the Stage 4 review (§5.1): both consoles and the public assistant
call this one service, so BR-1 (citation required), the answer bar, and conflict ordering
have exactly one enforcement point and cannot drift between surfaces.

The step order in ``answer`` is load-bearing. Three separate upstream review findings
live in it:

* **Conflict detection precedes the answer bar** (BR-6, amended in requirements v1.1).
  The other order silently drops below-bar conflicts.
* **Grounding failure suppresses, never warns** (BR-1). An ungrounded draft is discarded.
* **The answer is persisted before it is returned** (REQ-014). An answer that was shown
  but not recorded defeats the traceability the product exists for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.core.config import Settings
from app.core.deadline import Deadline
from app.core.logging import get_logger
from app.domain.errors import LanguageNotEnabled, ModelUnavailable
from app.domain.state import AnswerOutcome
from app.models.breaker import CircuitOpen
from app.models.generation import GenerationContext
from app.repositories.answer import AnswerToRecord, CitationRow
from app.repositories.protocols import ScoredChunk
from app.services.authz import Actor

log = get_logger(__name__)


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    item_id: UUID
    item_title: str
    issuing_authority: str
    issued_on: date
    passage: str
    passage_language: str
    heading_path: str | None
    review_pending: bool
    rank: int


@dataclass
class AnswerResult:
    outcome: AnswerOutcome
    answer_id: UUID | None = None
    answer_text: str | None = None
    answer_language: str | None = None
    confidence: Decimal | None = None
    citations: list[Citation] = field(default_factory=list)
    conflicting_sources: list[Citation] = field(default_factory=list)
    related_reading: list[Citation] = field(default_factory=list)
    handover_offered: bool = False
    stale_sources: bool = False
    latency_ms: int = 0
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        # BR-1 as an invariant, checked at construction: an `answered` result with no
        # citation cannot exist. The frontend enforces the same rule in its type system;
        # this is the server half.
        if self.outcome is AnswerOutcome.ANSWERED and not self.citations:
            raise ValueError("an answered result must carry at least one citation (BR-1)")


#: The judge's scale calls this "answers most of it, or answers it partially".
#: A score at or below it means a better record may still exist.
PARTIAL_MATCH = 0.7


@dataclass(frozen=True)
class AnswerRequest:
    query: str
    conversation_id: UUID | None = None
    preferred_language: str | None = None
    context_turns: list[dict] = field(default_factory=list)


def _to_citation(chunk: ScoredChunk, rank: int) -> Citation:
    return Citation(
        chunk_id=chunk.chunk_id,
        item_id=chunk.item_id,
        item_title=chunk.item_title,
        issuing_authority=chunk.issuing_authority,
        issued_on=chunk.issued_on,
        # BR-3: the passage is never re-worded into another language. A translated
        # quotation is no longer evidence.
        passage=chunk.body,
        passage_language=chunk.item_language,
        heading_path=chunk.heading_path,
        review_pending=chunk.item_is_stale,
        rank=rank,
    )


class AnswerService:
    def __init__(
        self, *, settings: Settings, retrieval, reranker, generator, extractive,
        verifier, conflict_detector, thresholds, answers, cache, gaps, masker,
        language_registry, coverage_gate, fair_use, generation_counter, detector,
        embedder, clock=None,
    ) -> None:
        self._settings = settings
        self._retrieval = retrieval
        self._reranker = reranker
        self._generator = generator
        self._extractive = extractive
        self._verifier = verifier
        self._conflicts = conflict_detector
        self._thresholds = thresholds
        self._answers = answers
        self._cache = cache
        self._gaps = gaps
        self._masker = masker
        self._languages = language_registry
        self._coverage = coverage_gate
        self._fair_use = fair_use
        self._generation = generation_counter
        self._detector = detector
        self._embedder = embedder

    async def answer(self, request: AnswerRequest, actor: Actor) -> AnswerResult:
        deadline = Deadline.start(
            self._settings.answer_deadline_public_ms
            if actor.is_public
            else self._settings.answer_deadline_ms
        )

        # 1. Gate the public surface only. Agent assist bypasses entirely — REQ-023
        #    makes assist live from the first approved item.
        if actor.is_public:
            if not self._coverage.is_public_answer_open():
                return self._blocked(AnswerOutcome.BLOCKED_COVERAGE, deadline)
            allowed, retry_after = self._fair_use.allow(actor.conversation_token)
            if not allowed:
                # Limiting never removes the path to a human (REQ-023).
                return self._blocked(
                    AnswerOutcome.BLOCKED_FAIR_USE, deadline, retry_after=retry_after
                )

        # 2. Explicit choice wins over detection (REQ-001).
        language = request.preferred_language or self._detector.detect(request.query)
        enabled = self._languages.enabled_codes()
        if language not in enabled:
            raise LanguageNotEnabled(language, sorted(enabled))

        # 3. Cache, keyed on the knowledge generation. A bump from any lifecycle change
        #    makes every prior key unreachable (guardrail G3).
        cached = self._cache.get(request.query, language)
        if cached is not None:
            log.info("answer.cache_hit", language=language)
            return self._from_cache(cached, deadline)

        answer_bar = float(self._thresholds.get("answer_bar"))

        # 4. Retrieve. The answerable-set filter lives inside the repository, so
        #    retirement takes effect on the next query with no cache or index sweep.
        try:
            vectors = await self._embedder.embed([request.query])
            candidates = self._retrieval.hybrid_search(
                vectors[0], request.query, self._settings.retrieval_candidate_count
            )
        except CircuitOpen as exc:
            raise ModelUnavailable("embedding unavailable") from exc

        if not candidates:
            return self._no_answer(request, language, [], "no_match", deadline, actor)

        # 5. Rerank. On timeout, cap confidence below the bar rather than answering from
        #    an unranked candidate set — a badly-ranked answer is worse than none.
        confidence_ceiling: float | None = None
        try:
            scores = await self._reranker.rerank(
                request.query, [c.body for c in candidates]
            )
            candidates = sorted(
                [
                    ScoredChunk(**{**c.__dict__, "rerank_score": s})
                    for c, s in zip(candidates, scores, strict=True)
                ],
                key=lambda c: c.score,
                reverse=True,
            )
        except (CircuitOpen, TimeoutError, ValueError) as exc:
            log.warning("answer.rerank_unavailable", error=str(exc))
            confidence_ceiling = answer_bar - 0.01

        top = candidates[: self._settings.rerank_top_n]

        # 5b. Second retrieval pass, triggered by the judge rather than by a lexical
        #     score. Measurement is the reason: for "my goods are stuck at the port"
        #     BM25 returns a confidently wrong record at 0.58, so a low lexical score
        #     does not mark the failure — the index is sure, and sure of the wrong
        #     thing. What does mark it is the judge finding that nothing retrieved
        #     answers the question. So the retry fires exactly where the request was
        #     otherwise about to end in a refusal or a partial answer, and nowhere
        #     else.
        #
        #     The trigger is "partial or worse", not "below the bar", and the
        #     difference is not cosmetic. The judge's own scale calls 0.7 "answers it
        #     partially" and the answer bar is also 0.7, so a partial match sits
        #     exactly on the bar and passes. "My goods are stuck at the port" scored
        #     0.7 against pre-shipment inspection and was answered from it. Retrying
        #     on equality is what reaches those; a strict inequality never fires.
        #
        #     The rewrite is a retrieval key only. It never reaches the generator and
        #     is never shown, so it cannot introduce a claim, and the judge still
        #     scores the second pass against the user's own words — the rewrite gets
        #     no say in whether its own results are good.
        rewriter = getattr(self, "_rewriter", None)
        judged_best = top[0].score if top else 0.0
        if (
            rewriter is not None
            and confidence_ceiling is None
            and judged_best <= PARTIAL_MATCH
            and rewriter.should_rewrite()
            and deadline.allows(2000)
        ):
            rewritten = await rewriter.rewrite(request.query)
            if rewritten:
                second = self._retrieval.hybrid_search(
                    vectors[0], rewritten, self._settings.retrieval_candidate_count
                )
                if second:
                    try:
                        scores2 = await self._reranker.rerank(
                            request.query, [c.body for c in second]
                        )
                        rejudged = sorted(
                            [
                                ScoredChunk(**{**c.__dict__, "rerank_score": s2})
                                for c, s2 in zip(second, scores2, strict=True)
                            ],
                            key=lambda c: c.score,
                            reverse=True,
                        )
                        # A tie goes to the rewrite, and only a tie. This branch is
                        # reached only when the first pass was partial or worse, so
                        # nothing strong is ever displaced. Between two equally-judged
                        # partial matches, the one retrieved on a named subject is the
                        # better citation: asked "what do I need to sell abroad", both
                        # the e-commerce consumer rules and the Importer Exporter Code
                        # score 0.7, and only one of them is what was asked about.
                        if rejudged and rejudged[0].score >= judged_best:
                            log.info("answer.rewrite_improved",
                                     before=round(judged_best, 3),
                                     after=round(rejudged[0].score, 3))
                            candidates = rejudged
                            top = candidates[: self._settings.rerank_top_n]
                    except (CircuitOpen, TimeoutError, ValueError) as exc:
                        log.warning("answer.rewrite_rerank_failed", error=str(exc))

        # 6. Conflict detection BEFORE the bar (BR-6). A conflict is shown regardless of
        #    confidence and is never counted as an answer.
        conflict = self._conflicts.detect(top)
        if conflict is not None:
            return self._conflict_result(request, language, conflict, deadline, actor)

        # 7. Confidence, then the bar.
        confidence = self._compute_confidence(top, grounding_coverage=None)
        if confidence_ceiling is not None:
            confidence = min(confidence, confidence_ceiling)
        if confidence < answer_bar:
            return self._no_answer(request, language, top[:3], "below_bar", deadline, actor)

        # 8. Generate, then verify. Nothing generated is shown before step 9 passes.
        context = [
            GenerationContext(
                chunk_id=c.chunk_id, body=c.body, heading_path=c.heading_path,
                source_language=c.item_language,
            )
            for c in top
        ]
        draft = await self._generate(context, request.query, language, deadline)
        report = self._verifier.verify(draft, {c.chunk_id: c.body for c in top})

        # 9. Suppression, not warning. An ungrounded draft is discarded and the
        #    extractive fallback takes over — still cited, still bar-checked.
        if report.grounded and draft.strip():
            final_text = draft
            cited = [c for c in top if c.chunk_id in report.supporting_chunk_ids] or [top[0]]
            confidence = self._compute_confidence(top, grounding_coverage=report.coverage)
        else:
            log.info("answer.grounding_failed", coverage=report.coverage)
            # Route through the extractive *strategy* rather than assembling a fallback
            # inline: two definitions of "extractive answer" is how the fallback path
            # quietly diverges from the one that runs when there is no GPU.
            final_text = await self._collect(
                self._extractive, request.query, context, language
            )
            cited = [top[0]]
            confidence = self._compute_confidence(top, grounding_coverage=None)
            if confidence < answer_bar:
                return self._no_answer(
                    request, language, top[:3], "grounding_failed", deadline, actor
                )

        citations = [_to_citation(c, rank=i + 1) for i, c in enumerate(cited)]

        # 10. BR-1 enforced at the last possible moment: an empty citation list cannot
        #     leave this method as an answer.
        if not citations:
            return self._no_answer(request, language, top[:3], "no_citation", deadline, actor)

        # 11. Persist BEFORE returning (REQ-014).
        stale = any(c.item_is_stale for c in cited)
        answer_id = self._answers.record(
            AnswerToRecord(
                conversation_id=request.conversation_id,
                query_text=self._masker.mask(request.query).text,
                query_language=language,
                answer_language=language,
                outcome=AnswerOutcome.ANSWERED,
                answer_text=final_text,
                confidence=Decimal(str(round(confidence, 3))),
                stale_sources=stale,
                generation=self._generation.current() or 0,
                latency_ms=deadline.elapsed_ms,
                citations=[
                    CitationRow(
                        chunk_id=c.chunk_id, item_id=c.item_id, rank=i + 1,
                        rerank_score=c.score,
                    )
                    for i, c in enumerate(cited)
                ],
            )
        )

        result = AnswerResult(
            outcome=AnswerOutcome.ANSWERED,
            answer_id=answer_id,
            answer_text=final_text,
            answer_language=language,
            confidence=Decimal(str(round(confidence, 3))),
            citations=citations,
            stale_sources=stale,
            latency_ms=deadline.elapsed_ms,
        )
        self._cache.put(request.query, language, self._to_cacheable(result))
        return result

    async def _generate(
        self, context: list[GenerationContext], query: str, language: str,
        deadline: Deadline,
    ) -> str:
        """Run generation, falling back to extractive on any failure.

        The deadline check before starting matters: beginning a 2.5 s generation with
        400 ms left yields a truncated answer nobody wanted, when the extractive path
        produces a complete cited one in the time available.
        """
        if not self._settings.generation_enabled or not deadline.allows(
            self._settings.timeout_generate_complete_ms
        ):
            return await self._collect(self._extractive, query, context, language)
        try:
            return await self._collect(self._generator, query, context, language)
        except (CircuitOpen, TimeoutError, ModelUnavailable) as exc:
            log.warning("answer.generation_unavailable", error=str(exc))
            return await self._collect(self._extractive, query, context, language)

    @staticmethod
    async def _collect(service, query, context, language) -> str:  # type: ignore[no-untyped-def]
        parts: list[str] = []
        async for token in service.generate(query, context, language):
            parts.append(token)
        return "".join(parts)

    @staticmethod
    def _compute_confidence(
        top: list[ScoredChunk], grounding_coverage: float | None
    ) -> float:
        """Composite confidence.

        Deliberately **not** the generator's self-reported certainty, which is
        uncorrelated with correctness. The rerank score carries most of the signal — it
        is a cross-encoder judgement of whether this passage answers this query — and
        grounding coverage adjusts it once generation has happened.

        Agreement across chunks is a **bonus, never a penalty**. An earlier version
        averaged it in, which made a single strong source score below the bar and left
        the system unable to answer from one authoritative circular — the most common
        real case in this domain. Corroboration should raise confidence; its absence
        should not lower it.

        The weights are calibration inputs, not truths: §4.6 records that they must be
        calibrated against the acceptance question set before the answer bar means
        anything.
        """
        if not top:
            return 0.0

        best = max(0.0, min(1.0, top[0].score))

        # Corroboration bonus: other retrieved passages from the same item saying
        # related things. Capped so it can never carry a weak match over the bar alone.
        corroboration = sum(1 for c in top[1:4] if c.item_id == top[0].item_id)
        bonus = min(0.05, 0.02 * corroboration)

        if grounding_coverage is None:
            # Pre-generation: retrieval strength is all we have.
            return round(min(1.0, best + bonus), 4)

        # Post-generation: coverage tempers the retrieval score in both directions.
        return round(min(1.0, 0.8 * best + 0.2 * grounding_coverage + bonus), 4)

    def _no_answer(
        self, request: AnswerRequest, language: str, related: list[ScoredChunk],
        reason: str, deadline: Deadline, actor: Actor,
    ) -> AnswerResult:
        """No reliable answer.

        Not an error (guardrail G5). Returned at 200 with related reading explicitly
        labelled as reading rather than as an answer, and always with a handover offer.
        """
        masked = self._masker.mask(request.query)
        answer_id = self._answers.record(
            AnswerToRecord(
                conversation_id=request.conversation_id,
                query_text=masked.text, query_language=language, answer_language=None,
                outcome=AnswerOutcome.NO_ANSWER, answer_text=None, confidence=None,
                stale_sources=False, generation=self._generation.current() or 0,
                latency_ms=deadline.elapsed_ms, citations=[],
            )
        )
        self._gaps.record_gap(
            query_text=masked.text, query_language=language, cause=reason,
            conversation_id=request.conversation_id, answer_id=answer_id,
        )
        return AnswerResult(
            outcome=AnswerOutcome.NO_ANSWER,
            answer_id=answer_id,
            related_reading=[_to_citation(c, i + 1) for i, c in enumerate(related)],
            handover_offered=True,
            latency_ms=deadline.elapsed_ms,
        )

    def _conflict_result(
        self, request: AnswerRequest, language: str, conflict, deadline: Deadline,
        actor: Actor,
    ) -> AnswerResult:
        masked = self._masker.mask(request.query)
        answer_id = self._answers.record(
            AnswerToRecord(
                conversation_id=request.conversation_id,
                query_text=masked.text, query_language=language, answer_language=language,
                outcome=AnswerOutcome.CONFLICT, answer_text=None, confidence=None,
                stale_sources=any(c.item_is_stale for c in conflict.sources),
                generation=self._generation.current() or 0,
                latency_ms=deadline.elapsed_ms,
                citations=[
                    CitationRow(chunk_id=c.chunk_id, item_id=c.item_id, rank=i + 1,
                                rerank_score=c.score)
                    for i, c in enumerate(conflict.sources)
                ],
            )
        )
        self._gaps.record_gap(
            query_text=masked.text, query_language=language, cause="conflict",
            conversation_id=request.conversation_id, answer_id=answer_id,
        )
        return AnswerResult(
            outcome=AnswerOutcome.CONFLICT,
            answer_id=answer_id,
            answer_language=language,
            conflicting_sources=[
                _to_citation(c, i + 1) for i, c in enumerate(conflict.sources)
            ],
            # A conflict needs a human, but it is not evidence the system cannot answer —
            # so it offers handover without counting toward the below-bar streak.
            handover_offered=True,
            latency_ms=deadline.elapsed_ms,
        )

    def _blocked(
        self, outcome: AnswerOutcome, deadline: Deadline, retry_after: int | None = None
    ) -> AnswerResult:
        return AnswerResult(
            outcome=outcome, handover_offered=True, latency_ms=deadline.elapsed_ms,
            retry_after_seconds=retry_after,
        )

    @staticmethod
    def _to_cacheable(result: AnswerResult) -> dict:
        return {
            "answer_text": result.answer_text,
            "answer_language": result.answer_language,
            "confidence": str(result.confidence) if result.confidence else None,
            "stale_sources": result.stale_sources,
            "citations": [c.__dict__ for c in result.citations],
        }

    @staticmethod
    def _rehydrate_citation(raw: dict) -> Citation:
        """Rebuild a Citation from its cached JSON form.

        The cache is JSON, so ``issued_on`` and ``item_id`` come back as strings. Passing
        them through unconverted produces a Citation that looks correct and then fails at
        serialisation time — on the cache-hit path only, which is exactly where it is
        least likely to be noticed in testing.
        """
        data = dict(raw)
        if isinstance(data.get("issued_on"), str):
            data["issued_on"] = date.fromisoformat(data["issued_on"])
        if isinstance(data.get("item_id"), str):
            data["item_id"] = UUID(data["item_id"])
        return Citation(**data)

    def _from_cache(self, payload: dict, deadline: Deadline) -> AnswerResult:
        return AnswerResult(
            outcome=AnswerOutcome.ANSWERED,
            answer_text=payload["answer_text"],
            answer_language=payload["answer_language"],
            confidence=Decimal(payload["confidence"]) if payload["confidence"] else None,
            citations=[self._rehydrate_citation(c) for c in payload["citations"]],
            stale_sources=payload["stale_sources"],
            latency_ms=deadline.elapsed_ms,
        )
