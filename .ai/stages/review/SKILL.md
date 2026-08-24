---
name: Review
description: Multi-dimensional code review for correctness, security, performance, and production readiness.
version: 2.0
---

# Purpose

Evaluate the implementation against requirements, architecture, coding
standards, and production best practices. The Review stage never
implements features. Its sole job is to determine whether the
implementation is acceptable.

---

# Inputs

| Artifact | Source |
|---|---|
| `requirements.md` | Requirement Analysis |
| `architecture.md` | Architecture |
| `implementation-report.md` | Implementation |
| `validation.md` | Implementation |
| Changed files | Implementation |
| Existing Codebase | Project |

---

# Process

Execute the Review Orchestrator skill (`.ai/skills/reviewer/SKILL.md`)
which runs these sub-reviews in order:

1. **code-reviewer** — Correctness, readability, maintainability.
   Output: `code-review.md`.
2. **architecture-reviewer** — Structural compliance with approved design.
   Output: `architecture-review.md`.
3. **security-reviewer** — OWASP Top 10 vulnerability scan.
   Output: `security-review.md`.
4. **performance-reviewer** — Bottleneck and scalability analysis.
   Output: `performance-review.md`.
5. **production-readiness-reviewer** — Operational readiness across
   error handling, logging, configuration, and documentation.
   Output: `production-review.md`.

The Review Orchestrator aggregates all findings into `review.md`.

---

# Outputs

| Artifact | Description |
|---|---|
| `review.md` | Unified review with aggregated findings, severity counts, top issues, and verdict |
| `code-review.md` | Detailed code review findings |
| `architecture-review.md` | Architecture compliance matrix |
| `security-review.md` | Security audit findings |
| `performance-review.md` | Performance analysis findings |
| `production-review.md` | Production readiness matrix |

---

# Severity Definitions

| Severity | Definition | Impact |
|---|---|---|
| CRITICAL | Must fix. Blocks approval. | Security vulnerability, data loss risk, architectural violation |
| HIGH | Should fix before merge. | Bugs, missing error handling, contract violations |
| MEDIUM | Improve if time permits. | Code quality, maintainability, minor performance |
| LOW | Nitpick, optional. | Style, naming, documentation |

---

# Verdict

| Verdict | Condition |
|---|---|
| `APPROVED` | Zero CRITICAL findings, zero HIGH findings across all reviews |
| `CHANGES_REQUESTED` | Any CRITICAL or HIGH finding exists |

---

# Failure Handling

If verdict is `CHANGES_REQUESTED`: report to the orchestrator with the
full `review.md`. The orchestrator will loop back to Implementation with
the review feedback as context.

---

# Constraints

- Never rewrite code. Only review and provide feedback.
- Every finding must reference a specific file and line.
- Every finding must include actionable fix guidance.
- No vague feedback like "improve code quality".
- Never approve if CRITICAL findings exist.
