---
title: "LLD Consistency Pass — Backend ↔ Frontend"
stage: 5c
subStage: 5c
skill: none — orchestrator cross-check
scope: fullstack
version: "1.0"
inputs: lld-backend.md, lld-backend-pass2.md, lld-backend-pass3.md, lld-frontend.md
---

# Stage 5c — LLD Consistency Pass

Not a regeneration of either document, and not an excuse to shorten either. This pass cross-checks the backend LLD's API specifications against the frontend LLD's API contracts and reports agreements and discrepancies. Nine discrepancies were found; four are blocking for Stage 7 planning because an engineer cannot implement either side without a decision.

## 1. Verdict

**Not yet consistent.** The two documents agree on every domain rule that matters — citation requirements, outcome sets, concurrency conventions, error semantics — which is the harder half. They disagree on **how an answer is actually delivered**, which is the most-used path in the product, and the frontend depends on **five endpoints and one event schema that the backend LLD never defines**. None of these require redesign; all require a decision recorded in one document or the other before Stage 7.

## 2. Agreements — verified, no action

| Concern | Backend | Frontend | Status |
|---|---|---|---|
| Citation completeness | `Citation` DTO carries passage, title, authority, date, language, `review_pending` | `CitationView` maps all six; `answered` requires a non-empty citation tuple by type | **Agree**, and the frontend strengthens it |
| Answer outcome set | `answer_outcome` enum: answered, no_answer, conflict, blocked_coverage, blocked_fair_use | `AnswerView` discriminated union, same five members | **Agree** |
| No-answer is not an error | 200 with `outcome: "no_answer"` (pass 1 §4.5) | `not-an-error` error category, never error styling (§15) | **Agree** — the most important shared decision in both documents |
| Conversation outcomes | Four terminal states (pass 2 §2.2) | `ConversationState` union, same nine members | **Agree** |
| Optimistic concurrency | `If-Match` + version, 409 with both versions | Sends version from last read; 409 → re-read → user choice, never auto-merge | **Agree** |
| Idempotency | `Idempotency-Key` on non-GET knowledge/ingestion | Generated per user-initiated mutation, reused verbatim on retry | **Agree**, and the frontend's "never regenerated on automatic retry" rule is the correct reading |
| Pagination | Keyset cursor only | Client never constructs offsets | **Agree** |
| Error branching | RFC 9457 `problem+json` with a domain `code` | Branches on `code`, never status alone, never `detail` | **Agree** |
| Assist degradation | `SuggestionSet(assist_available=False)` at 200 | Inline notice, conversation stays usable | **Agree** |
| Metric honesty | `MetricValue` with numerator, denominator, `low_volume`, `caveat` | `MetricView` maps all four; `GuardrailTile` cannot render a value without its caveat | **Agree**, frontend strengthens |
| Role enforcement | Server-side per endpoint, refusals recorded | Route guards documented as UX only | **Agree** |
| Language enablement | Enabled set gates answering | `useEnabledLanguages`; disabled language never appears in the switcher | **Agree** |
| Retirement propagation | Generation counter, immediate on next query | Query-key invalidation across open views | **Agree** — complementary halves of BR-8 |

## 3. Discrepancies

### D-1 — Answer delivery: request/response vs. streaming. **BLOCKING**

- **Backend** (pass 2 §4.1): `POST /public/conversations/{id}/ask` returns `AskResponse` containing a complete `AnswerResponse`. A separate `GET /public/conversations/{id}/stream` carries "streamed answer tokens, queue position, assignment".
- **Frontend** (§12): the sequence shows `POST .../ask` returning `202 + stream handle`, then subscribing for `token`, `grounding` and `final` events.

These are two different protocols for the same interaction. As written, the backend would return the finished answer synchronously and the frontend would wait for tokens that arrive on a channel it opened separately, with no defined correlation between the POST and the events.

**Resolution required.** The defensible option is the backend's shape with one addition: `POST .../ask` returns `202 Accepted` with an `answer_id`, and the events on the existing conversation SSE channel carry that `answer_id` so the client can correlate. Synchronous return contradicts the whole point of the frontend's provisional-region design and of the backend's own first-token latency budget (pass 1 §4.6 allocates 700 ms to first token — a number that only means something if tokens are delivered as they are produced).

### D-2 — SSE event schemas are undefined anywhere. **BLOCKING**

The frontend consumes `token`, `grounding` and `final` (§12), plus queue-position and assignment events (§10). The backend LLD names the channel and never specifies a single event payload. Backend HLD §16 chose SSE; no LLD pass wrote the contract.

**Resolution required.** SSE event names and payloads must be added to the backend LLD and included in the OpenAPI schema, because the frontend's §24 risk register already names "a silent contract change breaks streaming" and its mitigation is schema generation — which cannot work for events that are not in the schema.

The `grounding` event is the one that must be specified most carefully: it is what the frontend's central invariant keys on.

### D-3 — No token refresh endpoint. **BLOCKING**

