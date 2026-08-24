"""Reference-free evaluation of the answering pipeline, in the RAGAS style.

RAGAS (Es et al., EACL 2024) scores a retrieval-augmented pipeline without a
hand-written gold answer for every question, which is what makes it usable on a corpus
that changes weekly. Three of its metrics are computed here, plus two this system needs
that RAGAS does not define, because this system makes promises RAGAS does not measure.

  faithfulness       Of the claims in the answer, how many are supported by the cited
                     passages? This is the number the grounding verifier exists to
                     keep at 1.0. Anything less is an answer that went beyond its
                     source while still carrying a citation, which is the failure this
                     whole design is built to prevent.

  answer_relevancy   Does the answer address the question that was asked, rather than
                     a neighbouring one? Low relevancy with high faithfulness is the
                     signature of a correct quotation from the wrong record.

  context_precision  Of the passages retrieved, how many were actually useful? This
                     measures retrieval, separately from generation, so a bad answer
                     can be attributed to the stage that caused it.

  refusal_accuracy   On questions with no answer in the corpus, how often does the
                     desk refuse? A system that answers everything scores well on
                     nothing else that matters. Measured on its own question set.

  citation_integrity Fraction of answered questions carrying at least one citation.
                     Structurally guaranteed by the result type, so a value below 1.0
                     means that guarantee has been broken and everything else here is
                     unreliable.

The judge is a language model, and its scores are noisy at the margins — treat a
difference of a few points as noise and a difference of twenty as real. It is the same
model that serves the pipeline, which is a known weakness: a model is a lenient judge
of its own output, so faithfulness in particular should be read as an upper bound.

Usage:
    python -m scripts.evaluate            # full set
    python -m scripts.evaluate --quick    # six questions, for a fast check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.core.config import Settings  # noqa: E402

#: Questions a practitioner would actually ask, each answerable from the corpus.
ANSWERABLE = [
    "How do I get an Importer Exporter Code?",
    "What is the time limit for filing a bill of entry?",
    "When must export proceeds be realised and repatriated?",
    "How do I claim a refund of unutilised input tax credit?",
    "Within how many days must a buyer pay a micro enterprise?",
    "What is RoDTEP and who can claim it?",
    "Who needs to register under Udyam?",
    "What are an e-commerce platform's obligations on returns?",
    "What is SCOMET and when is a licence needed?",
    "How does the Credit Guarantee Fund work for a small enterprise?",
    "What is duty drawback and how is it claimed?",
    "When is BIS certification mandatory?",
    "What does an AD Code registration do?",
    "What is Advance Authorisation for duty-free inputs?",
    "How is a shipping bill used in export clearance?",
    # Phrased the way somebody without the vocabulary would ask. These are the ones
    # the lexical index cannot reach on its own.
    "my buyer has not paid my small firm for two months",
    "I want to start selling my goods abroad, what registration do I need",
    "my consignment is sitting at the port and nobody has assessed it",
    "an online shop added charges at checkout that were never shown",
    "how do I get back the tax I paid on materials I then exported",
]

#: Out of domain. The correct outcome for every one of these is a refusal.
UNANSWERABLE = [
    "What is the capital of France?",
    "Write me a Python function to sort a list.",
    "What will the rupee-dollar rate be next month?",
    "Should I invest in gold or equity this year?",
    "What is the exact GST rate on unmanufactured tobacco leaf in Assam?",
    "Who won the last cricket world cup?",
    "Draft a legal notice for my landlord.",
    "What is my personal income tax liability this year?",
]

_FAITHFULNESS = """You check whether an answer stays inside its sources.

Sources:
{passages}

Answer:
{answer}

Break the answer into its factual claims. Count how many are fully supported by the sources above. A claim that is *nearly* supported, or that adds a figure, date, deadline or condition the sources do not state, is NOT supported.

Reply with only a JSON object: {{"claims": <int>, "supported": <int>}}"""

_RELEVANCY = """Score how well this answer addresses the question that was asked.

Question: {question}
Answer: {answer}

  1.0  answers exactly what was asked
  0.7  answers a closely related question, but not quite this one
  0.4  same general subject, does not address the question
  0.0  different subject

Reply with only a JSON object: {{"score": <number>}}"""

_PRECISION = """For each passage, say whether it is useful for answering the question.

Question: {question}

Passages:
{passages}

