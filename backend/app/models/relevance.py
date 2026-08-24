"""Relevance judging — the cross-encoder the design always called for.

BM25 answers "which passages share vocabulary with this question". That is not the same
question as "does this passage answer it", and the gap between the two is where wrong
answers come from. Asked about an *authorised economic operator*, lexical retrieval
returns the *Export Oriented Unit* record at full confidence — they share the word
"operator" and nothing else that matters. No lexical threshold separates those, because
the problem is not the score, it is what the score measures.

This judge closes that gap. It scores each candidate on whether it actually answers the
question, which is precisely what a cross-encoder does in the production design
(`hld-backend.md` §12.1 — "reranking is where confidence becomes meaningful; raw vector
distance is a poor confidence signal and would make the answer bar meaningless").

All candidates are judged in one call, so the cost is one round trip per question rather
than one per passage.
"""

from __future__ import annotations

import json
import re

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.breaker import CircuitBreaker
from app.models.base import make_breaker

log = get_logger(__name__)

_PROMPT = """Score how well each passage answers the question.

Question: {question}

Passages:
{passages}

Scoring:
  1.0  directly and fully answers the question
  0.7  answers most of it, or answers it partially
  0.4  related subject, but does not answer this question
  0.0  different subject, or shares only vocabulary

Judge the *question asked*, not the general topic. A passage about a similar-sounding
but different scheme, term or procedure scores 0.0 — sharing a word is not answering.

Reply with only a JSON array of numbers, one per passage, in order. Nothing else."""


class RelevanceJudge:
    #: How many candidates to judge. Judging all eight doubled the token cost of every
    #: question and hit the rate limit; the answer is drawn from the top one or two in
    #: practice, so the rest were paid for and discarded.
    JUDGE_TOP = 5

    def __init__(self, settings: Settings, breaker: CircuitBreaker | None = None) -> None:
        self._settings = settings
        self._model = settings.groq_model
        self._key = settings.groq_api_key
        self._breaker = breaker or make_breaker("relevance", settings)
        #: Repeat questions are the norm on a helpdesk, and a judgement does not change
        #: between two identical asks against the same passages.
        self._cache: dict[tuple[str, str], list[float]] = {}

    @property
    def available(self) -> bool:
        return bool(self._key)

    async def score(self, question: str, passages: list[str]) -> list[float] | None:
        """Return a relevance score per passage, or None when judging is unavailable.

        None rather than a default: a fabricated score would flow straight into the
        answer bar, and a confidence nobody measured is worse than an admitted gap. The
        caller falls back to the lexical score and knows it is doing so.
        """
        if not passages or not self.available:
            return None

        head = passages[: self.JUDGE_TOP]
        tail_len = len(passages) - len(head)
        cache_key = (
            " ".join(question.lower().split()),
            "|".join(p[:60] for p in head),
        )
        if cache_key in self._cache:
            return self._cache[cache_key] + [0.0] * tail_len

        numbered = "\n\n".join(
            f"[{i + 1}] {p[:700]}" for i, p in enumerate(head)
        )
        prompt = _PROMPT.format(question=question, passages=numbered)

        async def _call() -> list[float]:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._key}",
                        "User-Agent": "scc-knowledge-platform/0.1",
                    },
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.0,
                        # The gpt-oss models emit reasoning tokens before their reply,
                        # and those come out of the same budget. At 120 the reasoning
                        # consumed it all and the content came back empty on roughly
                        # half the calls — a silent failure that read as "judge
                        # unavailable" rather than "budget too small".
                        "max_tokens": 700,
                        "reasoning_effort": "low",
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]

            match = re.search(r"\[[^\]]*\]", content, re.S)
            if not match:
                raise ValueError(f"no score array in judge reply: {content[:120]!r}")
            scores = [float(x) for x in json.loads(match.group(0))]
            # The model pads its array — it returned twenty scores for eight passages.
            # Rejecting the whole reply for being too long threw away a usable answer;
            # too *few* is the case that genuinely cannot be trusted, because there is no
            # way to know which passage each score belongs to.
            if len(scores) < len(head):
                raise ValueError(
                    f"judge returned {len(scores)} scores for {len(head)} passages"
                )
            return [max(0.0, min(1.0, s)) for s in scores[: len(head)]]

        try:
            scores = await self._breaker.call(_call)
        except Exception as exc:
            log.warning("relevance.unavailable", error=str(exc)[:160])
            return None
        self._cache[cache_key] = scores
        # Candidates past the judged head score zero rather than inheriting a lexical
        # score — an unjudged passage has no relevance evidence behind it.
        return scores + [0.0] * tail_len
