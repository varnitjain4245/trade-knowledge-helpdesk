---
title: "HLD Review Report — Smart Contact-Center Knowledge Platform"
stage: 4
skill: hld-reviewer
scope: fullstack
version: "1.0"
reviews: hld-backend.md v1.0, hld-frontend.md v1.0, tech-stack.md v1.1
against: requirements.md v1.1, prd-review.md v1.1
---

# HLD Review Report: Smart Contact-Center Knowledge Platform (backend + frontend)

## 1. Verdict

**Ready with Conditions.**

The design is coherent, right-sized to the stated load, and unusually honest about its own weak links — the GPU dependency, the uncalibrated answer bar and the single point of failure are all named by the authors rather than found by this review. Two decisions in particular are correct and load-bearing: routing every surface through one Answer service, and rejecting fine-tuning because a fine-tuned model cannot be retired or cited. The design does not, however, hold together on one point that the PRD treats as absolute: **the answer cache in backend §8 can serve an answer citing an item retired seconds earlier, which breaks BR-8 and the immediacy guarantee that the same document argues for elsewhere.** That, plus an entirely unspecified agent-availability and assignment mechanism behind REQ-008, are conditions on proceeding rather than notes for later. Five further High findings concern operability rather than correctness. None require rearchitecting; all require deciding something the HLD left silent.

## 2. Requirement Traceability (Three Doors)

- **Door 1 — Coverage:** **Pass with concerns**
- **Door 2 — Fidelity:** **Pass with concerns**
- **Door 3 — Readiness:** **Pass with concerns**

### Door 1 — Coverage walk (Must-Have set, 16 requirements)

| Req | Status | Note |
|---|---|---|
| REQ-001 Multilingual query | Covered | Backend §12.4, §13; frontend §9. Per-language gate reflected in both |
| REQ-002 Ingestion | **Partially covered** | Documents, manual entry and crawl are designed. **Ticket-export ingestion has no described input shape or path** — the pipeline diagram lists it as a source and then never treats it differently, though a ticket record is a question/answer pair, not a document |
| REQ-003 Classification | **Partially covered** | Proposal and confidence covered. **The taxonomy itself is undesigned** — REQ-003's last criterion requires a rename to preserve existing classifications, which implies taxonomy entities with stable identity and versioning. Neither appears |
| REQ-004 Cited answers | Covered | Strongly. §6, §12.2, plus the frontend's verifying-state rule in §7 |
| REQ-005 Confidence & no-answer | Covered | §12.3 with an honest calibration caveat |
| REQ-006 Agent assist | Covered | §5, §16, frontend §7 error classes |
| REQ-007 Self-serve assistant | Covered | §5, §16. Abandoned outcome is implied by the 15-minute boundary but see Door 2 |
| REQ-008 Handover with context | **Partially covered** | Transcript transfer is covered. **Agent availability, presence, queueing and language-preferred assignment are entirely absent** — REQ-008 has five criteria about assignment and the HLD describes none of the mechanism |
| REQ-009 Curation console | **Partially covered** | Operations listed; version history named but its storage strategy is undescribed, and the v1.1 concurrent-edit criterion has no corresponding concurrency mechanism |
| REQ-010 Freshness & supersession | Covered, but see High-1 | The retrieval-filter invariant is exactly right; the answer cache contradicts it |
| REQ-011 Gap queue | **Partially covered** | Clustering is scheduled hourly, but **how queries are grouped by meaning is unspecified** — across six languages this is a non-trivial design decision, not an implementation detail |
| REQ-012 Analytics | Covered | §15; export mechanism unspecified but that is a Stage 5 concern |
| REQ-013 Roles & access | **Partially covered** | Enforcement designed. **User provisioning, role assignment and deactivation have no home** — the administration surface lists thresholds, languages, coverage floor and deletions, but not users |
| REQ-014 Audit | Covered | §18 is the strongest section in the document |
| REQ-015 Privacy | Covered | §19, with masking in the worker path |
| REQ-023 Cold start & fair use | Covered | §5 gate, §21 Redis-down behaviour |