Reply with only a JSON array of 0 or 1, one per passage, in order. 1 means the passage contributes to an answer; 0 means it does not."""


@dataclass
class Scores:
    faithfulness: list[float] = field(default_factory=list)
    relevancy: list[float] = field(default_factory=list)
    precision: list[float] = field(default_factory=list)
    answered: int = 0
    cited: int = 0
    asked: int = 0
    refused_correctly: int = 0
    refusal_asked: int = 0

    @staticmethod
    def _mean(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 3) if xs else None

    def report(self) -> dict:
        return {
            "answerable_questions": self.asked,
            "answer_rate": round(self.answered / self.asked, 3) if self.asked else None,
            "faithfulness": self._mean(self.faithfulness),
            "answer_relevancy": self._mean(self.relevancy),
            "context_precision": self._mean(self.precision),
            "citation_integrity": (
                round(self.cited / self.answered, 3) if self.answered else None
            ),
            "out_of_domain_questions": self.refusal_asked,
            "refusal_accuracy": (
                round(self.refused_correctly / self.refusal_asked, 3)
                if self.refusal_asked else None
            ),
        }


class Judge:
    """A separate model call per metric. Failures are skipped, never guessed."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.groq_model
        self._key = settings.groq_api_key

    async def ask(self, prompt: str) -> str | None:
        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self._key}",
                                 "User-Agent": "scc-eval/0.1"},
                        json={"model": self._model,
                              "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0.0, "max_tokens": 500,
                              "reasoning_effort": "low"},
                    )
                if r.status_code == 429:
                    # The free tier rate-limits hard. Backing off is the difference
                    # between a measurement and a row of blanks that reads as failure.
                    await asyncio.sleep(12 * (attempt + 1))
                    continue
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except Exception:  # noqa: BLE001
                await asyncio.sleep(6)
        return None

    @staticmethod
    def _json(raw: str | None, pattern: str) -> object | None:
        import re
        if not raw:
            return None
        m = re.search(pattern, raw, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


async def run(quick: bool = False) -> dict:
    from app.demo.main import AGENT, answer_service
    from app.services.answer import AnswerRequest

    settings = Settings()
    if not settings.groq_api_key:
        raise SystemExit("SCC_GROQ_API_KEY is not set; the judge cannot run.")

    judge = Judge(settings)
    scores = Scores()

    answerable = ANSWERABLE[:6] if quick else ANSWERABLE
    unanswerable = UNANSWERABLE[:3] if quick else UNANSWERABLE

    for question in answerable:
        scores.asked += 1
        result = await answer_service.answer(AnswerRequest(query=question), AGENT)
        outcome = getattr(result.outcome, "value", str(result.outcome))
        print(f"  [{outcome:>10}] {question[:62]}")

        if outcome != "answered":
            await asyncio.sleep(8)
            continue

        scores.answered += 1
        if result.citations:
            scores.cited += 1

        passages = "\n\n".join(
            f"[{i + 1}] {c.passage}" for i, c in enumerate(result.citations)
        )

        raw = await judge.ask(_FAITHFULNESS.format(
            passages=passages, answer=result.answer_text))
        obj = judge._json(raw, r"\{[^{}]*\}")
        if isinstance(obj, dict) and obj.get("claims"):
            scores.faithfulness.append(
                min(1.0, float(obj.get("supported", 0)) / float(obj["claims"])))
        await asyncio.sleep(8)

        raw = await judge.ask(_RELEVANCY.format(
            question=question, answer=result.answer_text))
        obj = judge._json(raw, r"\{[^{}]*\}")
        if isinstance(obj, dict) and "score" in obj:
            scores.relevancy.append(float(obj["score"]))
        await asyncio.sleep(8)

        raw = await judge.ask(_PRECISION.format(question=question, passages=passages))
        arr = judge._json(raw, r"\[[^\]]*\]")
        if isinstance(arr, list) and arr:
            useful = [1.0 if float(x) >= 0.5 else 0.0 for x in arr]
            scores.precision.append(sum(useful) / len(useful))
        await asyncio.sleep(8)

    print()
    for question in unanswerable:
        scores.refusal_asked += 1
        result = await answer_service.answer(AnswerRequest(query=question), AGENT)
        outcome = getattr(result.outcome, "value", str(result.outcome))
        correct = outcome != "answered"
        scores.refused_correctly += correct
        print(f"  [{'refused ok' if correct else 'ANSWERED!!':>10}] {question[:62]}")
        await asyncio.sleep(8)

    return scores.report()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="six answerable and three out-of-domain questions")
    parser.add_argument("--out", type=Path, default=None,
                        help="write the report as JSON")
    args = parser.parse_args()

    report = asyncio.run(run(quick=args.quick))

    print("\n" + "=" * 58)
    for key, value in report.items():
        print(f"  {key:26} {value}")
    print("=" * 58)

    if report.get("faithfulness") is not None and report["faithfulness"] < 1.0:
        print("\n  faithfulness below 1.0: an answer stated something its citation "
              "does not support. The grounding verifier should have suppressed it.")

    if args.out:
        args.out.write_text(json.dumps(report, indent=2))
        print(f"\n  written to {args.out}")


if __name__ == "__main__":
    main()
