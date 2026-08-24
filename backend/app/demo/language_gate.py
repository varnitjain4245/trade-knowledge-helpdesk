"""The acceptance gate a language must pass before it is offered.

The system claims that a language is enabled only once its correctness has been
measured on that language's own question set. Until now the claim was policy and not
mechanism: ``enabled_languages`` could be set to anything by a request, so an
enablement with a measurement and an enablement without one were indistinguishable
afterwards. This module is the mechanism.

Why the gate exists at all. Offering a language is a promise that answers in it are as
trustworthy as answers in English. Retrieval indexes English and Hindi vocabulary;
generation and grounding verification are prompted in the answer language; sentence
splitting has to know a danda from a full stop. Any of those can degrade for one
language while the other five are fine, and the degradation is invisible from the
English side. A language offered on the assumption that the pipeline generalises is a
language whose users are being served worse without being told.

What is measured, per language:

  answer_rate         Of the acceptance questions, how many produced an answer. A
                      language where the pipeline silently refuses everything is worse
                      than one that is not offered, because it looks available.
  citation_integrity  Every answer must carry a citation. Below 1.0 the language is
                      refused outright, whatever else it scores, since the citation
                      guarantee is the product.
  script_fidelity     Whether the answer came back in the script that was asked in. A
                      Tamil question answered in English is not a Tamil answer.

**A recorded score is not the same as a reviewed question set.** A question set written
by somebody who does not speak the language measures whether the pipeline is
self-consistent, not whether the answers are right. The gate therefore tracks review
separately and refuses to mark a language *certified* until a speaker has signed off
the questions. A language may be enabled provisionally on measurement alone — that is a
judgement an operator can make — but the interface is told which it is, so nobody can
mistake the two later.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

#: Answer rate below which a language is not offered at all.
MIN_ANSWER_RATE = 0.7

#: Citation integrity is not a threshold. It is all or nothing.
REQUIRED_CITATION_INTEGRITY = 1.0

#: Answers that came back in the script the question was asked in. Measuring the first
#: round found Bengali at 0.0 — every question answered, every answer in English —
#: which passed a gate that only counted answer rate. A language that answers in
#: somebody else's script is not the language it claims to be, so this is a floor and
#: not a diagnostic. Not 1.0: an answer that is mostly numerals and scheme acronyms is
#: legitimately thin on the script, and failing it would punish a correct answer.
MIN_SCRIPT_FIDELITY = 0.8

#: Where recorded scores live, so an enablement survives a restart with its evidence.
SCORES_PATH = Path(__file__).resolve().parent / "language_scores.json"

#: Unicode ranges, for checking an answer came back in the script it was asked in.
SCRIPTS = {
    "eng": ((0x0041, 0x024F),),
    "hin": ((0x0900, 0x097F),),
    "mar": ((0x0900, 0x097F),),
    "ben": ((0x0980, 0x09FF),),
    "tam": ((0x0B80, 0x0BFF),),
    "tel": ((0x0C00, 0x0C7F),),
    "guj": ((0x0A80, 0x0AFF),),
    "kan": ((0x0C80, 0x0CFF),),
    "mal": ((0x0D00, 0x0D7F),),
    "pan": ((0x0A00, 0x0A7F),),
    "ori": ((0x0B00, 0x0B7F),),
}

#: Acceptance questions. Seeded, and explicitly NOT reviewed: see the module docstring.
#: Each set asks the same five things, so scores are comparable across languages.
ACCEPTANCE_QUESTIONS: dict[str, list[str]] = {
    "eng": [
        "How do I get an Importer Exporter Code?",
        "What is the time limit for filing a bill of entry?",
        "Within how many days must a buyer pay a micro enterprise?",
        "Who needs to register under Udyam?",
        "What is RoDTEP?",
    ],
    "hin": [
        "आयातक निर्यातक कोड कैसे प्राप्त करें?",
        "बिल ऑफ एंट्री दाखिल करने की समय सीमा क्या है?",
        "सूक्ष्म उद्यम को खरीदार कितने दिनों में भुगतान करे?",
        "उद्यम पंजीकरण किसे कराना चाहिए?",
        "RoDTEP क्या है?",
    ],
    "ben": [
        "আমদানি রপ্তানি কোড কীভাবে পাব?",
        "বিল অফ এন্ট্রি দাখিলের সময়সীমা কত?",
        "ক্ষুদ্র উদ্যোগকে ক্রেতা কত দিনে টাকা দেবে?",
        "উদ্যম নিবন্ধন কারা করবে?",
        "RoDTEP কী?",
    ],
    "tam": [
        "இறக்குமதி ஏற்றுமதி குறியீட்டை எப்படி பெறுவது?",
        "பில் ஆஃப் என்ட்ரி தாக்கல் செய்ய கால வரம்பு என்ன?",
        "நுண் நிறுவனத்திற்கு வாங்குபவர் எத்தனை நாட்களில் பணம் தர வேண்டும்?",
        "உத்யம் பதிவு யார் செய்ய வேண்டும்?",
        "RoDTEP என்றால் என்ன?",
    ],
    "tel": [
        "దిగుమతి ఎగుమతి కోడ్ ఎలా పొందాలి?",
        "బిల్ ఆఫ్ ఎంట్రీ దాఖలు చేయడానికి గడువు ఎంత?",
        "సూక్ష్మ సంస్థకు కొనుగోలుదారు ఎన్ని రోజుల్లో చెల్లించాలి?",
        "ఉద్యమ్ నమోదు ఎవరు చేయాలి?",
        "RoDTEP అంటే ఏమిటి?",
    ],
    "mar": [
        "आयातदार निर्यातदार कोड कसा मिळवावा?",
        "बिल ऑफ एंट्री दाखल करण्याची मुदत किती?",
        "सूक्ष्म उद्योगाला खरेदीदाराने किती दिवसांत पैसे द्यावेत?",
        "उद्यम नोंदणी कोणी करावी?",
        "RoDTEP म्हणजे काय?",
    ],
}

#: Languages whose acceptance questions a speaker has signed off. Empty, honestly:
#: the sets above were seeded by the implementer, not reviewed by speakers.
REVIEWED_BY: dict[str, str] = {}


def script_matches(text: str, language: str) -> bool:
    """Whether the text is written in the language's script.

    Latin characters and digits are ignored rather than counted against: an Indian
    trade answer legitimately contains "RoDTEP", "GST" and "2024", and penalising
    those would fail a correct answer for being about the right subject.
    """
    ranges = SCRIPTS.get(language)
    if not ranges:
        return True
    if language == "eng":
        return True
    for char in text:
        code = ord(char)
        if any(low <= code <= high for low, high in ranges):
            return True
    return False


@dataclass
class LanguageScore:
    language: str
    questions: int
    answered: int
    cited: int
    in_script: int
    measured_at: str
    reviewed_by: str | None = None
    notes: str = ""

    @property
    def answer_rate(self) -> float:
        return round(self.answered / self.questions, 3) if self.questions else 0.0

    @property
    def citation_integrity(self) -> float:
        return round(self.cited / self.answered, 3) if self.answered else 0.0

    @property
    def script_fidelity(self) -> float:
        return round(self.in_script / self.answered, 3) if self.answered else 0.0

    @property
    def passes(self) -> bool:
        return (self.answer_rate >= MIN_ANSWER_RATE
                and self.citation_integrity >= REQUIRED_CITATION_INTEGRITY
                and self.script_fidelity >= MIN_SCRIPT_FIDELITY)

    @property
    def certified(self) -> bool:
        """Passing *and* measured against questions a speaker has vouched for."""
        return self.passes and bool(self.reviewed_by)

    def why_not(self) -> str:
        if self.citation_integrity < REQUIRED_CITATION_INTEGRITY:
            return (f"{self.answered - self.cited} of {self.answered} answers carried "
                    f"no citation. The citation guarantee is not negotiable.")
        if self.answer_rate < MIN_ANSWER_RATE:
            return (f"Answered {self.answered} of {self.questions}; the floor is "
                    f"{MIN_ANSWER_RATE:.0%}.")
        if self.script_fidelity < MIN_SCRIPT_FIDELITY:
            return (f"Only {self.in_script} of {self.answered} answers came back in "
                    f"this language's script; the rest answered in another language.")
        if not self.reviewed_by:
            return ("Measured and passing, but the acceptance questions have not been "
                    "reviewed by a speaker, so this is provisional.")
        return ""

    def as_dict(self) -> dict:
        return {**asdict(self), "answer_rate": self.answer_rate,
                "citation_integrity": self.citation_integrity,
                "script_fidelity": self.script_fidelity,
                "passes": self.passes, "certified": self.certified,
                "why_not": self.why_not()}


@dataclass
class LanguageGate:
    """Holds recorded scores and decides what may be enabled."""

    scores: dict[str, LanguageScore] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        if not SCORES_PATH.exists():
            return
        try:
            raw = json.loads(SCORES_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("language_gate.scores_unreadable")
            return
        for code, body in raw.items():
            body.pop("answer_rate", None); body.pop("citation_integrity", None)
            body.pop("script_fidelity", None); body.pop("passes", None)
            body.pop("certified", None); body.pop("why_not", None)
            self.scores[code] = LanguageScore(**body)

    def save(self) -> None:
        SCORES_PATH.write_text(json.dumps(
            {c: asdict(s) for c, s in self.scores.items()}, indent=1, ensure_ascii=False))

    def record(self, score: LanguageScore) -> None:
        score.reviewed_by = REVIEWED_BY.get(score.language)
        self.scores[score.language] = score
        self.save()
        log.info("language_gate.recorded", language=score.language,
                 answer_rate=score.answer_rate, passes=score.passes)

    def may_enable(self, language: str) -> tuple[bool, str]:
        """Whether a language may be offered, and why not when it may not."""
        if language == "eng":
            # The pipeline's own language, measured by every other test in the suite.
            return True, ""
        score = self.scores.get(language)
        if score is None:
            return False, ("No acceptance score has been recorded for this language. "
                           "Run the gate before enabling it.")
        if not score.passes:
            return False, score.why_not()
        return True, score.why_not()

    def report(self) -> dict:
        return {
            "thresholds": {"answer_rate": MIN_ANSWER_RATE,
                           "citation_integrity": REQUIRED_CITATION_INTEGRITY,
                           "script_fidelity": MIN_SCRIPT_FIDELITY},
            "languages": {c: s.as_dict() for c, s in sorted(self.scores.items())},
            "question_sets": {c: len(q) for c, q in ACCEPTANCE_QUESTIONS.items()},
            "reviewed": sorted(REVIEWED_BY),
            "note": ("A recorded score measures the pipeline's self-consistency. Until "
                     "a speaker reviews the question set, a passing language is "
                     "provisional, not certified."),
        }


async def measure(language: str, answer_service, actor) -> LanguageScore:  # noqa: ANN001
    """Run the acceptance set for one language and score it."""
    from app.services.answer import AnswerRequest

    questions = ACCEPTANCE_QUESTIONS.get(language)
    if not questions:
        raise KeyError(f"no acceptance questions for {language!r}")

    answered = cited = in_script = 0
    for question in questions:
        result = await answer_service.answer(
            AnswerRequest(query=question, preferred_language=language), actor)
        outcome = getattr(result.outcome, "value", str(result.outcome))
        if outcome != "answered":
            continue
        answered += 1
        if result.citations:
            cited += 1
        if script_matches(result.answer_text or "", language):
            in_script += 1

    return LanguageScore(
        language=language, questions=len(questions), answered=answered,
        cited=cited, in_script=in_script,
        measured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def demo() -> None:
    """Self-check: the gate refuses what it has not measured, and citation is absolute."""
    # Constructed then emptied: __post_init__ loads whatever scores this installation
    # has recorded, and a self-check that depended on those would pass or fail
    # according to what somebody measured last week.
    gate = LanguageGate()
    gate.scores = {}

    ok, why = gate.may_enable("tam")
    assert not ok and "No acceptance score" in why

    # English needs no gate; it is the language every other test is written in.
    assert gate.may_enable("eng")[0]

    good = LanguageScore("tam", 5, 5, 5, 5, "2026-08-25T00:00:00")
    assert good.passes and not good.certified, "passing is not certified"
    gate.scores["tam"] = good
    assert gate.may_enable("tam")[0]
    assert "provisional" in gate.may_enable("tam")[1]

    # One uncited answer fails the language outright, however good the rest is.
    uncited = LanguageScore("ben", 5, 5, 4, 5, "2026-08-25T00:00:00")
    assert not uncited.passes
    assert "no citation" in uncited.why_not()
    gate.scores["ben"] = uncited
    assert not gate.may_enable("ben")[0]

    # A silent-refusal language is refused: it would look available and answer nothing.
    silent = LanguageScore("tel", 5, 2, 2, 2, "2026-08-25T00:00:00")
    assert not silent.passes and "floor" in silent.why_not()

    # Answering every question in the wrong script must fail, however complete and
    # well-cited the answers are. This is the case the first measured round produced.
    wrong_script = LanguageScore("ben", 5, 5, 5, 0, "2026-08-25T00:00:00")
    assert not wrong_script.passes
    assert "script" in wrong_script.why_not()

    assert script_matches("আমদানি রপ্তানি কোড", "ben")
    assert not script_matches("Apply on the DGFT portal", "ben")
    assert script_matches("இறக்குமதி", "tam")
    # Latin terms inside an Indian-script answer must not fail it.
    assert script_matches("RoDTEP এর অর্থ", "ben")

    print("language gate: checks passed, unmeasured languages refused")


if __name__ == "__main__":
    demo()
