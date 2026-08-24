---
title: "Backend LLD — Interface Amendments (Stage 5c resolutions)"
stage: 5a
subStage: 5a
skill: backend-lld-architect
scope: fullstack
version: "1.0"
pass: "amendment — resolves lld.md D-1 through D-10"
inputs: lld.md v1.0 (consistency pass), lld-backend.md passes 1-3, lld-frontend.md v1.0
---

# Backend LLD — Interface Amendments

Resolves every discrepancy raised by the Stage 5c consistency pass. Each section states which finding it closes. Nothing here changes a domain rule; these are the interface details that fell between passes.

## A. Answer delivery protocol (D-1)

**Decision: asynchronous, correlated by `answer_id` on the existing conversation channel.** The synchronous shape in pass 2 §4.1 is withdrawn.

Rationale: pass 1 §4.6 allocates 700 ms to first token and 2,500 ms to completion. Those two numbers are only distinguishable if tokens are delivered as produced. A synchronous response collapses them into one 4,300 ms wait, which discards the frontend's provisional-region design and the perceived-latency argument the whole design rests on.

### A.1 Amended request

```
POST /api/v1/public/conversations/{id}/ask      → 202 Accepted
POST /api/v1/conversations/{id}/assist          → 202 Accepted
```

```python
class AskAcceptedResponse(BaseModel):
    answer_id: UUID          # correlates every subsequent event on the SSE channel
    conversation_id: UUID
    accepted_at: datetime
```

The client already holds the SSE channel open (`GET .../stream`); it does not open one per answer. `answer_id` is the correlation key on every event below.

### A.2 Why 202 rather than a streaming response body

A streaming HTTP body would tie the answer's lifetime to one request, so a customer whose connection blips mid-answer loses it entirely. Events on a persistent channel survive reconnection with `Last-Event-ID`, which is what the frontend's edge case "SSE drops mid-stream" (§23) already assumes. This also keeps queue-position and assignment events on the same channel rather than inventing a second transport.

### A.3 Failure before acceptance

Gate rejections happen **before** 202: coverage-closed and fair-use are returned synchronously from the POST, because there is nothing to stream. Their shape is in §E.

## B. SSE event schemas (D-2)

**All events below are added to the OpenAPI schema** so `openapi-typescript` generates them, which is what makes the frontend's stated mitigation for silent contract drift actually work.

Every event carries `event:` (name), `id:` (monotonic, used for `Last-Event-ID`) and a JSON `data:` payload.

### B.1 Conversation channel — `GET /api/v1/public/conversations/{id}/stream`

| Event | Payload | Notes |
|---|---|---|
| `answer.token` | `{answer_id, seq, text}` | Incremental generated text. **Provisional by contract** — the client must not treat these as final |
| `answer.grounding` | `{answer_id, grounded, coverage}` | The verdict the frontend's invariant keys on. Emitted exactly once per answer that reached generation |
| `answer.final` | `{answer_id, answer: AnswerResponse}` | Terminal. Carries the complete, verified answer including citations. **Always emitted**, including when grounding failed and the extractive fallback took over |
| `answer.error` | `{answer_id, code, detail}` | Terminal. Model unavailable, timeout past all fallbacks |
| `conversation.state` | `{conversation_id, state}` | State machine transitions (pass 2 §2.2) |
| `queue.position` | `{conversation_id, position, estimated_wait_seconds, wait_threshold_exceeded}` | While queued |
| `conversation.assigned` | `{conversation_id, agent_display_name, language_matched}` | Handover completed |

**The contract that matters:** `answer.final` is authoritative and always arrives on a terminal path. A client that received `answer.token` events and never receives `answer.final` or `answer.error` must discard the draft — which is exactly the frontend's `verifying` timeout edge case, now backed by a stated server obligation rather than an assumption.

`answer.grounding` with `grounded: false` is **not** an error and is never followed by an absent `answer.final`; the fallback answer follows it.

### B.2 Agent channel — `GET /api/v1/agents/me/stream`

| Event | Payload |
|---|---|
| `assignment.offered` | `{conversation_id, language, wait_seconds, language_matched}` |
| `assignment.revoked` | `{conversation_id, reason}` — released by expiry or supervisor |
| `knowledge.retired_source` | `{conversation_id, item_id, item_title}` — BR-12 |
| `presence.expired` | `{}` — the server stopped believing the heartbeat |

