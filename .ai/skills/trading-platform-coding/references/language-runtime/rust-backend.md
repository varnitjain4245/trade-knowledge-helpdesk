# Rust Backend — Hot Path Implementation (5-8ms target, tuned TCP/UDP)

At 5-8ms end-to-end with standard tuned sockets, you do not need kernel bypass, FPGA, or exotic hardware. This budget is achievable through disciplined allocation, socket tuning, and avoiding accidental syscalls/locks in the hot path. Treat every one of these as a default, not a suggestion, for any code between "order received" and "order acknowledged."

**Scope these rules to the measured critical path — not the whole service.** "Zero allocation" and "no locks" are hot-path rules for the specific, profiled sequence between order intake and order acknowledgment. Applying them uniformly to code that isn't actually on that path (admin endpoints, batch reporting jobs, startup/config loading, connection setup) buys nothing and actively costs something: it pushes ordinary code toward `unsafe`, manual memory management, and lock-free structures it doesn't need, which is more places for a genuine bug to hide for no latency benefit. Identify the critical path by profiling first (see "Measurement discipline" below), apply these rules there specifically, and let everything else use normal, safe, boring Rust — a `Mutex` in your admin API is fine.

## OpenAPI / Swagger Auto-Bootstrapping (Rust Services)
For any HTTP REST API surface (e.g. Axum, Actix-web, or Poem service):
- **Auto-bootstrap interactive Swagger UI** via `utoipa` + `utoipa-swagger-ui` or `poem-openapi`.
- Mount `/swagger-ui` or `/docs` zero-config so documentation is automatically served when the backend starts.
- Annotate all API handlers with summary, description, request/response schemas, and error types matching `references/foundation/api-contract-design.md`.

## Allocation discipline
- **Zero allocation in the hot path, by default.** Pre-allocate everything at startup: buffers, connection pools, order book structures. If a hot-path function needs a `Vec`/`Box`/`String`, that's a design smell — use a pre-sized array, a slab/arena allocator, or an object pool instead.
- Use a fast global allocator (`mimalloc` or `jemalloc`) even so — it's a safety net, not a substitute for not allocating.
- Avoid `.clone()` on anything larger than a few bytes in the hot path. Pass references or `Copy` types (fixed-size structs) instead.
- No `format!`, `println!`, `.to_string()`, or string formatting anywhere in the hot path — these allocate and are surprisingly slow. Log via a pre-allocated, lock-free logging channel that's drained on a separate thread.

