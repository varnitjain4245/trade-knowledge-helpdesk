---
title: "Engineering Guardrails — Smart Contact-Center Knowledge Platform"
stage: cross-cutting
scope: fullstack
version: "1.0"
resolves: "lld-review.md P0-3"
---

# Engineering Guardrails

Project-wide conventions extracted from decisions already made across the HLD and LLD set. This document is the thing a fifth pass, or a second team, conforms to. Nothing here is new — it is the difference between these being conventions and being habits.

## G1 — Append-only tables

Any table that constitutes evidence (`audit_record`, `answer_record`, `answer_citation`, `assist_usage`) is append-only. Enforcement is **the absence of a grant**, not application discipline:

```sql
REVOKE UPDATE, DELETE, TRUNCATE ON <table> FROM app_role;
```

The repository interface for such a table must not expose a mutation method — the interface should be unable to express what the grant forbids. Retention is executed by the maintenance role via partition drops only, and that role's credentials are never present on the running host.

**Adding a new evidence table means applying all three: the revoke, the interface shape, and a test that asserts the revoke holds.**

## G2 — Answerability is decided at query time

An item's answerability is decided by its `status` in PostgreSQL, inside the retrieval query, never by the presence of an embedding, never by a cache, never by a filter applied after retrieval. Any new read path over knowledge must go through `ChunkRepository.hybrid_search` or replicate its filter with a test proving it.

## G3 — Caches are keyed on a generation counter

No cache over knowledge-derived data is invalidated per-key. All such caches include `knowledge_generation` in their key; the counter is bumped inside the same transaction as any state change. **If the counter cannot be read, the cache is bypassed** — a cache hit that cannot be validated is not a hit.

## G4 — Every degradation lands on the safe side

Every timeout, fallback and failure path must degrade toward showing less rather than showing something unverified. Concretely: never toward an uncited answer, never toward a stale item, never toward a guess above the bar. When adding a new failure branch, state which side it lands on.

## G5 — Expected conditions are not errors

Outcomes the domain models as legitimate results (`no_answer`, `conflict`, `blocked_coverage`, `blocked_fair_use`, assist unavailable, no agent available) return `200` and render as content. HTTP error statuses are reserved for genuine failures. This overrides conventional status-code mapping deliberately; see `lld-backend-pass4-interfaces.md` §E.

## G6 — Tunables live in configuration or the threshold table

Nothing that a person might need to change in production is a code constant. Two tiers:

- **Product thresholds** (answer bar, classification bar, low-volume, gap group size, masking min-confidence, inactivity boundary, fair-use window): the `threshold` table, changed through an audited endpoint.
- **Operational tunables** (retry caps, heartbeat TTL, clustering similarity, max analytics period, queue max attempts): configuration file with stated defaults, changed by deployment.

A value that gates a stated requirement belongs in the first tier, not the second.

## G7 — Locks are acquired in a documented order

System-wide order: **queue entry → agent presence → conversation → knowledge item**, and within a type, by identifier ascending. Any new transaction taking two or more row locks states its order and justifies any deviation. Deadlock probes are integration tests, not hopes.

## G8 — State machines are tables, not scattered checks

Every entity with a lifecycle declares a `_LEGAL` transition map and one `assert_transition` call site. Status is never assigned directly outside the lifecycle service that owns it.

## G9 — Exception hierarchies per domain

One base per domain (`KnowledgeDomainError`, `AnswerDomainError`, `IngestionError`, `ConversationDomainError`, `AssignmentError`), mapped to `problem+json` codes in one table per surface. A new exception without a mapping is an incomplete change.

## G10 — Structured logging and correlation

`structlog` JSON, one event per meaningful action, always carrying `correlation_id`. Never log query text, message bodies or citation passages — they contain customer content. Correlation ids are accepted from the client, generated when absent, propagated through model calls, and echoed on every `problem+json` response.

## G11 — Metrics accompany budgets

Any stated latency budget must have a corresponding histogram with the same stage names. A budget without a metric is unenforceable and does not count as specified.

## G12 — Scheduled jobs declare four things

Trigger, idempotency guarantee, failure behaviour, and what alerts if the job stops running. A job specified without all four is incomplete.

## G13 — Migrations are expand/contract

Additive first, backfill, switch reads, then contract in a later deployment. No migration both adds and removes in one step on a table over 100k rows. Every migration states its rollback.

## G14 — Client-side authorisation is UX only

Route guards, hidden controls and disabled buttons are affordances. Every one of them has a server-side check, and the code comment at each guard says so.

## G15 — Cross-tab consistency for shared mutable state

Any cache holding data another tab can mutate broadcasts its invalidations (`BroadcastChannel`) and enables `refetchOnWindowFocus`. Per-document cache invalidation does not cross tabs, and assuming it does is a bug that only appears when two windows are open.