Frontend §11: "a 401 triggers one silent refresh, then a single retry, then sign-out." Backend HLD §11 describes short-lived access tokens plus refresh with a Redis revocation list. **No backend LLD pass defines a refresh endpoint, a sign-in endpoint, or the token DTOs.**

Authentication is load-bearing for three surfaces and currently has no contract. This is a genuine gap rather than a mismatch — pass 1 covered knowledge, pass 2 conversations, pass 3 authorisation, and *authentication* fell between them.

### D-4 — Language code representation differs. **BLOCKING (cheap to fix, expensive to discover late)**

- **Backend:** `CHAR(3)` ISO 639-3 throughout — `'eng'`, `'hin'`, `'ben'`, `'tam'`, `'tel'`, `'mar'`. The `Lang` literal type in both documents' DTOs uses these.
- **Frontend §19:** the per-script type-scale tokens select on `[lang="hi"]`, `[lang="bn"]`, `[lang="ta"]`, `[lang="te"]` — ISO 639-1 two-letter codes. §16 sets `<html lang>`.

Both are correct in isolation: the HTML `lang` attribute conventionally carries BCP-47 (two-letter where available), and the API sensibly uses 639-3. But the mapping is nowhere, so the CSS selectors will silently never match values coming from the API.

**Resolution:** a single mapping table in `shared/i18n`, applied where `<html lang>` is set. One function, and it must be named in the frontend LLD so it is not improvised per component.

### D-5 — Fair-use rejection is modelled two ways in the backend itself

Pass 1 §4.5 maps `FairUseExceeded` → **429** with retry-after. Pass 1 §6.1's pseudocode returns `blocked_fair_use` as an **outcome** with `handover_offered=True`, and `answer_outcome` includes it as an enum member. The frontend consumes it as an outcome (`AnswerView` member carrying `retryAfterSeconds`).

Two of the three agree on the outcome shape. The 429 mapping is the outlier — and the outcome shape is the better answer, because REQ-023 requires that hitting the limit still offers handover, which is product content, not an error condition. A 429 with a problem-detail body would push the frontend's `not-an-error` rule into a status-code exception it does not currently have.

**Resolution:** remove the 429 mapping from pass 1 §4.5; fair-use rejection returns 200 with `outcome: "blocked_fair_use"`.

### D-6 — Taxonomy has no read endpoint

`ClassificationEditor` (frontend §7.5) lets a manager confirm or correct sector/topic assignments, which requires the taxonomy list. The backend exposes `PUT /knowledge/items/{id}/classifications` to write, and nothing to read the available sectors and topics. REQ-003's rename-safety criterion also implies an admin path to rename a display name, which likewise has no endpoint.

**Resolution:** add `GET /api/v1/taxonomy` (all roles that can read knowledge) and the administrator rename endpoint.

### D-7 — Language enablement has no endpoint

Pass 3 §4.3 defines the `admin.languages` permission and pass 1 §2.3 records enablement changes in the audit trail. The frontend's admin panel (§25, F12) enables and disables languages. **No endpoint exists for it.** REQ-001's enablement gate — the resolution of a Stage 2 *critical* finding — is currently unreachable through the API.

