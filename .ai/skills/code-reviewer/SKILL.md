---
name: code-reviewer
description: Structured code review process focusing on architecture, implementation, severity tiers, and constructive tone.
---

# Code Review — Process, Severity, Style

Read this when the user asks to review a PR, diff, or piece of code. The goal is a structured, consistent review — not an unstructured list of nitpicks.

## Four-phase review process

1. **Understand scope and intent first.** Before commenting on a single line, understand what the PR/change is trying to accomplish and why. Read the PR description/ticket if available. A review that misunderstands intent produces noise, not signal.
2. **Review architecture and design choices.** Does the overall approach make sense given the goal? Is this the right place in the codebase for this logic? Are there simpler approaches? This is cheaper to catch and fix before line-by-line review than after.
3. **Review implementation details, line by line.** Correctness, edge cases, error handling, security, performance, readability, test coverage (see checklist below).
4. **Summarize.** Roll findings up into a short summary: overall assessment, blocking issues, and anything the author should know even if it's not blocking. Don't make the author hunt through 30 inline comments to find the 2 that actually matter.

## Severity tiers

Tag every finding so the author can triage at a glance:

🔴 **Blocking** — must be fixed before merge (correctness bugs, security holes, broken tests, data loss risk)

🟡 **Should-fix** — real issue, but doesn't have to block this merge (can be a fast follow-up)

🟢 **Optional / nit** — style preference, minor readability suggestion, not worth blocking on

Non-blocking annotation markers, used alongside severity where useful: 💡 (suggestion/idea), 📚 (learning/reference), 🎉 (positive callout — good reviews aren't only criticism).

## Checklist categories

**Correctness** — does the code do what it claims? Are there logic errors, off-by-ones, wrong assumptions about input shape?

**Edge cases & error handling** — empty/null inputs, concurrent access, partial failures, timeouts, downstream errors surfaced sensibly (not swallowed silently)

**Security** — injection risks, auth/authz correctness (is this checking authentication when it means authorization, or vice versa?), secrets in code, unvalidated input reaching sensitive operations

**Performance** — obvious N+1s, unbounded loops/queries, unnecessary work in hot paths — but don't over-index on micro-optimizations that don't matter for the actual load profile

**Readability & maintainability** — is intent clear without needing the author to explain it? Is duplicated logic (3+ occurrences is a strong signal) worth extracting?

**Tests** — does test coverage match the risk of the change? Are the interesting cases covered, not just the happy path?

## Tone: ask, don't command

Phrase feedback as a question or suggestion where the "right" answer isn't obvious — it invites discussion instead of triggering defensiveness, and leaves room for context the reviewer doesn't have.

| Instead of | Prefer |
|---|---|
| "This will fail if the list is empty." | "What happens if items is an empty array?" |
| "You need error handling here." | "How should this behave if the API call fails?" |
| "You must change this to use async/await." | "Suggestion: async/await might make this more readable — thoughts?" |
| "Extract this into a function." | "This logic appears in 3 places — would it make sense to extract it?" |

Reserve direct, unhedged language for genuinely blocking issues (security holes, correctness bugs, data loss) — hedging those undersells the severity.

## Notes

If the codebase has its own style guide or lint config, defer to it over generic preferences.

For language/framework-specific review depth (React, Rust, Python/FastAPI, Go, etc.), apply the relevant idioms and common pitfalls for that ecosystem rather than generic advice — but don't fabricate framework-specific rules if unsure; say so and review at the level you're confident in.

A review that ties back to the original design doc or requirements (if this skill was used earlier in the project) can call out design/requirement drift explicitly — that's a stronger finding than a generic style comment.
