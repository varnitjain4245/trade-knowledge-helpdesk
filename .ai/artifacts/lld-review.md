---
title: "LLD Review — Backend and Frontend"
stage: 6
skill: "lld-reviewer (backend), frontend-lld-review (frontend)"
scope: fullstack
version: "1.0"
reviews: lld-backend.md, lld-backend-pass2.md, lld-backend-pass3.md, lld-backend-pass4-interfaces.md, lld-frontend.md v1.1, lld.md v1.1
against: requirements.md v1.1, hld-backend.md v1.0, hld-frontend.md v1.0, hld-review.md v1.0
---

# Part 1 — Backend LLD Review (`lld-reviewer`)

## 1. Verdict

**FAIL.**

This skill's verdict model is deliberately binary — there is no "ready with conditions" — and three P0s stand. That verdict deserves immediate context, because it does not mean the design is weak: the substantive engineering is strong, the concurrency work is genuinely careful, and every flow carries pseudocode for both its happy and exception branches. The failures are structural gate failures, and two of the three are cheap to fix:

1. **No Manifest.** Gate 0 stops on its absence, by rule.
2. **A new boundary appears at the LLD layer that no HLD defines** — the presence/queue/assignment subsystem.
3. **No project-wide engineering-guardrails document exists**, so several LLD decisions have nothing to be checked against.

Fixing 1 and 3 is documentation. Fixing 2 is a one-section amendment to the backend HLD, not a redesign — the design itself is sound and was mandated by REQ-008.

## 2. Gate 0 — Baseline & Manifest

| Check | Result |
|---|---|
| Upstream PRD/HLD/contract versions cited | **Pass** — every pass names its inputs with versions in frontmatter |
| Manifest of modules, Included/Excluded with reasons | **FAIL — P0** |
| Guardrails-mandated modules included | **FAIL — P0**, no Guardrails document exists |
| New services/interfaces/boundaries not in the HLD | **FAIL — P0**, one found |

### P0-1 — No Manifest

```
Severity: P0
Gate: 0
Observation: No pass contains a module Manifest. Each pass has an "Out of scope"
  paragraph, which is close but not the same thing: it names what the pass excludes,
  not the full set of modules the design covers with a per-module Included/Excluded
  decision and reason.
Impact: Completeness cannot be checked. A module nobody remembered would be invisible
  to this review — and across three passes plus an amendment, "nobody remembered" is a
  realistic failure mode, not a theoretical one.
Recommendation: Add one Manifest table spanning all four documents, listing every module
  from the HLD component diagram (backend HLD §5) with Included/Excluded, the pass that
  covers it, and a reason for every exclusion.
```

### P0-2 — Unratified bounded context: presence, queue and assignment

```
Severity: P0
Gate: 0
Observation: Pass 2 introduces AssignmentEngine, PresenceService, the queue model and
  its locking protocol. The backend HLD contains none of these — hld-review.md High-2
  found exactly this absence, and the Stage 4 gate was approved as-is, which moved the
  gap forward rather than closing it. The LLD then filled it.
Impact: A boundary with its own failure modes, its own scheduled job (heartbeat expiry),
  its own reconciliation process and its own SPOF characteristics now exists with no
  architecture-level sign-off. This is the correct finding even though the subsystem is
  well designed: whether it should be in-process, and what happens to it when the single
  VM restarts, are HLD questions that were never asked.
Recommendation: Amend hld-backend.md with a presence/queue/assignment section — component
  placement, failure behaviour on restart, and its interaction with §26's scaling triggers.
  The LLD content can be summarised upward; nothing needs redesigning.
```

### P0-3 — No engineering Guardrails document

```
Severity: P0
Gate: 0
Observation: The workflow has no project-wide guardrails artifact. Several LLD decisions
  are therefore unanchored: logging conventions, exception-hierarchy conventions, the
  timeout-budget philosophy, naming, migration policy, and the "no UPDATE/DELETE grant"
  pattern that pass 3 applies to two tables and would need applying consistently to any
  future append-only table.
Impact: These conventions currently live inside individual documents. A fifth pass, or a
  second team, has nothing project-wide to conform to, and consistency becomes a matter
  of whoever reviews the pull request.
Recommendation: Extract the cross-cutting conventions already implicit across the four
  documents into a short guardrails artifact before Stage 8. This is genuinely a
  half-page, and it is the difference between conventions and habits.
```

