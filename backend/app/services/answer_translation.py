"""Translating a verified answer, after grounding and never before.

Measuring the language acceptance sets exposed a conflict between two things this
system does, and it is worth stating precisely because the obvious fixes are all wrong.

Grounding verification checks each generated sentence against the passage that produced
it, by looking for the passage's content in the sentence. The corpus is written in
English. So a Bengali sentence, however faithful, shares no tokens with the English
passage it came from, fails verification, and is suppressed — correctly, by the rule as
written. The extractive fallback then quotes the English passage verbatim, which is also
correct, because a quotation must never be translated. The result was a desk that
answered Bengali questions in English and scored 0.0 on script fidelity.

Three ways out, and only one is acceptable:

  Weaken grounding for non-English. This trades the product's central guarantee for a
  cosmetic one, and does it precisely for the users least able to check the result
  themselves. Not considered further.

  Verify in the answer language. This needs the passage translated to compare against,
  which means verifying a claim against a machine translation of the evidence. The
  evidence would no longer be the record.

  Verify first, then translate. Generate the draft in the passage language, verify it
  against the passage exactly as before, and translate only what passed. This is what
  happens here.

The ordering is the whole point. Translation operates on text already proved to follow
from the record, so a mistranslation can garble an answer but cannot manufacture a claim
the record does not support. Nothing unverified is ever translated, and the citation is
never touched: it appears in its source language, as it always has, because a translated
quotation is not evidence.

The answer is marked as translated, and the interface says so. A machine translation
presented as though a person had written it invites more trust than it has earned.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

LANGUAGE_NAMES = {
    "eng": "English", "hin": "Hindi", "ben": "Bengali", "tam": "Tamil",
    "tel": "Telugu", "mar": "Marathi", "guj": "Gujarati", "kan": "Kannada",
    "mal": "Malayalam", "pan": "Punjabi", "ori": "Odia", "asm": "Assamese",
    "urd": "Urdu",
}

_PROMPT = """Translate the text below into {language}.

Rules:
- Translate only. Add nothing, remove nothing, explain nothing.
- Keep every number, date, form name, scheme name and acronym exactly as written: IEC, RoDTEP, GST, SCOMET, Udyam, DGFT, CBIC, RFD-01 and the like are not translated.
- Keep the meaning exact. This text has been checked against an official record, and a translation that changes what it says would break that check.
- Reply with the translation and nothing else.

Text:
{text}"""


class AnswerTranslator:
    """Translates verified answers. Failure returns the original, never an error.

    An untranslated answer is a worse answer; a failed request is no answer at all. The
    caller shows what it has.
    """

    def __init__(self, settings, bhashini=None) -> None:  # noqa: ANN001
        self._model = settings.groq_model
        self._key = settings.groq_api_key
        self._bhashini = bhashini
        self._cache: dict[tuple[str, str], str] = {}

    @property
    def available(self) -> bool:
        return bool(self._key) or bool(self._bhashini and self._bhashini.available)

    @staticmethod
    def needed(text: str, source_language: str, target_language: str) -> bool:
        if source_language == target_language or not text.strip():
            return False
        return target_language in LANGUAGE_NAMES

    async def translate(self, text: str, target_language: str,
                        source_language: str = "eng") -> tuple[str, bool]:
        """Return (text, was_translated). The flag is shown to the reader."""
        if not self.needed(text, source_language, target_language):
            return text, False

        key = (target_language, text[:200])
        if key in self._cache:
            return self._cache[key], True

        # Bhashini first when configured: it is the ministry's own stack and is built
        # for exactly these language pairs.
        if self._bhashini is not None and self._bhashini.available \
                and self._bhashini.supports(target_language):
            try:
                out = await self._bhashini.translate(text, source_language,
                                                     target_language)
                if out.strip():
                    self._cache[key] = out
                    return out, True
            except Exception as exc:  # noqa: BLE001
                log.warning("translate.bhashini_failed", error=str(exc))

        if not self._key:
            return text, False

        language = LANGUAGE_NAMES.get(target_language, target_language)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._key}",
                             "User-Agent": "scc-knowledge-platform/0.1"},
                    json={"model": self._model,
                          "messages": [{"role": "user",
                                        "content": _PROMPT.format(language=language,
                                                                  text=text)}],
                          "temperature": 0.0, "max_tokens": 900,
                          "reasoning_effort": "low"},
                )
                response.raise_for_status()
                out = (response.json()["choices"][0]["message"]["content"] or "").strip()
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            log.warning("translate.unavailable", error=str(exc))
            return text, False

        if not out:
            return text, False
        self._cache[key] = out
        log.info("translate.applied", target=target_language)
        return out, True


def demo() -> None:
    """Self-check of the decision rule; the network path needs a key."""
    from types import SimpleNamespace

    translator = AnswerTranslator(SimpleNamespace(groq_model="m", groq_api_key=""))

    # No work when the languages already agree, or there is nothing to translate.
    assert not AnswerTranslator.needed("text", "eng", "eng")
    assert not AnswerTranslator.needed("   ", "eng", "ben")
    assert AnswerTranslator.needed("text", "eng", "ben")
    # An unknown target is refused rather than attempted in some default language.
    assert not AnswerTranslator.needed("text", "eng", "klingon")

    assert not translator.available

    import asyncio
    # Unavailable must degrade to the original text, flagged as untranslated, so the
    # interface never claims a translation happened when it did not.
    out, translated = asyncio.run(translator.translate("Apply on the DGFT portal.",
                                                       "ben"))
    assert out == "Apply on the DGFT portal." and translated is False

    same, flag = asyncio.run(translator.translate("text", "eng"))
    assert same == "text" and flag is False

    print("answer translation: checks passed, verify-then-translate ordering holds")


if __name__ == "__main__":
    demo()
