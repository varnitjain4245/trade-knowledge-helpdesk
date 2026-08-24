"""Per-stage tracing for the answering pipeline.

The whole-request deadline already knows how long a request took. What nobody could see
was where it went: which stage spent the budget, which model call cost what, and how
often a stage degraded rather than failing outright. That gap has a cost this project
has already paid. The defect where the relevance judge scored partial matches at exactly
the answer bar was found by hand, by printing scores one query at a time. A trace that
recorded the judged score against the bar on every request would have shown a spike of
requests answering at exactly 0.70 on the first afternoon.

Two decisions worth stating.

**OpenTelemetry, not a vendor SDK.** Langfuse's own ingestion API is deprecated and its
supported path is now OTLP, so writing to a vendor shape would mean adopting something
already being retired. OTLP spans go to Langfuse, Grafana, Jaeger, Honeycomb or a file,
and the choice stays the operator's. The exporter here writes the OTLP JSON shape
directly over HTTP; no SDK is needed, and with no endpoint configured nothing leaves the
process at all.

**Spans carry no customer content by default.** A trace is an operational record, not a
transcript. Stage names, durations, scores, token counts and outcomes go in; question
text and passage text do not, unless ``capture_content`` is switched on deliberately for
debugging. The logging processor already redacts customer content, and a tracing system
that quietly reintroduced it through a side channel would undo that.
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from app.core.logging import get_logger

log = get_logger(__name__)

#: How many finished traces to keep for the dashboard. A ring, because this is
#: operational visibility and not storage: the alternative is a memory leak that shows
#: up as a crash a week after a demo.
MAX_TRACES = 200

#: Attribute keys that would carry customer content. Dropped unless capture is on.
_CONTENT_KEYS = frozenset({"query", "question", "answer", "passage", "text", "detail"})


@dataclass
class Span:
    name: str
    started_ms: float
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    #: 'ok' | 'degraded' | 'error'. Degraded is distinct on purpose: a stage that
    #: fell back is not a failure, but a system that never distinguishes the two
    #: cannot tell a healthy day from one held together by fallbacks.
    status: str = "ok"

    def as_dict(self) -> dict:
        return {"name": self.name, "duration_ms": round(self.duration_ms, 1),
                "status": self.status, "attributes": self.attributes}


@dataclass
class Trace:
    trace_id: str
    name: str
    started_at: float
    spans: list[Span] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def as_dict(self) -> dict:
        return {
            "trace_id": self.trace_id, "name": self.name,
            "duration_ms": round(self.duration_ms, 1),
            "attributes": self.attributes,
            "spans": [s.as_dict() for s in self.spans],
            "slowest_stage": max(
                (s.as_dict() for s in self.spans),
                key=lambda s: s["duration_ms"], default=None),
            "degraded_stages": [s.name for s in self.spans if s.status != "ok"],
        }


class Tracer:
    def __init__(self, capture_content: bool = False) -> None:
        self.capture_content = capture_content
        self._traces: list[Trace] = []
        self._current: Trace | None = None

    # --- recording -------------------------------------------------------------------
    def _clean(self, attributes: dict[str, Any]) -> dict[str, Any]:
        if self.capture_content:
            return dict(attributes)
        return {k: v for k, v in attributes.items() if k not in _CONTENT_KEYS}

    @contextmanager
    def trace(self, name: str, **attributes: Any) -> Iterator[Trace]:
        trace = Trace(trace_id=uuid.uuid4().hex, name=name,
                      started_at=time.monotonic(),
                      attributes=self._clean(attributes))
        previous, self._current = self._current, trace
        try:
            yield trace
        finally:
            trace.duration_ms = (time.monotonic() - trace.started_at) * 1000
            self._current = previous
            self._traces.append(trace)
            del self._traces[:-MAX_TRACES]

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        """Time one stage. Recording continues even when the stage raises."""
        span = Span(name=name, started_ms=time.monotonic() * 1000,
                    attributes=self._clean(attributes))
        started = time.monotonic()
        try:
            yield span
        except Exception:
            span.status = "error"
            raise
        finally:
            span.duration_ms = (time.monotonic() - started) * 1000
            if self._current is not None:
                self._current.spans.append(span)

    def set(self, **attributes: Any) -> None:
        """Attach attributes to the trace in flight, if there is one."""
        if self._current is not None:
            self._current.attributes.update(self._clean(attributes))

    # --- reading ---------------------------------------------------------------------
    def recent(self, limit: int = 20) -> list[dict]:
        return [t.as_dict() for t in reversed(self._traces[-limit:])]

    def summary(self) -> dict:
        if not self._traces:
            return {"traces": 0}

        def percentile(values: list[float], p: float) -> float:
            if not values:
                return 0.0
            ordered = sorted(values)
            return round(ordered[min(len(ordered) - 1, int(len(ordered) * p))], 1)

        durations = [t.duration_ms for t in self._traces]
        by_stage: dict[str, list[float]] = {}
        degraded: dict[str, int] = {}
        for trace in self._traces:
            for span in trace.spans:
                by_stage.setdefault(span.name, []).append(span.duration_ms)
                if span.status != "ok":
                    degraded[span.name] = degraded.get(span.name, 0) + 1

        outcomes: dict[str, int] = {}
        for trace in self._traces:
            outcome = str(trace.attributes.get("outcome", "unknown"))
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        return {
            "traces": len(self._traces),
            "latency_ms": {"p50": percentile(durations, 0.5),
                           "p95": percentile(durations, 0.95),
                           "max": round(max(durations), 1)},
            "stages": {
                name: {"calls": len(v), "p50_ms": percentile(v, 0.5),
                       "p95_ms": percentile(v, 0.95),
                       "degraded": degraded.get(name, 0)}
                for name, v in sorted(by_stage.items(),
                                      key=lambda kv: -sum(kv[1]))
            },
            "outcomes": outcomes,
            "capture_content": self.capture_content,
        }

    # --- export ----------------------------------------------------------------------
    def otlp(self, limit: int = 50) -> dict:
        """Recent traces in the OTLP/JSON shape, for any OpenTelemetry collector.

        Emitted on request rather than pushed: a helpdesk that blocked an answer on a
        telemetry endpoint being reachable would have made observability a source of
        outages instead of a defence against them.
        """
        spans = []
        for trace in self._traces[-limit:]:
            for span in trace.spans:
                start_ns = int(span.started_ms * 1_000_000)
                spans.append({
                    "traceId": trace.trace_id,
                    "spanId": uuid.uuid4().hex[:16],
                    "name": span.name,
                    "startTimeUnixNano": str(start_ns),
                    "endTimeUnixNano": str(start_ns + int(span.duration_ms * 1_000_000)),
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}}
                        for k, v in {**trace.attributes, **span.attributes}.items()
                    ],
                    "status": {"code": 2 if span.status == "error" else 1},
                })
        return {"resourceSpans": [{
            "resource": {"attributes": [
                {"key": "service.name",
                 "value": {"stringValue": "scc-knowledge-platform"}}]},
            "scopeSpans": [{"spans": spans}],
        }]}


#: Process-wide. One tracer per process is the honest model for a single-process demo;
#: a multi-worker deployment would scope it per worker and aggregate at the collector.
tracer = Tracer(capture_content=os.getenv("SCC_TRACE_CONTENT", "").lower()
                in ("1", "true", "yes"))


def demo() -> None:
    """Self-check: spans nest and time, errors are recorded, content is not."""
    t = Tracer()

    with t.trace("answer", outcome="answered", query="secret question text"):
        with t.span("retrieve", candidates=8):
            time.sleep(0.01)
        with t.span("judge", score=0.7):
            pass

    recorded = t.recent()[0]
    assert recorded["name"] == "answer"
    assert [s["name"] for s in recorded["spans"]] == ["retrieve", "judge"]
    assert recorded["spans"][0]["duration_ms"] >= 9
    assert recorded["slowest_stage"]["name"] == "retrieve"

    # The point of the redaction: an operational record is not a transcript.
    assert "query" not in recorded["attributes"], "customer content leaked into a trace"
    assert recorded["attributes"]["outcome"] == "answered"

    # A raising stage is still timed and is marked, not swallowed.
    try:
        with t.trace("answer"):
            with t.span("generate"):
                raise RuntimeError("model down")
    except RuntimeError:
        pass
    failed = t.recent()[0]
    assert failed["spans"][0]["status"] == "error"
    assert failed["degraded_stages"] == ["generate"]

    s = t.summary()
    assert s["traces"] == 2
    assert "retrieve" in s["stages"] and s["stages"]["generate"]["degraded"] == 1
    assert s["latency_ms"]["p50"] > 0

    # Opt-in capture is the only way content appears.
    loud = Tracer(capture_content=True)
    with loud.trace("answer", query="visible now"):
        pass
    assert loud.recent()[0]["attributes"]["query"] == "visible now"

    otlp = t.otlp()
    assert otlp["resourceSpans"][0]["scopeSpans"][0]["spans"], "no spans exported"

    # The ring must bound memory rather than growing without limit.
    small = Tracer()
    for _ in range(MAX_TRACES + 25):
        with small.trace("x"):
            pass
    assert len(small._traces) == MAX_TRACES

    print("tracing: checks passed, spans timed and customer content withheld")


if __name__ == "__main__":
    demo()
