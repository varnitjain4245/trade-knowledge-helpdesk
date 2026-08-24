# Comprehensive Testing — Evidence-Based Completion Gate

`test-execution.md` covers unit-test mechanics. `integration-testing.md` covers cross-boundary tests and the per-file cadence. This file is the **consolidating gate** for Standard and Critical tasks: run every applicable row and report the evidence. Do not claim that software is bug-free; say which checks passed, which were not applicable, and what remains unverified.

## The test-type matrix — run every row that applies to the task

Not every task touches every row (a one-line backend config change doesn't need a full E2E pass) — but skipping a row must be a stated decision in the Verification report, not a silent omission. Use Section 17's (Adaptability) task-type judgment to scope which rows apply, and say so explicitly.

| Test type | What it catches that others don't | Tooling on this platform | When it runs |
|---|---|---|---|
| **Unit** | Logic errors in a single function/module in isolation | `cargo nextest`/`rstest` (Rust), `go test` table-driven (Go), JUnit5 (Java), Jest/Vitest (React), `flutter test` (Flutter) — see `test-execution.md` | Per file, immediately after writing it (per-file cadence, `integration-testing.md`) |
| **Integration** | Real collaborator (DB, broker, downstream service) behaving differently than a mock assumed; cross-language contract mismatches | `testcontainers-*`, wire-format round-trip tests — see `integration-testing.md` | At each vertical-slice checkpoint, and always before the final Verification report |
| **End-to-end (E2E)** | A full real user flow breaking somewhere across the whole stack, even when every individual layer's tests pass | Playwright or Cypress (React web), `integration_test` package (Flutter) — real browser/device, real (or realistically faked) backend | Before calling any user-facing feature complete; required for any change touching order entry, confirmation, or the settlement/P&L display path |
| **Regression** | A change silently breaking previously-working behavior elsewhere in the system | Full existing test suite (unit + integration + E2E) run as a whole, not just the tests for files this task touched | Always, before the final Verification report — this is the specific test-type that per-file testing alone cannot catch, since a per-file run only proves that file didn't break, not that nothing *else* did |
| **Exploratory / edge-case sweep** | Bugs no automated test was written for because no one thought of the input | Manual reasoning pass: boundary values (zero, negative-where-invalid, max-size, empty collections), concurrent/race scenarios, malformed/adversarial input at every parsing boundary | After the "happy path" implementation and its planned tests are done, before considering the feature complete — actively ask "what input would break this that I haven't tested," per Section 11 |
| **Non-functional: performance** | A change that's functionally correct but too slow, or introduces a regression against the latency budget | `criterion` (Rust), `go test -bench`, JMH (Java) for microbenchmarks; HDR-histogram/k6-style load tests for end-to-end — see `performance-engineering.md` | Required for any change on or near the confirmed hot path, or any claim of a performance improvement |
| **Non-functional: security** | Input-handling and auth gaps that functional tests don't target because they only test intended usage | `security-review.md`'s differential-review pass, dependency/vulnerability scan for new dependencies, explicit adversarial-input tests at parsing boundaries | Required for any change touching input handling, auth, or a new dependency |
| **Accessibility** | Usability failures for keyboard-only or screen-reader users that a sighted-mouse-only manual check won't surface | Automated: axe-core/Lighthouse accessibility audit for React; manual: keyboard-only pass, screen-reader spot-check — see `ux-design.md`'s accessibility section for the specific requirements being verified | Required for any new or changed UI screen |
| **Cross-platform/responsive** | Layout or interaction breaking on a different viewport, browser, or device than the one used during development | Manual or automated viewport sweep (mobile/tablet/desktop breakpoints) for React; physical or simulator sweep across at least iOS and Android for Flutter | Required for any new or changed UI screen |
| **Contract/compatibility** | A change breaking an existing caller or a stored/serialized format already in flight | Explicit backward-compatibility test against the previous wire format/API shape, per Section 6's compatibility rule | Required for any change to a shared type, wire struct, or public API |
| **API contract (OpenAPI/Swagger)** | An implementation that silently diverges from its own published spec — a field the spec says is required but the handler doesn't enforce, a response shape the spec promises but the code doesn't return | Schema-validate real request/response payloads against the OpenAPI document (Schemathesis or Dredd for property-based/spec-driven contract tests, a Prism-mocked server for consumer-side validation) — see `api-contract-design.md` | Required for any new or changed REST endpoint, run in addition to (not instead of) the endpoint's own unit/integration tests |

## Why per-file and per-boundary testing alone is not sufficient evidence

Per-file testing (`integration-testing.md`) catches a broken file the moment it's introduced. Integration testing catches a broken boundary. Neither one, even done perfectly, catches:
- **Emergent bugs from the interaction of several individually-correct pieces** — this is specifically what the Regression row and a full-suite run are for.
- **Bugs in inputs nobody wrote a test for** — this is specifically what the Exploratory row is for; it's a deliberate, reasoned pass, not a hope that unit tests happened to cover everything.
- **Non-functional failure modes** (too slow, insecure, inaccessible, breaks on mobile) that a functionally-passing test suite is structurally blind to, because functional tests check "does it produce the right output," not "is it fast enough / safe / usable / responsive enough."

A task may say that all **applicable checks passed** only after it has walked the applicable rows of this matrix. Unit and integration tests alone are narrower evidence; never translate them into a guarantee that no bugs exist.

## Test-writing during implementation vs. this gate at the end

This file does not replace test-first discipline (Section 11) or the per-file cadence (`integration-testing.md`) — it's the pass that happens *in addition to* those, after implementation is functionally complete, specifically hunting for what file-by-file and boundary-by-boundary testing structurally can't catch. Sequence:
1. Test-first, per file, during implementation (Section 11, `integration-testing.md`).
2. Integration tests at vertical-slice checkpoints (`integration-testing.md`).
3. **This gate**, once the feature is functionally complete: regression (full suite), exploratory/edge-case sweep, and whichever non-functional/accessibility/cross-platform/contract rows apply — before the final Verification report, not instead of it.

## Bug triage when this gate finds something

- **Any bug found at this stage gets fixed before completion is reported** — don't report "mostly done, one known issue" as complete; either fix it or explicitly move the task to "not complete, blocked on X."
- **If a found bug reveals a gap in earlier test coverage** (a case that should have been unit-tested but wasn't), add that test now, retroactively — a bug found by exploratory testing without a regression test added is a bug that can silently reappear later.
- **Triage by consequence, not just presence** (Section 14, SKILL.md) — a bug in the order-confirmation flow gets fixed before a cosmetic misalignment in an admin screen, if both are found and time is constrained; but "time is constrained" is never a reason to skip fixing an order-path bug, only a reason to sequence lower-risk cosmetic issues after it.

## Required reporting format — extends Section 16's Verification report

```
## Comprehensive test pass
Rows run: <which rows of the matrix applied and were executed, with actual commands/tools>
Rows skipped: <which rows didn't apply to this task, and why>
Bugs found and fixed: <list, how each was caught, and the regression test added for each>
Bugs found and not yet fixed: <should be empty before reporting completion — if not empty, the task is not done>
```

## Review checklist before reporting applicable checks complete
- [ ] Full regression suite (not just this task's files) was run, with real pass/fail counts
- [ ] An explicit exploratory/edge-case pass was done and its findings (if any) addressed
- [ ] E2E coverage exists for any change touching order entry, confirmation, or settlement/P&L display
- [ ] Performance was checked (benchmarked, not assumed) for any hot-path-adjacent change
- [ ] Security review (`security-review.md`) was applied, including any new dependency
- [ ] Accessibility audit (automated + keyboard/screen-reader spot-check) was run for any new/changed UI screen
- [ ] Cross-platform/responsive behavior was checked for any new/changed UI screen
- [ ] Any shared-type/wire-format/API change has an explicit backward-compatibility test
- [ ] Every row skipped has a stated reason, not a silent omission
- [ ] The `## Comprehensive test pass` report has zero entries under "Bugs found and not yet fixed"
