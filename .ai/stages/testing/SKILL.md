---
name: Testing
description: Validate the implementation through unit tests, integration tests, browser workflow validation, and acceptance criteria verification.
version: 2.0
---

# Purpose

Verify that the implementation satisfies all requirements and is safe
to release. Testing proves correctness — it never implements features.

---

# Inputs

| Artifact | Source |
|---|---|
| `requirements.md` | Requirement Analysis |
| `tasks.json` | Planning |
| `implementation-report.md` | Implementation |
| `review.md` | Review |
| Changed files | Implementation |
| Existing Codebase | Project |
| `tech-stack.md` | Architecture |

---

# Process

Execute these skills in order:

1. **unit-test-generator** — Generate unit tests for all changed
   functions/modules. Output: test files + `test-summary.md`.
2. **integration-test-generator** — Generate integration tests for
   API endpoints and cross-component interactions. Output: test files
   + `integration-test-summary.md`.
3. **browser-workflow-validator** — Execute end-to-end browser feature validation across trading terminal pages (`/trading`, `/`), order modals, tick charts, market depth, and API routes. Output: `browser-report.md`.
4. **regression-test-runner** — Run the full existing test suite.
   Output: `regression-report.md`.
5. **acceptance-validator** — Trace every requirement's acceptance
   criteria to implementation and tests. Output: `acceptance-report.md`.
6. **test-reporter** — Aggregate all outputs into a single unified
   `test-report.md` with a machine-parseable verdict.

---

# Outputs

| Artifact | Description |
|---|---|
| Test source files | Unit and integration test files |
| `browser-report.md` | End-to-end browser workflow validation findings |
| `test-report.md` | Unified test report with all results and verdict |
| `regression-report.md` | Regression analysis with new vs pre-existing failures |
| `acceptance-report.md` | Requirement traceability matrix |

The `test-report.md` is the primary output consumed by the orchestrator.
It must contain a clear verdict.

---

# Test Report Schema

```markdown
## Test Results
- Total: N
- Passed: N
- Failed: N
- Skipped: N

## Browser Workflow Audit
- Dashboard (/) - Status 200 OK
- Zerodha Trading Terminal (/trading) - Status 200 OK
- Rust Backend API (/api/health) - Status 200 OK

## New Failures
| Test | File | Error | Classification |

## Acceptance Status
| Req ID | Status |

## Verdict: ALL_PASS | FAILURES_DETECTED
```

---

# Success Criteria

Release only if:

- All unit tests pass.
- All integration tests pass.
- All browser workflow pages load with HTTP 200 OK and zero console errors.
- Zero new regressions detected.
- All CRITICAL and HIGH acceptance criteria are SATISFIED.
- No CRITICAL defects remain.

---

# Failure Handling

If tests fail or acceptance criteria are not met: report to the
orchestrator with the full `test-report.md`. The orchestrator will
loop back to Implementation with the test failures as context.

---

# Constraints

- Never modify production code during testing. Only write and run tests.
- Generate only meaningful tests. No tests for unreachable code.
- Every failing test must explain why it fails.
- Use the test framework specified in `tech-stack.md`.
- Tests must complete in under 60 seconds total for the suite.
