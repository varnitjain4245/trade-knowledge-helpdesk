"""Answer generation — two strategies behind one interface.

AS-L1 (is a GPU available?) is still unresolved, and the extractive fallback is not an
error path bolted on: it is a second Strategy behind the same interface, so the GPU
question changes a binding rather than the orchestration (LLD §3.1).

The LSP contract both implementations honour: **every emitted span must be traceable to
a context chunk.** An implementation that invents prose is not a valid substitute.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings
from app.domain.errors import ModelUnavailable
from app.models.base import make_breaker, make_client
from app.models.breaker import CircuitBreaker


@dataclass(frozen=True)
class GenerationContext:
    """One retrieved passage offered to the generator."""

    chunk_id: int
    body: str
    heading_path: str | None
    source_language: str


class GenerationService(Protocol):
    async def generate(
        self, query: str, context: list[GenerationContext], target_language: str
    ) -> AsyncIterator[str]:
        """Yield answer text incrementally.

        Tokens are **provisional** by contract: nothing yielded here may be shown to a
        user until the grounding verifier has passed it (LLD §6.1 step 9).
        """
        ...


#: Language names the model will recognise, keyed by the ISO 639-3 codes the API uses.
_LANGUAGE_NAMES = {
    "eng": "English", "hin": "Hindi", "ben": "Bengali",
    "tam": "Tamil", "tel": "Telugu", "mar": "Marathi",
}

_PROMPT = """You are answering a question for India's commerce and industry helpdesk.

Rules you must follow exactly:
- Answer ONLY from the numbered passages below. If they do not answer the question, say
  that you cannot answer from the available sources.
- Do not add facts, figures, dates or requirements that are not in the passages.
- Do not restate a passage as your own authority. You are reporting what a document says.
- Write the answer in {language}. Keep it short and plain.

Passages:
{passages}

Question: {query}

Answer in {language}:"""


class VllmGenerationService:
    """Instruction-tuned generation over a self-hosted OpenAI-compatible endpoint.

    The passages are numbered so the grounding verifier can attribute output spans back
    to their source, and the prompt is delimited because the public surface accepts
    arbitrary text — prompt injection aimed at extracting unapproved content is a real
    attack here. The structural mitigation is stronger than the textual one: the
    generator only ever sees chunks the retrieval filter already deemed answerable, so a
    successful injection still cannot surface an unapproved item.
    """

    def __init__(self, settings: Settings, breaker: CircuitBreaker | None = None) -> None:
        self._http = make_client(
            settings.generation_endpoint, settings.timeout_generate_complete_ms
        )
        self._breaker = breaker or make_breaker("generation", settings)

    @staticmethod
    def _render(query: str, context: list[GenerationContext], language: str) -> str:
        passages = "\n\n".join(
            f"[{i + 1}] ({c.heading_path or 'untitled'}) {c.body}"
            for i, c in enumerate(context)
        )
        return _PROMPT.format(language=language, passages=passages, query=query)

    async def generate(
        self, query: str, context: list[GenerationContext], target_language: str
    ) -> AsyncIterator[str]:
        prompt = self._render(query, context, target_language)

        async def _open() -> AsyncIterator[str]:
            async def _stream() -> AsyncIterator[str]:
                async with self._http.stream(
                    "POST",
                    "/v1/completions",
                    json={
                        "prompt": prompt,
                        "stream": True,
                        "max_tokens": 400,
                        # Low temperature: this is a summarisation task over retrieved
                        # text, not a creative one. Variability here shows up as
                        # ungrounded spans the verifier then has to suppress.
                        "temperature": 0.2,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            import json

                            chunk = json.loads(line.removeprefix("data: "))
                            text = chunk["choices"][0].get("text", "")
                            if text:
                                yield text

            return _stream()

        stream = await self._breaker.call(_open)
        async for token in stream:
            yield token

    async def aclose(self) -> None:
        await self._http.aclose()


class GroqGenerationService:
    """Hosted generation over Groq's OpenAI-compatible API.

    **This sends query text and retrieved passages to a third party.** The stated
    non-functional requirement is that no query, conversation or document content leaves
    the operator's control (`requirements.md`, Cost & data control) — it is the reason
    the HLD chose self-hosted models and the reason the frontend is client-rendered. This
    strategy is a deliberate, opt-in exception for demonstration, selected by
    ``generation_provider``; it is never the default, and the interface says so while it
    is active.

    What does **not** change: the grounding verifier still runs on the output, and an
    ungrounded answer is still suppressed in favour of the extractive fallback. A hosted
    model is more fluent than the local one and therefore more capable of stating
    something the sources do not support — so the check matters more here, not less.
    """

    def __init__(self, settings: Settings, breaker: CircuitBreaker | None = None) -> None:
        self._model = settings.groq_model
        self._key = settings.groq_api_key
        self._http = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            timeout=httpx.Timeout(settings.timeout_generate_complete_ms / 1000.0),
            headers={
                "Authorization": f"Bearer {self._key}",
                # Groq sits behind Cloudflare, which rejects requests with no
                # recognisable user agent (403, code 1010) before they reach the API.
                "User-Agent": "scc-knowledge-platform/0.1",
            },
        )
        self._breaker = breaker or make_breaker("groq-generation", settings)

    @staticmethod
    def _render(query: str, context: list[GenerationContext], language: str) -> str:
        passages = "\n\n".join(
            f"[{i + 1}] ({c.heading_path or 'untitled'}) {c.body}"
            for i, c in enumerate(context)
        )
        return _PROMPT.format(language=_LANGUAGE_NAMES.get(language, language),
                              passages=passages, query=query)

    async def generate(
        self, query: str, context: list[GenerationContext], target_language: str
    ) -> AsyncIterator[str]:
        if not context:
            return

        prompt = self._render(query, context, target_language)

        async def _call() -> str:
            response = await self._http.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You answer strictly from the passages you are given. "
                                "You never add a fact, figure, date or requirement that "
                                "is not present in them. If the passages do not answer "
                                "the question, you say so plainly."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    # Low temperature: this is summarisation over retrieved text, not a
                    # creative task. Variability shows up as ungrounded spans the
                    # verifier then has to suppress, which wastes the whole round trip.
                    "temperature": 0.2,
                    "max_tokens": 400,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        try:
            text = await self._breaker.call(_call)
        except httpx.HTTPError as exc:
            # A rate limit, a 5xx or a dropped connection are all the same thing to the
            # answer path: generation is unavailable, fall back to quoting the record.
            # Letting an HTTP error escape produced a 500 where the design requires a
            # safe degradation (guardrail G4).
            raise ModelUnavailable(f"hosted generation unavailable: {exc}") from exc
        # Emitted in chunks so the caller's streaming contract holds identically to the
        # local strategy — the answer path must not care which model produced the text.
        for i in range(0, len(text), 24):
            yield text[i : i + 24]

    async def aclose(self) -> None:
        await self._http.aclose()


class ExtractiveGenerationService:
    """The honest CPU-only path, and the fallback when generation fails or is ungrounded.

    Returns the best passage verbatim rather than paraphrasing it. Slower to read and
    blunter, but every word is quotable from an approved source — which is precisely why
    it is a safe destination for every degradation in the answer path (guardrail G4).
    """

    async def generate(
        self, query: str, context: list[GenerationContext], target_language: str
    ) -> AsyncIterator[str]:
        if not context:
            return
        # No summarisation, no reordering, no joining of passages: a fallback that
        # combined sources would need its own grounding check, defeating the point.
        yield context[0].body
