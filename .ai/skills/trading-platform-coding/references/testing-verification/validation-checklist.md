# Validation Checklist — Final Gate Before Calling Any Task Done

This consolidates every checklist scattered across the other reference files into one place, so a final review only needs one file open, not five. Run through all sections relevant to the task — not every section applies to every change (a pure frontend change skips the Rust section; a non-security-sensitive refactor still gets the security pass, since input handling can hide anywhere).

## Process (every task, no exceptions)
- [ ] Referenced or discoverable PRD, HLD/LLD, and Planning-stage ticket were actually located and read before the Plan was written; missing artifacts were stated, and only load-bearing gaps blocked work — see Pipeline Position and Task tiers in SKILL.md
- [ ] A `## Plan` was written and shared before implementation began, using the required format (Section 3 of SKILL.md), with every field filled in — including Upstream reference, Codebase state, Type/domain invariants, Critical-path status, Complexity claims, and Red step
- [ ] The task type was correctly matched to its adaptability profile (Section 17) — full TDD for new logic, reproduce-first for bug fixes, rollback-planned for migrations, etc.
- [ ] A `## Verification report` was produced at the end, using the required format (Section 16), with real commands and real results — not a prose summary standing in for it
- [ ] Nothing outside this skill's stated Boundaries was touched (infra config, deployment actions, IAM/access policy, unrelated services) without it being explicitly in scope for this task

## Security scanning — MANDATORY, every task, no tier exception (`references/compliance-safety/security-scanning/`)
- [ ] SAST scan actually ran (`sast-code-scanning.md`) — tool + command stated, findings listed with file:line and severity, not summarized as a bare pass/fail
- [ ] Dependency/SCA scan ran on every package installed or version-changed this task (`dependency-vulnerability-scanning.md`) — required precisely because dependency installation is now automatic, this scan is the safety net that makes that safe
- [ ] Secrets/exposure scan ran on the full diff (`secrets-and-exposure-scanning.md`) — no hardcoded credentials; any found are flagged for rotation, not just deleted from the diff
- [ ] Every new/changed endpoint's actual exposure (public/internal/admin), auth presence, and error-response verbosity were checked, not assumed
- [ ] Any critical/high finding from any of the three scans was surfaced explicitly in the Verification report — either the user explicitly accepted it, or it was fixed and the fix re-scanned, never silently omitted
- [ ] If any finding triggered the failure loop-back (SKILL.md), the loop actually completed — fix, re-run the specific failing check, confirm it passes — not just attempted once and left unresolved

## Rust backend (if this task touched `references/language-runtime/rust-backend.md` territory)
- [ ] Zero heap allocation in the order-received → order-acknowledged path
- [ ] No locks (`Mutex`/`RwLock`) in that path — lock-free structures only
- [ ] No JSON/string formatting in that path
- [ ] `TCP_NODELAY` set on order-path sockets (in application code)
- [ ] CPU pinning and NIC interrupt coalescing are reported as deployment prerequisites to infrastructure, not configured directly, unless infra config was explicitly in scope for this task
- [ ] Every error path produces a deterministic, bounded-time response — nothing silently dropped
- [ ] No floats used for price/quantity — fixed-point or integer minor-units throughout
- [ ] p99.9 latency measured under realistic burst load, not just average under steady load
- [ ] Wire structs have documented byte order and field widths, and a cross-build round-trip test — not `#[repr(C)]` or `#[repr(C, packed)]` assumed to be sufficient
- [ ] If `panic = "abort"` is set, the supervisor/failover mechanism it depends on is named explicitly, not assumed
- [ ] Zero-allocation/no-lock rules were applied to the profiled critical path specifically, not blanket-applied to code that isn't actually on it
- [ ] Any lookup/data-structure complexity claim is accurate (a scanned array is "bounded O(N)," not "O(1)") — see Section 6 of SKILL.md and the Data Structures section of `rust-backend.md`

## Go backend (if this task touched `references/language-runtime/go-backend.md` territory)
- [ ] Every error is checked and either handled or wrapped with `%w`, never discarded with `_`
- [ ] Every long-lived goroutine has an explicit owner and a `context`/channel-driven shutdown path
- [ ] `go test -race ./...` passes on any package with concurrent code
- [ ] No `float64`/`float32` for price, quantity, or money
- [ ] `interface{}`/`any` used only where nothing more specific genuinely fits

## Java backend (if this task touched `references/language-runtime/java-backend.md` territory)
- [ ] `BigDecimal` (from `String`/`long`, never a `double` literal) used for all price/quantity/money
- [ ] No swallowed exceptions (empty `catch` blocks) anywhere in the diff
- [ ] Every `ExecutorService`/thread pool has an explicit shutdown path
- [ ] Every `CompletableFuture` chain has explicit exception handling
- [ ] GC algorithm choice stated explicitly for any latency-sensitive service