Should-Have coverage (REQ-016 to REQ-019) is deliberately thin and REQ-018 is explicitly deferred. That is a legitimate phase decision, not a coverage gap, and it is recorded as such in `traceability.md`.

### Door 2 — Fidelity findings

1. **BR-8 vs the answer cache** — the PRD requires retirement to take effect immediately, including for in-progress conversations. The design honours this in retrieval and then reintroduces the window through a cache. See High-1.
2. **REQ-007's "abandoned" outcome** — the PRD requires a recorded outcome after 15 minutes of inactivity. Backend §17's scheduled-job table has no job that closes abandoned conversations, so the outcome would never be written. A small omission with a direct metric consequence: the deflection denominator depends on it.
3. **Guardrail metrics** — §15 says guardrails are surfaced alongside KPIs, which is right. But **repeat-contact rate requires identifying that two conversations came from the same customer**, and the design keeps customers anonymous by default (§11). The guardrail is not computable as designed. This is genuine drift between an approved requirement and the mechanism, and it needs an explicit resolution rather than discovery at Stage 10.
4. **No fidelity drift found** on the citation rules, conflict-before-bar ordering, per-language enablement, or audit immutability — all four are implemented as specified, including the subtleties v1.1 added.

### Door 3 — Readiness findings

Load-bearing decisions still open at the point where engineers would need them:
- Whether a GPU exists (T-1). The design branches on this and both branches are stated, which is acceptable — but the branch must be resolved before Stage 7 planning, or the plan is unschedulable.
- Assignment/queueing mechanism (see High-2) — engineers cannot build REQ-008 from this document.
- API conventions — versioning, pagination, idempotency, timeouts are unaddressed (High-4).
- Gap-clustering method (Medium-3).

Everything else is concrete enough to hand over.

## 3. Findings

### High — resolve before Stage 5

```
Severity: High
Category: Reliability / Correctness
Observation: Backend §8 lists a "hot-query answer cache" in Redis, while §8's own invariant and BR-8 require an item's answerability to be decided at query time so that retirement takes effect immediately. A cached answer bypasses the retrieval filter entirely.
Impact: A customer or agent can be shown an answer citing a retired or superseded circular after retirement — the exact failure the product exists to prevent, and the one the PRD calls non-negotiable. It would also be nearly invisible in testing, since it only manifests in the window after a retirement.
Recommendation: Either drop the answer cache (it saves inference cost on a workload whose queries are mostly distinct anyway), or key it on a knowledge-version generation counter that any approval, retirement or supersession increments, so every such event invalidates the whole cache atomically. State which, and state it in the same section as the invariant it must not violate.
```
*(High-1)*

```
Severity: High
Category: Architecture / Coverage
Observation: REQ-008 specifies availability-based assignment, language-preferred routing, queue-wait thresholds, callback fallback and a supervisor escalation on assignment failure. The HLD describes none of the underlying mechanism — no agent presence model, no queue, no assignment policy.
Impact: A whole subsystem is missing from the design. It also has real-time and state implications (presence must be live, assignment must be race-free when two agents are free) that would surface as rework if discovered at Stage 8.
Recommendation: Add a section covering agent presence (how availability is known and how it expires when a browser closes), the queue model, the assignment policy including language preference, and race-freedom on assignment. Name where wait-threshold and escalation live.
```
*(High-2)*

```
Severity: High
Category: Security
Observation: The design specifies TLS in transit, authorisation per endpoint and immutable audit, but says nothing about encryption at rest or secrets management, on a system holding customer conversations, personal identifiers and a government service's operational record.
Impact: A stolen disk or a leaked environment file exposes transcripts and PII. The compliance NFR references India's data protection obligations, which this silence does not satisfy.
Recommendation: Specify disk or database-level encryption at rest for PostgreSQL and object storage, and a secrets mechanism for model, database and object-store credentials that is not environment variables in a Compose file.
```
*(High-3)*

