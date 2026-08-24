"""Local demo runner.

Wires the real ``AnswerService`` to in-memory adapters and serves a small UI, so the
answer path can be exercised end to end without PostgreSQL, Redis or a GPU.

This is a **demo harness, not the production entry point**. The production API is built
across TASK-11/17/19/20/21/22/23/24/25 and is still in progress; this file exists so the
decisions already implemented can be seen working rather than only described.
"""

from __future__ import annotations

from datetime import date
import contextlib
from pathlib import Path

import httpx
from uuid import UUID, uuid4

import json
from dataclasses import replace

from fastapi import (Cookie, FastAPI, File, Form, HTTPException, Request, Response,
                     UploadFile)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.demo.store import (DemoAnswers, DemoCoverage, DemoEmbedder, DemoFairUse,
                            DemoGaps, DemoGenerationCounter, DemoItem, DemoLanguages,
                            DemoReranker, DemoStore, DemoThresholds)
from app.demo.programmes import (DEADLINES, NOTICES, SCHEMES, SECTORS, TARIFF,
                                 eligible)
from app.demo.accounts import Accounts
from app.demo.attachments import ExtractionFailed, as_passages, extract
from app.demo.actions import CATALOGUE as ACTION_CATALOGUE, Actions, offers_for
from app.demo.eligibility import (QUESTIONS, TURNOVER_BANDS,
                                   state as eligibility_state)
from app.core.tracing import tracer
from app.services.answer_translation import AnswerTranslator
from app.demo.feedback import FeedbackStore
from app.demo.feeds import SOURCES as FEED_SOURCES, FeedWatcher
from app.demo.language_gate import LanguageGate, measure as language_measure
from app.demo.whatsapp import WhatsAppChannel
from app.demo.grievances import Grievances
from app.models.bhashini import ISO3_TO_BHASHINI, BhashiniClient, BhashiniUnavailable
from app.demo.opendata import CATALOGUE, OpenDataClient
from app.demo.verification import BusinessVerifier, classify_by_turnover
from app.demo.learning import LearningLog
from app.demo.workspace import Workspace
from app.models.generation import (ExtractiveGenerationService,
                                   GroqGenerationService)
from app.models.relevance import RelevanceJudge
from app.models.langdetect import ScriptLanguageDetector
from app.models.pii import RegexPiiDetector
from app.services.answer import AnswerRequest, AnswerService
from app.services.answer_cache import AnswerCache, InMemoryCacheBackend
from app.services.authz import Actor, Role
from app.services.conflict import ConflictDetector
from app.services.grounding import GroundingVerifier
from app.services.masking import Masker

configure_logging()
log = get_logger(__name__)
settings = get_settings()

store = DemoStore()
coverage = DemoCoverage()  # bound to the store after seeding
thresholds = DemoThresholds()
languages = DemoLanguages()
generation = DemoGenerationCounter()
answers = DemoAnswers()
gaps = DemoGaps()
cache = AnswerCache(InMemoryCacheBackend(), settings.answer_cache_ttl_seconds, generation)
workspace = Workspace()
accounts = Accounts(settings.database_path)
learning = LearningLog(settings)
grievances = Grievances(settings.database_path)
bhashini = BhashiniClient(settings)
feedback = FeedbackStore(settings.database_path)
language_gate = LanguageGate()
actions = Actions(settings.database_path)

_feed_sources = {k: dict(v) for k, v in FEED_SOURCES.items()}
_feed_sources["dgft_regulatory"]["feed_url"] = settings.dgft_feed_url
_feed_sources["cbic_customs"]["feed_url"] = settings.cbic_feed_url
feeds = FeedWatcher(settings.database_path, _feed_sources)
whatsapp = WhatsAppChannel(settings.whatsapp_token, settings.whatsapp_phone_number_id,
                           settings.whatsapp_verify_token, settings.whatsapp_app_secret)
opendata = OpenDataClient(settings.data_gov_api_key)
verifier = BusinessVerifier(settings.apisetu_api_key, settings.apisetu_client_id)

#: Extracted text from a document someone attached, held per conversation only. It never
#: enters the knowledge base — an uploaded file is not an approved record, and letting it
#: answer other people's questions would break the approval chain citations rest on.
attachments: dict[str, list] = {}


def _seed() -> dict[str, UUID]:
    """Load the corpus.

    The records live in ``corpus.py`` rather than inline here, because a helpdesk's value
    is its corpus and a corpus embedded in application code cannot be reviewed, corrected
    or replaced by the people who own the knowledge.
    """
    from app.demo.corpus import ALL_RECORDS, SPECIAL

    seeded: dict[str, UUID] = {}
    for record in ALL_RECORDS + SPECIAL:
        item_id = store.add(DemoItem(
            id=uuid4(), title=record.title, authority=record.authority,
            issued_on=record.issued, language=record.language, status=record.status,
            passages=list(record.passages), topic=record.topic,
        ))
        seeded[record.title] = item_id
    return seeded


SEEDED = _seed()

# The gate is evaluated against the corpus that was actually loaded, and opened only if
# every must-have topic has an answerable record. With 45 records across registration,
# licensing, customs, GST, tariff, MSME finance, e-commerce and standards it does — the
# floor exists to stop a public surface opening on thin knowledge, and this is no longer
# thin. It stays shut, loudly, if the corpus ever stops covering one of them.
coverage._store = store
if coverage.declare(by="knowledge manager, at seed"):
    log.info("coverage.declared", records=len(store.items))
else:
    log.warning("coverage.withheld", uncovered=coverage.uncovered_topics())

class JudgingReranker:
    """Relevance judging with a lexical fallback.

    This is the reranker the design specified all along: something that scores whether a
    passage *answers* the question rather than whether it shares words with it. The
    lexical stub stays behind it, because a judging service that is rate-limited or down
    must degrade to a worse ranking rather than to no answer (guardrail G4) — and the
    caller is told which one produced the score, so a confidence is never silently of a
    different kind than it appears.
    """

    def __init__(self, judge, fallback, store) -> None:  # noqa: ANN001
        self._judge = judge
        self._fallback = fallback
        self._store = store
        self.last_source = "lexical"

    def _titled(self, passages: list[str]) -> list[str]:
        """Prefix each passage with the record it belongs to.

        A demo shortcut — the answer service hands the reranker passage text alone, and
        production would pass structured candidates. The title matters: a record often
        names its subject only there, and judging the body in isolation misreads it.
        """
        titles = getattr(self._store, "_last_titles", {})
        return [
            f"From the record \"{titles[p]}\":\n{p}" if p in titles else p
            for p in passages
        ]

    #: A lexical score is evidence of shared vocabulary, not of relevance. Letting it
    #: reach the answer bar unchanged is what allowed "tell me about quantum computing"
    #: to be answered from a trade-policy record at full confidence. When judging is
    #: unavailable the desk says so instead of guessing — the safe side of the
    #: degradation, per guardrail G4.
    UNJUDGED_CEILING = 0.69

    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        scores = await self._judge.score(query, self._titled(passages))
        if scores is not None:
            self.last_source = "judged"
            return scores

        self.last_source = "lexical"
        lexical = await self._fallback.rerank(query, passages)
        return [min(s, self.UNJUDGED_CEILING) for s in lexical]