## Performance engineering (if this task claims a performance benefit, or touches confirmed-hot-path code — `references/performance-correctness/performance-engineering.md`)
- [ ] Every performance claim has a benchmark number attached (criterion microbenchmark or HDR-histogram end-to-end) — not asserted without evidence
- [ ] Benchmarks used a realistic burst load shape, not steady-state only, and report p99/p99.9, not just average
- [ ] Any `unsafe`, manual SIMD, or aggressive inlining used for performance is justified by cited profiling evidence, not a general sense that a section "seems slow"
- [ ] Cache-line padding applied where independently-written fields could false-share, if this is concurrent hot-path code

## Concurrency (if this task adds or modifies lock-free/concurrent code — `references/performance-correctness/concurrency-patterns.md`, required, not optional)
- [ ] A proven crate was used rather than hand-rolled lock-free code, unless a specific justified reason ruled that out
- [ ] Memory ordering (Acquire/Release vs Relaxed) was reasoned about explicitly, not assumed correct
- [ ] Concurrency correctness verification method is stated explicitly in the Verification report (loom-verified / load-tested / second-engineer-reviewed) — not left implicit
- [ ] Panic safety inside any shared lock-free mutation was considered — smallest possible critical section, ideally a single atomic store

## Memory management (if this task involves pre-allocation sizing, pooling, or unexplained latency jitter — `references/performance-correctness/memory-management.md`)
- [ ] Pre-allocation sizing is based on a stated worst-case number, not a guess
- [ ] Any object pool is bounded — can't silently grow into unbounded allocation under load
- [ ] Hot-path pre-allocated memory is pre-touched at startup
- [ ] Huge pages / `mlock` are reported to infrastructure as prerequisites, not assumed or configured directly outside explicit scope

## Durability & audit logging (if this task adds any logging/persistence near the order path — `references/compliance-safety/durability-and-audit.md`, required, not optional)
- [ ] No blocking I/O (disk write, fsync, network call) on the hot path — only a non-blocking channel push
- [ ] Backpressure behavior (channel full) is an explicit, counted, stated decision — never a silent drop
- [ ] Ordering guarantee (or explicit lack of one) matches the actual compliance requirement, not an assumption
- [ ] Real compliance requirements (retention, fields, tamper-evidence) came from an actual source and were confirmed, not assumed by this skill — flag as an Open Question in the Plan if not yet provided

## Test execution (every task — `references/testing-verification/test-execution.md`)
- [ ] `cargo nextest run` (or frontend equivalent) actually executed, with real pass/fail counts reported — not "tests should pass"
- [ ] Any dependency installation, upgrade, or addition was explicitly approved by the user after implementation; exact package-manager commands and resulting verification are recorded. If approval was not granted, the blocked checks are listed under `Not verified`.
- [ ] Any test needing retries is flagged as a tracked flakiness follow-up, not silently accepted
- [ ] Coverage checked for untested branches in changed code, especially hot-path code
- [ ] Fuzz testing considered (and its use or deferral stated) for any parsing/wire-boundary code changed

## Integration testing & per-file cadence (every multi-file or cross-boundary task — `references/testing-verification/integration-testing.md`)
- [ ] Each file with associated test logic was tested immediately after being written/changed, not only in a final batch run
- [ ] Any cross-service or cross-language boundary touched by this task has an integration test, not unit tests on each side alone
- [ ] Real external dependencies used in integration tests run as ephemeral instances (`testcontainers` or equivalent), not a shared persistent environment
- [ ] Any changed wire-format/API contract was tested against the actual output/input handling of both sides, not two independently-assumed-correct unit tests
- [ ] Integration tests clean up their own state and don't depend on run order

## Design quality (every UI change, and every newly-scaffolded service — `references/client-ui/design-system.md`)
- [ ] No unmodified default framework palette/gradient used without a project-specific token layer
- [ ] No emoji used as functional icons or section markers
- [ ] Numeric/price columns use tabular figures with consistent decimal alignment
- [ ] Gain/loss and buy/sell coloring has a non-color-only secondary cue
- [ ] Backend: transport, domain logic, and persistence are in distinguishable layers, not inlined into one handler
- [ ] Naming (components, functions, types) is domain-specific, not generic-tutorial naming

## Project structure (any task scaffolding a new service, app, or top-level folder — `references/foundation/project-structure.md`)
- [ ] Backend and frontend are separated at the top level, never interleaved
- [ ] Each backend service has its own independent dependency manifest
- [ ] `shared/`, if present, contains contracts/schemas only, not shared mutable application code, unless explicitly decided upstream
- [ ] The structure was stated in the `## Plan` before files were created
- [ ] The full directory skeleton (backend/frontend/service folders) was created before the first implementation file was written anywhere inside it — not interleaved

