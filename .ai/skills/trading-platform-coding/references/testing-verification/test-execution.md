# Test Execution & Verification — Running What Section 11 Requires You to Write

Section 11 (SKILL.md) and the Plan template's "Red step" field establish the *discipline*: write a failing test first, confirm it fails for the right reason, then implement. This file covers the *mechanics*: how to actually run, verify, and measure coverage on Rust tests efficiently — the part that turns "I wrote tests" into "I verified this code," per Section 16's requirement that a completion claim needs an attached verification method. For the equivalent unit-test tooling in Go and Java, see the Testing sections of `go-backend.md` and `java-backend.md`. For integration/cross-boundary tests and the required per-file test cadence (test immediately after each file, not batched at the end), see `references/testing-verification/integration-testing.md` — that file's rules apply regardless of which language(s) a task touches.

## Running tests — prefer `cargo nextest` over bare `cargo test`

- `cargo nextest run` executes each test in its own process, which is both faster (better parallelism than `cargo test`'s default) and safer — a test that segfaults or hangs can't take down the whole run or silently corrupt shared state between tests the way it can under `cargo test`'s default threaded model.
- Use `cargo nextest run --retries N` only for tests with a known, understood source of non-determinism you haven't eliminated yet (e.g. a timing-sensitive integration test) — retries mask flakiness, they don't fix it. Treat a test that needs retries as a tracked follow-up to actually fix, not a permanent state. Never apply retries to hot-path/concurrency tests specifically, since a retry there could hide the exact race condition `concurrency-patterns.md` requires you to catch.
- For CI or any automated verification step, use `cargo nextest run --profile ci` (or equivalent) producing JUnit/JSON output — that structured output is what makes "tests run: pass/fail" in the Verification report an actual checkable claim rather than a paraphrase of terminal output.
- `cargo test -- --nocapture` when actively debugging a failing test and needing to see `println!`/`dbg!` output — not for routine runs, where suppressed output keeps the signal-to-noise ratio high.

## Fixtures and parametrized tests — `rstest`

- Prefer `rstest`'s `#[case]`/`#[fixture]` over hand-rolled loops-inside-a-single-test-function for testing the same logic against multiple inputs (e.g. the limit-order validator's zero-quantity/negative-price/unsupported-symbol cases) — each case shows up as its own named, independently-passing-or-failing test, which is far more useful for pinpointing exactly what broke than one test function with an internal loop that just reports "failed on iteration 3."
- Use `#[fixture]` for shared setup (e.g. constructing a populated `OrderBook` for several tests) so setup logic lives in one place — but keep fixtures simple and fast; a fixture that itself does meaningful work risks becoming something that needs its own test.

## Coverage measurement — `cargo-llvm-cov`

- Use `cargo llvm-cov` (or `cargo llvm-cov nextest` to combine both) to measure actual coverage rather than assuming a test suite is thorough because it "feels" thorough — this directly operationalizes Section 11's "identify missing coverage actively" rule with a real number instead of a guess.
- Coverage percentage is still a signal, not a target to game (Section 11 already establishes this) — use the coverage report specifically to find *untested branches* (an error path, an edge case) worth a deliberate look, not to chase a percentage with low-value tests padding it out.
- For hot-path code specifically, cross-reference coverage gaps against the Complexity claims and Critical-path status fields in the Plan — an untested branch in confirmed hot-path code is a materially bigger risk than one in a rarely-touched admin utility, and should be prioritized accordingly.

## Fuzzing for parsing/boundary code — `cargo-fuzz`

- Any code parsing external input (wire-format deserialization, the parsing boundary described in `rust-backend.md`'s serialization section and demonstrated in `examples/limit-order-validator.md`) is a strong candidate for fuzz testing in addition to unit tests — unit tests check the cases you thought of; <cite index="14-1">coverage-guided fuzzing with AddressSanitizer catches complex memory vulnerabilities and malformed-input crashes that traditional unit tests often miss entirely</cite>, which matters specifically at a boundary parsing untrusted wire data.
- This is a "when it earns its cost" tool, not a default for every function — reserve it for boundary/parsing code specifically, per the same proportionality principle as everything else in this skill (Section 9's "don't optimize speculatively" applies equally to "don't fuzz speculatively").

## What "tested my files after generation" actually means as a required step

After any implementation is generated (by this skill or reviewed after being generated elsewhere), before it's considered done:
1. Run `cargo nextest run` (or the frontend's equivalent test runner) and report the actual pass/fail counts in the Verification report — not "tests should pass."
2. If new logic was added without corresponding new tests, that's a gap to name explicitly, not silently skip — see Section 11's characterization-test guidance for legacy code with no existing coverage.
3. For anything touching a parsing/wire boundary, note in the Verification report whether fuzz testing was run or is a recommended follow-up — don't silently omit it.
4. Cross-check against `validation-checklist.md`'s Process section — "tests run" there means this section's actual mechanics, not a description of intent.
5. For any task touching more than one file, this run-after-generation step happens **per file, immediately after that file is written or edited** — see `references/testing-verification/integration-testing.md`'s per-file cadence section for the full rule and why batching to one end-of-task run is not an acceptable substitute.

## Review checklist before calling any test-execution pass "done"
- [ ] `cargo nextest run` (or frontend equivalent) was actually executed, with real pass/fail counts in the Verification report
- [ ] Any test requiring retries is flagged as a tracked flakiness follow-up, not silently accepted as normal
- [ ] Coverage was checked for untested branches in changed code, especially anywhere touching the hot path
- [ ] Parsing/boundary code changes were checked against whether fuzz testing applies, not silently skipped
