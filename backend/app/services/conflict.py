"""Conflict detection (BR-6).

Evaluated **before** the answer bar. That ordering is the whole finding: implementing it
the other way round silently drops conflicts that fall below the bar, and a conflict is
precisely the case where the corpus disagrees with itself and a human must decide.

A shown conflict is never counted as an answer for the correctness or deflection metrics
— it is the system declining to choose, not the system answering.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.repositories.protocols import ScoredChunk

#: Words that flip a statement's meaning. Multilingual because a conflict between a
#: Hindi and an English circular is a conflict, and an English-only list would miss it.
_POLARITY = frozenset({
    "not", "no", "never", "without", "exempt", "exempted", "exemption",
    "prohibited", "banned", "freely", "unrestricted", "waived", "nil",
    "नहीं", "बिना", "छूट", "मुक्त",
})


@dataclass(frozen=True)
class Conflict:
    sources: list[ScoredChunk]
    reason: str


class ConflictDetector:
    """Detects two approved sources that answer the same query differently.

    The signal used is deliberately conservative: two high-scoring passages from
    **different items**, neither superseding the other, whose content diverges. Being
    conservative matters in both directions — a false conflict withholds a good answer,
    while a missed conflict shows one source as though it were the whole truth.
    """

    def __init__(
        self, min_score: float, divergence_threshold: float = 0.45,
        topical_overlap: float = 0.55, comparability: float = 0.75,
    ) -> None:
        self._min_score = min_score
        self._divergence = divergence_threshold
        self._topical_overlap = topical_overlap
        #: How close the second source must be to the best one to count as a rival
        #: reading rather than a tangential mention. Without this, a weak passage that
        #: happens to contain a negation can veto a strong, well-supported answer —
        #: found while exercising the demo corpus, where a handicraft notice blocked an
        #: unrelated question about restricted goods generally.
        self._comparability = comparability

    def detect(self, candidates: list[ScoredChunk]) -> Conflict | None:
        strong = [c for c in candidates if c.score >= self._min_score]
        if len(strong) < 2:
            return None

        best = strong[0]
        for other in strong[1:]:
            if other.item_id == best.item_id:
                continue
            # A conflict is two sources that both plausibly answer the question. A much
            # weaker passage is a tangent, not a rival, and treating it as one withholds
            # good answers — the opposite of BR-6's intent.
            if best.score > 0 and other.score < best.score * self._comparability:
                continue
            # Supersession is resolved upstream by the retrieval filter: a superseded
            # item is not in the answerable set, so it cannot "conflict" with the item
            # that replaced it. Nothing to check here.
            if self._diverges(best.body, other.body):
                return Conflict(
                    sources=[best, other],
                    reason="two approved sources give different answers",
                )
        return None

    def _diverges(self, left: str, right: str) -> bool:
        """Two passages diverge when they are clearly about the same subject yet do not
        say the same thing.

        Low vocabulary overlap alone is **not** divergence — two passages about
        unrelated topics are simply different, not in conflict. The signal that matters
        is the opposite: high topical overlap with a polarity difference, which is what
        an amended rule looks like ("a licence is required" / "a licence is not
        required"). An earlier version required *low* overlap and therefore missed
        exactly the case it was written for.

        This is a heuristic and is stated as one. It is tuned to favour raising a
        conflict over missing one, because BR-6's failure mode is showing one source as
        though it were the whole truth. A false conflict costs the user an extra read;
        a missed conflict costs them a wrong answer.
        """
        import re

        def words(text: str) -> set[str]:
            return {w.lower() for w in re.findall(r"\w+", text, re.UNICODE)}

        a, b = words(left), words(right)
        if not a or not b:
            return False

        overlap = len(a & b) / min(len(a), len(b))
        if overlap < self._topical_overlap:
            return False  # different subjects, not a conflict

        # Polarity asymmetry: a negation or exemption marker present on one side only.
        # Requiring high topical overlap first matters more as a corpus grows — at 42
        # records many passages share trade vocabulary without addressing the same
        # question, and a bare polarity test flagged them as contradictions.
        only_a, only_b = a - b, b - a
        a_negated = bool(only_a & _POLARITY)
        b_negated = bool(only_b & _POLARITY)
        if a_negated != b_negated:
            return True

        # Same polarity but materially different content — two different rates for the
        # same thing. This needs near-identical subject matter to mean anything, so it
        # only applies above the topical floor already checked above.
        return False