## UX design (every UI change — `references/client-ui/ux-design.md`)
- [ ] Every async action has distinct, specific pending/success/failure states
- [ ] Invalid actions are prevented and explained, not just caught after submission
- [ ] Critical/hard-to-reverse actions have a real-consequence confirmation step
- [ ] Full keyboard navigation and visible focus states work, especially for order entry
- [ ] Contrast meets WCAG AA in both light and dark mode; color is never the sole status signal
- [ ] Error messages are specific and actionable, in plain interface language — no raw backend errors surfaced
- [ ] Empty states guide the user to a next action

## Comprehensive testing gate (Standard/Critical tasks — `references/testing-verification/comprehensive-testing.md`)
- [ ] Full regression suite (not just this task's files) run, with real pass/fail counts
- [ ] Explicit exploratory/edge-case pass done and findings addressed
- [ ] E2E coverage present for any change touching order entry, confirmation, or settlement/P&L display
- [ ] Performance benchmarked (not assumed) for any hot-path-adjacent change
- [ ] Accessibility audit run for any new/changed UI screen
- [ ] Cross-platform/responsive behavior checked for any new/changed UI screen
- [ ] Any shared-type/wire-format/API change has an explicit backward-compatibility test
- [ ] The `## Comprehensive test pass` report has zero unresolved entries under "Bugs found and not yet fixed"

## Clarification protocol (any task where an open question was raised, or where one arguably should have been — `references/foundation/clarification-protocol.md`)
- [ ] The codebase/HLD/LLD/ticket was actually checked for an answer before asking
- [ ] Any question raised named a specific fork with a recommended default, not an open-ended prompt
- [ ] Any assumption made instead of asking was stated explicitly in the Plan's "Codebase state: Assumed" field, not left implicit

## Frontend (if this task touched `references/client-ui/frontend.md` territory)
- [ ] No float/double used for price, quantity, or money anywhere
- [ ] Rendering is throttled to frame rate, not driven 1:1 by incoming message rate
- [ ] Stale data is visibly indicated, never silently shown as current
- [ ] Reconnect flow requests a fresh snapshot rather than trusting resumed incremental updates
- [ ] Order submission is disabled until a definitive backend response, not a timeout guess
- [ ] Long lists (order book, watchlist) are virtualized
- [ ] For any stateful/async change: the Behavioural Flow Audit was run (state map, touchpoint trace, named-pattern hunt for async races/stale closures/effect interference)

## API contract design (any new or changed REST endpoint — `references/foundation/api-contract-design.md`)
- [ ] The OpenAPI spec was designed and reviewed before implementation (design-first), not generated from the code after
- [ ] Every operation has a stable `operationId`, `summary`, `description`, and both success and error examples
- [ ] Price/quantity/money fields are `type: string` with a documented decimal format — never `number`/`double`
- [ ] Every operation declares its required security scheme explicitly in the spec, and the handler actually enforces it
- [ ] No real credentials/tokens appear in any example
- [ ] The spec passes lint (Spectral or platform-equivalent) with no unresolved errors
- [ ] Any breaking change carries a new version; deprecations are marked with a stated migration path
- [ ] A contract test (Schemathesis/Dredd or equivalent) validates the real implementation against the published spec

## Security (`references/compliance-safety/security-review.md` — every task, since input handling can hide anywhere)
- [ ] Every `unsafe` Rust block has a written safety justification
- [ ] No new dependency added to the hot path without being named and justified
- [ ] Server-side authorization checked, not inferred from client-supplied data
- [ ] No secrets/PII in logs or error output
- [ ] Changed *behavior* (not just changed code) has been explicitly considered via a differential-review pass, not just the diff read in isolation
- [ ] Any known-footgun pattern used (float comparison, mutex ordering, `?`-chained error type mismatches) is flagged explicitly, even if believed safe in the current usage
- [ ] Every ID-taking API endpoint verifies caller ownership/entitlement server-side, not just valid authentication (OWASP API Top 10, `security-review.md`)
- [ ] Response schemas return only the fields the consumer needs, and request bodies deserialize into a purpose-built request type, never an internal domain/database model directly

## Codebase understanding (`references/foundation/codebase-context.md` — for any unfamiliar or shared-code change)
- [ ] Component archetype identified before modification (hot-path service / UI component / shared library / infra-adjacent)
- [ ] Every caller of a changed shared type/signature was found, not assumed absent
- [ ] Existing codebase conventions were matched, not overridden with a personal preference
- [ ] The risk-profile split (verified / assumed / not explored) was stated explicitly, not left implicit

## If any box above is unchecked
Don't silently mark the task done anyway. State which box is unchecked and why in the Verification report's "Not verified" field — an honest gap disclosed is a minor issue; an unchecked box hidden behind a confident completion claim is the failure mode this whole skill exists to prevent.