## 3. Gate 1 — Consistency & Drift

Signature job of this review. Four findings, classified per the taxonomy.

### P1-1 — Degradation: cache behaviour when the database is unavailable

```
Severity: P1  |  Drift type: Degradation
Observation: hld-backend.md §21 states that when the database is unavailable the system
  fails hard and "no cached answers served, because a cached answer cannot be checked
  against current retirement status." Pass 1 §7.3 specifies the Redis answer cache and
  its generation key but never states what happens on a cache hit while PostgreSQL is
  down — and the generation counter itself lives in PostgreSQL, so it cannot be read to
  validate the key.
Impact: The most likely implementation serves the cached answer (Redis is up, the key
  matches the last-known generation), which is precisely the behaviour the HLD forbids,
  for exactly the reason the HLD gives.
Recommendation: State explicitly that a cache hit requires a successful generation read;
  if the counter cannot be read, the cache is bypassed and the request fails. Add it to
  §7.3 and to the failure table.
```

### P1-2 — Omission: per-stage latency instrumentation

```
Severity: P1  |  Drift type: Omission
Observation: hld-backend.md §20 requires "latency histograms per pipeline stage
  (retrieval, rerank, generation) because a p95 breach needs to name its stage." Pass 1
  defines the budget per stage (§4.6) but no pass specifies emitting the corresponding
  metrics.
Impact: The budget is unenforceable in production. When the 5-second target is breached,
  nothing says which stage did it — the exact scenario §20 was written for.
Recommendation: Specify the metric names and labels alongside the §4.6 budget table, so
  budget and measurement are defined in one place and cannot drift apart.
```

### P1-3 — Omission: scheduled jobs specified in the HLD, unspecified in the LLD

```
Severity: P1  |  Drift type: Omission
Observation: hld-backend.md §17 lists six scheduled jobs. The LLD specifies the staleness
  sweep (pass 1), gap clustering (pass 3 §6.1), the inactivity sweep and presence expiry
  (pass 2 §6.5). It does not specify the analytics aggregation job's schedule and
  idempotency contract beyond a passing note, the weekly masking-verification sampling
  job, or the daily retention-enforcement job — pass 3 §7.3 describes retention as a
  concept, not as a job with a failure mode.
Impact: Three jobs will be implemented from a one-line HLD table, which is where
  "runs twice and double-counts" and "fails silently for a week" come from.
Recommendation: One table specifying every job: trigger, idempotency guarantee, failure
  behaviour, and what alerts when it stops running.
```

### P1-4 — Deformation: HLD's presence model vs. LLD's dual source of truth

```
Severity: P1  |  Drift type: Deformation
Observation: Pass 2 §7.2 makes agent_presence advisory and open assignments authoritative,
  reconciled hourly. This is a defensible design and it is well argued — but it is a
  different mechanism from anything the HLD describes (the HLD describes no presence
  mechanism at all, which is P0-2), and the reconciliation job is a third scheduled
  process introduced without architectural review.
Impact: Called out separately from P0-2 because even after the HLD is amended, the
  advisory/authoritative split is the kind of decision an architect should ratify rather
  than inherit.
Recommendation: Include the split and its reconciliation job in the P0-2 HLD amendment.
```

**Contract conformance:** interface signatures, error codes and permission requirements were checked against `lld.md` v1.1's amended contracts. **No mismatches** — the Stage 5c iteration closed all ten, and spot-checking the auth, SSE and language-enablement contracts against the frontend's v1.1 obligations found them aligned. This gate's most dangerous class of finding is absent.

## 4. Gate 2 — Module Completeness

