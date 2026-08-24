# Memory Management Strategy — Pre-allocation, Allocators, and Jitter

`rust-backend.md` establishes "zero allocation on the hot path" as the baseline rule. This file covers the layer underneath that rule: how to actually achieve it (pre-allocation strategy), what backs it (allocator choice), and a latency-jitter source that's easy to miss entirely (page faults).

## Pre-allocation strategy

- **Everything the hot path touches should be allocated once, at startup, sized for the worst case you're willing to handle** — connection buffers, order-book capacity, ring-buffer capacity, audit-channel capacity (see `durability-and-audit.md`). "Worst case" needs an actual number, not a guess — size it from expected peak order rate × burst duration, and state that reasoning in the Plan when introducing a new pre-allocated structure.
- **Object pools** for anything that has a natural "checked out, used, returned" lifecycle on the hot path (e.g. a reusable buffer for constructing an outgoing message) — check one out of the pool instead of allocating, return it when done. A pool is itself a small, bounded, pre-allocated structure; don't let the pool's own management logic become an unbounded allocation source (e.g. a pool that grows unboundedly under load defeats the purpose).
- **Arena/bump allocators** for a batch of short-lived allocations that all get freed together (e.g. all the temporary state for processing one incoming message) — allocate a chunk once, hand out slices from it with a bump pointer, reset the whole arena at the end of the batch instead of freeing each piece individually. This trades individual-object flexibility for allocation speed and predictability; only reach for it where profiling shows individual allocation/deallocation overhead actually matters.
- **State the pre-allocation sizing and its worst-case assumption explicitly** wherever it's introduced — a silently-undersized pre-allocated buffer that falls back to an unexpected heap allocation under a real burst is a worse failure mode than never having pre-allocated at all, because it looks correct in every test that doesn't hit the actual limit.

## Allocator choice

- Even with hot-path code aiming for zero allocation, the rest of the service (connection setup, admin endpoints, startup, the audit-logging writer thread) still allocates normally — a fast global allocator (`mimalloc` or `jemalloc`) is a reasonable default for the whole binary as a safety net, not a substitute for the zero-allocation discipline on the actual hot path.
- Don't assume a faster global allocator "solves" a hot-path allocation problem — it reduces the cost of an allocation you shouldn't be doing in the first place, but the right fix is still removing the allocation, not making it cheaper. Measure with and without to confirm which is actually true for a given case rather than assuming.

## Page-fault jitter (an easy-to-miss latency source)

- A pre-allocated buffer that's been allocated but never *touched* (written to) can still cause a page fault the first time the hot path actually writes to a previously-untouched page — this shows up as a rare, hard-to-reproduce latency spike, exactly the kind of thing that ruins a p99.9 number while looking fine on average.
- **Pre-fault/pre-touch pre-allocated hot-path memory at startup** — write to every page of a pre-allocated buffer once, during initialization, before the service starts accepting real traffic, so the OS has already backed every page with physical memory before the hot path ever touches it for real.
- **Huge pages** (reducing the number of page-table entries and TLB misses for large pre-allocated regions) can help further, but configuring them is OS/deployment-level (`madvise`/hugetlbfs setup) — per this skill's Boundaries section, that's a deployment prerequisite to report to infrastructure, not something to configure directly, unless infra config is explicitly in scope for the task.
- **Memory locking** (`mlock`, preventing pre-allocated hot-path memory from being swapped out) is the same category — report as a deployment prerequisite rather than assuming it's already in place.

## Verifying this actually worked

- The way to know pre-touching/pre-allocation is working is the same as everywhere else in this skill: measure, don't assume. A p99.9 latency histogram that shows no early-run outliers (compared to one that does) is the evidence a pre-fault strategy is actually effective — cite that comparison in the Verification report if claiming this as a fix for observed jitter, per `performance-engineering.md`'s benchmarking-methodology rules.

## Review checklist before calling memory-strategy work "done"
- [ ] Pre-allocation sizing is based on a stated worst-case number, not a guess, and that reasoning is in the Plan
- [ ] Any object pool has a bounded size — it can't silently degrade into unbounded allocation under load
- [ ] Hot-path pre-allocated memory is pre-touched at startup, not left to fault in on first real use
- [ ] Huge pages / `mlock` are reported as deployment prerequisites, not assumed configured or configured directly outside of explicitly-in-scope infra work
- [ ] Any claim that a memory-strategy change fixed observed jitter is backed by a before/after p99.9 comparison, not asserted
