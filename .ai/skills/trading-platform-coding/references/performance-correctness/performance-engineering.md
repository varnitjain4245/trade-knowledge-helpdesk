# Performance Engineering — Proving "Efficient," Not Just Claiming It

`rust-backend.md` covers the baseline hot-path rules (no allocation, no locks, socket tuning). This file covers the next level down — techniques that matter once the basics are in place, and, just as important, how to actually prove a change made things faster rather than asserting it.

## Memory layout

- **False sharing**: when two variables written by different threads/cores land on the same CPU cache line, each write invalidates the other core's cache, silently destroying the benefit of otherwise-correct lock-free code. Pad hot, independently-written fields to their own cache line with `#[repr(align(64))]` (64 bytes is the common x86_64 cache line size — confirm for your actual deployment CPU rather than assuming). This applies most directly to ring-buffer producer/consumer indices — see `concurrency-patterns.md`.
- **Struct-of-arrays vs array-of-structs**: when iterating over many order-book entries and only touching one or two fields each time (e.g. scanning prices), a struct-of-arrays layout (`prices: Vec<i64>, quantities: Vec<u64>` as parallel arrays) can dramatically outperform an array-of-structs (`Vec<OrderBookEntry>`) because it keeps the CPU cache full of relevant data instead of loading unused fields along with each entry. Don't reach for this by default — it adds real complexity — but consider it specifically for tight scan loops over large collections where profiling shows cache misses are the bottleneck.
- **Field ordering**: within a single hot-path struct, group fields that are accessed together physically close together, and put less-frequently-accessed fields (e.g. debug/audit metadata) at the end so the hot fields fit in fewer cache lines.

## Branch prediction and control flow

- Hot loops with a predictable outcome (e.g. "is this order valid" being true 99.9% of the time) benefit from structuring the common case as the straight-line path with early-out only for the rare case — this isn't usually something to hand-optimize with intrinsics, but avoid needlessly interleaving rare-error-handling logic into the middle of the common path where it can defeat the branch predictor and bloat the instruction cache.
- Prefer `#[inline]` hints only on small, hot, frequently-called functions where profiling shows the call overhead matters — over-using `#[inline]` bloats the binary and can hurt icache behavior, which is a real cost, not a free win.

## SIMD (only when profiling justifies it)

- Rust's autovectorizer will already vectorize simple, predictable loops in release mode with LTO — check the generated assembly or a profiler before assuming manual SIMD (`std::simd` or a crate) is necessary. Manual SIMD is a real complexity and correctness cost; reserve it for a proven, measured bottleneck (e.g. bulk price-level scanning across a wide book), not applied speculatively.

## Avoiding hidden syscalls in the hot path

- Getting the current time (`Instant::now()`/`SystemTime::now()`) can be more expensive than expected depending on the OS clock source — if timestamps are needed on every hot-path message, measure this specifically rather than assuming it's free; consider a coarser/cached clock read strategy if profiling shows it matters.
- Logging: even a "fast" logger can hide an unexpected syscall (flush behavior) — route hot-path log events through a pre-allocated lock-free channel to a dedicated logging thread (mentioned in `rust-backend.md`) so the hot-path thread never blocks on I/O, ever.

## Benchmarking methodology (how to actually prove a claim)

- **Microbenchmarks**: use `criterion` for any hot-path function in isolation. Run with enough iterations that noise averages out, and check criterion's own reported confidence interval, not just the point estimate.
- **End-to-end latency**: use an HDR histogram (the `hdrhistogram` crate or equivalent) capturing every request in a realistic load test, not just a handful of manual timings — report p50/p99/p99.9, never just an average (see `rust-backend.md`'s "Measurement discipline" section for why the average hides the behavior that actually matters).
- **Realistic load shape**: benchmark against a burst pattern representative of market open/news events, not a smooth steady-state rate — tail latency under burst is usually where a design's real weaknesses show up, and a steady-state-only benchmark can hide a serious problem.
- **Before/after comparison discipline**: when claiming an optimization helped, benchmark the exact same code path before and after on the same hardware in the same run/session — cross-machine or cross-day comparisons introduce enough noise to make a claimed improvement unreliable.
- **Never claim a performance win without a number attached.** "This should be faster" is not evidence — see Section 16 (Self-Verification) in SKILL.md and the Complexity claims / Acceptance thresholds fields in the required Plan and Verification report templates.

## When NOT to chase more performance

- If the current measured p99.9 already meets the 5-8ms budget with margin, resist further micro-optimization — it adds complexity and bug surface for a latency win nobody asked for and that isn't visible to the business. Flag headroom explicitly in the Verification report rather than silently spending more engineering effort chasing it.
- Performance work that trades away correctness clarity (e.g. `unsafe` block, hand-rolled SIMD, aggressive inlining) needs to be justified by an actual measured bottleneck it fixes — cite the specific profiling evidence in the Plan's "Critical-path status" field, not a general sense that "this part is probably slow."
