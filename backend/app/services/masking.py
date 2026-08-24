"""Personal-identifier masking (REQ-015).

The rule that is easiest to get wrong in *either* direction, so it is stated once here
and enforced by call site:

* The **live transcript** is not masked. It is the working record an agent needs, and
  masking it would make them unable to help. It is protected by retention and access
  control instead.
* Content stored **for analytics, gap entries or reuse** is masked before it is written.
  That is REQ-015's exact scope.

When masking cannot be applied confidently the content is **withheld** rather than
stored partially masked. The detector is recall-tuned (AS-P3-3), so a low-confidence hit
means "possibly sensitive, not sure" — and storing that is the failure this rule exists
to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.models.pii import DetectedEntity, PiiDetector

WITHHELD_PLACEHOLDER = "[withheld: manual review required]"


class CallSite(StrEnum):
    """Where masked content is going. Determines what withholding means."""

    GAP_ENTRY = "gap_entry"
    AUDIT_DETAIL = "audit_detail"
    ANSWER_RECORD = "answer_record"
    KNOWLEDGE_REUSE = "knowledge_reuse"


@dataclass(frozen=True)
class MaskResult:
    text: str
    entities_masked: int
    min_confidence: float
    withheld: bool


class Masker:
    def __init__(self, detector: PiiDetector, min_confidence: float) -> None:
        self._detector = detector
        self._min_confidence = min_confidence

    def mask(self, text: str) -> MaskResult:
        if not text:
            return MaskResult(text="", entities_masked=0, min_confidence=1.0, withheld=False)

        entities = self._detector.detect(text)
        if not entities:
            return MaskResult(text=text, entities_masked=0, min_confidence=1.0, withheld=False)

        lowest = min(e.confidence for e in entities)
        if lowest < self._min_confidence:
            # Withhold rather than guess. Over-masking costs readability; under-masking
            # is a data breach, and REQ-015 weights those correctly.
            return MaskResult(
                text=WITHHELD_PLACEHOLDER,
                entities_masked=0,
                min_confidence=lowest,
                withheld=True,
            )

        return MaskResult(
            text=self._replace(text, entities),
            entities_masked=len(entities),
            min_confidence=lowest,
            withheld=False,
        )

    @staticmethod
    def _replace(text: str, entities: list[DetectedEntity]) -> str:
        """Replace spans back-to-front so earlier offsets stay valid."""
        result = text
        for entity in sorted(entities, key=lambda e: e.start, reverse=True):
            result = f"{result[: entity.start]}[{entity.entity_type}]{result[entity.end :]}"
        return result

    def mask_for(self, text: str, call_site: CallSite) -> MaskResult:
        """Mask with the call site recorded.

        The behaviour is identical across call sites; what differs is what the *caller*
        does with ``withheld``:

        * GAP_ENTRY — store the placeholder but still count the entry toward its group.
          Losing the signal would hide a real gap, which is worse than losing the text.
        * AUDIT_DETAIL — replace the field, still write the record. An unwritten audit
          record is a worse failure than a redacted one.
        * KNOWLEDGE_REUSE — the item is not citable (BR-7); it stays in manual review.
        """
        return self.mask(text)