**Resolution:** add `GET`/`PUT /api/v1/admin/languages`, with the acceptance score recorded at enablement (pass 3's tracking table already expects that field).

### D-8 — Public coverage status is not readable before asking

Frontend `AssistantApp` renders `CoverageClosedNotice` before the customer types anything (§5, §25 F4). Backend `GET /api/v1/coverage` requires `knowledge_manager` or `administrator`. A public customer cannot read it, so as specified the assistant would have to let the customer type a question and *then* discover the surface is closed — which is precisely the "wall of I don't know" REQ-023 exists to avoid.

**Resolution:** `POST /public/conversations` returns a coverage indication (or refuses with a clear code) so the notice renders before the composer, not after a wasted question. The minimal change is a boolean on `StartConversationResponse`.

### D-9 — `X-Correlation-Id` is consumed but not accepted

Frontend §11 sends it on every request and §12 threads it through observability. Backend HLD §20 describes a correlation identifier "spanning SPA request through model call", but no backend LLD pass specifies accepting or propagating the header.

**Resolution:** minor — state the header in the backend's API conventions (pass 1 §4.1) and note that it is echoed in problem responses, which the frontend's fatal-error boundary already promises to show the user.

### D-10 — Deletion request creation DTO unspecified

`POST /api/v1/privacy/deletion-requests` exists in pass 3 §4.1 with no request DTO. The frontend admin panel needs to know what identifies the customer whose data is being erased — presumably the `customer_key_hash` from pass 3 §2.3, but an administrator does not hold a hash; they hold a conversation reference or a contact detail.

**Resolution:** define the DTO, and decide whether erasure is initiated by conversation id (traceable) or by contact detail (what a customer actually supplies). This is a small design decision with a real privacy consequence and should not be improvised at Stage 8.

## 4. Summary and required actions

| # | Discrepancy | Blocking | Owner document |
|---|---|---|---|
| D-1 | Answer delivery protocol | **Yes** | Backend LLD pass 2 §4.1, frontend §12 |
| D-2 | SSE event schemas undefined | **Yes** | Backend LLD (new section) |
| D-3 | No authentication endpoints | **Yes** | Backend LLD (new section) |
| D-4 | Language code mapping | **Yes** | Frontend LLD §19 + `shared/i18n` |
| D-5 | Fair-use 429 vs outcome | No — internal fix | Backend LLD pass 1 §4.5 |
| D-6 | Taxonomy read/rename endpoints | No | Backend LLD pass 1 §4.2 |
| D-7 | Language enablement endpoints | No | Backend LLD pass 3 §4.1 |
| D-8 | Public coverage status | No | Backend LLD pass 2 §4.1 |
| D-9 | Correlation header unaccepted | No | Backend LLD pass 1 §4.1 |
| D-10 | Deletion request DTO | No | Backend LLD pass 3 §4.2 |

**What this pass did not find**, stated because its absence is informative: no disagreement about citation rules, outcome semantics, concurrency conventions, error philosophy, or role enforcement. The two documents were designed against the same requirements and they show it. Every discrepancy above is an interface detail that fell between two passes — which is exactly the class of defect a consistency pass exists to catch, and exactly the class that becomes expensive when it is found during implementation instead.

---

# Re-Check: after the Stage 5c amendments

**Trigger:** Stage 5c gate returned ITERATE. Both sides were amended — backend via `lld-backend-pass4-interfaces.md` v1.0, frontend to `lld-frontend.md` v1.1.

## Disposition

| # | Finding | Status | Resolution as built |
|---|---|---|---|
| D-1 | Answer delivery protocol | **Closed** | `POST .../ask` → `202 {answer_id}`; events correlate on the already-open conversation channel. The synchronous shape is withdrawn. Chosen over a streaming response body so an answer survives a connection blip — events replay, a body does not |
| D-2 | SSE event schemas | **Closed** | 11 events specified with payloads, in the OpenAPI schema so they generate. `answer.final` is guaranteed on every terminal path, and the client's obligation when that guarantee is not met is stated on both sides |
| D-3 | Authentication endpoints | **Closed** | Four endpoints; refresh rotates and a replay revokes the session family; `GET /auth/me` returns resolved permissions plus the enabled-language set in one call. The refresh token is never visible to JavaScript, which turns the frontend's storage rule from discipline into structure |
| D-4 | Language code mapping | **Closed, and improved** | API stays ISO 639-3; `GET /languages` serves the mapping; **type tokens now key on `data-script`, not language** — the original frontend selectors would have needed Hindi and Marathi listed separately and would have silently missed any future Devanagari language |
| D-5 | Fair-use 429 vs outcome | **Closed** | 429 withdrawn; 200 with `outcome`. The frontend's error table now states explicitly that it contains no status-code exception |
| D-6 | Taxonomy endpoints | **Closed** | Read plus admin create/rename/deactivate; `code` immutable by contract, which is the mechanism behind REQ-003's rename guarantee |
| D-7 | Language enablement | **Closed, with a guard added** | Endpoints exist, and **enabling requires an acceptance score**; a below-bar enablement needs an audited override. An enablement with no recorded score is indistinguishable from ignoring REQ-001's gate |
| D-8 | Public coverage status | **Closed** | `self_serve_open` and `closed_notice` on conversation start; the composer is not rendered until it is known |
| D-9 | Correlation header | **Closed** | Accepted, propagated, and echoed on problem responses specifically — the fatal-error boundary shows it to the user, so it must exist on failures |
| D-10 | Deletion request DTO | **Closed, with a decision recorded** | Erasure by conversation reference, not contact detail: matching personal data against personal data risks erasing a different customer on a near-match, and that failure is silent and unrecoverable. `scope_conversation_count` is confirmed before execution, and the two-device limitation is stated rather than hidden |

## Second-order check

Three amendments introduced new surface; each was re-checked against the other document:

1. **One channel per conversation** (frontend §11.1) against the backend's per-channel `Last-Event-ID` replay (§B.3) — consistent. A channel per answer would have broken replay, which is why the frontend now states the constraint explicitly.
2. **`GET /auth/me` returning `enabled_languages`** against `GET /languages` being public — both exist deliberately: the assistant needs the set before sign-in, the consoles get it free at bootstrap. No conflict, and the client caches the public one long.
3. **Acceptance-score-required enablement** against the frontend admin panel — the frontend's acceptance criterion 14 now mirrors the server guard, so the UI cannot submit what the server would reject.

## Revised Verdict

**Consistent.** All ten discrepancies closed, four of them blocking. Two amendments (D-4's script keying, D-7's score guard) made the design better than the original of either document rather than merely reconciling them. Cleared to proceed to Stage 6.
