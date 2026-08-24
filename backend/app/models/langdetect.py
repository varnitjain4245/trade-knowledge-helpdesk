"""Language detection.

Offline and fast — it sits at the front of the answer path with a 30 ms budget. An
explicit user choice always wins over detection (REQ-001), so this is a default, never
an override.
"""

from __future__ import annotations

from typing import Protocol

#: Unicode block ranges that identify a script unambiguously. Script identification is
#: enough for five of the six launch languages; Hindi and Marathi share Devanagari and
#: are separated by the caller's stored preference, because no reliable script-level
#: signal distinguishes them.
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0900, 0x097F, "hin"),  # Devanagari — Hindi by default, see note above
    (0x0980, 0x09FF, "ben"),
    (0x0B80, 0x0BFF, "tam"),
    (0x0C00, 0x0C7F, "tel"),
)


class LanguageDetector(Protocol):
    def detect(self, text: str) -> str:
        """Return an ISO 639-3 code. Falls back to 'eng' on an unrecognised script."""
        ...


class ScriptLanguageDetector:
    """Script-range detection.

    Deliberately simple and dependency-free. It is correct for the launch six because
    their scripts do not overlap, except for the Devanagari pair noted above. A
    statistical detector would add a dependency and a model download to solve a problem
    the alphabet already solves.
    """

    def detect(self, text: str) -> str:
        counts: dict[str, int] = {}
        for char in text:
            code = ord(char)
            for low, high, language in _SCRIPT_RANGES:
                if low <= code <= high:
                    counts[language] = counts.get(language, 0) + 1
                    break
        if not counts:
            return "eng"
        # Majority script wins — REQ-001's mixed-language rule ("answer in the language
        # of the majority of the message") is implemented right here.
        return max(counts.items(), key=lambda kv: kv[1])[0]
