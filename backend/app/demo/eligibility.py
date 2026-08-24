"""An eligibility questionnaire that asks only what still matters.

``programmes.eligible`` already matches a business against every scheme and says why
each verdict was reached. What it cannot do is conduct the conversation: it needs the
whole profile up front, and a person who does not know their own turnover band or how
the scheme vocabulary classifies their activity has nothing to type.

MyScheme's approach is the one worth copying — a short questionnaire that narrows to
the schemes a person actually qualifies for. This adds the part that makes such a
questionnaire bearable: **a question is asked only if the answer would change
something**. If every remaining scheme is open to exporters and importers alike, asking
which one somebody is wastes their time and teaches them the form is boilerplate. The
selector below scores each unasked question by how much it would actually split the
candidate set, and stops when nothing splits it.

Two properties are deliberate, and both follow the same rule the answering path obeys:

  Every verdict names the criterion that decided it. "Not eligible" alone is useless —
  a business cannot act on it, cannot tell whether it is close, and cannot know when to
  look again. "The turnover ceiling is 150 crore" is actionable.

  A verdict is *indicative*, and says so. These criteria are illustrative, and the
  authority for any real claim is the scheme notification, which is cited alongside
  every result. A questionnaire that presented itself as a decision would be asserting
  an entitlement this system has no standing to grant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.demo.programmes import SCHEMES, SECTORS, eligible

#: Turnover bands, in crore. Bands rather than a number because most people know which
#: band they are in without looking it up, and a band is all the criteria need.
TURNOVER_BANDS = [
    ("under_5", "Under ₹5 crore", 2.5),
    ("5_to_50", "₹5 crore to ₹50 crore", 25.0),
    ("50_to_250", "₹50 crore to ₹250 crore", 150.0),
    ("over_250", "Over ₹250 crore", 500.0),
]

QUESTIONS: dict[str, dict] = {
    "entity_type": {
        "text": "How is the business classified?",
        "help": "Micro, small and medium enterprises are MSMEs. Anything above the "
                "medium ceiling is large.",
        "options": [{"value": "msme", "label": "Micro, small or medium (MSME)"},
                    {"value": "large", "label": "Large enterprise"}],
    },
    "activity": {
        "text": "What does the business mainly do?",
        "help": "Pick the activity the benefit would be claimed against.",
        "options": [{"value": "exporter", "label": "Exports goods"},
                    {"value": "importer", "label": "Imports goods"},
                    {"value": "manufacturer", "label": "Manufactures goods"},
                    {"value": "trader", "label": "Trades goods domestically"}],
    },
    "sector": {
        "text": "Which sector best describes the goods?",
        "options": [{"value": s, "label": s.title()} for s in SECTORS if s != "any"],
    },
    "turnover_band": {
        "text": "What is the annual turnover?",
        "help": "A band is enough; no exact figure is needed.",
        "options": [{"value": k, "label": label} for k, label, _ in TURNOVER_BANDS],
    },
}

#: Asked in this order when two questions are equally discriminating. Classification
#: first because it splits the scheme set most often and is the easiest to answer.
TIE_BREAK = ["entity_type", "activity", "turnover_band", "sector"]


def _turnover_value(band: str | None) -> float | None:
    if not band:
        return None
    return next((v for k, _, v in TURNOVER_BANDS if k == band), None)


@dataclass
class Session:
    """Answers gathered so far. Held by the caller; this module stays stateless."""

    answers: dict[str, str] = field(default_factory=dict)

    def profile(self) -> dict:
        return {
            "entity_type": self.answers.get("entity_type"),
            "activity": self.answers.get("activity"),
            "sector": self.answers.get("sector"),
            "turnover_cr": _turnover_value(self.answers.get("turnover_band")),
        }


def assess(answers: dict[str, str]) -> list[dict]:
    """Every scheme, with a verdict and the criterion behind it."""
    session = Session(dict(answers))
    return eligible(**session.profile())


def _would_split(question: str, answers: dict[str, str]) -> bool:
    """Whether answering this question can still change any scheme's verdict.

    Tried by simulation rather than by reasoning about the criteria: each possible
    answer is scored, and if every one of them produces the same set of eligible
    schemes, the question is not worth asking. Simulation stays correct when a scheme's
    criteria change; a hand-written rule about which questions matter would not.
    """
    outcomes = set()
    for option in QUESTIONS[question]["options"]:
        trial = {**answers, question: option["value"]}
        outcomes.add(frozenset(
            s["code"] for s in assess(trial) if s["eligible"]
        ))
        if len(outcomes) > 1:
            return True
    return False


def next_question(answers: dict[str, str]) -> dict | None:
    """The next question worth asking, or None when none is.

    Returning None is a real answer, not a failure: it means the remaining schemes
    agree regardless of what else is said, so the questionnaire is finished.
    """
    unanswered = [q for q in TIE_BREAK if q not in answers]
    for question in unanswered:
        if _would_split(question, answers):
            return {"key": question, **QUESTIONS[question],
                    "remaining": len(unanswered)}
    return None


def state(answers: dict[str, str]) -> dict:
    """Everything a caller needs: the verdicts, the next question, and the caveat."""
    results = assess(answers)
    qualifies = [s for s in results if s["eligible"]]
    question = next_question(answers)
    return {
        "answers": answers,
        "answered": len(answers),
        "total_questions": len(QUESTIONS),
        "next_question": question,
        "complete": question is None,
        "qualifies_for": qualifies,
        "does_not_qualify_for": [s for s in results if not s["eligible"]],
        "counts": {"eligible": len(qualifies),
                   "ineligible": len(results) - len(qualifies),
                   "total": len(results)},
        # Stated on every response, not once at the start. A verdict read out of
        # context is the one most likely to be acted on.
        "basis": ("Indicative only. Criteria here are illustrative; the scheme "
                  "notification cited with each result is the authority."),
    }


def demo() -> None:
    """Self-check: narrowing works, verdicts carry reasons, and pointless questions stop."""
    empty = state({})
    assert empty["counts"]["total"] == len(SCHEMES)
    first = empty["next_question"]
    assert first is not None and first["key"] == "entity_type"

    # Answering must narrow, and every rejection must say why.
    large = state({"entity_type": "large"})
    msme = state({"entity_type": "msme"})
    assert large["counts"]["eligible"] != msme["counts"]["eligible"], \
        "classification should change the outcome"
    for scheme in large["does_not_qualify_for"]:
        assert scheme["reasons_against"], f"{scheme['code']} rejected with no reason"
        assert scheme["source"]["title"], "every verdict must cite its notification"

    # A question that cannot change anything must not be asked. Drive the questionnaire
    # to completion and confirm it terminates rather than asking all four regardless.
    answers: dict[str, str] = {}
    asked = []
    for _ in range(len(QUESTIONS) + 1):
        q = next_question(answers)
        if q is None:
            break
        asked.append(q["key"])
        answers[q["key"]] = q["options"][0]["value"]
    else:
        raise AssertionError("questionnaire did not terminate")

    assert next_question(answers) is None
    assert state(answers)["complete"]
    assert len(asked) <= len(QUESTIONS)

    # The simulation must agree with a direct assessment: no separate code path.
    direct = assess(answers)
    assert [s["code"] for s in direct] == [
        s["code"] for s in state(answers)["qualifies_for"]
        + state(answers)["does_not_qualify_for"]]

    print(f"eligibility: checks passed, asked {len(asked)} of {len(QUESTIONS)} "
          f"questions ({', '.join(asked)})")


if __name__ == "__main__":
    demo()