### B.3 Reconnection

`Last-Event-ID` replays **state, not backlog**: on reconnect the server emits the current `conversation.state`, the current `queue.position` if queued, and `answer.final` for any answer that completed while disconnected. Token events are never replayed — a partial draft has no value after the final answer exists, and replaying it would reopen the very window the provisional-region design closes.

## C. Authentication endpoints (D-3)

The gap between passes. Authentication, as distinct from the authorisation covered in pass 3.

| Verb & path | Purpose | Auth |
|---|---|---|
| `POST /api/v1/auth/sign-in` | Exchange identity-provider credentials for tokens | none |
| `POST /api/v1/auth/refresh` | Rotate the access token | Refresh cookie |
| `POST /api/v1/auth/sign-out` | Revoke the session | Bearer |
| `GET /api/v1/auth/me` | Current user, roles, permissions, working languages | Bearer |

```python
class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_token: str            # identity-provider assertion; this service is not an IdP

class TokenResponse(BaseModel):
    access_token: str
    expires_in: int                # seconds; 900 (15 min)
    token_type: Literal["Bearer"]
    # The refresh token is NOT in this body. It is set as an HttpOnly, Secure,
    # SameSite=Strict cookie scoped to the API origin — which is what makes the
    # frontend's "no token in localStorage" rule (§21) achievable rather than aspirational.

class MeResponse(BaseModel):
    user_id: int
    display_name: str
    roles: list[str]
    permissions: list[str]         # resolved union, so the client need not replicate §4.3
    primary_language: Lang
    working_languages: list[Lang]
    enabled_languages: list[Lang]  # saves a second round trip on startup
```

**Refresh semantics.** Refresh rotates: the old refresh token is revoked as the new one is issued. A replayed refresh token is treated as theft — the whole session family is revoked and the event is audited. This is stricter than necessary for an internal console and appropriate for one holding customer conversations.

**Revocation.** `sign-out`, role revocation and deactivation (pass 3) all add the session to the Redis revocation list checked per request, so the frontend's single-refresh-then-sign-out rule terminates rather than looping.

## D. Language code mapping (D-4)

**Decision: the API is ISO 639-3 everywhere, and the mapping to BCP-47 lives on the client, in one place.** The API is not changed, because 639-3 is correct for stored linguistic data and the database is full of it.

Canonical table, stated here so both sides implement the same one:

| ISO 639-3 (API) | BCP-47 (`lang` attribute, CSS) | Script | Language |
|---|---|---|---|
| `eng` | `en` | Latin | English |
| `hin` | `hi` | Devanagari | Hindi |
| `ben` | `bn` | Bengali | Bengali |
| `tam` | `ta` | Tamil | Tamil |
| `tel` | `te` | Telugu | Telugu |
| `mar` | `mr` | Devanagari | Marathi |

