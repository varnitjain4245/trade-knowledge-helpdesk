"""Second-pass query rewriting for questions the lexical index cannot reach.

The limitation this addresses was measured, not assumed. Retrieval over the trade
corpus indexes stemmed words and character trigrams. Both operate on surface form, so
both fail on the same class of question: one that asks about the right subject in
entirely different vocabulary. "Faster customs clearance for a trusted trader" shares
no stemmed term with "Authorised Economic Operator"; "my goods are stuck at the port"
shares none with "bill of entry". Trigram matching does not help, because the surface
forms are not similar either — the gap is semantic.

A model is asked to restate the question in the vocabulary the corpus is written in.
The rewrite is a *retrieval key only*: it never reaches the generator, is never shown
to the user, and cannot introduce a claim, because everything downstream still comes
from a retrieved passage. The worst case is a rewrite that retrieves nothing useful,
which leaves the outcome exactly where it already was — a refusal.

It runs only when the first pass is weak. A question the index already answers well
must not pay for a second model call, and the whole-request deadline is the reason:
this is spent from the budget that would otherwise have gone to generation.
"""

from __future__ import annotations

import re

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger(__name__)

_PROMPT = """You rewrite a question into the vocabulary of Indian trade, customs, GST and MSME regulation, so that a keyword index can find the right circular.

Rules:
- Name ONE subject, the single thing the person is actually asking about. A list of related topics is wrong: it makes the index match all of them and answer from whichever scores highest, which is how a question about export registration gets answered from an e-commerce rule.
- Output ONLY the search terms. No explanation, no punctuation.
- Use the official term for what the person described. "Stuck at the port" is bill of entry. "Trusted trader" is Authorised Economic Operator. "Buyer not paying" is delayed payment to micro and small enterprises. "Sell to other countries" is Importer Exporter Code.
- Keep any number, form name or code the person gave.
- If you do not recognise the subject, repeat the question's own key words. Never invent a scheme name.
- At most 8 words.

Question: {query}
Search terms:"""

_CLEAN = re.compile(r"[^\w\s-]", re.UNICODE)


class QueryRewriter:
    """Restates a question in corpus vocabulary. Failure is never fatal."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.groq_model
        self._key = settings.groq_api_key
        #: The same badly-phrased question recurs across a helpdesk, and a rewrite does
        #: not change between two identical asks.
        self._cache: dict[str, str | None] = {}

    @property
    def available(self) -> bool:
        return bool(self._key)

    def should_rewrite(self) -> bool:
        """Whether a retry is possible at all. *When* to retry is the caller's call.

        The caller asks after judging, not after retrieval: a measurement over the
        trade corpus found the lexical score no guide at all to whether the subject
        was found — "my goods are stuck at the port" scores 0.58 against a record
        about BIS certification. Only the judge separates a confident match from a
        confidently wrong one.
        """
        return self.available

    async def rewrite(self, query: str) -> str | None:
        """Return rewritten search terms, or None if unavailable or unusable.

        Every failure path returns None rather than raising. A rewrite is an
        optimisation on a query that was already heading for a refusal; letting it
        turn that refusal into an error would make the system worse, not better.
        """
        if not self.available:
            return None

        key = " ".join(query.lower().split())
        if key in self._cache:
            return self._cache[key]

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._key}",
                        "User-Agent": "scc-knowledge-platform/0.1",
                    },
                    json={
                        "model": self._model,
                        "messages": [{"role": "user",
                                      "content": _PROMPT.format(query=query)}],
                        "temperature": 0.0,
                        # As with the relevance judge: reasoning tokens are drawn from
                        # this budget, so a tight cap returns empty content rather than
                        # a short answer.
                        "max_tokens": 400,
                        "reasoning_effort": "low",
                    },
                )
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"] or ""
        except Exception as exc:  # noqa: BLE001 - see docstring
            log.warning("query_rewrite.unavailable", error=str(exc))
            return None

        terms = _CLEAN.sub(" ", raw.strip().splitlines()[-1] if raw.strip() else "")
        terms = " ".join(terms.split()[:8]).strip()

        # A rewrite that only echoes the question buys nothing and costs a retrieval
        # pass; treat it as no rewrite at all.
        if not terms or terms.lower() == key:
            terms = None
        self._cache[key] = terms
        if terms:
            log.info("query_rewrite.applied", original=query[:60], rewritten=terms)
        return terms
