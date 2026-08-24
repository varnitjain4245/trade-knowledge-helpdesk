"""Structured logging (guardrail G10).

JSON output, one event per meaningful action, always carrying ``correlation_id``.

**Never log query text, message bodies or citation passages** — they contain customer
content. ``redact_customer_content`` is installed as a processor so that a field named
like customer content is dropped even if a call site forgets.
"""

import logging
from typing import Any

import structlog

_FORBIDDEN_KEYS = frozenset(
    {
        "query",
        "query_text",
        "body",
        "message_body",
        "passage",
        "answer_text",
        "sent_text",
        "transcript",
        "contact_detail",
    }
)


def redact_customer_content(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Drop customer content from every log event.

    This is a backstop, not a licence: call sites are still expected not to pass these
    fields. Redacting rather than raising keeps a logging mistake from taking down a
    request path.
    """
    for key in list(event_dict):
        if key in _FORBIDDEN_KEYS:
            event_dict[key] = "[redacted]"
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, level))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_customer_content,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