| Area | Assessment |
|---|---|
| Module & class design | **Complete.** Single responsibilities stated; the deliberate refusals (no `KnowledgeManager` catch-all, no Observer for the generation bump) are argued rather than assumed |
| Method contracts | **Complete.** Repository contracts state preconditions, not-found behaviour, exceptions and transactional guarantees — this is the strongest section of the whole LLD set |
| Data access | **Complete.** Every index names the query it serves; partitioning specified; the hot-path filter is confined to one repository method |
| Concurrency & state | **Complete and unusually careful.** Lock ordering documented, mechanism chosen per access pattern rather than uniformly, deadlock probes specified as tests |
| Error handling | **Complete.** Three exception hierarchies; retryable vs. terminal distinguished per stage |
| Design patterns | **Appropriate.** No over-engineering found; the Strategy for generation earns itself against the unresolved GPU question. One under-engineering note below (P2-1) |
| Configuration | **P1-5 — incomplete** (below) |
| Testability | **Complete.** Seams stated, mocking boundaries justified per layer rather than by habit |

### P1-5 — Tunables hardcoded as constants

```
Severity: P1
Gate: 2 (Configuration)
Observation: The four product thresholds live in the `threshold` table with an audited
  change path — correct. But a second tier of tunables appears only as inline constants:
  MAX_ATTEMPTS (per ingestion stage and per queue entry), HEARTBEAT_TTL, MAX_PERIOD_DAYS,
  SIMILARITY_THRESHOLD (gap clustering), MIN_CONFIDENCE (masking), the 15-minute
  inactivity boundary, and the fair-use window.
Impact: Several of these need changing in production without a deployment. The masking
  MIN_CONFIDENCE in particular gates a compliance guarantee, and the inactivity boundary
  is explicitly marked PROPOSED in the PRD — meaning it is expected to change.
Recommendation: Promote them to configuration with stated defaults. The ones that gate a
  requirement (MIN_CONFIDENCE, inactivity boundary, fair-use window) should follow the
  threshold table's audited-change pattern rather than living in a config file.
```

### P2-1 — Under-engineering: no circuit breaker on model clients

```
Severity: P2
Gate: 2 (Design Patterns)
Observation: Timeouts are specified per stage with defined degradations, which is most of
  the value. But when the model server is genuinely down, every request still pays its
  full timeout before degrading — 2 seconds of first-token timeout per request, 13 times
  a second at peak.
Impact: A dead model server converts into a queue of waiting requests rather than fast
  degradation to extractive answering.
Recommendation: A circuit breaker around the generation and rerank clients: trip after N
  consecutive timeouts, fail fast to the extractive strategy, half-open probe to recover.
  The Strategy pattern already in place makes this a small addition.
```

## 5. Gate 3 — Implementability

| Check | Result |
|---|---|
| Pseudocode for key flows, happy path **and** exception branches | **Pass.** `answer`, `retire`, `supersede`, `IngestionOrchestrator.run`, `assignNext`, `ask`, `sendReply`, `executeDeletion`, `resolve`, clustering — all carry branch structure and error paths |
| Concrete, executable test strategy | **Pass.** 37 + 26 + 28 named scenarios with specific assertions and justified mocking boundaries. Test 28 and test 24 are written as regressions for named review findings, which is the right instinct |
| Observability addressed | **Partial** — see P1-2 |
| Rollout/migration/deployment addressed | **P1-6 — absent** (below) |

### P1-6 — Deployment and migration unaddressed

```
Severity: P1
Gate: 3
Observation: hld-review.md Medium-7 raised this at Stage 4; it was approved as-is and no
  LLD pass picked it up. There is no migration ordering, no zero-downtime statement, no
  rollback plan. Two specifics matter concretely here: adding the customer_key_hash column
  and the answer_record partitioning both touch large tables, and the model server holds
  several gigabytes in memory, so a naive restart is a multi-minute outage during support
  hours against a 99.5% target.
Recommendation: A short migration and deployment section: expand/contract migration
  ordering, which restarts are rolling, and what a rollback does to a partially-applied
  schema change.
```

### Implementability Score

| Module group | Tag |
|---|---|
| Answer path (retrieval, rerank, generate, ground, cache) | **Fully specified** |
| Knowledge lifecycle and ingestion | **Fully specified** |
| Conversation, handover, assignment, presence | **Fully specified** |
| Gaps, analytics, authorisation, audit, privacy | **Fully specified** |
| Auth, SSE, taxonomy, enablement (amendment) | **Fully specified** |
| Scheduled jobs (three of six) | **Specified with gaps** |
| Observability instrumentation | **Still HLD-level** |
| Deployment and migration | **Not addressed** |