masker = Masker(RegexPiiDetector(), min_confidence=0.85)

# The extractive strategy is always built: it is the fallback whenever generation fails
# its grounding check, and the whole answer path is designed so that fallback is safe
# rather than exceptional (guardrail G4).
extractive = ExtractiveGenerationService()

if settings.generation_provider == "groq" and settings.groq_api_key:
    generator = GroqGenerationService(settings)
    GENERATION_NOTE = (
        "Answers are drafted by a hosted model (Groq). Query text and the retrieved "
        "passages leave this machine — a deliberate exception to the data-control "
        "requirement, made for the demonstration. Every draft is still checked against "
        "its sources, and anything unsupported is discarded."
    )
else:
    generator = extractive
    GENERATION_NOTE = (
        "Answers quote the record verbatim. No query text or document content leaves "
        "this machine."
    )

answer_service = AnswerService(
    settings=settings,
    retrieval=store,
    reranker=JudgingReranker(RelevanceJudge(settings), DemoReranker(store), store),
    generator=generator,
    extractive=extractive,
    verifier=GroundingVerifier(min_coverage=settings.grounding_min_coverage),
    conflict_detector=ConflictDetector(min_score=0.5),
    thresholds=thresholds,
    answers=answers,
    cache=cache,
    gaps=gaps,
    masker=masker,
    language_registry=languages,
    coverage_gate=coverage,
    fair_use=DemoFairUse(),
    generation_counter=generation,
    detector=ScriptLanguageDetector(),
    embedder=DemoEmbedder(),
)

# Attached rather than passed: the rewriter is an optional second retrieval pass, and
# AnswerService treats its absence as "no rewriting" so the constructor signature stays
# the one the design documents describe.
from app.services.query_rewrite import QueryRewriter  # noqa: E402

answer_service._rewriter = QueryRewriter(settings)
answer_service._feedback = feedback
answer_service._translator = AnswerTranslator(settings, bhashini)

app = FastAPI(title="Smart Contact-Center Knowledge Platform — demo", version="0.1.0")

AGENT = Actor(user_id=1, roles=frozenset({Role.AGENT}))
MANAGER = Actor(user_id=2, roles=frozenset({Role.KNOWLEDGE_MANAGER}))


class AskBody(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    surface: str = "agent"
    preferred_language: str | None = None
    conversation: str | None = "bot"


def _serialise(result) -> dict:  # noqa: ANN001
    return {
        "outcome": result.outcome.value,
        "answer_text": result.answer_text,
        "answer_language": result.answer_language,
        "confidence": float(result.confidence) if result.confidence is not None else None,
        "stale_sources": result.stale_sources,
        "handover_offered": result.handover_offered,
        # What the desk can actually do about this answer, offered from what the answer
        # contains rather than from a fixed menu.
        "actions": [o.as_dict() for o in offers_for(result)],
        "retry_after_seconds": result.retry_after_seconds,
        "latency_ms": result.latency_ms,
        "citations": [
            {
                "item_title": c.item_title, "issuing_authority": c.issuing_authority,
                "issued_on": c.issued_on.isoformat(), "passage": c.passage,
                "passage_language": c.passage_language,
                "review_pending": c.review_pending, "rank": c.rank,
            }
            for c in result.citations
        ],
        "conflicting_sources": [
            {
                "item_title": c.item_title, "issuing_authority": c.issuing_authority,
                "issued_on": c.issued_on.isoformat(), "passage": c.passage,
            }
            for c in result.conflicting_sources
        ],
        "related_reading": [
            {"item_title": c.item_title, "passage": c.passage}
            for c in result.related_reading
        ],
    }


@app.post("/api/v1/demo/ask")
async def ask(body: AskBody, scc_session: str | None = Cookie(default=None)) -> dict:
    actor = Actor.public("demo-token") if body.surface == "public" else AGENT
    from app.domain.errors import LanguageNotEnabled

    user = _me(scc_session)
    # A signed-in person's saved answer language applies unless they override it for
    # this question — the point of saving a preference is not restating it every time.
    preferred = body.preferred_language or (
        user.preferences.answer_language if user else None
    )

    # An attached document joins the answerable set for this conversation only.
    held = attachments.get(body.conversation or "bot")
    with _with_attachment(held):
        try:
            result = await answer_service.answer(
                AnswerRequest(query=body.query, preferred_language=preferred), actor
            )
        except LanguageNotEnabled as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": exc.code,
                    "language": exc.extra["language"],
                    "enabled": exc.extra["enabled"],
                },
            ) from exc

    payload = _serialise(result)
    outcome = result.outcome.value
    cited = result.citations[0].item_title if result.citations else None

    # Anything the desk could not settle goes to the learning log rather than a queue
    # somebody has to remember to work.
    if outcome in ("no_answer", "conflict"):
        entry = learning.record(body.query, result.answer_language or "eng", outcome)
        allowed, reason = learning.should_draft(entry)
        payload["can_learn"] = allowed
        payload["learn_reason"] = reason
    else:
        payload["can_learn"] = False
        payload["learn_reason"] = ""

    if user:
        accounts.record_query(
            user, body.query, outcome, result.answer_text, cited,
            result.answer_language or "eng",
        )
    payload["signed_in"] = bool(user)
    return payload


@contextlib.contextmanager
def _with_attachment(held: list | None):
    """Make an attached document retrievable for the duration of one question.

    Added to the store and removed afterwards, so a document one person attached can
    never surface in another person's answer. Doing this by mutating the shared store is
    a demo shortcut and is marked as one — production would scope retrieval by
    conversation instead of adding and removing rows.
    """
    if not held:
        yield
        return

    item_id = store.add(DemoItem(
        id=uuid4(), title=f"Attached: {held[0]['name']}",
        authority="Document you attached", issued_on=date.today(),
        language="eng", status="approved",
        passages=[h["body"] for h in held], topic="attachment",
    ))
    try:
        yield
    finally:
        store.items.pop(item_id, None)
        store._chunk_index = {
            k: v for k, v in store._chunk_index.items() if v[0] != item_id
        }
        store._dirty = True


@app.get("/api/v1/demo/knowledge")
def list_knowledge() -> list[dict]:
    return [
        {
            "id": str(item.id), "title": item.title, "authority": item.authority,
            "issued_on": item.issued_on.isoformat(), "language": item.language,
            "status": item.status, "topic": item.topic,
            "answerable": item.status in ("approved", "stale"),
        }
        for item in store.items.values()
    ]


class StatusBody(BaseModel):
    status: str


