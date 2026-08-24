# Integration Testing & Per-File Test Cadence

`test-execution.md` covers the mechanics of running and measuring *unit* tests, with a Rust-specific toolchain (`cargo nextest`, `rstest`, `cargo-llvm-cov`, `cargo-fuzz`). This file covers two things that file doesn't: (1) integration testing — verifying that pieces actually work together across a process/service/language boundary, not just in isolation — and (2) the cross-language cadence rule that testing happens **after each file is generated or changed**, not batched to the end of a multi-file task.

## Why integration tests are a distinct discipline from unit tests

Section 11 (SKILL.md) already establishes test-pyramid discipline: most coverage at the unit level, less at integration, least at end-to-end. That doesn't mean integration tests are optional — it means they're deliberately scoped to what unit tests structurally cannot catch:
- A unit test verifies a function/module's logic against a mocked or in-memory collaborator. An integration test verifies that the *real* collaborator (a real database, a real message broker, a real downstream service, a real cross-language wire format) behaves the way the unit test's mock assumed it would.
- The single most common bug class integration tests catch that unit tests miss on this platform: **a wire-format or contract mismatch between two independently-developed sides** — the Rust matching engine's binary wire format and a Go/Java service's deserializer, or a backend API's response shape and the React/Flutter frontend's parser. Two sides can each have 100% passing unit tests and still be incompatible with each other.

## What needs an integration test on this platform (not everything does)

- **Any cross-service boundary a task touches**: order gateway → matching engine, matching engine → audit/durability sink, risk service → order path, backend → frontend wire contract.
- **Any real external dependency**: database, message queue/broker, cache, third-party API integration (custodian, clearing house, market-data vendor).
- **Any change to a shared contract** (wire format, API schema, protobuf definition in `project-structure.md`'s `shared/` contracts folder) — a contract change with only unit tests on one side is exactly the gap this section exists to close.
- **Not needed** for a pure internal refactor with no external boundary crossed, or a change fully contained within one function/module already covered by unit tests — don't inflate the integration suite with tests that duplicate unit-level coverage for no boundary-crossing reason (same proportionality principle as Section 11's pyramid discipline).

## Tooling by language

- **Rust**: integration tests live in a crate's `tests/` directory (compiled as separate binaries, exercising the crate's public API like an external caller would) for in-process integration; for real external dependencies, `testcontainers-rs` to spin up real Postgres/Kafka/Redis instances in Docker for the test run rather than mocking them — a mocked database can't catch a real SQL syntax error or a real serialization mismatch.
- **Go**: `testcontainers-go` for the same real-dependency principle; Go's `_test` package convention (`package foo_test`) for black-box integration tests against a package's public API, kept separate from white-box unit tests in `package foo`.
- **Java**: `testcontainers-java` (the ecosystem this pattern originated in) with `@Testcontainers`/`@Container` JUnit 5 annotations for real Postgres/Kafka instances; Spring Boot's `@SpringBootTest` for full-context integration tests, used deliberately (it's slower — reserve it for tests that actually need the full wired context, not as a default for every test).
- **Cross-language wire-format/contract tests**: a round-trip or golden-file test where one side's actual serialized output is checked against the other side's actual deserializer — not two independent unit tests that each assume the other side is correct. `rust-backend.md`'s "cross-build round-trip test" requirement for wire structs is the specific instance of this rule for the matching engine's binary protocol; the same principle applies to any REST/gRPC contract between backend and frontend.
- **Frontend-to-backend contract tests**: for a REST/GraphQL API, prefer a contract-testing approach (e.g. generating the frontend's expected shape from the backend's actual OpenAPI/schema output, or a shared schema both sides validate against) over hand-maintained parallel type definitions on each side that can silently drift.
- **OpenAPI-spec-driven contract testing**: every REST endpoint's design-first spec (`api-contract-design.md`) is itself a testable artifact, not just documentation — validate that the real implementation's request/response payloads actually conform to the spec (Schemathesis for property-based fuzzing directly against the OpenAPI document, Dredd for spec-vs-implementation conformance checks, or a Prism-mocked server for consumer-side validation before the real implementation exists). A spec and an implementation that have quietly drifted apart is exactly the "two sides independently assumed correct" failure mode this section exists to catch — the spec doesn't get a pass just because it's documentation instead of code.

## Environment setup and teardown discipline

- **Every integration test must clean up its own state**, whether via `testcontainers`' automatic container teardown, a transactional rollback wrapper, or explicit teardown code — a test suite where tests must run in a specific order because an earlier test's leftover state is required is a hidden coupling that will eventually cause a flaky, hard-to-debug failure.
- **Never point an integration test at a shared persistent environment (staging, a shared dev database) as its default mode** — real containers/ephemeral instances per test run, so tests are reproducible and don't corrupt state another engineer (or CI run) depends on. A task that genuinely needs to validate against a shared environment (e.g. a pre-cutover validation per `deployment-safety.md`) is a distinct, explicitly-scoped activity, not the default integration-test mode.
- **Seed data explicitly and minimally** — construct exactly the fixture state a test needs, not a large shared fixture reused (and silently depended on) across many unrelated tests, which makes it unclear which parts of the fixture a given test actually needs.

## Per-file test cadence — test after each file, not at the end of a multi-file task

This is the cross-language generalization of `test-execution.md`'s "what tested my files after generation actually means" section, and it applies regardless of which language(s) a task touches:

1. **After generating or meaningfully editing a file that has an associated test file (existing or newly written), run that file's tests before moving to the next file** — `cargo nextest run -p <crate> <test_name_filter>` / `go test ./path/to/package/...` / `mvn test -Dtest=ClassNameTest` (or the Gradle equivalent), not a full-suite run held until every file in the task is done. This catches a broken file immediately, while the context of what just changed is still fresh, rather than after five more files have been layered on top of a bug introduced early.
2. **For a new file with no test file yet**, write its test(s) as part of generating that file — not deferred to a "write tests" pass at the end of the task. This is Section 11's test-first discipline applied at file granularity, not just feature granularity.
3. **Run the full relevant test suite (not just the one file's tests) at natural checkpoints**: after completing a vertical slice (Section 3, SKILL.md's "sequence as vertical slices" guidance), and always before the final Verification report — per-file testing catches an immediate local regression, a full-suite run catches a regression this file's change caused somewhere else.
4. **If a per-file test run fails, stop and fix it before generating the next file** — don't continue building on top of a known-broken file with the intention of coming back to it; the next file may end up depending on the broken behavior, compounding the fix later.
5. **State the per-file cadence that was actually followed in the Verification report** — "ran `go test ./orders/...` after `validator.go`, after `handler.go`, and the full suite before completion" is a checkable claim; "tests were run throughout" is not.

## Review checklist before calling any multi-file task's testing "done"
- [ ] Each file with an associated test was tested immediately after being written/changed, not only in a final batch run
- [ ] Any new file introducing testable logic has its own test(s) written alongside it, not deferred to an end-of-task pass
- [ ] Every cross-service or cross-language boundary touched by this task has an integration test, not only unit tests on each side independently
- [ ] Any real external dependency (DB, broker, downstream service) used in integration tests runs as a real ephemeral instance (`testcontainers` or equivalent), not a shared persistent environment
- [ ] Integration tests clean up their own state and don't depend on execution order
- [ ] Any changed wire-format/API contract has a test that checks the *actual* output of one side against the *actual* input handling of the other, not two independently-assumed-correct unit tests
- [ ] The full relevant suite was run at least once before the final Verification report, not just per-file runs in isolation
