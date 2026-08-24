# Concurrency Patterns — Lock-Free Done Correctly

`rust-backend.md` says "use lock-free SPSC/MPSC ring buffers, never a Mutex on the hot path." That's the right default, but "lock-free" is not automatically "bug-free" — this class of code is exactly where subtle, hard-to-reproduce bugs hide, so it earns its own scrutiny rather than being treated as a solved problem once you've picked a crate.

## Prefer a proven crate over hand-rolling

- Use an established, audited crate (`ringbuf`, `rtrb`, `crossbeam::channel` for less latency-sensitive paths) rather than hand-writing a lock-free ring buffer from scratch, unless there's a specific, measured reason an existing crate doesn't fit. Lock-free data structures are notoriously easy to get subtly wrong (memory ordering bugs, ABA problems) in ways that pass every test you happen to write and fail under a specific interleaving you didn't think to test for.
- If a hand-rolled structure genuinely is necessary (a specific layout/behavior no existing crate provides), that's exactly the kind of `unsafe`-adjacent code `security-review.md`'s "every `unsafe` block needs a written safety justification" rule applies to most strictly — and it should get a second reviewer's eyes specifically on the memory-ordering reasoning, not just the logic.

## SPSC (single-producer single-consumer) — the common case for I/O thread → matching engine thread

- This is the simplest lock-free case and the one to prefer whenever the actual data flow genuinely is one writer to one reader (e.g. one network I/O thread feeding one matching engine thread for a given symbol/partition).
- Producer and consumer indices must be padded to separate cache lines (`#[repr(align(64))]` — see `performance-engineering.md`) — without this, false sharing between the two indices can silently degrade throughput even though the logic is completely correct.
- Memory ordering: a correct SPSC ring buffer needs `Release` ordering when the producer publishes a new write, and `Acquire` ordering when the consumer reads the corresponding index, so that the data write is guaranteed visible before the index update is observed. Getting this wrong (e.g. using `Relaxed` where `Acquire`/`Release` is needed) is the single most common source of "works in testing, corrupts data under real load" bugs in hand-rolled lock-free code — if you're not confident in the exact ordering semantics for a given operation, that's a signal to use a proven crate instead of asserting confidence you don't have.

## MPSC (multi-producer single-consumer) — only when genuinely needed

- Don't reach for MPSC by default just because "there might be multiple producers eventually" — it's more complex and slower than SPSC. Confirm the actual topology first (see the Plan template's "Critical-path status" field — state what the real producer/consumer count is, not an assumed one).
- If genuinely multi-producer (e.g. multiple connection-handling threads feeding one matching engine), a proven crate (`crossbeam::channel`, or a sharded-SPSC pattern with one ring per producer feeding a single consumer that polls all of them) is strongly preferred over a hand-rolled multi-producer lock-free structure — the correctness bar for hand-rolled MPSC lock-free code is meaningfully higher than SPSC.

## Panic safety inside lock-free code

- A panic partway through a lock-free write (e.g. mid-way through updating a multi-field entry) can leave the structure in a state a concurrent reader observes as partially updated, even though no explicit lock was held to "protect" against that — lock-free doesn't mean "safe from partial-update visibility," it means "safe without blocking." Keep the actual mutation of shared lock-free state to the smallest possible critical section, ideally a single atomic store, precisely so there's no window where a panic could leave visible inconsistent state.
- This connects directly to `rust-backend.md`'s conditional `panic = "abort"` guidance — a panic inside lock-free shared-state code is exactly the scenario where "does an abort here actually correspond to safe recovery" needs a real answer, not an assumed one.

## Verifying lock-free code specifically

- Standard unit tests are necessary but not sufficient for concurrent code — they usually can't reliably reproduce a race. Where feasible, use a tool built for this (`loom` for exhaustively exploring possible interleavings of a small piece of concurrent Rust code) rather than relying on "ran fine under load testing" as proof of correctness — load testing under-samples rare interleavings by nature.
- State explicitly in the Plan/Verification report which concurrency-correctness method was used (`loom`-verified vs. load-tested vs. reviewed-by-a-second-engineer) — "I wrote a lock-free structure and it passed the tests I wrote" is not the same claim as "this was verified against the actual race conditions it's exposed to," and the Verification report's honesty requirement (Section 16) means saying explicitly which one actually happened.
