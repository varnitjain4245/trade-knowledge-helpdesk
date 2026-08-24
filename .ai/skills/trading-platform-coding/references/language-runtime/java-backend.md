# Java Backend — Service Implementation (order-adjacent services, enterprise integration, back-office systems)

Java is the right choice on this platform for services where the JVM ecosystem's maturity matters more than a hand-tuned latency budget: back-office/settlement systems, compliance and reporting pipelines, integration with enterprise systems (custodian banks, clearing houses) that speak Java-ecosystem protocols, and services with heavy transactional/ORM needs. **The profiled order-received → order-acknowledged path is `rust-backend.md` territory** — standard JVM GC pause behavior makes it a poor default for that specific budget. Where a low-latency Java service is genuinely required (e.g. a risk-check service consulted just off the hot path), the low-GC section below is required reading, not optional.

## OpenAPI / Swagger Auto-Bootstrapping (Java / Spring Services)
For any HTTP REST API service in Java (Spring Boot, Quarkus, Micronaut):
- **Auto-bootstrap interactive Swagger UI** using `springdoc-openapi-starter-webmvc-ui` (Spring Boot 3) or `springdoc-openapi-ui` (Spring Boot 2).
- Mount `/swagger-ui/index.html` or `/v3/api-docs` automatically on application startup zero-config.
- Annotate Controllers and DTOs with `@Operation`, `@ApiResponse`, `@Parameter`, and `@Schema` matching `references/foundation/api-contract-design.md`.

## Idiomatic Java, not transliterated patterns from another language

- **Favor immutability by default**: `final` fields, records (Java 16+) for data carriers instead of hand-rolled getter/setter POJOs, defensive copies at boundaries for mutable collections passed in or returned. An `Order` or `Position` type should be immutable — state transitions produce a new instance, they don't mutate in place, which eliminates an entire class of concurrent-modification bugs by construction.
- **Checked vs unchecked exceptions — use the distinction deliberately, don't default to `RuntimeException` for everything or catch-and-swallow checked exceptions to make the compiler stop complaining.** A checked exception is appropriate for a recoverable, expected failure the caller should be forced to handle (e.g. a domain validation failure); an unchecked exception is appropriate for a programmer error or an unrecoverable state. Never catch an exception and do nothing (`catch (Exception e) {}`) — at minimum log it with context, or let it propagate.
- **Dependency inversion via interfaces, wired through constructor injection** (Spring `@Autowired` on constructors, or manual DI) — not field injection, which hides a class's real dependencies and makes it harder to construct in a test without the DI container.
- **Prefer the Streams API for genuinely declarative transformations** (filter/map/collect over a collection), but don't force a multi-stage `.stream()...collect()` pipeline where a plain for-loop is clearer and equally fast — Streams aren't automatically more idiomatic than a loop; use them where they improve readability, not as a style mandate.
- **Optional<T> for "a value may genuinely be absent" return types, not for every nullable field** — don't use `Optional` as a class field type (it's not serializable-friendly and adds overhead for no benefit there), and don't return `null` from a method whose signature could honestly be `Optional<T>` instead, since a caller checking `!= null` is exactly the bug class `Optional` exists to prevent at the API boundary.

## Concurrency

- **`java.util.concurrent` primitives over hand-rolled `synchronized`/`wait`/`notify`**: `ExecutorService`/`CompletableFuture` for async orchestration, `ConcurrentHashMap`/`CopyOnWriteArrayList` for shared collections where they fit the access pattern, `AtomicLong`/`AtomicReference` for simple shared counters/references instead of a full lock. Reach for a hand-rolled `synchronized` block only when none of the higher-level primitives fit the specific access pattern, and justify why in a comment.
- **Virtual threads (Java 21+, Project Loom) are the default for high-concurrency I/O-bound services** on this platform where the runtime is confirmed to support them — they remove the traditional thread-pool-sizing tradeoff for blocking I/O-heavy workloads (order-status polling, downstream service calls). Confirm the target JVM/runtime version before assuming virtual-thread availability; don't silently write `Thread.ofVirtual()` against a runtime that hasn't been confirmed to support it.
- **`CompletableFuture` chains need an explicit exception-handling stage** (`.exceptionally`/`.handle`) — an unhandled exception in an async chain that nothing ever calls `.join()`/`.get()` on can fail silently with no log line and no caller ever finding out.
- Every `ExecutorService` needs an explicit shutdown path (`shutdown()`/`awaitTermination()` on service teardown) — an executor with unbounded lifetime and no shutdown hook is a resource leak, identical in spirit to the unowned-goroutine rule in `go-backend.md`.

## GC and latency awareness (where Java sits near, not on, the hot path)