No module is a fancier HLD wearing LLD headers — the common failure mode of this artifact type is absent.

## 6. Backend findings summary

| ID | Severity | Area | Fix cost |
|---|---|---|---|
| P0-1 | P0 | Manifest missing | One table |
| P0-2 | P0 | Assignment subsystem unratified at HLD | One HLD section |
| P0-3 | P0 | No guardrails document | Half a page |
| P1-1 | P1 | Cache vs. database-down degradation | Two sentences + a test |
| P1-2 | P1 | Per-stage metrics unspecified | One table |
| P1-3 | P1 | Three scheduled jobs unspecified | One table |
| P1-4 | P1 | Presence advisory/authoritative split unratified | Folds into P0-2 |
| P1-5 | P1 | Second-tier tunables hardcoded | Config section |
| P1-6 | P1 | Deployment and migration absent | One section |
| P2-1 | P2 | No circuit breaker on model clients | Small addition |

---

# Part 2 — Frontend LLD Review (`frontend-lld-review`)

## 7. Defining constraints

Named first, because a design that misses its defining constraint fails regardless of what else it gets right. This feature set has three:

1. **The grounding invariant** — no ungrounded text may ever reach the transcript.
2. **Latency legibility** — the backend owns the seconds; the UI owns whether they feel broken.
3. **Multi-script layout** — six languages, four scripts, on surfaces built by people who read one of them.

**The design nails all three.** The provisional-region mechanism, the non-empty citation tuple type, the script-keyed tokens and the `not-an-error` category are all direct, well-chosen answers. This is the review's most important judgement and it is positive.

## 8. Findings by priority

### 🔴 Critical — cross-tab invalidation does not work as claimed

```
Dimension: State management (multi-tab consistency)
Observation: §23 states: "Two curation tabs open, one retires an item → Query
  invalidation updates the other tab; a stale item cannot linger in a second view."
  This is not true. TanStack Query's cache and its invalidation are per-document.
  Retiring an item in tab A leaves tab B's cache untouched.
Impact: A knowledge manager working in two tabs — a completely normal pattern in a
  console built around a list and a detail view — can retire an item in one and continue
  to see it as answerable in the other, then act on that stale view. Because §23 claims
  this case is handled, nobody will implement anything for it. That combination, a false
  claim of coverage on a governance-critical path, is what makes this critical rather
  than a gap.
Fix: Broadcast invalidations across tabs. Concretely: a BroadcastChannel('knowledge')
  posting {type: 'invalidate', keys: [...]} from every lifecycle mutation's onSuccess,
  with a listener in the query provider calling queryClient.invalidateQueries for the
  received keys. Add refetchOnWindowFocus: true for the item and list queries as a
  second line of defence for the case where the channel is unavailable. Then correct
  §23's claim to describe the mechanism rather than assume it.
```

### 🔴 Critical — optimistic rating has no failure path

```
Dimension: State management / error handling
Observation: §2 and §20 specify optimistic UI for feedback ratings ("optimistic feedback
  on ratings but never on governance actions" — the right distinction). No rollback
  behaviour is specified for a failed rating mutation.
Impact: The rating a supervisor sees as recorded may never have been recorded. Ratings
  feed the wrong-answer rate and the wrong-answer-versus-adoption guardrail, so a
  silently-dropped negative rating removes exactly the signal the guardrail exists to
  catch. Optimistic UI without rollback is not optimism, it is a lie with a short
  half-life.
Fix: onMutate snapshots the previous rating, onError restores it and surfaces a
  recoverable-request retry inline on the suggestion card, onSettled invalidates.
  State it in §7.3's spec and assert it in the §22 integration set.
```

### 🟡 Should address — validation timing unspecified for the classification editor

```
Dimension: State management (validation architecture)
Observation: §14 lists validation rules but never states timing. For the classification
  editor this matters: below-bar fields render empty and required (§7.5, a good decision),
  and whether they validate on blur, on change or only on submit determines whether a
  manager sees four red fields the moment the form opens.
Impact: On-change validation of intentionally-empty required fields makes a correct design
  feel broken on first render.
Fix: Specify on-blur for field-level, on-submit for form-level, and no validation on
  fields the user has not yet touched.
```

