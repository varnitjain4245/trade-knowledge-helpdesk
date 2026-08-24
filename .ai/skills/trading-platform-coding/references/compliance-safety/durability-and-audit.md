# Durability & Audit Logging — Compliance Without Breaking the Budget

A trading platform almost always has a regulatory or internal requirement to durably record order events (received, validated, matched, rejected, cancelled) — this file exists because that requirement, done naively, directly conflicts with every hot-path rule in `rust-backend.md`: a synchronous `fsync()` on the order path is a guaranteed latency-budget violation, easily tens of milliseconds against your 5-8ms target.

**This is a scope note, not an implementation mandate**: confirm what your actual regulatory/compliance requirement is (retention period, what fields must be captured, whether it must be tamper-evident) before implementing — this file covers the *pattern* for doing it without breaking latency, not the specific legal requirement, which this skill has no visibility into and should not assume.

## The core pattern: write-behind, never write-through

- The hot path never performs a blocking write (disk I/O, network call to a logging service) itself. It publishes an audit event to a lock-free channel (same SPSC/MPSC pattern as `concurrency-patterns.md`) and immediately continues — the write itself happens on a dedicated writer thread, off the hot path entirely.
- This means the hot path's job is only to construct a small, fixed-size, already-serialized-or-cheaply-serializable audit record and push it — not to touch disk, not to wait for acknowledgment, not to retry.
- The writer thread batches records (e.g. flush every N records or every T milliseconds, whichever comes first) and performs the actual `fsync`/write there, where blocking is acceptable.

## What "durable enough" requires you to think about explicitly

- **What happens if the writer thread's channel is full?** This is a backpressure scenario, same category as the ring-buffer-full case in `matching-engine-hot-path.md` — decide explicitly whether the hot path blocks (violates latency budget, usually wrong), drops the audit event (usually unacceptable for compliance — silent audit gaps are a serious finding), or triggers a load-shedding/alerting path. State this decision explicitly in the Plan; don't let it be an accidental default.
- **What happens if the process crashes between "order acknowledged to the client" and "audit record flushed to disk"?** If audit durability must be guaranteed before acknowledgment (common regulatory requirement), that's a genuine tension with pure write-behind — one resolution is a fast, still-non-blocking durable append (write to an OS page cache immediately, ordinary `write()` without `fsync()`, and a separate, less time-sensitive fsync-and-verify pass) rather than either "fully synchronous" or "fully deferred." Which resolution is correct depends on your actual compliance requirement — state the requirement and the chosen tradeoff explicitly, don't silently pick one.
- **Ordering guarantees**: if audit records must reflect the exact order in which events actually happened (usually required for a trading audit trail), a single writer thread consuming a single ordered channel per matching-engine partition is simpler to reason about than multiple writer threads that could reorder — don't parallelize the writer without confirming ordering isn't required.

## Format and integrity

- Use the same explicit-byte-format discipline as `rust-backend.md`'s wire-format section — an audit log that can't be reliably parsed later because of an undocumented layout is not actually durable, it's just disk usage.
- If tamper-evidence is required (common for regulated audit trails), consider a hash-chain (each record includes a hash of the previous record) — this is an append-time cost on the writer thread, not the hot path, so it doesn't threaten the latency budget, but it does need to be designed in from the start since retrofitting a hash chain onto existing records isn't possible.

## Testing this specifically

- Test the backpressure/full-channel behavior explicitly (see above) — this is exactly the kind of edge case that's easy to leave untested because the happy path (channel has room) is what gets exercised in normal test runs.
- Test writer-thread crash/restart recovery: does replaying the log from the last known-good position produce a consistent state, or can a partial/torn write at the point of a crash corrupt recovery? This needs an explicit answer, not an assumption.

## Review checklist before calling audit-logging work "done"
- [ ] No blocking I/O (disk write, network call) on the hot path — only a channel push
- [ ] Backpressure behavior (channel full) is an explicit, stated decision — not a silent default
- [ ] Ordering guarantee (or lack thereof) is stated explicitly and matches the actual compliance requirement
- [ ] Crash-recovery behavior (partial/torn write at point of crash) has been considered, not just the happy path
- [ ] The actual retention/tamper-evidence/field requirements came from a real compliance source, not assumed by this skill