`GET /api/v1/languages` returns this table (code, bcp47, script, display name in the requester's language, enabled flag), so the mapping is served rather than hard-coded twice. Hindi and Marathi sharing Devanagari is why the type-scale tokens key on **script**, not language — a detail the frontend LLD's §19 selectors got right by accident and now get right by contract.

## E. Fair-use rejection shape (D-5)

The `429` mapping in pass 1 §4.5 is **withdrawn**. Fair-use rejection returns:

```
POST .../ask → 200 OK
{ "outcome": "blocked_fair_use", "retry_after_seconds": 1800,
  "handover_offered": true, "citations": [], "answer_text": null }
```

Same for `blocked_coverage`. REQ-023 requires that limiting never removes the path to a human; expressing that as an error status would put the frontend's `not-an-error` rule into an exception it does not have, and an exception in that rule is how "I don't know" starts looking like "broken".

Note this is one of the few places where the correct HTTP status is not the conventional one. The reasoning is product-level and is recorded here so a later reviewer does not "fix" it.

## F. Taxonomy endpoints (D-6)

| Verb & path | Purpose | Authorisation |
|---|---|---|
| `GET /api/v1/taxonomy` | Sectors and topics with ids, codes, display names, `is_must_have` | any `knowledge.read` |
| `POST /api/v1/admin/taxonomy/sectors` | Create a sector | administrator |
| `POST /api/v1/admin/taxonomy/topics` | Create a topic | administrator |
| `PATCH /api/v1/admin/taxonomy/topics/{id}` | Rename display name; `code` is immutable | administrator |
| `POST /api/v1/admin/taxonomy/topics/{id}/deactivate` | Deactivate | administrator |

```python
class TaxonomyResponse(BaseModel):
    sectors: list["SectorView"]

class SectorView(BaseModel):
    id: int
    code: str                      # immutable
    display_name: str
    topics: list["TopicView"]

class TopicView(BaseModel):
    id: int
    code: str
    display_name: str
    is_must_have: bool             # drives the REQ-023 coverage floor
    is_active: bool
```

The rename endpoint touches `display_name` only; `code` is immutable by contract, which is the mechanism behind REQ-003's guarantee that a rename preserves every existing classification (pass 1 §2.3).

## G. Language enablement endpoints (D-7)

REQ-001's per-language gate — the resolution of a Stage 2 critical finding — had no API surface at all.

| Verb & path | Purpose | Authorisation |
|---|---|---|
| `GET /api/v1/languages` | All six with enabled state, script, BCP-47 (see §D) | public + authenticated |
| `PUT /api/v1/admin/languages/{code}` | Enable or disable | administrator |

```python
class LanguageEnablementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    acceptance_score: Decimal | None = None   # required when enabling
    acceptance_run_id: str | None = None      # which acceptance-set run produced it

class LanguageView(BaseModel):
    code: Lang
    bcp47: str
    script: Literal["latin","devanagari","bengali","tamil","telugu"]
    display_name: str
    enabled: bool
    acceptance_score: Decimal | None
    enabled_at: datetime | None
```

**Enabling requires an acceptance score.** A language cannot be switched on without stating what it scored, because REQ-001's gate is "enable only once it clears the bar" — and an enablement with no recorded score is indistinguishable from ignoring the gate. The server rejects `enabled: true` with a null score, and rejects a score below the correctness bar unless an administrator supplies an explicit override reason, which is audited.

`GET /api/v1/languages` is public because the assistant must show its supported set before anyone signs in.

## H. Public coverage status (D-8)

`StartConversationResponse` (pass 2 §4.2) gains two fields:

```python
class StartConversationResponse(BaseModel):
    conversation_id: UUID
    conversation_token: str
    detected_language: Lang | None
    supported_languages: list[Lang]
    self_serve_open: bool                 # NEW — coverage floor declared?
    closed_notice: str | None             # NEW — what to tell the customer, localised
```

When `self_serve_open` is false the client renders the notice and routes straight to handover, **before** the composer is shown. Making the customer type a question only to learn the surface is closed is the "wall of I don't know" REQ-023 exists to prevent, and discovering it after the fact is the same failure with an extra step.

## I. Correlation header (D-9)

Added to pass 1 §4.1's conventions: the API accepts `X-Correlation-Id` on every request, propagates it through retrieval, rerank and generation logs, echoes it in every `problem+json` response as an extension member, and generates one when absent. The frontend's fatal-error boundary shows it to the user, so it must be present on error responses specifically, not only on success paths.

## J. Deletion request DTO (D-10)

**Decision: erasure is initiated by conversation reference, not by contact detail.**

```python
class DeletionRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: UUID          # any one conversation the customer identifies
    requester_note: str = Field(min_length=5, max_length=1000)

class DeletionRequestView(BaseModel):
    id: UUID
    scope_conversation_count: int  # how many conversations share the resolved customer key
    executed_at: datetime | None
    conversations_removed: int | None
    gap_entries_removed: int | None
    items_retained: int | None
```

The server resolves the conversation to its `customer_key_hash` and erases every conversation sharing it. Rationale for choosing conversation id over contact detail: matching on a contact detail means matching personal data against personal data across the corpus, which is a search that could erase a *different* customer's records on a near-match — the failure mode is silent and unrecoverable. A conversation reference is exact, and the response reports the resolved scope **before** execution so an administrator sees how many conversations they are about to erase.

The known limitation, stated rather than hidden: this erases only conversations linked by the pseudonymous browser key (pass 3 §2.3). A customer who used two devices must supply a conversation reference from each. The `scope_conversation_count` field is what makes that visible instead of surprising.

## K. Summary

| Finding | Resolution | Where |
|---|---|---|
| D-1 | 202 + `answer_id`, events on the existing channel | §A |
| D-2 | 11 event schemas, in the OpenAPI spec | §B |
| D-3 | Four auth endpoints, rotating refresh, revocation | §C |
| D-4 | API stays 639-3; served mapping table; tokens key on script | §D |
| D-5 | 429 withdrawn; 200 with outcome | §E |
| D-6 | Taxonomy read + admin rename, `code` immutable | §F |
| D-7 | Enablement endpoints; enabling requires an acceptance score | §G |
| D-8 | `self_serve_open` on conversation start | §H |
| D-9 | Header accepted, propagated, echoed on errors | §I |
| D-10 | Erasure by conversation reference, scope reported before execution | §J |

---

# L. Manifest (resolves lld-review.md P0-1)

Every module in `hld-backend.md` §5, with its coverage decision. This is the completeness baseline for the whole backend LLD set.

| Module (HLD §5) | Decision | Covered in | Notes / exclusion reason |
|---|---|---|---|
| Answer service | Included | Pass 1 §6.1 | |
| Retrieval service | Included | Pass 1 §6.3, §3 | |
| Rerank service | Included | Pass 1 §3, §4.6 | |
| Generation service (+ extractive strategy) | Included | Pass 1 §3.1, §6.1 | |
| Grounding verifier | Included | Pass 1 §6.1 step 9 | |
| Conflict detector | Included | Pass 1 §6.1 step 6 | |
| Answer cache | Included | Pass 1 §7.3, §M below | |
| Knowledge service / lifecycle | Included | Pass 1 §6.2 | |
| Ingestion orchestrator + 6 stage handlers | Included | Pass 1 §6.4, §7.4 | |
| Classification job | Included | Pass 1 §2.3, §3 | |
| Coverage & fair-use gate | Included | Pass 1 §6.5 | |
| Conversation service | Included | Pass 2 §6.1 | |
| Agent assist service | Included | Pass 2 §6.4 | |
| Handover service | Included | Pass 2 §6.3 | |
| Assignment engine | Included | Pass 2 §6.2 | Boundary ratified by the HLD amendment in §N |
| Presence service | Included | Pass 2 §6.5 | As above |
| Inactivity sweeper | Included | Pass 2 §6.5 | |
| Gap & feedback service | Included | Pass 3 §6.1, §6.2 | |
| Analytics service + rollup job | Included | Pass 3 §6.3, §6.4, §O | |
| Authorisation service | Included | Pass 3 §6.7 | |
| User admin service | Included | Pass 3 §2.2, §4.1 | |
| Audit writer | Included | Pass 3 §6.8, guardrail G1 | |
| Masker / PII detector | Included | Pass 3 §6.5 | |
| Privacy service | Included | Pass 3 §6.6 | |
| Authentication service | Included | §C above | The gap the consistency pass found |
| SSE channel service | Included | §B above | |
| Taxonomy service | Included | §F above | |
| Language enablement service | Included | §G above | |
| Model runtime clients (embed, rerank, generate, OCR, PII) | **Excluded** | — | Vendor client wrappers over documented model-server APIs; no domain logic. Their *contracts* are specified where used (timeouts §4.6, strategies §3.1). Designing their internals would be specifying someone else's HTTP client |
| Object storage client | **Excluded** | — | Thin S3-compatible wrapper; the access pattern (write once, read for display) is stated in pass 1 §2.3 and carries no design decision |
| Portal crawler | **Excluded** | — | REQ-017, Phase 2. Out of MVP scope per requirements.md |
| Ticket-history miner | **Excluded** | — | REQ-016, Phase 2 |
| Cross-language comparison | **Excluded** | — | REQ-018, Phase 2 |
| Bulk import / re-classification | **Excluded** | — | REQ-019, Phase 2 |

## M. Cache behaviour when PostgreSQL is unavailable (P1-1)

The degradation `hld-backend.md` §21 requires, now stated as mechanism:

```
cache.get(key, lang):
    gen = generation_counter.current()      # reads PostgreSQL
    if gen is unavailable:
        return MISS                          # bypass, do not serve
    return redis.get(compose(key, lang, gen))
```

Because the generation counter lives in PostgreSQL, a database outage makes every cache lookup a miss, the request then fails on retrieval, and **no cached answer is served against an unverifiable knowledge state** — which is what §21 required and what the previous text left to chance. Guardrail G3 states this project-wide. Added to the failure table:

| Failure | Behaviour |
|---|---|
| PostgreSQL unavailable, Redis healthy | Every cache lookup returns MISS; requests fail with `503`; no stale answers served |

Test (added to pass 1 §8.3): with the database unavailable, a query whose answer is present in Redis returns `503`, not the cached answer.

## N. HLD amendment — presence, queue and assignment (P0-2, P1-4)

Ratifying at the architecture layer what pass 2 designed. To be merged into `hld-backend.md` as §5.1.

- **Placement:** in-process with the FastAPI application, not a separate service. The dequeue is a single `SKIP LOCKED` statement and the assignment transaction is short; a separate service would add a network hop and a second failure domain for work that is already database-mediated.
- **Restart behaviour:** all state is in PostgreSQL and Redis. On restart, queued conversations remain queued, assignments remain assigned, and heartbeat expiry reclaims any agent whose console did not reconnect. **No in-memory state is lost because none is held** — this is the property that makes in-process placement safe.
- **Presence is advisory; open assignments are authoritative** (pass 2 §7.2). Ratified explicitly: the fast path is the one that can be wrong, and hourly reconciliation repairs drift. The alternative — making presence authoritative — would require distributed coordination for a fast path that is only an optimisation.
- **Scaling trigger** (extends `hld-backend.md` §26): if assignment latency becomes visible at the queue, or if agent count passes ~200, move the assignment worker to its own process before splitting anything else. The `SKIP LOCKED` design already permits multiple workers.
- **Failure mode:** if the assignment worker stops, conversations queue and nothing is lost; the supervisor escalation view is the operational signal, and queue depth is the alert (§P).

## O. Scheduled jobs — complete specification (P1-3, guardrail G12)

Every job declares trigger, idempotency, failure behaviour, and its stop-alert.

| Job | Trigger | Idempotency | On failure | Alerts if it stops |
|---|---|---|---|---|
| Staleness sweep | Daily 01:00 | Conditional bulk update on `review_due_on`; re-running the same day changes nothing | Retry next cycle; no partial state | No successful run in 36 h |
| Gap clustering | Hourly | Operates only on `group_id IS NULL`; re-run adds nothing | Retry next cycle; entries accumulate harmlessly | Unclustered entries older than 6 h |
| Analytics rollup | Hourly for today, nightly recompute for yesterday | `INSERT ... ON CONFLICT DO UPDATE` full recompute, never increment | Retry; the day stays absent from `analytics_gap_day` and is reported as a missing interval rather than silently zero | Any day older than 48 h absent from `analytics_gap_day` |
| Inactivity sweep | Every 5 min | Transitions only non-terminal conversations past the boundary; terminal rows are untouched | Retry next cycle | No run in 30 min |
| Presence expiry | Every 30 s | Idempotent per agent; expiring an already-offline agent is a no-op | Retry next cycle | No run in 5 min |
| Presence/assignment reconciliation | Hourly | Compares and repairs; repairing a consistent pair is a no-op | Retry next cycle | No run in 3 h |
| Masking verification sample | Weekly, Monday 09:00 | Draws a new sample per run; a missed week is a gap in evidence, not corrupt data | Alert immediately — this is compliance evidence, not housekeeping | No `masking_check` row in 14 days |
| Retention enforcement | Daily 02:00 | Partition drops are idempotent — dropping an already-dropped partition is a no-op | **Alert, do not retry blindly.** A retention failure is a compliance issue and a retry loop against a locked partition makes it worse | No successful run in 48 h |

Retention runs as the maintenance role (guardrail G1), which is why it is a separately-credentialed job rather than part of the worker.

## P. Observability instrumentation (P1-2, guardrail G11)

Stage names match `lld-backend.md` §4.6 exactly, so budget and measurement cannot drift.

| Metric | Type | Labels |
|---|---|---|
| `answer_stage_duration_seconds` | Histogram | `stage` ∈ {detect, embed, retrieve, rerank, conflict, generate_first_token, generate_complete, ground, persist}, `surface` |
| `answer_outcome_total` | Counter | `outcome`, `language`, `surface` |
| `answer_confidence` | Histogram | `outcome` |
| `cache_lookup_total` | Counter | `result` ∈ {hit, miss, bypassed} |
| `ingestion_stage_duration_seconds` | Histogram | `stage` |
| `ingestion_job_total` | Counter | `outcome` ∈ {complete, retried, dead_lettered} |
| `queue_depth` | Gauge | `language` |
| `queue_wait_seconds` | Histogram | `language_matched` |
| `assignment_total` | Counter | `result` ∈ {assigned, escalated, no_candidate} |
| `presence_available_agents` | Gauge | `language` |
| `scheduled_job_last_success_timestamp` | Gauge | `job` — the metric behind every stop-alert in §O |
| `masking_withheld_total` | Counter | `call_site` |
| `access_refused_total` | Counter | `permission` |

**Alerts** (resolving `hld-review.md` Medium-9): no-answer rate above 40% over 1 h; wrong-answer rate rising while assist adoption rises; model server unavailable > 2 min; queue depth above 50 or wait above the published threshold; any `scheduled_job_last_success_timestamp` past its §O bound; masking check overdue.

## Q. Configuration tiers (P1-5, guardrail G6)

Promoted out of code constants:

**Tier 1 — threshold table, audited change endpoint:**
`answer_bar` 0.70 · `classification_bar` 0.60 · `low_volume_threshold` 100 · `gap_group_size` 5 · `masking_min_confidence` 0.85 · `inactivity_boundary_minutes` 15 · `fair_use_per_hour` 30

Every one of these gates a stated requirement, which is the test for tier 1 membership.

**Tier 2 — configuration file, deployment change:**
`ingestion_max_attempts` per stage (extract 3, ocr 2, embed 5, classify 3) · `queue_max_attempts` 5 · `heartbeat_ttl_seconds` 60 · `heartbeat_interval_seconds` 20 · `gap_similarity_threshold` 0.85 · `analytics_max_period_days` 366 · `answer_cache_ttl_seconds` 3600 · `circuit_breaker_failure_threshold` 5 · `circuit_breaker_half_open_seconds` 30

## R. Circuit breaker on model clients (P2-1)

Wraps the generation and rerank clients, using the Strategy seam already present:

- **Closed → open:** 5 consecutive timeouts or connection failures.
- **Open:** fail fast to the extractive strategy without waiting for a timeout. This is the point — a dead model server currently costs every request its full 2-second first-token timeout, 13 times a second at peak.
- **Open → half-open:** after 30 s, one probe request. Success closes; failure re-opens.
- **Never breaks the citation guarantee:** the open state routes to extractive answering, which is still retrieval-grounded and still bar-checked. It degrades prose quality, never provenance (guardrail G4).

Metric `circuit_breaker_state` gauge, labelled by client; an open breaker is an alert.

## S. Deployment and migration (P1-6, guardrail G13)

- **Migration style:** expand/contract. The two large-table changes named by the review are handled explicitly: `customer_key_hash` is added nullable with no backfill (it applies to new conversations only, and the guardrail's lower-bound caveat already accounts for its absence on older rows); `answer_record` partitioning is created for future months only, with historical rows left in the original table until it ages past retention.
- **Deployment order:** migrate (expand) → deploy workers → deploy API → deploy frontend bundles. The frontend is last because it is the only component that can be rolled back instantly and independently.
- **Restarts:** API and worker restarts are rolling and take seconds. **The model server is not rolling** — it holds several gigabytes and takes minutes to load. Model-server restarts happen outside published support hours, or behind a second instance if the 99.5% target tightens. Stated because a naive restart during support hours is a multi-minute outage that the availability target would notice.
- **Rollback:** application rollback is a redeploy of the previous image. Schema rollback is forward-only for contractions; expansions are safe to leave in place, which is the reason for choosing expand/contract on a single-VM deployment where a restore is hours (`hld-backend.md` §23).
