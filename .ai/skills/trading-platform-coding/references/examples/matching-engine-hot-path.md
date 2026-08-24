# Worked Example — Matching Engine Order-Book Update (Hot Path)

Unlike `examples/limit-order-validator.md`, which deliberately was *not* on the hot path (a new, unprofiled component), this example is explicitly on the profiled critical path — so it shows the full weight of `rust-backend.md`, `performance-engineering.md`, and `concurrency-patterns.md` actually applied together, not just described.

**Task**: "The network I/O thread needs to hand off incoming limit orders to the matching engine thread without blocking either side. Implement the hand-off and the order-book insertion."

## Plan

```
## Plan
Goal: Lock-free hand-off of validated orders from the I/O thread to the matching engine thread, and O(1)/O(log n) insertion into the price-ladder order book.
Files touched: src/handoff.rs — SPSC ring buffer wrapper; src/order_book.rs — price-ladder insertion logic.
Approach: Use the `rtrb` crate for the SPSC ring buffer rather than hand-rolling one (see concurrency-patterns.md — proven crate preferred over hand-rolled lock-free code absent a specific reason). Order book uses a BTreeMap<Price, PriceLevel> per side (bids/asks) for O(log n) insertion and O(1) best-price via first_key_value/last_key_value, per the existing Data Structures rule in rust-backend.md.
Codebase state: Verified: read src/network.rs (I/O thread entry point) and confirmed it currently calls order_book.insert() directly and synchronously — this is the actual coupling being removed. Assumed: nothing beyond what was read. Not explored: the matching logic that consumes a fully-inserted order (out of scope — see below).
Type/domain invariants: Order price/quantity are already validated u64 minor-units by the time they reach this code (see limit-order-validator.md) — no additional type-conflict risk here since this consumes already-valid LimitOrder values, it doesn't construct them.
Critical-path status: CONFIRMED on the profiled critical path — this is literally the order-received-to-order-acknowledged hand-off, per a flamegraph from the existing synchronous insert() path showing 40% of end-to-end latency currently spent blocked on this insertion under burst load. Full hot-path discipline (zero-allocation, no locks, cache-line-padded indices) applies here, unlike the validator example.
Complexity claims: BTreeMap insertion is O(log n) in the number of distinct price levels (not O(log n) in order count — multiple orders at the same price share a level). Best-bid/ask read is O(1) via first_key_value/last_key_value. SPSC ring buffer push/pop is O(1) amortized (may briefly spin if the ring is full/empty, bounded by ring capacity).
Red step: Write a failing test asserting that pushing an order onto the ring buffer from a producer thread and popping it from a consumer thread round-trips the exact order data — fails first because handoff.rs doesn't exist yet.
Out of scope: The matching logic itself (what happens after an order is in the book); changing the BTreeMap to a custom price-ladder array (a possible future optimization, not justified by current profiling — see performance-engineering.md's "when NOT to chase more performance").
Risk: medium — concurrent code, on the confirmed hot path; mitigated by using a proven ring-buffer crate rather than hand-rolled, and by the loom-based concurrency test described in Verification below.
```

## Implementation (abbreviated)

```rust
// src/handoff.rs
use rtrb::{RingBuffer, Producer, Consumer};

// Cache-line padding on the wrapper isn't needed here since rtrb already
// handles producer/consumer index separation internally — confirmed by
// reading rtrb's source, not assumed. (This is the kind of check
// "Codebase state: Verified" should reflect for a third-party crate too.)
pub fn create_order_handoff(capacity: usize) -> (Producer<LimitOrder>, Consumer<LimitOrder>) {
    RingBuffer::new(capacity)
}

// I/O thread side — never blocks; a full ring is a backpressure signal,
// handled explicitly rather than silently dropped (see SKILL.md Section 10:
// no silent failure on the order path).
pub fn try_handoff(producer: &mut Producer<LimitOrder>, order: LimitOrder) -> Result<(), HandoffError> {
    producer.push(order).map_err(|_| HandoffError::RingFull)
}
```

```rust
// src/order_book.rs
use std::collections::BTreeMap;

pub struct OrderBook {
    bids: BTreeMap<Price, PriceLevel>, // sorted ascending; best bid = last_key_value
    asks: BTreeMap<Price, PriceLevel>, // sorted ascending; best ask = first_key_value
}

impl OrderBook {
    pub fn best_bid(&self) -> Option<&PriceLevel> {
        self.bids.last_key_value().map(|(_, level)| level) // O(1)
    }

    pub fn best_ask(&self) -> Option<&PriceLevel> {
        self.asks.first_key_value().map(|(_, level)| level) // O(1)
    }

    pub fn insert(&mut self, order: LimitOrder) {
        let side = if order.side == Side::Buy { &mut self.bids } else { &mut self.asks };
        side.entry(order.price).or_insert_with(PriceLevel::new).push(order); // O(log n) in price levels
    }
}
```

## Verification report

```
## Verification report
Tests run: cargo test handoff:: -- pass (round-trip test, ring-full backpressure test); cargo test order_book:: -- pass (insertion, best-bid/ask correctness)
Concurrency verification: loom-verified for the SPSC handoff specifically (concurrency-patterns.md's requirement for hot-path lock-free code) — exhaustively checked producer/consumer interleavings for the push/pop sequence, not just load-tested
Manually verified: traced a burst of 3 orders at the same price level through insert() by hand, confirmed they land in the same PriceLevel rather than overwriting
Acceptance thresholds met: p99.9 for the full receive-to-book-insert path measured at [placeholder — requires your actual load-test harness, not fabricated here] under a market-open burst replay; compare against the 8ms end-to-end budget once integrated with the rest of the intake path
Not verified: end-to-end latency through the full order path (this component in isolation only) — integration measurement is explicitly out of scope per the Plan
Risk / reviewer focus: the memory-ordering correctness of the ring buffer hand-off is the highest-risk part even though a proven crate was used — worth a second engineer confirming the loom test actually covers the interleaving that matters (producer push racing consumer pop at the boundary conditions: empty ring, full ring)
```

## What this example demonstrates that the validator example didn't

- A **CONFIRMED** critical-path status (with the specific evidence — a flamegraph — cited), versus the validator's explicit "not confirmed, use boring safe Rust for now."
- Full hot-path discipline actually applied (zero-allocation ring buffer, O(log n)/O(1) structure) rather than deferred.
- `concurrency-patterns.md`'s loom-verification requirement shown as an actual line in the Verification report, not just described in the abstract.
- An honest, unfabricated placeholder for the one number that genuinely requires your real infrastructure to produce — the actual measured p99.9. Note what this file does *not* do: it doesn't invent a plausible-looking benchmark number to make the example look more complete. See Section 16 of SKILL.md — a fabricated verification number would be worse than an honest placeholder.