### 🟡 Should address — no stale-response guard named for assist suggestions

```
Dimension: Data layer (race conditions)
Observation: The query key includes the query string, so TanStack Query handles ordering
  correctly for distinct queries. But an agent editing and re-submitting the same query
  while a request is in flight produces two identical keys, and nothing states which
  response wins or whether the panel shows a stale result.
Impact: Low severity, but this is the classic autocomplete race in a different costume,
  and the agent console is the surface where speed encourages exactly this behaviour.
Fix: Name the behaviour explicitly — cancel the in-flight request on re-submit
  (AbortController via the query's signal) — rather than relying on library defaults that
  a future version may change.
```

### 🟡 Should address — the provisional region is not specified visually

```
Dimension: Component architecture / accessibility
Observation: §7.1 requires draft tokens to render in a "visually distinct provisional
  region", and §19 correctly forbids a flashy transition. But nothing states what
  "visually distinct" is, and this is the one visual treatment in the product with a
  correctness meaning attached.
Impact: An implementer choosing a subtle grey achieves nothing; one choosing amber
  implies an error where none exists. Both are plausible readings of the current text.
Fix: Specify the treatment as a token (reduced opacity plus a left rule, no colour
  semantics), and add it to the §19 token list so it is not invented per surface.
```

### 🟢 Polish — normalisation not addressed for the item list/detail pair

The item table and item detail hold overlapping data under different query keys, so a lifecycle mutation must invalidate both — which §9 correctly requires. A normalised entity cache would make that automatic. Not worth it at this scale, but the reason for not doing it should be stated so the next reviewer does not re-raise it.

### 🟢 Polish — feature flags and experimentation

Not addressed, and **correctly out of scope**: nothing in the requirements implies flagged rollout, and inventing a flag architecture would be exactly the manufactured finding this skill warns against. Noted so its absence is visibly deliberate.

## 9. Dimensions marked not applicable

| Dimension | Why out of scope |
|---|---|
| Offline synchronisation | No offline requirement; both consoles are staffed on-site and the assistant is a live service |
| SSR/hydration/RSC boundaries | CSR chosen deliberately for a stated data-control reason; no hydration surface exists |
| Virtualisation on the assistant | Conversations are short; virtualisation is correctly applied only to the item table and agent queue |
| Cross-tab sync on the assistant | A customer with two assistant tabs has two independent conversations, which is correct behaviour, not divergence |

## 10. What is genuinely good — specifics, not praise

1. **The non-empty citation tuple type.** Making BR-1 a compile error rather than a runtime check is the single best decision in the document.
2. **`GuardrailTile`'s value/caveat discriminated pair.** Type-level enforcement of an honesty requirement is rare and exactly right for a figure that would otherwise be read as exact.
3. **`not-an-error` as a first-class category**, with the v1.1 note that no status-code exception exists in the table.
4. **Below-bar classification fields render empty and required**, not pre-filled with a low-confidence guess. This is a small decision with a large effect on whether REQ-003's human confirmation is real or ceremonial.
5. **`usePresence` pausing on `visibilitychange`.** Catching that a backgrounded tab lies to the assignment engine is the kind of detail that is usually found in production.
6. **Keying type tokens on script rather than language.** Correct, and it prevents a silent failure in any future Devanagari language.

## 11. Combined verdict

| Side | Verdict |
|---|---|
| Backend (`lld-reviewer`, zero-tolerance) | **FAIL** — 3 P0, 6 P1, 1 P2 |
| Frontend (`frontend-lld-review`) | **2 🔴, 3 🟡, 2 🟢** — not a formal fail model, but the two criticals are blocking in substance |

The two reviews agree in character: the engineering is strong and the gaps are structural — a missing manifest, an unratified boundary, an unbacked claim of cross-tab coverage, an optimistic update with no rollback. Every finding is fixable without redesigning anything.

**The single most important finding across both parts** is the frontend's 🔴 on cross-tab invalidation, because it is the only one where a document currently claims a behaviour that will not occur, on a path that governs whether retired knowledge stays visible.

---

# Part 3 — Re-Review after the Stage 6 amendments

**Trigger:** Stage 6 gate returned ITERATE. Amendments: `guardrails.md` v1.0 (new), `lld-backend-pass4-interfaces.md` §L–§S, `lld-frontend.md` v1.2.

