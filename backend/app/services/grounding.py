"""Grounding verification (BR-1, LLD §6.1 step 9).

A generator can produce a fluent sentence supported by nothing it was given. BR-1 makes
an uncited answer unshowable, so grounding is verified **after** generation and anything
failing is **suppressed, not flagged**.

That distinction is the whole point. A warning label on an ungrounded answer still shows
the answer, and in this domain a confidently wrong statement about a licence requirement
is exactly the harm the product exists to prevent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Sentence split that tolerates Indic danda (।) alongside Latin punctuation. A splitter
#: that only knew '.' would treat an entire Hindi answer as one sentence and grade it
#: all-or-nothing.
_SENTENCE = re.compile(r"(?<=[.!?।])\s+")

#: Tokens shared with a source passage. Deliberately simple: this is a containment check,
#: not semantic similarity. A semantic scorer would let a plausible-but-unsupported
#: paraphrase through, which is the failure mode being guarded against.
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class GroundingReport:
    coverage: float
    ungrounded_spans: list[str]
    grounded: bool
    supporting_chunk_ids: list[int]


class GroundingVerifier:
    def __init__(self, min_coverage: float, min_sentence_overlap: float = 0.6) -> None:
        self._min_coverage = min_coverage
        self._min_overlap = min_sentence_overlap

    def verify(
        self, answer_text: str, context: dict[int, str]
    ) -> GroundingReport:
        """Check every answer sentence against the passages the generator was given.

        ``context`` maps chunk id to passage body. A sentence counts as grounded when
        enough of its content words appear in one passage — one passage, not the union,
        because a claim assembled from fragments of several sources is not supported by
        any of them.
        """
        if not answer_text.strip():
            return GroundingReport(0.0, [], False, [])
        if not context:
            # Nothing to ground against: everything is ungrounded, by definition.
            return GroundingReport(0.0, [answer_text], False, [])

        chunk_words = {
            chunk_id: set(w.lower() for w in _WORD.findall(body))
            for chunk_id, body in context.items()
        }

        sentences = [s for s in _SENTENCE.split(answer_text.strip()) if s.strip()]
        grounded_count = 0
        ungrounded: list[str] = []
        supporting: set[int] = set()

        for sentence in sentences:
            words = {w.lower() for w in _WORD.findall(sentence)}
            if not words:
                grounded_count += 1  # punctuation-only fragment carries no claim
                continue

            best_id, best_overlap = None, 0.0
            for chunk_id, vocabulary in chunk_words.items():
                overlap = len(words & vocabulary) / len(words)
                if overlap > best_overlap:
                    best_id, best_overlap = chunk_id, overlap

            if best_overlap >= self._min_overlap and best_id is not None:
                grounded_count += 1
                supporting.add(best_id)
            else:
                ungrounded.append(sentence)

        coverage = grounded_count / len(sentences)
        # Both conditions, not either: high coverage with one badly ungrounded sentence
        # is still an answer containing an unsupported claim.
        grounded = coverage >= self._min_coverage and not ungrounded
        return GroundingReport(
            coverage=coverage,
            ungrounded_spans=ungrounded,
            grounded=grounded,
            supporting_chunk_ids=sorted(supporting),
        )
