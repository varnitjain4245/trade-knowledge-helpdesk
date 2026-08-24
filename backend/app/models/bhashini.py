"""Bhashini — the Government of India's own speech and translation stack.

Bhashini is MeitY's National Language Translation Mission. It matters here for three
reasons, in descending order of how much they matter.

First, coverage. The browser's Web Speech API recognises a handful of Indian languages
and only in Chrome; Bhashini publishes models across the 22 scheduled languages. A desk
serving exporters in Assam and Tamil Nadu cannot be a Chrome-only, six-language desk.

Second, sovereignty of the data path. Speech is the most personal input this system
takes, and routing it through a foreign commercial API to be transcribed is a data
transfer the requirements do not permit. Bhashini is operated by the ministry that owns
the problem.

Third, correctness on Indian names. A general model transcribes "RoDTEP" and "SCOMET"
as whatever English words they resemble. Models trained on Indian corpora do better on
exactly the vocabulary this desk needs.

**Translation is not used on cited passages, and the interface must never offer it.**
A translated quotation is no longer evidence: the words a user is asked to rely on
would be a machine's words, attributed to a circular that does not contain them. The
existing rule that a citation appears in its source language stands unchanged. What
Bhashini translates here is the *question* on the way in and the generated answer on
the way out — never the passage in between.

Two calls are required by the platform's design: a pipeline config call to discover
which service is serving a language pair, and a compute call to run it. The config
result is cached, because it changes on the order of model deployments, not requests.

Absent credentials this module reports itself unavailable and every caller falls back
to what the system already does. That is deliberate: the desk must work for somebody
who has not registered for a Bhashini key.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger(__name__)

AUTH_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

#: The published multi-task pipeline. Named as a constant because a pipeline id is a
#: deployment fact, not a tuning knob — changing it changes which models answer.
DEFAULT_PIPELINE_ID = "64392f96daac500b55c543cd"

#: ISO 639-3 (what this system stores) to ISO 639-1 (what Bhashini expects). Only the
#: languages the desk can actually serve are listed; an unmapped language is refused
#: rather than guessed, because guessing sends Marathi audio to a Hindi model and
#: returns confident nonsense.
ISO3_TO_BHASHINI = {
    "eng": "en", "hin": "hi", "ben": "bn", "tam": "ta", "tel": "te",
    "mar": "mr", "guj": "gu", "kan": "kn", "mal": "ml", "pan": "pa",
    "ori": "or", "asm": "as", "urd": "ur", "nep": "ne", "san": "sa",
    "kok": "gom", "mni": "mni", "brx": "brx", "doi": "doi", "mai": "mai",
    "sat": "sat", "snd": "sd", "kas": "ks",
}


class BhashiniUnavailable(RuntimeError):
    """Raised when Bhashini cannot serve a request. Callers fall back, never fail."""


@dataclass(frozen=True)
class _Service:
    """Which service id serves a task, and where to send the compute call."""

    service_id: str
    endpoint: str
    auth_name: str
    auth_value: str


class BhashiniClient:
    def __init__(self, settings: Settings) -> None:
        self._user_id = getattr(settings, "bhashini_user_id", "") or ""
        self._api_key = getattr(settings, "bhashini_api_key", "") or ""
        self._pipeline_id = (
            getattr(settings, "bhashini_pipeline_id", "") or DEFAULT_PIPELINE_ID
        )
        #: Keyed on the task tuple, because the service serving Tamil ASR is not the
        #: one serving Bengali ASR and a single cached entry would send both to one.
        self._services: dict[tuple, _Service] = {}

    @property
    def available(self) -> bool:
        return bool(self._user_id and self._api_key)

    @staticmethod
    def supports(iso3: str) -> bool:
        return iso3 in ISO3_TO_BHASHINI

    @staticmethod
    def _code(iso3: str) -> str:
        code = ISO3_TO_BHASHINI.get(iso3)
        if code is None:
            raise BhashiniUnavailable(f"no Bhashini language code for {iso3!r}")
        return code

    # --- pipeline configuration ------------------------------------------------------
    async def _configure(self, tasks: list[dict]) -> tuple[list[_Service], str]:
        """Ask which services serve these tasks. Cached per task signature."""
        if not self.available:
            raise BhashiniUnavailable("no Bhashini credentials configured")

        key = tuple(
            (t["taskType"], t["config"].get("language", {}).get("sourceLanguage"),
             t["config"].get("language", {}).get("targetLanguage"))
            for t in tasks
        )
        if key in self._services:
            cached = self._services[key]
            return list(cached[0]), cached[1]  # type: ignore[index]

        payload = {
            "pipelineTasks": [{"taskType": t["taskType"], "config": t["config"]}
                              for t in tasks],
            "pipelineRequestConfig": {"pipelineId": self._pipeline_id},
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                AUTH_URL,
                headers={"userID": self._user_id, "ulcaApiKey": self._api_key,
                         "Content-Type": "application/json"},
                json=payload,
            )
            if response.status_code in (401, 403):
                raise BhashiniUnavailable("Bhashini rejected the credentials")
            response.raise_for_status()
            body = response.json()

        try:
            endpoint = body["pipelineInferenceAPIEndPoint"]
            auth_name = endpoint["inferenceApiKey"]["name"]
            auth_value = endpoint["inferenceApiKey"]["value"]
            callback = endpoint["callbackUrl"]
            services = [
                _Service(
                    service_id=cfg["config"][0]["serviceId"],
                    endpoint=callback, auth_name=auth_name, auth_value=auth_value,
                )
                for cfg in body["pipelineResponseConfig"]
            ]
        except (KeyError, IndexError, TypeError) as exc:
            raise BhashiniUnavailable(f"unexpected pipeline config shape: {exc}") from exc

        self._services[key] = (services, callback)  # type: ignore[assignment]
        return services, callback

    async def _compute(self, tasks: list[dict], inputs: dict) -> dict:
        services, callback = await self._configure(tasks)
        if len(services) < len(tasks):
            raise BhashiniUnavailable("pipeline returned fewer services than tasks")

        body = {
            "pipelineTasks": [
                {"taskType": t["taskType"],
                 "config": {**t["config"], "serviceId": s.service_id}}
                for t, s in zip(tasks, services, strict=False)
            ],
            "inputData": inputs,
        }
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                callback,
                headers={services[0].auth_name: services[0].auth_value,
                         "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            return response.json()

    # --- tasks -----------------------------------------------------------------------
    async def transcribe(self, audio: bytes, language: str,
                         audio_format: str = "webm", sampling_rate: int = 16000) -> str:
        """Speech to text in the language spoken. Returns the transcript."""
        tasks = [{
            "taskType": "asr",
            "config": {
                "language": {"sourceLanguage": self._code(language)},
                "audioFormat": audio_format,
                "samplingRate": sampling_rate,
            },
        }]
        inputs = {"audio": [{"audioContent": base64.b64encode(audio).decode()}]}
        result = await self._compute(tasks, inputs)
        try:
            return result["pipelineResponse"][0]["output"][0]["source"]
        except (KeyError, IndexError) as exc:
            raise BhashiniUnavailable(f"no transcript in ASR reply: {exc}") from exc

    async def translate(self, text: str, source: str, target: str) -> str:
        """Translate text. Never called on a cited passage — see the module docstring."""
        if source == target:
            return text
        tasks = [{
            "taskType": "translation",
            "config": {"language": {"sourceLanguage": self._code(source),
                                    "targetLanguage": self._code(target)}},
        }]
        result = await self._compute(tasks, {"input": [{"source": text}]})
        try:
            return result["pipelineResponse"][0]["output"][0]["target"]
        except (KeyError, IndexError) as exc:
            raise BhashiniUnavailable(f"no translation in reply: {exc}") from exc

    async def speak(self, text: str, language: str, gender: str = "female") -> bytes:
        """Text to speech. Returns audio bytes for the browser to play."""
        tasks = [{
            "taskType": "tts",
            "config": {
                "language": {"sourceLanguage": self._code(language)},
                "gender": gender,
                "samplingRate": 8000,
            },
        }]
        result = await self._compute(tasks, {"input": [{"source": text}]})
        try:
            encoded = result["pipelineResponse"][0]["audio"][0]["audioContent"]
        except (KeyError, IndexError) as exc:
            raise BhashiniUnavailable(f"no audio in TTS reply: {exc}") from exc
        return base64.b64decode(encoded)


def demo() -> None:
    """Self-check of the parts that do not need credentials.

    The network paths cannot be checked without a key, and inventing a fake response
    to assert against would only test the fake. What is checkable is the language
    mapping and the refusal to guess, both of which are where a silent wrong answer
    would come from.
    """
    from app.core.config import Settings

    client = BhashiniClient(Settings())

    assert client._code("hin") == "hi"
    assert client._code("tam") == "ta"
    assert client._code("kok") == "gom", "Konkani's Bhashini code is gom, not kok"
    assert BhashiniClient.supports("ben")
    assert not BhashiniClient.supports("fra")

    # An unmapped language must raise, never fall through to a default. Defaulting
    # would send Bodo audio to a Hindi model and return fluent nonsense.
    try:
        client._code("fra")
    except BhashiniUnavailable:
        pass
    else:
        raise AssertionError("an unmapped language must be refused, not guessed")

    # Every language the desk can serve must be mappable, or enabling it would
    # silently lose voice support.
    for code in ("eng", "hin", "ben", "tam", "tel", "mar"):
        assert BhashiniClient.supports(code), code

    assert len(ISO3_TO_BHASHINI) >= 22, "should cover the scheduled languages"
    print(f"bhashini: checks passed, {len(ISO3_TO_BHASHINI)} languages mapped, "
          f"available={client.available}")


if __name__ == "__main__":
    demo()