## Backend disposition

| ID | Status | Resolution |
|---|---|---|
| P0-1 Manifest | **Closed** | §L — 33 modules, 6 excluded with reasons. The model-runtime clients exclusion is the one worth noting: their *contracts* are specified where used; designing their internals would be specifying someone else's HTTP client |
| P0-2 Unratified assignment boundary | **Closed** | §N — placement, restart behaviour, scaling trigger, failure mode. The property that makes in-process placement safe is stated: no in-memory state is held, so a restart loses nothing |
| P0-3 No guardrails document | **Closed** | `guardrails.md`, 15 rules extracted from decisions already made. G1, G3, G4 and G15 each encode a finding this review chain produced |
| P1-1 Cache vs. database-down | **Closed** | §M — the generation counter lives in PostgreSQL, so an outage makes every lookup a miss by construction. A test asserts `503` rather than a cached answer |
| P1-2 Per-stage metrics | **Closed** | §P — 13 metrics with stage labels matching §4.6 exactly, plus six alerts |
| P1-3 Scheduled jobs | **Closed** | §O — all eight jobs with trigger, idempotency, failure behaviour and stop-alert. Two carry a deliberate "alert, do not retry": masking verification and retention, both compliance paths where a retry loop makes things worse |
| P1-4 Presence advisory split | **Closed** | Folded into §N as ratified |
| P1-5 Hardcoded tunables | **Closed** | §Q — two tiers, with the membership test stated: a value gating a stated requirement belongs in tier 1. Masking min-confidence and the inactivity boundary moved up accordingly |
| P1-6 Deployment and migration | **Closed** | §S — expand/contract, deployment order, and the honest statement that the model server restart is not rolling and belongs outside support hours |
| P2-1 Circuit breaker | **Closed** | §R — trips to the extractive strategy, which degrades prose quality and never provenance |

## Frontend disposition

| Finding | Status | Resolution |
|---|---|---|
| 🔴 Cross-tab invalidation | **Closed** | §9.1 — `BroadcastChannel` plus `refetchOnWindowFocus`, scoped to curation with the reason the other two surfaces are exempt. §23's false claim corrected to describe the mechanism. Acceptance criterion 16 requires a two-context integration test, so the claim is now asserted rather than assumed |
| 🔴 Optimistic rating rollback | **Closed** | §7.3 — snapshot/restore/retry, plus acceptance criterion 17 |
| 🟡 Validation timing | **Closed** | §14 — on-blur for touched fields only, on-submit for form-level, debounced async with out-of-order discard |
| 🟡 Assist re-submit race | **Closed** | §10 — abort via the query signal, named rather than left to library defaults |
| 🟡 Provisional region undefined | **Closed** | §19 — opacity plus an inline-start rule, explicitly not a semantic colour |
| 🟢 Normalisation | **Accepted as-is** | The reason for not normalising is now implicit in §9.1's explicit invalidation list; not worth a change at this scale |
| 🟢 Feature flags | **Correctly out of scope** | No requirement implies flagged rollout |

## Second-order check

- G15 (cross-tab) generalises the frontend's 🔴 fix into a project rule, so the next cache added does not repeat it.
- §M's bypass-on-unreadable-counter is now G3 project-wide, covering any future knowledge-derived cache.
- §Q's tier-1 promotion of `masking_min_confidence` means changing a compliance-gating value is now an audited event rather than a deployment — a strictly better outcome than the original design.
- §O's stop-alerts depend on `scheduled_job_last_success_timestamp` from §P; the two amendments were written together and reference the same metric name.

## Revised Verdict

| Side | Verdict |
|---|---|
| Backend (`lld-reviewer`) | **PASS** — 0 P0, 0 P1, 0 P2 outstanding |
| Frontend (`frontend-lld-review`) | **0 🔴, 0 🟡** outstanding; 2 🟢 accepted with stated reasons |

Cleared to proceed to Stage 7. Three fixes made the design better rather than merely compliant: the guardrails document turned four hard-won findings into project-wide rules, the circuit breaker closes a real production failure mode nobody had raised, and promoting the masking confidence into the audited tier improved a compliance path.
