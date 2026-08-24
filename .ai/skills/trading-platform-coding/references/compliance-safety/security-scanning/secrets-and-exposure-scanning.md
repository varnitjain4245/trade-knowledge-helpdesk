# Secrets & API Exposure Scanning

**Mandatory gate**: runs on every diff before completion, regardless of task tier — a leaked secret or an unintentionally exposed endpoint is a single-file, single-line mistake that's just as dangerous in a "Small" task as a "Critical" one, so this is the one security gate that doesn't get a lighter version for lower-tier tasks.

## Secrets detection

- **Scan every diff for hardcoded credentials** before it's presented as complete: API keys, database connection strings with embedded passwords, private keys, JWT signing secrets, cloud provider credentials. Tools: Gitleaks or TruffleHog (both scan diffs/history for known secret patterns and high-entropy strings); GitHub's native secret scanning with push protection if the platform is on GitHub.
- **A detected secret is never "fixed" by just removing it from the current diff** — if it was ever committed (even to a local branch that hasn't been pushed), treat it as compromised: it needs rotation (issue a new credential, revoke the old one), not just deletion from the file. State this explicitly if a secret is found — "removed from the diff" is a materially weaker and potentially misleading claim than "removed and flagged for rotation."
- **Environment-variable/secrets-manager usage is the fix, not a suggestion** — any new credential this task introduces goes through the project's existing secrets management (environment variables, a secrets manager, injected config), never hardcoded, from the first version of the code, not as a follow-up cleanup.

## API/endpoint exposure review — the specific "exposed API" concern

This is a review pass, not just a text-pattern scan, since "is this endpoint safely exposed" is a design question, not just a string match:

- **Every new or changed endpoint gets checked against its intended exposure**: is this meant to be public, internal-only, or admin-only — and does the actual routing/network configuration match that intent? A debug/admin endpoint accidentally reachable on the same public route table as customer-facing endpoints is a common, high-impact mistake this check exists to catch.
- **Authentication and authorization are verified present on every new endpoint**, not assumed from the framework's default — a new route added to an existing authenticated router inherits that protection, but a new route on a different router, or a framework misconfiguration, can silently create an unauthenticated path. Confirm explicitly, don't assume by proximity to other protected code.
- **Verbose error responses are checked for information leakage**: a stack trace, an internal file path, or a database error message returned directly to the client hands an attacker a reconnaissance advantage — this connects directly to `security-review.md`'s "no secrets in logs, error messages, or client-visible responses" rule, checked here specifically at the API-response layer.
- **Rate limiting and abuse protection presence is checked for any new public-facing or expensive endpoint** (auth, search, anything calling an external paid API) — same rule already established in `rust-backend.md`'s security baseline, verified here as part of the exposure-scanning pass rather than left to be caught only in manual review.
- **CORS configuration is checked for over-permissiveness** on any new web-facing endpoint — a wildcard origin on an authenticated API is a common accidental-exposure pattern worth an explicit check, not an assumption that the framework default is safe.

## Tooling

- **Gitleaks/TruffleHog**: secrets scanning, as above — integrate as a pre-commit hook where the project supports it, so a secret never even reaches a shared branch, not just caught after the fact.
- **API-specific**: OWASP ZAP (or a lighter API-focused scanner) can automate a portion of the endpoint-exposure checks above (auth presence, response information leakage) against a running instance — treat this as a supplement to the manual exposure-intent review above, not a replacement for it, since "is this endpoint supposed to be public" is a design judgment a scanner can't make on its own.

## Review checklist before calling the secrets/exposure gate satisfied
- [ ] Diff scanned for hardcoded secrets — none present, or any found are flagged for rotation, not just deletion
- [ ] Every new endpoint's actual exposure (public/internal/admin) matches its intended exposure
- [ ] Auth/authorization confirmed present on every new endpoint, not assumed from framework defaults
- [ ] Error responses checked for information leakage (stack traces, internal paths, raw DB errors)
- [ ] Rate limiting considered for any new public-facing or expensive endpoint
- [ ] CORS configuration checked for over-permissiveness on any new web-facing endpoint
