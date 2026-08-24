# Security Review — Engineering Practices

Applies to any code before it's considered ready, on top of the domain-specific rules already in `rust-backend.md` and `frontend.md`. For any REST endpoint governed by `api-contract-design.md`, the API/Swagger section below is required reading in addition to the general rules — an API contract is public attack surface by definition, and deserves the same scrutiny as the code behind it.

## Rust-specific review focus
- **`unsafe` boundary**: every `unsafe` block needs an explicit, written justification for why the invariant it relies on actually holds — not just that the code compiles. Treat each `unsafe` block as a place requiring extra scrutiny proportional to how far from the call site its safety invariant is established.
- **Concurrency correctness**: check for data races that the type system can't catch across `unsafe` boundaries, and for panic-induced denial-of-service — a single thread panicking inside a shared structure can take down more than itself if it happens mid-mutation. Prefer designs where a panic in one connection/order can't corrupt state shared with others.
- **FFI boundaries**: any call into non-Rust code needs its inputs validated on the Rust side — don't assume the other side upholds a contract Rust's type system would otherwise enforce.
- **Async runtime edge cases**: cancellation safety matters — check whether a future being dropped mid-execution (e.g. on timeout) can leave shared state in a half-updated condition.

## General application security (both backend and frontend)
- **Input validation at the boundary**, not deep in business logic — reject malformed input before it propagates.
- **Authorization checked server-side**, always, regardless of what the client claims about itself or another user's data.
- **No secrets in logs, error messages, or client-visible responses** — a stack trace or debug string is a common accidental leak path.
- **Dependency awareness**: flag any new dependency being added, especially in the hot path — a new crate is new attack surface and new unaudited code running with the same trust level as your own.

## API/Swagger surface security (any REST endpoint governed by `api-contract-design.md`)
A published OpenAPI contract is itself part of the attack surface — it tells an attacker (human or automated) exactly what to try, which makes rigor here disproportionately valuable. Review every new or changed endpoint against the OWASP API Security Top 10 categories most relevant to this platform, not as an external audit step but as part of the same review pass as the code:
- **Broken object-level authorization**: does every operation that takes an ID (`orderId`, `accountId`) actually verify the caller owns or is entitled to that specific object, server-side — not just that the caller is authenticated in general? An endpoint that returns "someone's" order data based only on a valid token, without checking *whose* order it is, is the single most common real-world API vulnerability class and is easy to miss because the happy-path test (fetching your own order) passes fine.
- **Broken authentication / missing security scheme declaration**: cross-check that every operation's `security` requirement in the spec (per `api-contract-design.md`) matches what the implementation actually enforces — a spec that declares a scope requirement the handler doesn't check is worse than an undocumented gap, because it creates false confidence for anyone reading the contract.
- **Excessive data exposure**: does a response schema return only the fields the consumer actually needs, or does it return an entire internal domain object (including fields like internal risk scores, other users' references, or raw database columns) because it was easier to serialize the whole struct? Trim the response schema deliberately; don't let `api-contract-design.md`'s "schema reused via `$ref`" convenience turn into over-sharing convenience.
- **Lack of rate limiting / resource exhaustion**: any endpoint that's expensive to compute or that accepts a caller-controlled size/count parameter (a bulk order-history query, a pagination `limit`) needs an enforced upper bound — an unbounded `limit` parameter is a denial-of-service vector, not just a performance nit, and should be flagged as a security issue, not filed separately as a performance one.
- **Mass assignment**: a request body deserialized directly into an internal domain/database model (rather than a dedicated request-schema type) risks letting a caller set fields they were never meant to control (e.g. an order's internal status, a user's role) just because the field exists on the struct. Always deserialize into a purpose-built request type with only the fields the operation is meant to accept.
- **Security misconfiguration surfaced through the spec itself**: verify the published spec doesn't leak internal implementation detail that has no business being public — internal-only operations, debug/admin endpoints, or infrastructure hostnames accidentally included in a `servers` block meant for a different environment.

## Differential review mindset
When reviewing a change rather than writing one, compare behavior before and after rather than judging the diff in isolation — a change can be locally correct and still alter system behavior in a way that matters (a timeout that got shorter, a retry that got removed, an error that's now silently swallowed instead of surfaced). Check what changed in *behavior*, not just what changed in *text*.

## Footgun awareness ("sharp edges")
Flag, rather than silently use, any API or pattern known to be easy to misuse even when the immediate usage looks correct — for example: floating-point comparisons, mutex lock ordering that could deadlock under a different code path, error types that are easy to accidentally swallow with `?` chaining across mismatched error types, or any construct where the type system allows a state that should be impossible by the business logic. Naming the risk explicitly, even when you believe the current usage is safe, gives the next person (or the next change) the context to not break it.

## Review checklist before calling any change "secure enough"
- [ ] Every `unsafe` block has a written safety justification
- [ ] No new dependency added to the hot path without being named and justified
- [ ] Server-side authorization checked, not inferred from client-supplied data
- [ ] No secrets/PII in logs or error output
- [ ] Changed behavior (not just changed code) has been explicitly considered, not just the diff
- [ ] Every ID-taking endpoint verifies caller ownership/entitlement server-side, not just valid authentication
- [ ] Every operation's declared `security` scheme in the OpenAPI spec matches what the handler actually enforces
- [ ] Response schemas return only the fields the consumer needs — no full internal-object dumps
- [ ] Any caller-controlled size/count parameter has an enforced upper bound
- [ ] Request bodies deserialize into a purpose-built request type, never directly into an internal domain/database model
- [ ] The published API spec contains no internal-only operations, debug endpoints, or non-public infrastructure detail
