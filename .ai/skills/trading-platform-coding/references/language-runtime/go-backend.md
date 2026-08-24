# Go Backend — Service Implementation (order-adjacent services, non-hot-path or soft-real-time)

Go is the right choice on this platform for services that need concurrency and operational simplicity more than a hand-tuned latency budget: order-routing gateways, risk-check services that sit beside (not inside) the matching engine's critical loop, position/account services, reporting, admin APIs. **If a task lands squarely inside the profiled order-received → order-acknowledged path, that's `rust-backend.md` territory, not this file** — Go's garbage collector makes sub-10ms worst-case tail latency guarantees genuinely harder to hit than Rust's, so don't reach for Go there by default. Where Go is used adjacent to the hot path (a risk service the matching engine calls out to, a gateway in front of it), the GC-pause discussion below still applies.

## OpenAPI / Swagger Auto-Bootstrapping (Go Services)
For any HTTP REST API service in Go (Gin, Echo, Chi, standard `net/http`):
- **Auto-bootstrap interactive Swagger UI** using `swag` annotations + `http-swagger` / `echo-swagger` / `chi-doc`.
- Mount `/swagger/index.html` or `/docs` automatically on server initialization.
- Annotate all route handler functions with `@Summary`, `@Description`, `@Tags`, `@Accept`, `@Produce`, `@Param`, `@Success`, and `@Failure` matching `references/foundation/api-contract-design.md`.

## Idiomatic Go, not transliterated Rust/Java

- **Errors are values, not exceptions.** Return `error` as the last return value and check it immediately — never ignore an error with `_`, and never use `panic`/`recover` as ordinary control flow. `panic` is reserved for genuinely unrecoverable programmer errors (nil map write, index out of range you failed to prevent), not for expected failure paths like "order rejected" or "symbol not found."
- **Wrap errors with context, don't swallow or re-stringify them**: `fmt.Errorf("placing order %s: %w", orderID, err)` preserves the original error for `errors.Is`/`errors.As` — string-concatenating an error's message and discarding the original loses the ability to check its type upstream.
- **Small interfaces, defined by the consumer.** Go interfaces are structural — define them where they're used (`OrderValidator` in the package that validates, not a giant `interfaces.go` of every interface in the system), and keep them to 1-3 methods. A large interface is a sign something should be split.
- **Accept interfaces, return concrete types** — a function should take the narrowest interface it needs as input, and return a concrete struct the caller can use fully, not an interface that hides fields the caller legitimately needs.
- **Composition over inheritance**: use struct embedding for code reuse, not as a substitute for interface-based polymorphism where genuine polymorphism is needed.
- **Avoid `interface{}`/`any` as an escape hatch** the same way Section 8 (SKILL.md) forbids `dynamic`/`any` in TS/Dart — if you're reaching for it because a type doesn't fit, understand why before working around it. Generics (Go 1.18+) are usually the correct tool when you'd otherwise reach for `any`.

## Concurrency

- **Goroutines are cheap but not free — every long-lived goroutine needs an explicit owner and shutdown path.** A goroutine started with no way to stop it (no `context.Context`, no done channel) is a leak, even though it doesn't look like one in a code review — it just keeps running, holding whatever it captured.
- **`context.Context` is the cancellation/deadline mechanism, threaded explicitly through every call that can block** (network calls, channel sends/receives, DB queries) — not stored in a struct field, not passed as `context.Background()` deep in a call chain where a real deadline should have propagated. The order-routing gateway calling into the matching engine's soft-real-time boundary should propagate a deadline derived from the platform's latency budget, not use an unbounded context.
- **Channels for orchestration and ownership hand-off, mutexes for protecting shared state.** Don't reach for a channel where a simple `sync.Mutex`-protected counter would do — that's the classic Go over-engineering mistake in the other direction from Rust's "use Mutex only when nothing lock-free fits."
- **`select` with a `context.Done()` case on every blocking channel operation** that isn't guaranteed to complete quickly — a `select` without a cancellation path can hang a goroutine forever if the other side never sends.
- **Race detector is not optional**: any concurrent code (anything using goroutines + shared state) must be run under `go test -race` before being called done — a data race that doesn't crash in testing will eventually corrupt state in production, and the race detector catches classes of bugs that pass every functional test.
- **`sync.WaitGroup` for "wait for N goroutines to finish," `errgroup.Group` (golang.org/x/sync/errgroup) when any of them can fail** and you need the first error plus coordinated cancellation of the rest — don't hand-roll error aggregation across goroutines with a shared slice and a mutex when `errgroup` already does this correctly.

