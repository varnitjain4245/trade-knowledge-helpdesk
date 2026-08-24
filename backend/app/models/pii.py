"""Personal-identifier detection (REQ-015).

Recall matters far more than precision here: over-masking costs a little readability,
under-masking is a data breach. The detector is therefore recall-tuned (AS-P3-3), and a
low-confidence hit means "possibly sensitive, not sure" — which the masker turns into
withholding rather than a guess.

Indian identifier formats are first-class, not an afterthought: PAN, Aadhaar, GSTIN and
IEC are what actually appear in these conversations, and a generic detector misses all
four.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DetectedEntity:
    start: int
    end: int
    entity_type: str
    confidence: float


class PiiDetector(Protocol):
    def detect(self, text: str) -> list[DetectedEntity]:
        """Return every span believed to be a personal identifier.

        Contract (LSP, pass 3 §5): implementations must be recall-comparable and must
        report an honest confidence. A detector returning high confidence on a miss
        breaks the withholding rule that depends on it.
        """
        ...


#: Format-anchored recognisers. Checksums are deliberately not validated: a mistyped
#: Aadhaar number is still a disclosed Aadhaar number, and rejecting it as invalid would
#: leave it unmasked.
_PATTERNS: tuple[tuple[str, re.Pattern[str], float], ...] = (
    ("IN_PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), 0.95),
    ("IN_AADHAAR", re.compile(r"\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b"), 0.90),
    ("IN_GSTIN", re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b"), 0.95),
    ("IN_IEC", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), 0.80),
    ("PHONE_IN", re.compile(r"(?:\+91[\s-]?)?\b[6-9][0-9]{9}\b"), 0.90),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), 0.98),
    ("BANK_ACCOUNT", re.compile(r"\b[0-9]{9,18}\b"), 0.60),
)


class RegexPiiDetector:
    """Format-based detector.

    Used directly in tests and as the deterministic layer beneath Presidio in
    production. Regex alone would miss names and addresses entirely, which is why the
    HTTP detector below composes both rather than replacing one with the other.
    """

    def detect(self, text: str) -> list[DetectedEntity]:
        found: list[DetectedEntity] = []
        for name, pattern, confidence in _PATTERNS:
            for match in pattern.finditer(text):
                found.append(
                    DetectedEntity(match.start(), match.end(), name, confidence)
                )
        return _merge_overlaps(found)


def _merge_overlaps(entities: list[DetectedEntity]) -> list[DetectedEntity]:
    """Collapse overlapping spans, keeping the *highest* confidence.

    Overlaps are common — an IEC and a PAN share a format — and keeping the highest
    confidence is the recall-favouring choice: it prevents a confident hit being masked
    out by a weaker overlapping one, which would then trigger withholding unnecessarily.
    """
    if not entities:
        return []
    ordered = sorted(entities, key=lambda e: (e.start, -e.confidence))
    merged = [ordered[0]]
    for entity in ordered[1:]:
        last = merged[-1]
        if entity.start < last.end:
            if entity.confidence > last.confidence or entity.end > last.end:
                merged[-1] = DetectedEntity(
                    last.start,
                    max(last.end, entity.end),
                    last.entity_type if last.confidence >= entity.confidence else entity.entity_type,
                    max(last.confidence, entity.confidence),
                )
        else:
            merged.append(entity)
    return merged