- **Default to G1GC or, for services with a genuinely tighter latency requirement, ZGC/Shenandoah** (both designed for sub-millisecond pause targets on modern JVMs) — don't leave GC selection as a JVM default without a deliberate choice, and state the choice and why in the Plan for any latency-sensitive service.
- **Reduce allocation churn in request-handling hot paths**: avoid boxing primitives (`Integer`/`Long`/`Double`) in tight loops where a primitive array or primitive-specialized collection (e.g. Eclipse Collections' or fastutil's primitive collections) would avoid the box/unbox and GC pressure entirely; avoid unnecessary intermediate object creation in a request's critical path (e.g. building and discarding several intermediate `String`/List objects per request when a single pass would do).
- **Warm up before trusting a latency measurement**: the JIT compiler needs time (and enough invocations) to compile hot methods — a latency benchmark taken from a cold JVM start materially overstates steady-state latency. Use JMH (Java Microbenchmark Harness) for microbenchmarks specifically because it handles warmup correctly by default; a hand-rolled `System.nanoTime()` loop without a warmup phase produces misleading numbers.
- **Off-heap/direct memory (`ByteBuffer.allocateDirect`, Chronicle libraries) is a legitimate lever for services that need to avoid GC involvement in their data path entirely** — but it moves the service outside normal GC-managed safety, so treat it with the same care as `unsafe` in Rust: justify it explicitly, and don't reach for it unless profiling has shown GC pressure is the actual bottleneck (Section 9, SKILL.md — measure before optimizing).

## Error handling and validation at service boundaries

- Validate all external input (REST body, message-queue payload, JDBC result mapping) at the boundary, same rule as every other language on this platform (Section 10, SKILL.md).
- Use `BigDecimal` (never `double`/`float`) for price, quantity, or money — and construct `BigDecimal` from a `String` or `long` minor-units value, never from a `double` literal (`new BigDecimal(0.1)` captures the binary floating-point value's imprecision; `new BigDecimal("0.1")` does not). This is the Java-specific instance of the platform-wide "money is never a float" rule.
- Define a clear exception hierarchy for domain errors (e.g. `OrderRejectedException extends DomainException`) that a service boundary (REST controller advice, message-consumer error handler) maps to a well-defined external response — don't let a raw internal exception's stack trace or message leak to an external caller (also a Section 10 security rule: no internal detail in client-visible errors).

## Testing

- **JUnit 5** as the test framework, with `@ParameterizedTest` + `@MethodSource`/`@CsvSource` as the Java-idiomatic equivalent of `rstest`'s parametrized cases / Go's table-driven tests — one named case per input, not a loop inside a single test method.
- **Mockito** for mocking, used sparingly: mock external boundaries (a downstream HTTP client, a message publisher) — don't mock your own domain objects or value types; construct real instances of those, since mocking them just tests that the mock does what you told it to.
- **AssertJ** for fluent, readable assertions (`assertThat(order.status()).isEqualTo(...)`) over raw JUnit `assertEquals`, for anything beyond a trivial equality check.
- Coverage via JaCoCo, used the same way `cargo-llvm-cov`/`go test -cover` are used elsewhere on this platform: to find untested branches in changed code, not to chase a percentage (Section 11, SKILL.md).
- For anything with real concurrency, consider running relevant tests under increased thread contention/stress (a tight loop invoking the concurrent path from multiple threads) to surface races that a single-threaded test run won't — the JVM doesn't have a built-in race detector equivalent to `go test -race`, so this kind of deliberate stress-testing is the closest substitute; don't skip it just because there's no one-flag tool for it.

## Project layout

See `project-structure.md` for the full cross-language layout guide. Java-specific notes: standard Maven/Gradle multi-module layout (`src/main/java`, `src/test/java`, package-by-feature over package-by-layer for anything beyond a small service — `com.platform.orders.validation` rather than a top-level `com.platform.validators` that mixes every feature's validators together), and a clear module boundary between API/DTO types exposed to other services and internal domain types that shouldn't leak across a module boundary.

## Review checklist before calling Java service code "done"
- [ ] `BigDecimal` (constructed from `String`/`long`, never a `double` literal) used for all price/quantity/money — no `double`/`float`
- [ ] No swallowed exceptions (`catch` block that does nothing) anywhere in the diff
- [ ] Every `ExecutorService`/thread pool has an explicit shutdown path
- [ ] Every `CompletableFuture` chain has explicit exception handling, not left to fail silently
- [ ] GC algorithm choice stated explicitly for any latency-sensitive service, not left as JVM default without a decision
- [ ] Input validated at the service boundary; internal exception details never leak into a client-visible response
- [ ] JMH (not a hand-rolled timing loop) used for any latency/throughput claim on hot code