```
Severity: High
Category: API Design
Observation: No API conventions are specified — no versioning strategy, no pagination convention, no idempotency for uploads or approvals, no client or server timeout budgets.
Impact: Idempotency matters concretely here: a retried document upload creates a duplicate that then trips REQ-002's near-duplicate flow and wastes a manager's time; a retried approval could double-write audit records. Timeouts matter because the answer path calls a model that can hang, and without a budget the frontend's 5-second target is unenforceable.
Recommendation: State a versioning scheme, a single pagination convention, idempotency keys on all non-GET knowledge and conversation operations, and a per-stage timeout budget summing to the p95 target (retrieval / rerank / generation / total).
```
*(High-4)*

```
Severity: High
Category: Database
Observation: Audit records are retained 3 years and every answer shown, reply sent, and access refusal writes one. Messages and conversations accumulate at conversation volume. No partitioning, archival or index strategy is described beyond the vector index.
Impact: On the stated volumes the audit table becomes the largest in the system and the primary cause of slow analytics queries within the first year — precisely the queries REQ-012 promises to serve in 10 seconds.
Recommendation: Specify time-based partitioning for audit and message tables, the indexes the analytics access patterns need, and how the 12-month transcript retention job interacts with partitions (dropping a partition is cheap; deleting rows at that volume is not).
```
*(High-5)*

```
Severity: High
Category: Reliability
Observation: Celery is chosen but no failure semantics are specified — retry policy, poison-message handling, dead-letter destination, or what a half-completed ingestion leaves behind.
Impact: REQ-002 requires that nothing partially extracted is published and that failures are reported with reasons. Without explicit job semantics, a worker killed mid-embedding can leave an item in an ambiguous state that no requirement describes.
Recommendation: Define per-stage idempotency for ingestion, bounded retries with backoff, a dead-letter queue surfaced to the curation console, and the rule that an item's state advances only on stage completion.
```
*(High-6)*

### Medium — resolve before Stage 8

- **Medium-1 (Fidelity / Analytics):** The repeat-contact guardrail is not computable against anonymous customers (Door 2, item 3). Resolve by either scoping the guardrail to identified customers and saying so, deriving it from a conversation-linking heuristic and declaring the heuristic, or escalating OQ-6 (identified vs anonymous access) as a blocker on this guardrail. Do not leave it looking measurable when it is not.
- **Medium-2 (Coverage / REQ-007):** No scheduled job closes abandoned conversations. Add it to §17 and to the retention/analytics reasoning.
- **Medium-3 (Coverage / REQ-011):** Gap-query grouping "by meaning" across six languages is a design decision — the obvious approach is clustering the same multilingual embeddings already computed, which would also make cross-language grouping fall out naturally, but the document should say so rather than leave it to whoever implements it.
- **Medium-4 (Coverage / REQ-003):** Taxonomy has no entity design, yet a criterion requires renames to preserve existing classifications. Specify taxonomy identity and versioning.
- **Medium-5 (Coverage / REQ-013):** User provisioning, role assignment and deactivation have no described home, though token revocation assumes deactivation exists.
- **Medium-6 (Coverage / REQ-009):** Version history is named but its storage model is unstated, and the v1.1 concurrent-edit criterion needs an explicit optimistic-concurrency mechanism (version token on read, conflict on stale write) surfaced through the API to the frontend. The frontend HLD does not mention it either, so this is a two-document gap.
- **Medium-7 (Deployment):** No rollback plan, no migration strategy, no statement of whether deploys are zero-downtime. On a single VM with a model server holding several gigabytes in memory, a naive restart is a multi-minute outage during support hours — which the 99.5% target notices.
- **Medium-8 (Scalability):** "200 concurrent conversations" is stated but never converted into an arrival rate or a concurrent-inference figure. vLLM batching is asserted to make it viable without any arithmetic. Give the capacity calculation, even roughly — it is the difference between a sizing claim and a hope, and it directly determines whether one GPU suffices.
- **Medium-9 (Observability):** Metrics are listed; alerts are not. Specify what pages a human: no-answer rate spiking (corpus or threshold drift), queue depth growth, model-server unavailability, masking-check failures.
- **Medium-10 (Security / Audit):** Audit immutability is enforced by withholding grants from the application role — good — but migrations run under a role that necessarily has them. State how migration credentials are controlled, or the guarantee is one careless script away from being untrue.
- **Medium-11 (Frontend):** No bundle-size budget is given, despite §15 naming CSR first-paint on low-end phones as a weak link and §8 naming bundle discipline as its mitigation. A mitigation without a number is not enforceable.
- **Medium-12 (Testability / QA lens):** Nothing describes how the acceptance question set is stored, versioned and run, though three separate mechanisms depend on it — the REQ-001 language gate, the REQ-023 coverage floor and Stage 10 QA. It is infrastructure, and it currently has no owner in the design.