@app.post("/api/v1/demo/knowledge/{item_id}/status")
def set_status(item_id: UUID, body: StatusBody) -> dict:
    """Change an item's lifecycle status, bumping the generation counter.

    The bump is what makes the change take effect on the very next answer — the
    mechanism that resolves the cache-versus-retirement contradiction the Stage 4 review
    found (hld-review High-1). Retire an item, ask the same question again, and the
    cached answer is gone.
    """
    if item_id not in store.items:
        raise HTTPException(404, "unknown item")
    store.set_status(item_id, body.status)
    new_generation = generation.bump()

    # Anyone who acted on this record is the person the change matters to. Telling them
    # is the point of letting them watch it: guidance changing silently under somebody
    # who already relied on it is the failure the lifecycle exists to prevent.
    told = 0
    if body.status in ("superseded", "retired", "stale"):
        told = actions.notify_watchers(str(item_id), body.status)

    return {"status": body.status, "generation": new_generation,
            "watchers_notified": told}


@app.get("/api/v1/demo/state")
def state() -> dict:
    return {
        "generation_provider": settings.generation_provider
        if (settings.generation_provider != "groq" or settings.groq_api_key) else "extractive",
        "generation_model": settings.groq_model
        if settings.generation_provider == "groq" and settings.groq_api_key else "extractive",
        "generation_note": GENERATION_NOTE,
        "sends_data_offsite": settings.generation_provider == "groq" and bool(settings.groq_api_key),
        "accounts": accounts.stats(),
        "self_serve_open": coverage.declared,
        "coverage_floor_met": coverage.floor_met(),
        "uncovered_topics": coverage.uncovered_topics(),
        "declared_by": coverage.declared_by,
        "answer_bar": thresholds.get("answer_bar"),
        "enabled_languages": sorted(languages.enabled),
        "generation": generation.current(),
        "answers_recorded": len(answers.records),
        "gap_entries": [
            {"cause": e["cause"], "language": e["query_language"], "query": e["query_text"]}
            for e in gaps.entries
        ],
    }


class SettingsBody(BaseModel):
    self_serve_open: bool | None = None
    answer_bar: float | None = None
    enabled_languages: list[str] | None = None


@app.post("/api/v1/demo/state")
def update_state(body: SettingsBody) -> dict:
    if body.self_serve_open is not None:
        coverage.declared = body.self_serve_open
    if body.answer_bar is not None:
        thresholds.set("answer_bar", body.answer_bar)
    if body.enabled_languages is not None:
        # The gate, enforced. Previously a language could be switched on by naming it,
        # which made an enablement backed by a measurement indistinguishable from one
        # that ignored the gate — and the second kind is a promise the desk cannot keep.
        requested = set(body.enabled_languages)
        allowed, refused = set(), {}
        for code in requested:
            ok, why = language_gate.may_enable(code)
            (allowed.add(code) if ok else refused.__setitem__(code, why))
        languages.enabled = allowed
        if refused:
            log.warning("language.enable_refused", languages=sorted(refused))
            return {**state(), "refused_languages": refused}
    return state()


@app.get("/api/v1/demo/languages/gate")
def language_gate_report() -> dict:
    return language_gate.report()


@app.post("/api/v1/demo/languages/{code}/measure")
async def measure_language(code: str) -> dict:
    """Run the acceptance question set for a language and record the score.

    Recording is the point. A language enabled without a score on file cannot be
    audited later, and 'we tested it' is not a measurement.
    """
    try:
        score = await language_measure(code, answer_service, AGENT)
    except KeyError as exc:
        raise HTTPException(404, f"No acceptance questions for {code!r}.") from exc
    language_gate.record(score)
    return score.as_dict()


# ======================================================================================
# Conversations — agent console and customer assistant
# ======================================================================================


class StartBody(BaseModel):
    surface: str = "agent"
    language: str = "eng"


@app.post("/api/v1/demo/conversations")
def start_conversation(body: StartBody) -> dict:
    state_name = "active_agent" if body.surface == "agent" else "active_self_serve"
    conversation = workspace.start(body.surface, body.language, state_name)
    return _conversation(conversation)


class TurnBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    preferred_language: str | None = None


@app.post("/api/v1/demo/conversations/{conversation_id}/turn")
async def customer_turn(conversation_id: UUID, body: TurnBody) -> dict:
    """A customer turn on the self-serve surface.

    Implements REQ-007's streak rule: two consecutive below-bar answers offer handover
    without the customer having to ask. A conflict resets the streak but still offers
    handover — the corpus disagreeing with itself needs a human, but it is not evidence
    the system cannot answer.
    """
    conversation = _require(conversation_id)
    language = body.preferred_language or conversation.language
    workspace.add_message(conversation, "customer", body.text, language)

    actor = Actor.public(str(conversation.id)) if conversation.surface == "public" else AGENT
    result = await answer_service.answer(
        AnswerRequest(query=body.text, conversation_id=conversation.id,
                      preferred_language=language),
        actor,
    )

    outcome = result.outcome.value
    if outcome == "answered":
        conversation.below_bar_streak = 0
        workspace.add_message(conversation, "assistant", result.answer_text or "",
                              result.answer_language or language, result.answer_id, outcome)
    elif outcome == "conflict":
        conversation.below_bar_streak = 0
        workspace.add_message(conversation, "assistant",
                              "The available sources give different answers.",
                              language, result.answer_id, outcome)
    elif outcome in ("blocked_coverage", "blocked_fair_use"):
        # Neither is a failure to answer, and recording one as though it were both
        # misleads the reader and inflates the below-bar streak that triggers handover.
        workspace.add_message(
            conversation, "assistant",
            "The assistant is not open to customers yet — connecting you to a person."
            if outcome == "blocked_coverage"
            else "You have reached the question limit for now.",
            language, result.answer_id, outcome)
    else:
        conversation.below_bar_streak += 1
        workspace.add_message(conversation, "assistant",
                              "No reliable answer from the approved sources.",
                              language, result.answer_id, outcome)

    payload = _serialise(result)
    payload["conversation"] = _conversation(conversation)
    payload["auto_handover"] = conversation.below_bar_streak >= 2
    return payload


@app.post("/api/v1/demo/conversations/{conversation_id}/resolve")
def resolve(conversation_id: UUID) -> dict:
    conversation = _require(conversation_id)
    workspace.end(conversation, "self_resolved")
    return _conversation(conversation)


@app.post("/api/v1/demo/conversations/{conversation_id}/abandon")
def abandon(conversation_id: UUID) -> dict:
    """The inactivity outcome, triggered manually here.

    Without this state the deflection denominator is silently wrong — which is why it is
    a recorded outcome rather than the absence of one.
    """
    conversation = _require(conversation_id)
    workspace.end(conversation, "abandoned")
    return _conversation(conversation)


@app.post("/api/v1/demo/conversations/{conversation_id}/handover")
def handover(conversation_id: UUID) -> dict:
    conversation = _require(conversation_id)
    position = workspace.enqueue(conversation)
    return {"queue_position": position, "conversation": _conversation(conversation)}


@app.post("/api/v1/demo/conversations/{conversation_id}/assign")
def assign(conversation_id: UUID) -> dict:
    conversation = _require(conversation_id)
    workspace.assign(conversation, "Anjali")
    return _conversation(conversation)


