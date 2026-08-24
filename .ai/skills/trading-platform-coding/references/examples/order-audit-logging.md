# Worked Example — Order Audit Logging Without Breaking the Budget

This example exists specifically because audit/compliance logging is the single easiest way to accidentally destroy a latency budget that's otherwise correctly engineered — a well-optimized matching engine with a naive `write_to_disk()` call bolted onto its audit trail is not actually a 5-8ms system anymore.

**Task**: "Every order event (received, matched, rejected) needs to be durably logged for compliance. Add this without affecting order-path latency."

## What a naive (wrong) approach would look like — for contrast, not to copy

```rust
// DO NOT DO THIS — synchronous write on the hot path
fn on_order_received(order: &LimitOrder) {
    let record = AuditRecord::from(order);
    audit_file.write_all(&record.to_bytes()).unwrap(); // blocking I/O, hot path
    audit_file.sync_all().unwrap();                     // fsync — tens of ms, guaranteed budget violation
    // ... continue processing
}
```
This compiles, looks reasonable in a code review that isn't specifically checking for hot-path I/O, and will not show up as wrong until it's measured under load — exactly the failure mode `performance-engineering.md`'s benchmarking-methodology section exists to catch.

## Plan (the corrected approach)

```
## Plan
Goal: Durably log every order event for compliance without adding blocking I/O to the order-received-to-acknowledged path.
Files touched: src/audit.rs — AuditRecord type, lock-free publish channel, dedicated writer thread; src/matching_engine.rs — add a non-blocking audit_channel.push() call at each event point (received/matched/rejected).
Approach: Write-behind pattern per durability-and-audit.md — hot path only pushes a fixed-size AuditRecord onto an SPSC channel (rtrb, same crate as the order handoff in matching-engine-hot-path.md) and continues immediately. A dedicated writer thread batches records and performs the actual write + fsync off the hot path.
Codebase state: Verified: no existing audit logging in the repo (searched for "audit", "compliance", "AuditRecord" — none found). Assumed: nothing beyond what was searched. Not explored: the actual regulatory retention/field requirements — these were NOT provided in this task and are explicitly flagged as an open question below, not assumed.
Type/domain invariants: AuditRecord is a fixed-size, #[repr]-explicit struct (see rust-backend.md's corrected wire-format guidance — explicit byte encoding, not #[repr(C, packed)]) so it can be pushed onto the hot-path channel without allocation.
Critical-path status: The push itself IS on the confirmed hot path (called from matching_engine.rs's event points) and must be genuinely non-blocking and non-allocating. The writer thread that consumes the channel is explicitly NOT on the hot path — full freedom to block, batch, and fsync there.
Complexity claims: Channel push is O(1) amortized, same as the order handoff. Writer-thread batched write is O(batch size), irrelevant to hot-path latency since it's off-path.
Red step: Write a failing test asserting that calling the audit-publish function 10,000 times in a tight loop completes without measurable blocking (bounded time assertion) and that all 10,000 records are eventually observed by a test consumer — fails first because audit.rs doesn't exist yet.
Out of scope: The actual compliance requirements (retention period, required fields, tamper-evidence) — see Open Questions. Backpressure alerting/monitoring integration.
Risk: medium — new concurrent component on the confirmed hot path (the push side); mitigated by reusing the same proven ring-buffer crate and pattern already verified in matching-engine-hot-path.md.

## Open Questions (per durability-and-audit.md — these are compliance questions this skill cannot answer on its own)
- What is the actual required retention period and field set for the audit record? (Blocking this task's "done" state on real compliance input, not assuming.)
- Must the audit record be durably written *before* the client receives an order acknowledgment (stricter, harder to reconcile with write-behind) or is eventual durability within a bounded window acceptable? This determines whether the simple write-behind pattern below is sufficient or whether a hybrid (fast non-fsync'd write + deferred fsync-and-verify) is required.
- Is tamper-evidence (hash-chaining) a real requirement? If yes, that needs to be designed in now — see durability-and-audit.md, it can't be retrofitted onto existing records later.
```

## Implementation (abbreviated)

```rust
// src/audit.rs
pub struct AuditRecord {
    event_type: EventType,   // fixed-size enum, no heap variant
    order_id: u64,
    symbol: SymbolId,        // dense u16, per rust-backend.md's symbol-representation guidance
    price: u64,
    quantity: u64,
    timestamp_ns: u64,
}

// Hot-path side — called from matching_engine.rs, must never block.
pub fn publish_audit_event(producer: &mut Producer<AuditRecord>, record: AuditRecord) {
    // A full channel here is a backpressure event, per durability-and-audit.md —
    // explicitly counted and alerted, never silently dropped and never blocked on.
    if producer.push(record).is_err() {
        AUDIT_BACKPRESSURE_COUNTER.fetch_add(1, Ordering::Relaxed);
    }
}

// Writer thread — NOT on the hot path, blocking I/O is fine here.
fn audit_writer_loop(mut consumer: Consumer<AuditRecord>, mut file: File) {
    let mut batch = Vec::with_capacity(BATCH_SIZE); // allocated once, reused — not per-batch
    loop {
        // drain up to BATCH_SIZE records or wait up to FLUSH_INTERVAL, whichever first
        collect_batch(&mut consumer, &mut batch, BATCH_SIZE, FLUSH_INTERVAL);
        if !batch.is_empty() {
            for record in &batch {
                file.write_all(&record.to_bytes()).expect("audit write failed");
            }
            file.sync_all().expect("audit fsync failed"); // blocking is fine here — off hot path
            batch.clear();
        }
    }
}
```

## Verification report

```
## Verification report
Tests run: cargo test audit:: -- pass (publish/consume round-trip, backpressure-counter test)
Manually verified: ran the 10,000-iteration tight-loop publish test under a profiler, confirmed no syscall (no write/fsync) appears in the hot-path thread's profile — only in the separate writer thread's
Acceptance thresholds met: hot-path push latency contribution measured at [placeholder — requires actual load-test harness] ns per call; must be negligible relative to the 8ms budget — not fabricated here, requires your real measurement
Not verified: the actual compliance/regulatory correctness of what's being logged — explicitly flagged as an open question in the Plan, not something this skill can verify on its own
Risk / reviewer focus: (1) the Open Questions above need a real compliance answer before this ships, not just engineering sign-off; (2) the backpressure counter needs to actually be wired to an alert, not just incremented silently — flagged as follow-up, out of scope for this task
```

## What this example demonstrates

- The naive version isn't a strawman — it's the exact shape of code that would pass a normal review and only fail once measured, which is precisely why `performance-engineering.md`'s "never claim a performance win without a number" rule and the Verification report's honesty requirement both exist.
- **Compliance questions get flagged as Open Questions, not silently assumed** — this skill has real technical authority over how to make audit logging non-blocking, and zero authority over what your actual regulatory retention/field requirements are. Pretending otherwise would be worse than admitting the gap.
