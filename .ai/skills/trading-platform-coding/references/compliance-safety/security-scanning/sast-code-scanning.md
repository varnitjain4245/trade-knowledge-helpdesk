# Static Application Security Testing (SAST) — Code-Level Vulnerability Scanning

**Mandatory gate**: this runs after implementation and before the task is considered complete, for every task above Small tier (see `SKILL.md`'s Task tiers) and for any Small task touching an HTTP boundary, auth, or user input. It is not optional to run — what's optional is whether a finding blocks completion (see "What mandatory actually means" below).

## What this scans for

Static analysis examines source code without executing it, catching a specific class of bug pattern unit tests structurally can't: injection flaws, authentication logic errors, and unsafe data flow from an untrusted source to a dangerous sink — the same category of concern `security-review.md`'s differential-review and footgun-awareness sections describe, but applied here as an automated first pass rather than manual review alone.

- **SQL/NoSQL injection**: string-concatenated queries, unparameterized database calls — same rule as `rust-backend.md`'s "parameterized queries, never string-concatenate user input" applied across all three backend languages.
- **Cross-site scripting (XSS)**: unescaped output into HTML/DOM context — relevant to the React frontend specifically; Flutter's rendering model is less exposed to this class but not immune where it renders raw HTML/markdown content.
- **Authentication/authorization logic flaws**: a check that can be bypassed by a specific code path, not just "is there a check at all" — the automated pattern-matching catches some of this; `security-review.md`'s "authorization checked server-side, never inferred from client-supplied data" rule is the manual complement, since logic-level auth flaws often need human judgment to catch.
- **Unsafe deserialization, path traversal, command injection**: untrusted input reaching a dangerous sink (a shell command, a file path, a deserializer) without validation at the boundary — the automated-scan equivalent of Section 10's "input validated at the boundary" rule.

## Tooling by language (use what fits the existing project setup; don't introduce a second tool where one is already configured)

- **Multi-language, semantic analysis**: CodeQL — treats code as queryable data rather than pattern-matching text, giving materially fewer false positives than regex-based scanners; the standard choice when running via GitHub Advanced Security / `github/codeql-action`.
- **Fast, broad-language, rule-based**: Semgrep — lower setup cost than CodeQL, strong for catching the injection/XSS/auth-flaw patterns above across Rust, Go, Java, TypeScript in one pass; a reasonable default for a pre-commit or per-file scan given this skill's per-file testing cadence.
- **Rust-specific supplement**: `cargo audit`/`cargo clippy` catch a narrower but Rust-specific slice (some clippy lints double as security-relevant patterns) — not a substitute for a cross-language SAST pass, a supplement to it.

## What mandatory actually means here

**Running the scan is not optional. Acting on every finding before proceeding is a judgment call the user makes, not this skill.**
- Every SAST finding gets surfaced in the Verification report, categorized by severity (critical/high/medium/low), with the specific file:line and what pattern triggered it — not summarized away as "scan passed" if it didn't cleanly pass.
- A **critical or high-severity finding on the order path, auth logic, or any money-handling code is flagged prominently and implementation is not silently presented as "done"** until the user has seen it — but the user retains the authority to explicitly acknowledge and accept a finding (e.g. a known false positive, or an accepted risk with a tracked follow-up) and proceed anyway. This skill states the finding; it does not have standing to unilaterally block the user's own codebase indefinitely.
- What's never acceptable: running the scan, getting a critical finding, and reporting "implementation complete" without mentioning it. Silence on a real finding is the failure mode this gate exists to prevent — an acknowledged, accepted risk is a legitimate outcome; a hidden one is not.

## Review checklist before calling the SAST gate satisfied
- [ ] Scan actually ran (tool + command stated in the Verification report), not assumed clean
- [ ] Every finding above low severity is listed with file:line and category, not summarized as a pass/fail count alone
- [ ] Any critical/high finding on hot-path, auth, or money-handling code was explicitly surfaced to the user, not silently deferred
- [ ] If a finding was accepted/skipped, that's a stated user decision in the Verification report, not an assumption made on the user's behalf
