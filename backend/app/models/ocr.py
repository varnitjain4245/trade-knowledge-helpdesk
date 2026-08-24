"""OCR for scanned documents.

Must handle Indic scripts, not just Latin — the corpus is six languages and a Latin-only
engine would silently return empty text for a Tamil circular, which the ingestion
pipeline would then report as an extraction failure with a misleading reason.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings
from app.models.base import make_client


class OcrClient(Protocol):
    async def extract(self, image_bytes: bytes, language_hint: str | None) -> str:
        """Return recognised text, or an empty string when nothing is recognisable.

        An empty return is a legitimate result meaning "no text layer found", not an
        error: the caller turns it into a FatalStageError with a reason the knowledge
        manager can act on (REQ-002).
        """
        ...


class HttpOcrClient:
    def __init__(self, settings: Settings) -> None:
        # OCR is slow by nature; it runs in the worker, never on the request path, so it
        # gets a generous timeout rather than the answer path's stage budget.
        self._http = make_client(settings.embedding_endpoint, timeout_ms=120_000)

    async def extract(self, image_bytes: bytes, language_hint: str | None = None) -> str:
        response = await self._http.post(
            "/ocr",
            files={"file": image_bytes},
            data={"language": language_hint or ""},
        )
        response.raise_for_status()
        return response.json().get("text", "")

    async def aclose(self) -> None:
        await self._http.aclose()