### Low

- **Low-1:** The frontend's error taxonomy (§7) is right, but the assist-unavailable state has no described recovery behaviour — does it retry automatically, and how does the agent learn it is back?
- **Low-2:** SSE reconnection semantics are unspecified; a dropped stream mid-answer needs a defined behaviour (resume, restart, or fail visibly).
- **Low-3:** Backup restore is stated as a 4-hour target but never rehearsed in any described process. An untested restore is a guess.
- **Low-4:** Object storage via MinIO is justified as making a later move to S3 a config change — worth noting that the data-control NFR would forbid that move to a public cloud region outside the operator's control, so the stated flexibility is narrower than it reads.

## 4. Category Summary

| Category | Assessment | Weight of findings |
|---|---|---|
| Architecture | Strong — right-sized, alternatives genuinely argued, the one process split earns itself | High-2 (missing subsystem) |
| Scalability | Adequate — targets stated, arithmetic absent | Medium-8 |
| Database | Weak — store choices well argued, operational design absent | High-5 |
| API Design | Weak — deliberately deferred to Stage 5, but conventions are HLD-level | High-4 |
| Reliability | Adequate — failure table is good, job semantics missing | High-6, Medium-7 |
| Security | Adequate — authorisation and audit strong, at-rest and secrets absent | High-3, Medium-10 |
| Performance | Adequate — the honest framing (backend owns seconds, frontend owns legibility) is correct; budgets unallocated | High-4, Medium-11 |
| Observability | Adequate — instrumentation planned, alerting undefined | Medium-9 |
| Deployment | Weak — topology clear, lifecycle undefined | Medium-7 |

## 5. What This Review Explicitly Endorses

Recorded so that Stage 5 does not "improve" decisions that are already correct:

1. **One Answer service as the sole producer of answers.** Do not let the LLD introduce a second answering path for the public assistant, however convenient it looks.
2. **Retrieval-grounded, never fine-tuned**, for the retirement and citation reasons given. This is the right call and the reasoning is sound.
3. **Conflict detection before the answer bar** — matches BR-6 as amended, and the ordering is easy to invert by accident during implementation.
4. **Post-generation grounding check with extractive fallback.** This is what makes BR-1 structural. Do not let it become a warning flag instead of a suppression.
5. **CSR over SSR**, for the data-control reason rather than the performance reason. The argument holds.
6. **Status filtering inside the retrieval query rather than after it.** The correct mechanism for immediate retirement — which is exactly why High-1's cache is such a sharp inconsistency.

## 6. Conditions for Proceeding

Stage 5a and 5b may begin once the following are resolved in the HLD documents (not deferred into the LLD):

1. High-1 — the cache/retirement contradiction, resolved one way or the other in writing.
2. High-2 — presence, queue and assignment designed.
3. High-3 — encryption at rest and secrets management specified.
4. High-4 — API conventions and the timeout budget stated.
5. High-5 — audit and message table partitioning and index strategy stated.
6. High-6 — job failure semantics stated.
7. Medium-1 — the repeat-contact guardrail either made computable or explicitly re-scoped.

The remaining Medium and Low findings may be resolved inside the LLD, provided they are carried forward rather than dropped.