## Concurrency
- Prefer **thread-per-core with explicit CPU pinning** over a general work-stealing async runtime (tokio's default scheduler) for the matching engine core loop — tokio's scheduler adds jitter that's hard to bound. Tokio is fine for connection handling / non-hot-path I/O; keep the matching engine itself on pinned threads with a tight, predictable loop. This is an architectural/code-design decision and stays in scope.
- Use lock-free SPSC/MPSC ring buffers (`ringbuf`, `rtrb`, or a hand-rolled ring buffer) to move messages between the network I/O thread and the matching engine thread — never a `Mutex` on the hot path.
- **CPU pinning execution (`taskset`, `isolcpus` kernel boot param) and NUMA topology are deployment/infrastructure configuration, not application code — out of scope for this skill per the platform's own SDLC split.** Identify and report these as deployment prerequisites rather than configuring them: state explicitly which cores/NUMA node the matching engine thread(s) need pinned and why (e.g. "matching engine thread should be pinned to an isolated core on the same NUMA node as the NIC handling market-data ingress"), and hand that requirement to the infrastructure team rather than writing `isolcpus` kernel parameters or systemd unit pinning directives yourself, unless a task explicitly puts infra configuration in scope.

## Socket tuning (this is your latency budget lever, since you're not doing kernel bypass)
- `TCP_NODELAY` — always, to disable Nagle's algorithm. Non-negotiable for a request/response order path. Set via the socket API in application code (e.g. `TcpStream::set_nodelay`) — this is in-scope application code, not infra config.
- Consider `SO_BUSY_POLL` / busy-polling the socket instead of blocking on epoll for the last few hundred microseconds of latency — trades CPU for latency, worth it on a dedicated core. Also set programmatically via socket options — in-scope.
- Tune `SO_RCVBUF`/`SO_SNDBUF` to avoid buffer-induced delay, but don't oversize — bigger buffers can increase tail latency under bursty load (bufferbloat). In-scope, set via socket options in code.
- Consider `SO_REUSEPORT` with per-core listener sockets so each core handles its own connections without cross-core contention — in-scope, set in code.
- **NIC-level interrupt coalescing (`ethtool -C`) is OS/hardware configuration outside the application boundary — report it as a deployment prerequisite, don't configure it as part of this task.** State the requirement explicitly (e.g. "NIC interrupt coalescing should be tuned toward latency over throughput on the interface handling order traffic") and hand it to infrastructure, the same as CPU pinning above, unless infra configuration is explicitly in scope for the current task.
- If UDP multicast is used for market data fan-out, size the kernel receive buffer generously there specifically (multicast fan-out is bursty) — but keep it separate from the tightly-tuned order-path TCP buffers. (Kernel receive buffer sizing via `SO_RCVBUF` is a code-level socket option, in-scope; if it requires raising a system-wide `net.core.rmem_max` sysctl ceiling, that ceiling change itself is infra's call — report the needed value.)

## Serialization
- No `serde_json` (or any JSON) in the hot path — it allocates and is slow relative to your budget. Use a fixed-layout binary format for the wire, not a `#[repr(C)]` struct dumped directly.
- **`#[repr(C)]` alone is not a wire-format specification.** It fixes field order and disables field reordering, but it does *not* fix byte order (endianness), and its padding/alignment rules are platform- and target-dependent — a struct that round-trips fine between two processes on the same machine can silently misparse across a different architecture, a different compiler version, or even a different alignment of the same struct after an unrelated field gets added. Never treat `#[repr(C)]` as "the wire format" — treat it as an in-memory layout that still needs an explicit, documented serialization step on top of it.
- **What "explicit wire format" actually requires**: for every field, document the byte width (`u32`, not `usize`/`isize` — those are platform-dependent), the explicit byte order (pick one, e.g. little-endian for x86_64 deployment, and state it), and the exact byte offset. Hand-write the to/from-bytes conversion using `to_le_bytes()`/`from_le_bytes()` (or `to_be_bytes()`/`from_be_bytes()`, whichever endianness is chosen) per field, and pair it with a round-trip test that serializes on one build and deserializes on another to catch drift. **Do not use `#[repr(C, packed)]` as a shortcut for this** — packed structs make it easy to take a reference to a field that isn't properly aligned, which is undefined behavior in Rust even though the compiler often doesn't warn about it at the call site; the explicit per-field byte-conversion approach avoids this risk entirely and is barely more code.
- `zerocopy`/`rkyv` are reasonable choices *if* you explicitly configure and test their byte-order behavior — don't assume "zero-copy library" implies "wire-safe" without checking that specifically.
- Design the wire format so parsing is just reading fixed offsets — no length-prefixed variable fields on the critical path where avoidable.
- If integrating with exchange protocols (FIX, or a proprietary binary protocol), isolate the parsing/encoding for that protocol into its own module so it can be swapped or optimized independently of business logic, and follow that protocol's own explicit wire spec rather than inventing one.
- **Before this ships**: write a cross-build/cross-architecture round-trip test for every wire struct, not just a same-process serialize/deserialize test — that's the specific gap that lets this class of bug through.

## Data structures
- No `HashMap` lookups in the hot path where the key space is known/bounded (e.g. symbol IDs) — use a pre-sized array or perfect-hash indexed by a dense integer ID assigned at startup. This applies to both the symbol → book lookup AND any lookup inside the book itself (e.g. price level → orders).
- **Name complexity accurately — don't call a linear scan O(1).** A fixed-size array scanned with `.iter().find()`/`.contains()` is a **bounded linear scan, O(N) where N is the array length** — not O(1). For small N (e.g. a few hundred supported symbols or fewer) this is often the *right* choice anyway, since a small contiguous array is cache-friendly and can outperform a hash lookup in practice — but state it as "bounded linear scan, N≤X, chosen for cache locality" in your plan, not as O(1). If true O(1)/O(log n) is actually required (large N, or a claim your plan is relying on), use a dense-integer-indexed array (direct indexing, genuinely O(1)) or a perfect hash — not a scanned array relabeled.
- Avoid `dyn Trait` (dynamic dispatch) in the hot loop — use generics/static dispatch so the compiler can inline and optimize.
- **Symbol representation**: prefer a dense `SymbolId(u16)` or `SymbolId(u32)` assigned at startup (e.g. from a static symbol table loaded once) over a raw `[u8; N]` byte array threaded through hot-path structs. A dense integer ID gives genuine O(1) array indexing everywhere it's used (order book lookup, risk checks, logging) and is cheaper to compare/hash than a byte array — reserve the raw symbol bytes for the boundary where you parse wire/display text into a `SymbolId` once, not for repeated internal use.
- **Order book internals — be explicit, don't default to `Vec` + linear scan.** Best-bid/best-ask must be O(1) or O(log n), never a `.iter().max_by_key()`/`.min_by_key()` scan over an unsorted collection — that's O(n) on every single lookup, which defeats the entire latency budget on the single most frequent operation in the system. Use one of:
  - A price-indexed array/ladder (fixed price ticks mapped directly to array offsets) if the instrument's tick size and price range are bounded — gives O(1) best-price access.
  - A sorted structure (e.g. `BTreeMap<Price, PriceLevel>` or an intrusive skip list) if price range is unbounded — gives O(log n) with O(1) best-price via `first_key_value`/`last_key_value`.
  - Maintain bids sorted descending and asks sorted ascending so "best" is always the first element, never computed by scanning.
  - Whichever structure is chosen, insertion/cancellation cost matters as much as best-price read cost — check both, not just the read path.

## Error handling on the hot path
- `Result`, never `panic!`/`unwrap()`, on anything in the order path — a panic that unwinds mid-transaction is a correctness bug, not just a latency spike. Consider `panic = "abort"` in release profile so a bug fails fast and loud (triggering restart/failover) rather than leaving state inconsistent.
- Every rejected/failed order path must still produce a deterministic response to the caller within budget — "silently drop" is never acceptable on an order path.

## Build profile
- Release builds: `lto = true`, `codegen-units = 1`, `opt-level = 3`. Consider `target-cpu=native` if the deployment hardware is fixed and known.
- **`panic = "abort"` is conditional, not a default — it requires a supervisor/failover story to already exist before you enable it.** Aborting the matching-engine process converts a bug into an immediate hard outage; that is only a *safe* outcome if something else (a supervisor process, an orchestrator health check, a hot standby that takes over open orders) is guaranteed to detect the abort and fail over correctly, and if in-flight order state is recoverable or safely reconstructable after the abort. If that supervisor/failover mechanism doesn't exist yet, don't set `panic = "abort"` — an unwinding panic that at least gets caught and logged at a boundary is safer than an abrupt process death with nothing catching it. State explicitly, in the PR/plan, which failover mechanism this assumes before relying on this flag.
- Don't guess — measure with these flags in a realistic staging environment before assuming they help; occasionally `codegen-units = 1` regressions happen for icache-heavy code, verify with your actual matching engine.

## Measurement discipline
- Track **p99 and p99.9, not average** — a trading system's user experience is defined by its worst moments, not its typical one. A 2ms average with a 40ms p99.9 tail is worse than a steady 6ms.
- Use `criterion` for microbenchmarks on hot functions, and end-to-end latency histograms (HDR histogram) in staging/production under realistic load, not synthetic best-case pings.
- Profile with `perf` + flamegraphs before optimizing — don't guess where the time goes. Allocation and lock contention are the two most common surprises.
- Load-test with realistic burst patterns (market open, news events) — steady-state latency numbers hide the tail behavior that actually matters for a broking platform.

## Review checklist before calling backend hot-path code "done"
- [ ] Zero heap allocation in the order-received → order-acknowledged path
- [ ] No locks (`Mutex`/`RwLock`) in that path — lock-free structures only
- [ ] No JSON/string formatting in that path
- [ ] `TCP_NODELAY` set on order-path sockets (in application code)
- [ ] CPU pinning and NIC interrupt coalescing are reported as deployment prerequisites to infrastructure, not configured directly, unless infra config was explicitly in scope for this task
- [ ] Every error path produces a deterministic, bounded-time response — nothing silently dropped
- [ ] No floats used for price/quantity — fixed-point or integer minor-units throughout
- [ ] p99.9 latency measured under realistic burst load, not just average under steady load
- [ ] Wire structs have documented byte order and field widths, and a cross-build round-trip test — not just `#[repr(C)]` assumed to be sufficient
- [ ] If `panic = "abort"` is set, the supervisor/failover mechanism it depends on is named explicitly, not assumed
- [ ] Zero-allocation/no-lock rules were applied to the profiled critical path specifically, not blanket-applied to code that isn't actually on it