class CallbackBody(BaseModel):
    contact: str = Field(min_length=3, max_length=200)


@app.post("/api/v1/demo/conversations/{conversation_id}/callback")
def callback(conversation_id: UUID, body: CallbackBody) -> dict:
    conversation = _require(conversation_id)
    workspace.end(conversation, "callback_recorded")
    # The contact detail is personal data; it is masked everywhere except the agent
    # working the callback.
    workspace.write_audit("callback_recorded", "system", "conversation",
                          str(conversation.id),
                          contact_detail=masker.mask(body.contact).text)
    return _conversation(conversation)


class ReplyBody(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    from_answer_id: UUID | None = None
    suggestion_body: str | None = None


@app.post("/api/v1/demo/conversations/{conversation_id}/reply")
def reply(conversation_id: UUID, body: ReplyBody) -> dict:
    """An agent's reply — the REQ-014 write point.

    The record distinguishes what was *suggested* from what the customer was actually
    told. Without that, an audit trail can show a correct cited suggestion while the
    customer received something materially different.
    """
    conversation = _require(conversation_id)
    workspace.add_message(conversation, "agent", body.body, conversation.language)
    edited = None
    if body.from_answer_id and body.suggestion_body is not None:
        usage = workspace.record_assist(
            conversation.id, body.from_answer_id, body.suggestion_body, body.body, "Anjali"
        )
        edited = usage.edited_before_send
    return {"conversation": _conversation(conversation), "edited_before_send": edited}


class RatingBody(BaseModel):
    rating: int
    #: The question and the record it was answered from. Without both, a rating cannot
    #: be attached to anything and is recorded but not acted upon.
    query: str = ""
    item_id: str = ""
    item_title: str = ""
    note: str = ""


@app.post("/api/v1/demo/answers/{answer_id}/rating")
def rate(answer_id: UUID, body: RatingBody, request: Request,
         scc_session: str | None = Cookie(default=None)) -> dict:
    """Record a rating and act on it.

    Previously this wrote to the audit log and was read by nothing, which asked people
    to spend attention marking answers wrong and spent none of its own in return.
    """
    if body.rating not in (-1, 1):
        raise HTTPException(422, "rating must be -1 or 1")

    found = workspace.rate(answer_id, body.rating, "Anjali")

    outcome = None
    if body.query and body.item_id:
        user = _me(scc_session)
        outcome = feedback.rate(
            body.query, body.item_id, body.rating,
            item_title=body.item_title, note=body.note,
                # Most people rating a public helpdesk are not signed in. A single
            # literal "anonymous" would make every visitor one rater, so two people
            # reporting the same wrong answer would count once and suppression could
            # never be reached. The client address separates them while still
            # stopping one person clicking twice.
            rater=(user.email if user else f"anon:{request.client.host if request.client else 'unknown'}"),
        )
        if outcome.suppressed:
            # A withheld pairing changes what the desk will answer, so every cached
            # answer must become unreachable — the same rule a lifecycle change obeys.
            generation.bump()

    return {
        "rated": body.rating,
        "assist_usage_found": found,
        **(outcome.as_dict() if outcome else
           {"message": "Recorded.", "suppressed": False}),
    }


# --- WhatsApp channel -----------------------------------------------------------------
# The same AnswerService serves this channel. A looser standard for a casual medium
# would be the worst thing to grow here: the person on WhatsApp has less ability to
# check a claim than the one looking at the evidence panel, not more.

@app.get("/api/v1/demo/whatsapp/webhook")
def whatsapp_verify(request: Request) -> Response:
    q = request.query_params
    challenge = whatsapp.verify(q.get("hub.mode", ""), q.get("hub.verify_token", ""),
                                q.get("hub.challenge", ""))
    if challenge is None:
        raise HTTPException(403, "Verification failed.")
    return Response(content=challenge, media_type="text/plain")


@app.post("/api/v1/demo/whatsapp/webhook")
async def whatsapp_inbound(request: Request) -> dict:
    raw = await request.body()
    if not whatsapp.signature_ok(raw, request.headers.get("X-Hub-Signature-256")):
        # Checked before the body is parsed. An unsigned webhook is rejected whether
        # or not it looks well-formed.
        raise HTTPException(403, "Bad signature.")

    payload = json.loads(raw or b"{}")
    handled = 0
    for message in WhatsAppChannel.parse(payload):
        if message.kind == "audio" and message.audio_id:
            audio = await whatsapp.fetch_audio(message.audio_id)
            text = ""
            if audio and bhashini.available:
                try:
                    text = await bhashini.transcribe(audio, "hin", audio_format="ogg")
                except Exception:  # noqa: BLE001
                    text = ""
            if not text:
                await whatsapp.send(message.from_number,
                                    "I could not make out that voice note. "
                                    "Please type the question.")
                continue
            message = replace(message, text=text)
        elif message.kind != "text" or not message.text:
            await whatsapp.send(message.from_number,
                                "I can read text and voice notes. Please send one of "
                                "those.")
            continue

        await _whatsapp_reply(message)
        handled += 1
    return {"handled": handled}


async def _whatsapp_reply(message) -> None:  # noqa: ANN001
    word = message.text.strip().upper()
    if word == "AGENT":
        await whatsapp.send(message.from_number,
                            "Put through to a person. Somebody will reply here.")
        workspace.write_audit("whatsapp_handover", "system", "conversation",
                              message.from_number)
        return
    if word == "GRIEVANCE":
        await whatsapp.send(
            message.from_number,
            "Send your complaint as one message beginning with the word GRIEVANCE, "
            "and you will get a tracking reference.")
        return
    if word.startswith("GRIEVANCE "):
        detail = message.text.strip()[len("GRIEVANCE "):].strip()
        lodged = grievances.lodge(detail[:80], detail, contact=message.from_number)
        await whatsapp.send(
            message.from_number,
            f"Lodged. Your reference is *{lodged['reference']}*.\n"
            f"With {lodged['assigned_to']}, {lodged['authority']}.\n"
            f"Reply *STATUS {lodged['reference']}* at any time.")
        return
    if word.startswith("STATUS "):
        found = grievances.track(word[len("STATUS "):].strip())
        if found is None:
            await whatsapp.send(message.from_number, "No grievance with that reference.")
            return
        g = found.as_dict()
        await whatsapp.send(
            message.from_number,
            f"*{g['reference']}* — {g['status']}\n{g['subject']}\n"
            f"With {g['assigned_to']}, {g['authority']}."
            + ("\n_Overdue; it has been escalated._" if g["overdue"] else ""))
        return

    result = await answer_service.answer(
        AnswerRequest(query=message.text), Actor.public("whatsapp"))
    await whatsapp.send(message.from_number, WhatsAppChannel.render(result))


@app.get("/api/v1/demo/channels")
def channels() -> dict:
    """Which ways in are actually live. Stated, not implied."""
    return {
        "web": {"live": True},
        "whatsapp": {"live": whatsapp.available,
                     "signed": bool(settings.whatsapp_app_secret),
                     "commands": ["AGENT", "GRIEVANCE <text>", "STATUS <ref>", "WRONG"]},
        "voice": {"live": bool(settings.groq_api_key) or bhashini.available,
                  "engine": "bhashini" if bhashini.available else "whisper"},
    }


# --- eligibility questionnaire ---------------------------------------------------------

class EligibilityBody(BaseModel):
    answers: dict[str, str] = {}


@app.post("/api/v1/demo/eligibility")
def eligibility_step(body: EligibilityBody,
                     scc_session: str | None = Cookie(default=None)) -> dict:
    """Narrow to the schemes a business qualifies for, one question at a time.

    A question is returned only when the answer would change a verdict, so the
    questionnaire ends as soon as the remaining schemes agree.
    """
    answers = {k: v for k, v in body.answers.items() if k in QUESTIONS}

    # A signed-in person has already said some of this. Asking again is the fastest
    # way to teach somebody that a form is not paying attention.
    user = _me(scc_session)
    if user:
        prefs = user.preferences
        for key, value in (("entity_type", prefs.entity_type),
                           ("activity", prefs.activity),
                           ("sector", prefs.sector)):
            if value and key not in answers:
                answers[key] = value
        if prefs.turnover_cr is not None and "turnover_band" not in answers:
            answers["turnover_band"] = next(
                (k for k, _, v in TURNOVER_BANDS if prefs.turnover_cr <= v),
                TURNOVER_BANDS[-1][0])

    return eligibility_state(answers)


@app.get("/api/v1/demo/eligibility/questions")
def eligibility_questions() -> dict:
    return {"questions": [{"key": k, **v} for k, v in QUESTIONS.items()],
            "turnover_bands": [{"value": k, "label": lbl}
                               for k, lbl, _ in TURNOVER_BANDS]}


# --- tracing --------------------------------------------------------------------------

@app.get("/api/v1/demo/traces")
def traces(limit: int = 20) -> dict:
    """Per-stage timings for recent requests.

    Operational record, not transcript: question and passage text are withheld unless
    SCC_TRACE_CONTENT is set for debugging.
    """
    return {"summary": tracer.summary(), "recent": tracer.recent(limit)}


@app.get("/api/v1/demo/traces/otlp")
def traces_otlp(limit: int = 50) -> dict:
    """Recent spans in OTLP/JSON, for Langfuse, Grafana, Jaeger or any collector."""
    return tracer.otlp(limit)


# --- actions --------------------------------------------------------------------------
# Every action is inside this system's own authority and is reversible. Nothing here
# files anything with DGFT, CBIC or GSTN: this desk explains their processes, it has no
# standing to act inside them, and an action that appeared to would be believed.

class ActionBody(BaseModel):
    kind: str
    payload: dict = {}
    contact: str = ""


@app.post("/api/v1/demo/actions")
def run_action(body: ActionBody,
               scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    try:
        return actions.run(body.kind, body.payload,
                           user_id=user.id if user else None,
                           contact=body.contact, grievances=grievances)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/v1/demo/actions/catalogue")
def action_catalogue() -> dict:
    return {
        "actions": [{"kind": k, "label": lbl, "detail": detail}
                    for k, (lbl, detail) in ACTION_CATALOGUE.items()],
        "summary": actions.summary(),
        "note": ("This desk prepares and tracks. It does not submit anything to any "
                 "department on your behalf."),
    }


@app.get("/api/v1/demo/me/actions")
def my_actions(scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    if not user:
        raise HTTPException(401, "Sign in to see what you have asked the desk to do.")
    return {"actions": actions.for_user(user.id)}


# --- departmental feeds ---------------------------------------------------------------

@app.get("/api/v1/demo/feeds")
def feed_status() -> dict:
    return {"summary": feeds.summary(), "pending": feeds.pending(20)}


@app.post("/api/v1/demo/feeds/{source}/poll")
async def poll_feed(source: str) -> dict:
    try:
        return await feeds.poll(source)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/v1/demo/feeds/drafts")
def feed_drafts(limit: int = 20) -> dict:
    """Feed entries as records a curator can review. None of them can answer yet."""
    return {"drafts": feeds.to_records(limit)}


@app.get("/api/v1/demo/curation/tasks")
def curation_tasks(state: str = "open") -> dict:
    """What ratings have asked a person to look at."""
    return {"tasks": feedback.tasks(state), "summary": feedback.summary()}


class TaskResolveBody(BaseModel):
    state: str
    resolution: str = ""


@app.post("/api/v1/demo/curation/tasks/{task_id}")
def resolve_curation_task(task_id: int, body: TaskResolveBody) -> dict:
    """Close a task as record_wrong, retrieval_wrong or rating_wrong."""
    try:
        ok = feedback.resolve_task(task_id, body.state, body.resolution)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not ok:
        raise HTTPException(404, "No such task.")
    if body.state == "rating_wrong":
        generation.bump()
    return {"resolved": body.state, "summary": feedback.summary()}


@app.get("/api/v1/demo/conversations/{conversation_id}")
def get_conversation(conversation_id: UUID) -> dict:
    return _conversation(_require(conversation_id))


@app.get("/api/v1/demo/queue")
def queue() -> list[dict]:
    return [_conversation(workspace.conversations[c]) for c in workspace.queue]


def _require(conversation_id: UUID):  # noqa: ANN202
    conversation = workspace.conversations.get(conversation_id)
    if conversation is None:
        raise HTTPException(404, "unknown conversation")
    if conversation.state in {"self_resolved", "agent_resolved", "callback_recorded",
                              "abandoned"}:
        raise HTTPException(409, f"conversation already ended as {conversation.state}")
    return conversation


def _conversation(conversation) -> dict:  # noqa: ANN001
    return {
        "id": str(conversation.id),
        "surface": conversation.surface,
        "state": conversation.state,
        "language": conversation.language,
        "below_bar_streak": conversation.below_bar_streak,
        "queue_position": conversation.queue_position,
        "agent_name": conversation.agent_name,
        "retired_source_flag": conversation.retired_source_flag,
        "messages": [
            {
                "id": m.id, "author": m.author, "body": m.body, "language": m.language,
                "answer_id": str(m.answer_id) if m.answer_id else None,
                "outcome": m.outcome,
                "at": m.created_at.strftime("%H:%M:%S"),
            }
            for m in conversation.messages
        ],
    }


# ======================================================================================
# Curation, gaps, analytics, audit
# ======================================================================================


class EntryBody(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    body: str = Field(min_length=10)
    authority: str = Field(min_length=2)
    language: str = "eng"
    topic: str = "general"


@app.post("/api/v1/demo/knowledge")
def create_entry(body: EntryBody) -> dict:
    """A manually authored entry.

    It lands in `pending_review`, never straight to answerable: the pipeline's terminal
    state is always pending, and only a human approval makes something citable.
    """
    item_id = store.add(DemoItem(
        id=uuid4(), title=body.title, authority=body.authority,
        issued_on=date.today(), language=body.language, status="pending_review",
        passages=[body.body], topic=body.topic,
    ))
    workspace.write_audit("knowledge_created", "Meera", "knowledge_item", str(item_id),
                          title=body.title)
    return {"id": str(item_id), "status": "pending_review"}


@app.get("/api/v1/demo/gaps")
def list_gaps() -> list[dict]:
    """Gap entries grouped by cause and language.

    Grouping by meaning uses the same multilingual embeddings as retrieval in
    production; here it groups on the query itself, which is enough to show the queue
    and its resolution states.
    """
    grouped: dict[tuple[str, str], dict] = {}
    for entry in gaps.entries:
        key = (entry["cause"], entry["query_text"][:60])
        group = grouped.setdefault(key, {
            "cause": entry["cause"], "label": entry["query_text"],
            "count": 0, "languages": {}, "resolution": "open",
        })
        group["count"] += 1
        language = entry["query_language"]
        group["languages"][language] = group["languages"].get(language, 0) + 1
    for key, resolution in _gap_resolutions.items():
        if key in grouped:
            grouped[key]["resolution"] = resolution
    return sorted(grouped.values(), key=lambda g: g["count"], reverse=True)


_gap_resolutions: dict[tuple[str, str], str] = {}


class ResolveGapBody(BaseModel):
    cause: str
    label: str
    resolution: str
    owner: str | None = None


@app.post("/api/v1/demo/gaps/resolve")
def resolve_gap(body: ResolveGapBody) -> dict:
    """Four resolution types, each with its own required field.

    `pending_external` needs an owner: a gap nobody owns is not pending, it is
    forgotten. `resolved_with_item` would require an answerable item in production.
    """
    if body.resolution == "pending_external" and not body.owner:
        raise HTTPException(422, "pending_external requires an owner")
    _gap_resolutions[(body.cause, body.label[:60])] = body.resolution
    workspace.write_audit("gap_resolved", "Meera", "gap", body.label[:60],
                          resolution=body.resolution, owner=body.owner)
    return {"resolution": body.resolution}


@app.get("/api/v1/demo/analytics")
def analytics() -> dict:
    return workspace.metrics(answers.records, [g for g in list_gaps() if g["resolution"] == "open"])


@app.get("/api/v1/demo/audit")
def audit(conversation_id: UUID | None = None) -> list[dict]:
    records = (
        workspace.audit_for_conversation(conversation_id)
        if conversation_id else workspace.audit
    )
    return [
        {
            "id": r.id, "action": r.action, "actor": r.actor,
            "subject_type": r.subject_type, "subject_id": r.subject_id,
            "detail": r.detail, "at": r.occurred_at.strftime("%H:%M:%S"),
        }
        for r in reversed(records)
    ]


# ======================================================================================
# Business-facing: schemes, tariff lines, trade notices, deadlines
#
# Everything below is illustrative sample data. The interface says so wherever it is
# shown — a platform whose argument is that guidance must be traceable cannot quietly
# present invented figures as policy.
# ======================================================================================


@app.get("/api/v1/demo/schemes")
def schemes(
    entity_type: str | None = None, activity: str | None = None,
    sector: str | None = None, turnover_cr: float | None = None,
) -> dict:
    """Schemes matched against a business profile.

    Every entry carries its verdict *and* the reasons behind it, so a business that does
    not qualify learns what would have to change rather than just being turned away.
    """
    matched = eligible(entity_type, activity, sector, turnover_cr)
    return {
        "illustrative": True,
        "filters": {
            "entity_types": ["msme", "large"],
            "activities": ["exporter", "importer", "manufacturer", "trader"],
            "sectors": [s for s in SECTORS if s != "any"],
        },
        "eligible_count": sum(1 for s in matched if s["eligible"]),
        "total": len(SCHEMES),
        "schemes": matched,
    }


@app.get("/api/v1/demo/tariff")
def tariff(q: str | None = None, sector: str | None = None) -> dict:
    """Duty lines, searchable by heading or description."""
    rows = TARIFF
    if sector:
        rows = [t for t in rows if t.sector == sector]
    if q:
        needle = q.lower().strip()
        rows = [
            t for t in rows
            if needle in t.heading.lower() or needle in t.description.lower()
        ]
    return {
        "illustrative": True,
        "rows": [
            {
                "heading": t.heading, "description": t.description,
                "basic_duty_pct": t.basic_duty_pct,
                "effective_from": t.effective_from.isoformat(),
                "sector": t.sector, "note": t.note,
                "source": {"title": t.source_title, "authority": t.source_authority},
            }
            for t in rows
        ],
    }


@app.get("/api/v1/demo/notices")
def notices(authority: str | None = None, sector: str | None = None) -> dict:
    """What changed recently, newest first.

    Each entry says what *changed*, not what the document is called. A feed that repeats
    document titles tells a reader nothing they can act on.
    """
    rows = sorted(NOTICES, key=lambda n: n.issued_on, reverse=True)
    if authority:
        rows = [n for n in rows if n.authority == authority]
    if sector:
        rows = [n for n in rows if sector in n.affects or "any" in n.affects]
    return {
        "illustrative": True,
        "authorities": sorted({n.authority for n in NOTICES}),
        "rows": [
            {
                "reference": n.reference, "authority": n.authority,
                "issued_on": n.issued_on.isoformat(), "subject": n.subject,
                "change": n.change, "kind": n.kind, "affects": n.affects,
                "supersedes": n.supersedes,
            }
            for n in rows
        ],
    }


@app.get("/api/v1/demo/deadlines")
def deadlines() -> dict:
    """Upcoming dates, with what happens if each is missed."""
    today = date.today()
    # Upcoming first, closest first; anything already past goes to the end. A lapsed
    # window still matters — a business needs to know the door has shut — but listing it
    # above live obligations under a heading that says "ahead" is simply wrong.
    rows = sorted(
        DEADLINES,
        key=lambda d: ((d.due_on - today).days < 0, abs((d.due_on - today).days)),
    )
    return {
        "illustrative": True,
        "rows": [
            {
                "label": d.label, "due_on": d.due_on.isoformat(),
                "days_left": (d.due_on - today).days,
                "applies_to": d.applies_to, "consequence": d.consequence,
            }
            for d in rows
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Voice
#
# Speech in through Whisper, speech out through the browser. Voice is not decoration
# here: the PRD's own personas include business owners with variable digital literacy who
# are more fluent speaking than typing, and typing a question in Devanagari or Tamil on a
# phone is a real barrier to asking at all.
#
# Transcription runs server-side rather than in the browser because browser speech
# recognition is uneven across engines and markedly weaker on Indian languages — and
# because the same data-control exception already declared for generation applies, rather
# than a second, quieter one.
# ══════════════════════════════════════════════════════════════════════════════════════


@app.post("/api/v1/demo/transcribe")
async def transcribe(
    audio: UploadFile = File(...), language: str = "eng"
) -> dict:
    """Turn a recorded clip into text.

    The language hint matters: Whisper will otherwise guess, and it guesses badly on a
    short Hindi clip that contains English trade terms — which is most of them.
    """
    if not settings.groq_api_key:
        raise HTTPException(
            503,
            "Speech input needs a transcription service. Type the question instead — "
            "the desk answers identically either way.",
        )

    payload = await audio.read()
    if len(payload) < 1200:
        # Well under a second of audio. Reporting this plainly beats returning an empty
        # transcript that looks like the desk misheard.
        raise HTTPException(422, "That recording was too short to make out.")

    # Bhashini first, when it is configured and covers the language. It is the
    # ministry's own stack, it reaches all twenty-two scheduled languages rather than
    # the six a foreign model serves well, and speech is the input least appropriate
    # to send abroad. Whisper remains the fallback so the desk still hears somebody
    # who is using an installation with no Bhashini key.
    if bhashini.available and bhashini.supports(language):
        try:
            text = await bhashini.transcribe(
                payload, language,
                audio_format=(audio.content_type or "audio/webm").split("/")[-1],
            )
            if text.strip():
                log.info("transcribe.bhashini", language=language)
                return {"text": text.strip(), "language": language,
                        "engine": "bhashini"}
        except (BhashiniUnavailable, httpx.HTTPError) as exc:
            # A degradation, not a failure: the question can still be transcribed.
            log.warning("transcribe.bhashini_failed", error=str(exc))

    whisper_lang = {"eng": "en", "hin": "hi", "ben": "bn",
                    "tam": "ta", "tel": "te", "mar": "mr"}.get(language, "en")

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "User-Agent": "scc-knowledge-platform/0.1",
            },
            files={"file": ("speech.webm", payload, audio.content_type or "audio/webm")},
            data={
                "model": "whisper-large-v3-turbo",
                "language": whisper_lang,
                "response_format": "json",
                # Priming the decoder with domain vocabulary: without it "IEC" comes back
                # as "I E C" or "easy", and "RoDTEP" as almost anything.
                "prompt": (
                    "Trade helpdesk. Terms: IEC, Udyam, RoDTEP, EPCG, DGFT, CBIC, GST, "
                    "MSME, SCOMET, TReDS, RCMC, LUT, shipping bill, drawback, tariff."
                ),
            },
        )

    if response.status_code == 429:
        raise HTTPException(429, "The transcription service is busy. Try again shortly, "
                                 "or type the question.")
    response.raise_for_status()
    text = response.json().get("text", "").strip()
    if not text:
        raise HTTPException(422, "Nothing was audible in that recording.")
    return {"text": text, "language": language, "engine": "whisper"}


@app.get("/api/v1/demo/speech/engines")
def speech_engines() -> dict:
    """What is actually serving speech, and in how many languages.

    Stated rather than implied: a claim to support twenty-two languages that rests on
    an unconfigured key is a claim the interface should not make on the desk's behalf.
    """
    return {
        "bhashini": {
            "configured": bhashini.available,
            "languages": sorted(ISO3_TO_BHASHINI) if bhashini.available else [],
            "count": len(ISO3_TO_BHASHINI) if bhashini.available else 0,
        },
        "whisper": {
            "configured": bool(settings.groq_api_key),
            "languages": ["eng", "hin", "ben", "tam", "tel", "mar"],
            "count": 6,
        },
        "active": "bhashini" if bhashini.available else (
            "whisper" if settings.groq_api_key else "browser"),
    }


class SpeakBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str = "eng"


@app.post("/api/v1/demo/speak")
async def speak(body: SpeakBody) -> Response:
    """Server-side text to speech, for languages the browser cannot voice."""
    if not (bhashini.available and bhashini.supports(body.language)):
        raise HTTPException(
            503,
            "Server-side speech is not configured. The browser's own voice is used "
            "instead, which covers fewer languages.",
        )
    try:
        audio_bytes = await bhashini.speak(body.text, body.language)
    except (BhashiniUnavailable, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Speech synthesis failed: {exc}") from exc
    return Response(content=audio_bytes, media_type="audio/wav")


# ══════════════════════════════════════════════════════════════════════════════════════
# Accounts
# ══════════════════════════════════════════════════════════════════════════════════════


class SignupBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=200)
    business_name: str = Field(default="", max_length=120)


class LoginBody(BaseModel):
    email: str
    password: str


def _me(token: str | None):  # noqa: ANN202
    return accounts.user_for(token)


def _profile(user) -> dict:  # noqa: ANN001
    p = user.preferences
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "business_name": user.business_name,
        "preferences": {
            "ui_language": p.ui_language, "answer_language": p.answer_language,
            "text_scale": p.text_scale, "read_aloud": p.read_aloud,
            "entity_type": p.entity_type, "activity": p.activity,
            "sector": p.sector, "turnover_cr": p.turnover_cr,
        },
        "history_count": len(user.history),
    }


@app.post("/api/v1/demo/auth/signup")
def signup(body: SignupBody, response: Response) -> dict:
    try:
        user = accounts.create(body.name, body.email, body.password, body.business_name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    token = accounts.start_session(user)
    # HttpOnly so the token is never reachable from page scripts, which is what makes
    # "no credential in browser storage" true rather than merely intended.
    response.set_cookie("scc_session", token, httponly=True, samesite="lax", max_age=604800)
    workspace.write_audit("account_created", user.email, "user", str(user.id))
    return _profile(user)


@app.post("/api/v1/demo/auth/login")
def login(body: LoginBody, response: Response) -> dict:
    user = accounts.authenticate(body.email, body.password)
    if user is None:
        # One message for both causes: saying which of the two was wrong tells an
        # attacker whether an address is registered.
        raise HTTPException(401, "That email address and password do not match.")
    token = accounts.start_session(user)
    response.set_cookie("scc_session", token, httponly=True, samesite="lax", max_age=604800)
    return _profile(user)


@app.post("/api/v1/demo/auth/logout")
def logout(response: Response, scc_session: str | None = Cookie(default=None)) -> dict:
    accounts.end_session(scc_session or "")
    response.delete_cookie("scc_session")
    return {"signed_out": True}


@app.get("/api/v1/demo/auth/me")
def whoami(scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    return _profile(user) if user else {"id": None}


class PrefsBody(BaseModel):
    ui_language: str | None = None
    answer_language: str | None = None
    text_scale: float | None = None
    read_aloud: bool | None = None
    entity_type: str | None = None
    activity: str | None = None
    sector: str | None = None
    turnover_cr: float | None = None


@app.put("/api/v1/demo/me/preferences")
def save_prefs(body: PrefsBody, scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    if not user:
        raise HTTPException(401, "Sign in to save your preferences.")
    accounts.save_preferences(user, body.model_dump(exclude_none=True))
    return _profile(user)


# --- grievances ---------------------------------------------------------------------
# A question the desk cannot settle becomes a tracked item rather than a dead end. The
# reference is the person's receipt: it works without an account, because requiring one
# to complain would exclude exactly the people most likely to need to.

class GrievanceBody(BaseModel):
    subject: str
    detail: str
    category: str = "general"
    contact: str = ""
    language: str = "eng"


@app.post("/api/v1/demo/grievances")
def lodge_grievance(body: GrievanceBody,
                    scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    try:
        return grievances.lodge(
            body.subject, body.detail, category=body.category,
            user_id=user.id if user else None, contact=body.contact,
            language=body.language,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/v1/demo/grievances/{reference}")
def track_grievance(reference: str) -> dict:
    found = grievances.track(reference)
    if found is None:
        raise HTTPException(404, "No grievance with that reference.")
    return found.as_dict()


class GrievanceStatusBody(BaseModel):
    status: str
    note: str = ""


@app.post("/api/v1/demo/grievances/{reference}/status")
def set_grievance_status(reference: str, body: GrievanceStatusBody) -> dict:
    try:
        updated = grievances.update_status(reference, body.status, body.note)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if updated is None:
        raise HTTPException(404, "No grievance with that reference.")
    return updated


@app.get("/api/v1/demo/grievances")
def grievance_queue() -> dict:
    return {"queue": grievances.queue(), "summary": grievances.summary()}


@app.get("/api/v1/demo/me/grievances")
def my_grievances(scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    if not user:
        raise HTTPException(401, "Sign in to see the grievances you have lodged.")
    return {"grievances": grievances.for_user(user.id)}


# --- business verification and open data ---------------------------------------------

class VerifyBody(BaseModel):
    udyam: str = ""
    gstin: str = ""


@app.post("/api/v1/demo/verify")
async def verify_business(body: VerifyBody) -> dict:
    """Check a Udyam or GST registration against the registry that issued it.

    A number that cannot be checked is reported as unchecked, never as invalid: a
    registry outage is not evidence about the business behind the number.
    """
    out: dict = {}
    if body.udyam.strip():
        out["udyam"] = (await verifier.verify_udyam(body.udyam)).as_dict()
    if body.gstin.strip():
        out["gstin"] = (await verifier.verify_gstin(body.gstin)).as_dict()
    if not out:
        raise HTTPException(422, "Give a Udyam number or a GSTIN to check.")

    verified = [v for v in out.values() if v["trusted"]]
    out["registry_connected"] = verifier.available
    out["classification"] = next(
        (v["classification"] for v in verified if v.get("classification")), None
    )
    out["basis"] = "registry" if out["classification"] else "self_declared"
    return out


@app.get("/api/v1/demo/opendata/catalogue")
def opendata_catalogue() -> dict:
    """What could be ingested, and whether ingestion is actually configured."""
    return {
        "configured": opendata.available,
        "datasets": [
            {"key": k, "title": v["title"], "authority": v["authority"],
             "topic": v["topic"]}
            for k, v in CATALOGUE.items()
        ],
        "note": ("Ingested records enter the corpus at pending_review and cannot be "
                 "cited until a curator approves them."),
    }


@app.get("/api/v1/demo/me/dashboard")
def my_dashboard(scc_session: str | None = Cookie(default=None)) -> dict:
    user = _me(scc_session)
    if not user:
        raise HTTPException(401, "Sign in to see your questions.")
    return accounts.dashboard(user)


class ResolveBody(BaseModel):
    id: int


@app.post("/api/v1/demo/me/resolved")
def mark_resolved(body: ResolveBody, scc_session: str | None = Cookie(default=None)) -> dict:
    """Let a person say whether an answer actually settled their question.

    The site-wide figures measure whether the desk *produced* an answer; only the person
    who asked knows whether it helped, and that is the number worth having.
    """
    user = _me(scc_session)
    if not user:
        raise HTTPException(401, "Sign in first.")
    # Addressed by row id rather than by position in a list: a position shifts as soon as
    # another question is asked, so the wrong entry would be marked.
    if not accounts.mark_resolved(user, body.id):
        raise HTTPException(404, "No such question.")
    return accounts.dashboard(user)


# ══════════════════════════════════════════════════════════════════════════════════════
# Attachments — ask about your own document
# ══════════════════════════════════════════════════════════════════════════════════════


@app.post("/api/v1/demo/attach")
async def attach(
    conversation: str = Form(default="bot"), file: UploadFile = File(...)
) -> dict:
    payload = await file.read()
    try:
        parsed = extract(file.filename or "file", file.content_type or "", payload)
    except ExtractionFailed as exc:
        raise HTTPException(422, str(exc)) from exc

    passages = as_passages(parsed)
    attachments[conversation] = [
        {"name": parsed.name, "body": p} for p in passages
    ]
    return {
        "name": parsed.name, "passages": len(passages), "pages": parsed.pages,
        "chars": len(parsed.text),
        "note": "Held for this conversation only. It is not added to the knowledge base — "
                "an uploaded document is not an approved record.",
    }


@app.delete("/api/v1/demo/attach")
def detach(conversation: str = "bot") -> dict:
    attachments.pop(conversation, None)
    return {"cleared": True}


# ══════════════════════════════════════════════════════════════════════════════════════
# Learning — what the desk could not answer, and what it did about it
# ══════════════════════════════════════════════════════════════════════════════════════


@app.get("/api/v1/demo/learning")
def learning_log() -> dict:
    return {
        "summary": learning.summary(),
        "entries": [
            {
                "query": e.query, "language": e.language, "cause": e.cause,
                "status": e.status, "times_asked": e.times_asked,
                "drafted_title": e.drafted_title, "decline_reason": e.decline_reason,
                "at": e.at.strftime("%d %b %H:%M"),
            }
            for e in sorted(learning.entries, key=lambda e: (-e.times_asked, e.at))
        ],
    }


class DraftBody(BaseModel):
    query: str


@app.post("/api/v1/demo/learning/draft")
async def draft_knowledge(body: DraftBody) -> dict:
    """Draft a record for a question the corpus could not answer.

    The drafted record is answerable immediately, which is the point — the same question
    is settled next time it is asked. It carries a machine-drafted authority line so a
    reader can see the provenance differs from a published circular, and a knowledge
    manager can verify or replace it.
    """
    entry = learning._find(body.query)
    if entry is None:
        raise HTTPException(404, "That question is not in the log.")

    record = await learning.draft(entry)
    if record is None:
        return {"drafted": False, "reason": entry.decline_reason}

    item_id = store.add(DemoItem(
        id=uuid4(), title=record["title"], authority=record["authority"],
        issued_on=date.today(), language=record["language"], status="approved",
        passages=record["passages"], topic=record["topic"],
    ))
    generation.bump()
    workspace.write_audit("knowledge_auto_drafted", "system", "knowledge_item",
                          str(item_id), title=record["title"], from_query=body.query)
    return {"drafted": True, "title": record["title"], "id": str(item_id)}


_UI = Path(__file__).parent / "ui.html"


@app.get("/")
def ui() -> FileResponse:
    return FileResponse(_UI)