## GC-pause awareness (where Go sits near, not on, the hot path)

- Go's GC is concurrent and low-pause by design, but it is not zero-pause, and allocation-heavy code increases GC frequency and pressure — a service that's supposed to add single-digit milliseconds of overhead can blow that budget if it's allocating per-request without discipline.
- **Reduce allocation in request-handling hot paths**: reuse buffers via `sync.Pool` for short-lived, frequently-allocated objects (request-scoped byte buffers, structs recycled across requests); avoid unnecessary `interface{}` boxing of small values in tight loops; prefer passing structs by pointer only when the struct is large enough that copying costs more than the pointer indirection — for small structs, passing by value is often faster and avoids a heap escape.
- **Watch for accidental heap escapes**: a value that could live on the stack gets heap-allocated (and becomes GC pressure) if a pointer to it escapes the function — e.g. returning `&localVar`, storing it in an interface, or passing it to a function the compiler can't inline. Use `go build -gcflags="-m"` to see escape-analysis decisions on latency-sensitive code paths, don't guess.
- **Tune `GOGC`/`GOMEMLIMIT` deliberately for latency-sensitive services**, and treat that tuning as an infrastructure/deployment concern to report and justify (same boundary as CPU pinning in `rust-backend.md`) rather than a knob to change without measurement.
- If a service genuinely needs Rust-level tail-latency guarantees, that's a signal it may belong in the Rust service instead of Go — don't fight the GC indefinitely trying to make Go do what Rust is already the platform's answer for.

## Error handling and validation at service boundaries

- Validate all external input (HTTP body, gRPC request, message-queue payload) at the boundary — the same "validated at the boundary, not deep in business logic" rule from Section 10 (SKILL.md) applies identically in Go.
- Use typed, sentinel, or wrapped errors (`errors.New`, custom error types implementing `error`, or `errors.Is`/`errors.As` for structured checks) rather than parsing error strings to determine what went wrong downstream — string-matching an error message is a portability and correctness hazard.
- Money: use a fixed-point/decimal type (`shopspring/decimal`, or integer minor-units) — never `float64` for price or quantity, identical rule to Rust and the frontend.

## Testing

- **Table-driven tests are the Go-idiomatic equivalent of `rstest`'s parametrized cases** (see `test-execution.md`/`integration-testing.md`): a `[]struct{ name string; input ...; want ... }` slice iterated with `t.Run(tc.name, ...)` so each case reports independently rather than one test function failing opaquely on "case 3."
- `go test -race ./...` is required for any package with concurrent code — not optional, not "when it seems relevant."
- `go test -cover` (or `go tool cover -html` for a visual gap report) to check coverage the same way `cargo-llvm-cov` is used on the Rust side — use it to find untested branches, not to chase a percentage.
- Use `testify/assert` and `testify/require` for readable assertions and `testify/mock` sparingly — prefer real implementations or lightweight hand-written fakes over heavy mocking frameworks where the dependency is simple enough (see `integration-testing.md` for when a real dependency via `testcontainers-go` beats a mock).
- Benchmark with Go's built-in `testing.B` (`go test -bench=. -benchmem`) for any function whose allocation count or latency matters — `-benchmem` specifically surfaces allocations-per-op, which is the number that matters for GC-pressure-sensitive code.

## Project layout

See `project-structure.md` for the full cross-language layout guide. Go-specific notes: follow the community-standard layout (`cmd/<service>/main.go` as the thin entrypoint, `internal/` for code not meant to be imported by other modules, `pkg/` only for genuinely reusable exported code) rather than a flat package-per-file structure — `internal/` in particular is a real compiler-enforced boundary in Go, not just a convention, and should be used deliberately to keep implementation details out of your module's public API.

## Review checklist before calling Go service code "done"
- [ ] Every error is checked and either handled or wrapped with `%w` and propagated — none silently discarded with `_`
- [ ] Every long-lived goroutine has an explicit owner and a `context`-driven or channel-driven shutdown path
- [ ] `go test -race ./...` passes on any package with concurrent code
- [ ] No `float64`/`float32` for price, quantity, or money
- [ ] Input validated at the service boundary, not deep in business logic
- [ ] `interface{}`/`any` used only where a concrete type or generic genuinely doesn't fit, not as a shortcut past a type error
- [ ] If this service is latency-sensitive, allocation hot spots were checked (`-gcflags="-m"`, `-benchmem`), not assumed fine because Go's GC is "usually low-pause"
