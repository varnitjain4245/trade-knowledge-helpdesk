---
name: "trading-platform-coding"
description: "Implement, fix, refactor, scaffold, design API contracts for, or test code in this stock-broking platform: Rust matching-engine paths, Go/Java services, React/Flutter trading interfaces (with strict Figma-driven UI implementation), automated security-reviewed dependency management across package managers, and production-ready zero-config REST/OpenAPI (Swagger) endpoint contracts. Applies trading-specific safety rules, design-first API governance, proportionate planning and testing, mandatory security scanning (SAST, dependency/SCA, secrets/API-exposure) before every completion, and an evidence-based verification report. Do not use for standalone architecture, formal code review, QA/UAT, deployment, monitoring, or unrelated systems."
---

# Trading Platform — Coding Implementation (Comprehensive)

This skill is deliberately long-form: each of the 18 dimensions that matter for implementation quality gets its own section with concrete, checkable rules rather than a one-line pointer. A set of domain files (`references/language-runtime/rust-backend.md`, `references/language-runtime/go-backend.md`, `references/language-runtime/java-backend.md`, `references/client-ui/frontend.md`, `references/client-ui/design-system.md`, `references/foundation/project-structure.md`, `references/foundation/clarification-protocol.md`, `references/testing-verification/integration-testing.md`, `references/foundation/api-contract-design.md`, and more listed in Section 4's routing table) hold stack-specific and cross-cutting detail too large to inline here — read the relevant one(s) before writing code, in addition to everything below.

**The one rule that overrides every section below: this system moves money.** Where a general best practice and "safe for a trading system" conflict, safe wins. No floats for money, no silent failure on the order path, no unbounded work in the hot path — non-negotiable regardless of what section you're reading.

## Pipeline Position

This platform's SDLC is: **PRD → HLD → LLD → Planning → Code Implementation → Code Review → QA → UAT → Deployment → Monitoring.** Each stage is owned by a separate team, and — where built — a separate skill. This skill is **stage 5 only**. Getting the boundary right in both directions matters as much as the technical content inside it:

**What this skill consumes as input** (produced by upstream stages, not re-derived by this skill):
- Architecture and interface decisions from HLD/LLD — this skill implements against those decisions, it does not re-litigate them. If a task seems to require an architectural choice HLD/LLD should have made (e.g. "should this be a new service or a module in the existing one"), that's a signal to surface the gap upward, not to silently decide it here.
- A scoped task/ticket from Planning — if a request arrives with no clear scope or acceptance criteria and none is discoverable from the codebase, treat that as a Planning-stage gap to flag, not something to invent from scratch (see Section 1, Problem Understanding, for the difference between resolving ambiguity from the codebase vs. inventing scope that was never decided).

**Recovery protocol for broken or incomplete upstream Planning/HLD/LLD** — If Planning, HLD, or LLD is missing, contradictory, underspecified, or clearly stale, this skill must recover instead of stalling or hallucinating:
- Detect the gap explicitly before implementation: missing ticket, missing architecture doc, conflicting interfaces, stale assumptions, or a request that requires an architectural choice not captured upstream.
- Recover by reconstructing the minimum safe implementation from codebase evidence: existing modules, APIs, schemas, tests, and prior implementations.
- Produce a fallback plan that clearly labels what is verified, what is assumed, and what remains unresolved.
- Ask one focused blocking question only when the gap is truly load-bearing (public contract, auth, money movement, state model, persistence, service boundary) and attach a recommended default.
- For non-blocking gaps, proceed conservatively by preserving existing behavior, minimizing blast radius, and leaving a clear TODO for upstream follow-up.
- Never silently invent service boundaries, data models, or API shapes; if the gap is architectural, surface it with a specific recommendation and a bounded implementation plan.
- Record the recovery in the Plan under a dedicated "Recovery/upstream gap" field so the handoff makes the issue, evidence, fallback decision, and unresolved items explicit.

**Actually locating and reading referenced or discoverable artifacts is required; inventing missing artifacts is not.** Before writing a `## Plan`:
1. **Search for them deliberately** — a `docs/architecture/` or `docs/api-contracts/` folder (per `project-structure.md`), a linked ticket/issue, a PRD/HLD/LLD document referenced in the task, or prior conversation context. Don't proceed on a guess about what the PRD/HLD/LLD says when the actual document is findable.
2. **Read the PRD for the *why*** — the actual user/business problem being solved — so an implementation decision can be checked against intent, not just against a literal field list. A PRD that says "traders need to react to fast-moving prices" implies latency and staleness-handling requirements even where the ticket's acceptance criteria don't spell every one out.
3. **Read the HLD/LLD for the *what/how*** — the architecture and interface decisions this skill must implement against per the bullet above. Treat a conflict between the LLD's stated interface and what seems like a better idea as a signal to flag upward (per the bullet above), not license to deviate silently.
4. **Read the Planning-stage ticket for *scope and acceptance criteria*** — what's actually in scope for this task, and what "done" is measured against.
5. **If an artifact is referenced but not findable/accessible, say so explicitly** rather than proceeding as if it had been read. For a bounded low-risk task, continue from verified codebase behavior; for an architectural, public-contract, money-movement, or otherwise load-bearing gap, raise a focused question and pause.
6. **State what was actually read, in the `## Plan`'s "Upstream reference" field** (Section 3) — name the specific document(s)/ticket consulted, not just "per requirements." This is what turns "read the PRD/HLD/LLD" from an assumed step into a checkable one.

**What this skill produces as output** (the handoff package to stage 6, Code Review):
- The code itself, plus tests, plus the required `## Plan` (Section 3) and `## Verification report` (Section 16) — together these are what a human or another skill's Code Review stage should be able to review without needing to reconstruct context this skill already had. A diff with no Plan and no Verification report is an incomplete handoff, not just a style gap.
- This skill performs **self-review** (Section 16's re-read-your-own-diff step, and the full `validation-checklist.md` gate) as quality control on its own output — that is not the same thing as the platform's formal Code Review stage, and does not replace it. Self-review catches what the author can catch; Code Review exists specifically to catch what the author can't.

## Workflow — the six module categories and how they connect

Every reference file under `references/` belongs to exactly one of six categories. This is the internal shape of stage 5 (Code Implementation) itself — Pipeline Position above shows where this skill sits in the platform's 10-stage SDLC; this shows what happens *inside* this skill on every task:

```
 FOUNDATION                     (always first: understand, clarify, plan, scaffold)
      │
      ▼
 LANGUAGE/RUNTIME  +  CLIENT/UI (implement — routed by Section 4, language and/or frontend)
      │
      ▼
 PERFORMANCE & CORRECTNESS      (as routed — hot-path/concurrency/memory work only)
      │
      ▼
 ┌─────────────────────────────────────────┐
 │  COMPLIANCE & SAFETY  — MANDATORY GATE   │◄──┐
 │  security scan · audit · deploy-safety   │   │  loop back and fix,
 └─────────────────────────────────────────┘   │  re-run the failing
      │                                          │  check, then continue
      ▼                                          │  forward — never skip
 ┌─────────────────────────────────────────┐    │  forward on a known
 │  TESTING & VERIFICATION — MANDATORY GATE │────┘  failure or finding
 │  unit · integration · comprehensive      │
 └─────────────────────────────────────────┘
      │  (only once every mandatory check passes
      │   or every finding is explicitly user-accepted)
      ▼
 Self-Verification + Communication → ## Verification report → handoff to Code Review
```

The two bottom boxes are drawn as a loop deliberately: a Compliance & Safety finding or a Testing failure does not flow forward past this point silently. It sends execution back up to Language/Runtime + Client/UI (or Performance & Correctness) to actually fix the root cause, then back down through both mandatory gates again before completion is reported. See "Mandatory Gates" and "Failure loop-back" below for the exact rules governing what counts as passing this loop versus an explicitly user-accepted exception.



Activate this skill when you need to:
- **Implement a new feature** in the backend — Rust (matching engine, order intake, execution path), Go, or Java (services adjacent to the hot path, back-office/enterprise integration) — or the Flutter/React frontend (trading UI, market data display)
- **Fix a bug** in any of the above
- **Refactor** existing backend or frontend code on this platform
- **Scaffold a new service, app, or top-level folder structure** — routes through `references/foundation/project-structure.md`
- **Write or update tests** (unit or integration) for backend or frontend logic, as part of implementing or fixing something
- **Produce an implementation plan** for a Code Implementation task specifically, when asked to plan first — not a Planning-stage sprint/roadmap plan, which belongs upstream

Do **not** activate this skill for: requirement analysis/PRD writing, system design (HLD/LLD) as a standalone deliverable, sprint/task planning, **formal code review as a distinct gate** (this skill self-reviews its own output per Section 16, but the platform's Code Review stage is a separate skill/team consuming this skill's output), QA test-strategy design, UAT, deployment/release execution, production monitoring/incident response, workflow automation, or data analytics. Each of those is a distinct stage on this platform's own SDLC, owned by other teams and, where built, other skills — this skill's job is to hand that stage a complete, well-formed package, not to perform the stage itself.

## Boundaries — What This Skill Does Not Do

Being explicit about this prevents scope creep into territory this skill isn't authorized or equipped to handle correctly:
- **Does not execute infrastructure/deployment actions.** CPU pinning, NIC tuning, kernel parameters, container/orchestration config, CI/CD pipeline changes — these get *identified and reported* as prerequisites (see `references/language-runtime/rust-backend.md`), never configured directly, unless a task explicitly puts infra in scope.
- **Does not push, merge, or deploy without explicit instruction.** Writing a commit is in scope; deciding to push it to a shared branch or trigger a deploy is not, unless the user asked for that specifically.
- **Does not make access-control/IAM policy decisions.** Application-level authorization logic (checking a user's permission in code) is in scope; provisioning or changing who has access to infrastructure, secrets stores, or admin panels is not.
- **Does not touch services outside this platform's two domains** (e.g. unrelated internal tools, other teams' repos) even if a task seems to reference them in passing — flag the boundary rather than guessing at unfamiliar code.

---

## Task tiers — match rigor to risk

Classify the task before loading references or choosing a test plan. Always apply the money, authorization, and no-silent-failure rules; tiering reduces ceremony, never safety.

| Tier | Use for | Minimum workflow |
|---|---|---|
| **Small** | Bounded internal bug fix, copy/layout adjustment, or test-only change; no public contract, money calculation, order state, concurrency, or shared type change | Read the relevant code and domain reference. Search for upstream artifacts if referenced or easily discoverable. State a compact plan, add/run a focused regression or unit test where testable, then report exact verification. |
| **Standard** | A normal feature, multi-file change, stateful UI behavior, or cross-module change | Read applicable upstream artifacts and all routed domain references. Use the full Plan template, test as each logical unit is completed, run affected integration tests, and report applicable checks. |
| **Critical** | Matching/order path, money or position calculation, auth, public/wire contract, durable audit, concurrency, or measured-performance work | Use the Standard workflow plus every relevant safety/performance/contract reference, explicit rollback or migration treatment, realistic-load measurement where applicable, and the full comprehensive test gate. Pause on unresolved load-bearing requirements. |

For a **Small** task, use this compact plan instead of the full template:

```
## Plan
Goal: <one line>
Scope: <files/behavior changed; explicit non-goals>
Verified: <code, tests, and upstream artifacts actually inspected>
Risk and invariants: <why Small; money/order/contract impact or “none”>
Test: <focused test or concrete reason no automated test applies>
```

---

## 1. Problem Understanding

Do not start implementing from an ambiguous request. A one-line request is almost always hiding requirements.

- **Decompose before planning.** "Add a new order type" implies: what fields, what validation rules, does it need a new wire-format variant, does the risk-check layer need to know about it, does the frontend need a new form state. Write out the implied sub-requirements before touching code.
- **Resolve what you can from the codebase first.** If an existing similar feature answers the question (how error codes are structured, what a comparable form does), read it and answer yourself. Don't ask the user something the code already tells you.
- **Ask what you genuinely can't resolve — one focused question at a time, with your own recommended answer attached**, not an open-ended "what do you want?" State the tradeoff, don't just list options.
- **Walk decision branches sequentially, not as a flat list.** Resolving one decision often changes what the next question even needs to be — asking everything up front hides those dependencies.
- **Infer implicit non-functional requirements too**: does this need to be idempotent? Auditable? Does it touch anything regulatory (trade reporting, KYC)? These are rarely stated explicitly but are usually assumed.
- **See `references/foundation/clarification-protocol.md` for the full mechanics** of this — how to formulate a question that's actually easy to answer, when a genuine ambiguity is worth blocking on vs. worth stating as an assumption and proceeding past, and how to handle new ambiguity that surfaces mid-task rather than only at the start. This applies every time this section's "ask what you can't resolve" rule fires, not just for the initial request.
- **For upstream gaps specifically, use `references/foundation/recovery-protocol.md`**. This gives a concrete fallback path when Planning, HLD, or LLD is missing or weak, so the skill can recover safely instead of inventing architecture or scope.

## 2. Codebase Understanding

Build a working model of the area you're touching before modifying it — see `references/foundation/codebase-context.md` for the full phased approach (orientation → dependency mapping → risk profile). In short:

- Identify the component archetype (hot-path service, UI component, shared library, config/infra) — this determines which rules apply.
- Trace one real request/data flow end to end before changing anything; don't infer behavior from names.
- Find every caller before changing a shared type or signature — a "local" change to a widely-used struct is rarely local in effect.
- Note existing conventions (naming, error handling, module layout) and match them rather than introducing a personally-preferred alternative.

## 3. Implementation Strategy

- **Compare at least two approaches internally before committing**, even if you only present one — this catches cases where the "obvious" first approach has a hidden cost (e.g. touching a shared hot-path struct when a local wrapper would do).
- **Prefer the minimal-diff approach that fully satisfies the requirement.** A broader "while I'm in here" rewrite has more regression surface, which costs more in a system where regressions cost money.
- **Never break an existing API/contract silently.** If a change requires breaking one, name it explicitly, and propose a migration path (versioning, deprecation window) rather than a flag day.
- **Plan affected files up front** and state them before starting, using this required format — not free-text, so it's actually checkable at a glance. Every field below is required; "N/A" is an acceptable answer, silence is not:

```
## Plan
Upstream reference: <the ticket/task from Planning, and the HLD/LLD decision this implements against, if one exists. If neither exists and the task's scope isn't discoverable from the codebase, say so explicitly here — that's a signal to flag upstream, not to invent scope, per Pipeline Position above.>
Goal: <one line — what this accomplishes>
Files touched: <path> — <what changes>, <path> — <what changes>, ...
Approach: <1-3 sentences>
Codebase state: Verified: <what you actually read/checked directly> | Assumed: <what you're inferring without having checked> | Not explored: <what's genuinely out of scope for this task>
Recovery/upstream gap: <if Planning/HLD/LLD was missing, contradictory, or weak, describe how you recovered from it, what evidence you used, and whether any follow-up is still needed upstream>
Type/domain invariants: <does any type choice make a stated requirement structurally unreachable? e.g. "u64 price makes negative values unrepresentable — negative-price rejection must be enforced at the parse/construction boundary, not inside a function that only ever receives an already-valid u64." If no such conflict exists, say so explicitly rather than leaving this blank.>
Critical-path status: <is this code confirmed on the profiled hot path (cite what confirmed it), or is hot-path discipline being applied precautionarily without profiling? Say which — don't assert "zero-allocation" or "O(1)" rules apply without stating which case this is.>
Complexity claims: <actual Big-O for any lookup/data structure this introduces, with justification. A bounded linear scan over a small fixed N is often fine — but call it "bounded linear scan, N≤X" not "O(1)" unless it actually is.>
Red step: <the first failing test you will write and run before any implementation, and what its failure will confirm>
Out of scope: <what this deliberately does not touch>
Risk: <low/medium/high> — <why>
```

- **Sequence as vertical slices** for anything nontrivial — a thin, testable end-to-end path first, broadened afterward — rather than building every layer to completion before anything is runnable.
- **Design deep modules with narrow seams**: a caller should need to know *what* a function/module does, not *how* — hide implementation complexity behind a simple interface rather than leaking internal state or feature-specific logic into shared/general-purpose code. Before a change crosses an architectural seam (the boundary between two modules), define an explicit interface/adapter at that boundary rather than reaching across it directly.

## 4. Domain Expertise (Frontend / Backend / Infrastructure)

This platform has genuinely different rules per domain and per backend language — read every matching file before writing code, every time, not just when the task "seems complex enough to need it":

| Task touches | File |
|---|---|
| Rust backend — matching engine, order intake, execution path (the confirmed hot path defaults here) | `references/language-runtime/rust-backend.md` |
| Go backend — order-routing gateways, risk services adjacent to the hot path, general services favoring concurrency + operational simplicity | `references/language-runtime/go-backend.md` |
| Java backend — back-office/settlement, compliance/reporting, enterprise/custodian integration, transactional/ORM-heavy services | `references/language-runtime/java-backend.md` |
| Choosing which backend language a new service should use, when not already dictated by an HLD/LLD decision | See each file's opening paragraph for its intended niche; if genuinely unclear from the task/architecture docs, this is a `references/foundation/clarification-protocol.md` question, not a default guess |
| Flutter/React frontend — trading UI, market data display (functional/real-time correctness rules) | `references/client-ui/frontend.md` |
| Any frontend UI work where a Figma URL or design specification is provided | `references/client-ui/figma-design-engine.md` — **PRIMARY source of truth** (`Figma > written prompt`); extract design tokens and build matching components strictly |
| Any frontend UI work, or any backend service-structure work, where visual/structural design quality matters | Also `references/client-ui/design-system.md` — use its bundled token, hierarchy, density, and review process before calling new UI or newly-scaffolded service structure done |
| Any frontend UI work — usability, flow, accessibility, interaction quality | Also `references/client-ui/ux-design.md` — required alongside `design-system.md`, not a substitute for it or optional once the UI "looks good" |
| Scaffolding a new service, new frontend app, or any new top-level folder structure | Also `references/foundation/project-structure.md` — required before creating files, not just for "big" projects. **The directory skeleton (backend/frontend/service folders) must be created before any implementation file is written inside them** — see that file's "Hard rule" section |
| Any task, before declaring it complete, where the deliverable must be verified free of known bugs | Also `references/testing-verification/comprehensive-testing.md` — the consolidating gate covering E2E, regression, exploratory, non-functional, accessibility, and cross-platform testing on top of the unit/integration coverage from `test-execution.md`/`integration-testing.md` |
| Both backend and frontend | The relevant backend file(s) first (the wire contract should be settled before the frontend consumes it), then `references/client-ui/frontend.md`, `references/client-ui/figma-design-engine.md`, and `references/client-ui/design-system.md` |
| Designing, adding, or changing any REST endpoint's request/response contract | Also `references/foundation/api-contract-design.md` — the OpenAPI/Swagger spec is designed and reviewed *before* implementation, and interactive Swagger UI is auto-bootstrapped to serve on `/swagger` or `/docs` zero-config |
| Anything on a **confirmed** critical path where the baseline hot-path rules aren't enough | Also `references/performance-correctness/performance-engineering.md` |
| Any concurrent hand-off or lock-free shared structure (Rust), or any concurrent code generally (Go goroutines, Java `java.util.concurrent`) | Also `references/performance-correctness/concurrency-patterns.md` — required whenever `Mutex`-free concurrent Rust is being written; the concurrency sections of `go-backend.md`/`java-backend.md` cover the equivalent discipline for those languages |
| Any allocation-strategy decision (pre-allocation sizing, object pools, allocator choice) or unexplained hot-path latency jitter | Also `references/performance-correctness/memory-management.md` (Rust); see the GC-pause-awareness sections of `go-backend.md`/`java-backend.md` for the equivalent concern on those runtimes |
| Any audit trail, compliance logging, or durable record-keeping touching the order path | Also `references/compliance-safety/durability-and-audit.md` — required before adding any logging/persistence near the hot path, since the naive approach silently breaks the latency budget |
| Any task requiring unit tests to actually be run and verified after code is generated | Also `references/testing-verification/test-execution.md` — required for the "tests run" claim in any Verification report to be a real, checkable claim rather than an assumption |
| Any task crossing a service, process, or language boundary (backend↔backend, backend↔frontend), or any multi-file task at all | Also `references/testing-verification/integration-testing.md` — covers cross-boundary/contract testing and the required per-file test cadence (test immediately after each file, not batched at the end) |
| Any change to matching logic, risk checks, or other hot-path decision-making that needs validating against real traffic before full cutover | Also `references/compliance-safety/deployment-safety.md` |
| Authentication, JWT, session management, or password security handling | Also `references/compliance-safety/security check/authentication-patterns/SKILL.md` |
| Resource access by ID, user-scoped endpoints, or authorization checks | Also `references/compliance-safety/security check/idor/SKILL.md` |
| Logging, data persistence, PII handling, or sensitive token exposure prevention | Also `references/compliance-safety/security check/senstive-data-exposure/SKILL.md` |
| Raw SQL queries, database access layers, or ORM parameter binding | Also `references/compliance-safety/security check/sql-injection/SKILL.md` |
| **Every task, no exceptions, before completion is reported** | **Also `references/compliance-safety/security-scanning/sast-code-scanning.md`, `references/compliance-safety/security-scanning/dependency-vulnerability-scanning.md` (automated security review gate), and `references/compliance-safety/security-scanning/secrets-and-exposure-scanning.md` — MANDATORY, see the Mandatory Gates section below. Not tier-reducible the way other checks are.** |

Infrastructure/deployment work is explicitly **out of scope** for this skill — say so rather than improvising infra advice; that's a separate team's domain per your own SDLC split.

## Mandatory Gates — FORCEFUL SECURITY TESTING & USER REVIEW PAUSE

Two gates apply to every task regardless of tier, and neither is optional to *run*:

- **Forceful Security Scanning Gate (MANDATORY)** (`references/compliance-safety/security-scanning/`) — Automated security testing commands (dependency vulnerability audit e.g. `npm audit`, `cargo audit`, `go vulncheck`, `pip audit`; SAST code scanning; and secrets/exposure scanning) **MUST BE EXECUTED FORCEFULLY** after code implementation and dependency installation.
  - **MANDATORY USER REVIEW PAUSE ON ANY VULNERABILITY**: If ANY security scan or audit surfaces ANY vulnerability (Critical, High, Medium, or Low severity), security risk, or secret exposure:
    1. **DO NOT silently bypass or auto-complete the task.**
    2. **STOP execution immediately.**
    3. **Present a structured "Security Vulnerability Review" table** to the user detailing: `Target / Package`, `CVE / Finding ID`, `Severity`, `Vulnerability Details`, and `Recommended Remediation`.
    4. **EXPLICITLY PAUSE AND REQUIRE USER REVIEW**: Ask the user to review the findings and choose whether to fix, override with justification, or update dependencies before proceeding.
  - Reporting a task "complete" without running security tests or without obtaining explicit user review for surfaced vulnerabilities is a critical violation of this skill.
- **Testing** (`references/testing-verification/`) — the tier-appropriate test suite (Section 11's `test-execution.md`/`integration-testing.md`, plus `comprehensive-testing.md` for Standard/Critical tasks) must actually run and pass, or fail with a resolved reason, before completion. **A failing test blocks completion — it does not get silently reported alongside a "done" claim.** See "Failure loop-back" immediately below for what happens when it fails.

## Failure loop-back — testing and security findings send you back, not forward

If a mandatory test fails, or a security scan surfaces a finding you're fixing rather than the user accepting: **do not proceed to the next stage or report completion.** Go back to implementation:
1. Diagnose the actual cause — re-read the failing test's output or the scanner's finding detail, don't guess.
2. Fix at the root (the implementation, not the test — unless the test itself was wrong, which is a distinct, rarer case worth stating explicitly if true).
3. Re-run the specific check that failed, not just eyeball the fix.
4. Only once it passes, continue forward from where you left off — this is a loop back to Section 11/Testing or Section 10/Security, not a restart of the entire task from Section 1.
5. If the same check fails repeatedly (3+ attempts) without a clear cause, that's a signal to stop looping and surface the pattern to the user explicitly — a repeated silent retry loop that never asks for help is its own failure mode.

## 5. Code Quality

- **Naming carries meaning.** A variable/function name should make its purpose obvious without needing to read its body. Avoid abbreviations that aren't already established convention in this codebase.
- **Modularity**: one function, one responsibility. If a function needs "and" in its description, split it.
- **DRY, with judgment**: duplicated logic in 3+ places is a strong signal to extract; 2 places is often fine — premature abstraction has its own maintenance cost, don't over-correct.
- **SOLID, applied pragmatically**: especially single-responsibility and dependency-inversion (depend on an interface/trait, not a concrete implementation, where it enables testing or swapping — but don't add an abstraction layer nothing currently needs).
- **Idiomatic code for the language in use** — Rust/Go/Java code should each read like idiomatic code in that language (not a transliteration of another language's patterns — see `references/language-runtime/rust-backend.md`, `references/language-runtime/go-backend.md`, `references/language-runtime/java-backend.md`), React/Flutter code should follow that framework's conventions, not fight them.
- **Structural quality applies to more than logic correctness.** Layering, naming specificity, and folder/file organization are part of code quality, not separate from it — see `references/client-ui/design-system.md`'s "backend design quality" section and `references/foundation/project-structure.md` for what a well-organized (as opposed to a merely-working) implementation looks like.

## 6. Correctness

- **Preserve existing behavior unless the task explicitly asks to change it.** A refactor that quietly alters behavior is a bug, not a refactor — see the "differential review mindset" in `references/compliance-safety/security-review.md`.
- **Handle edge cases explicitly**: empty input, boundary values, concurrent access, partial failure. State which ones you considered and how they're handled — don't let "it works on the happy path" pass as done.
- **Compatibility**: check whether a change affects existing callers, stored data formats, or serialized wire messages already in flight. A backend field-type change that's fine for new connections can break an in-progress session using the old format.
- **Contracts**: honor documented and implicit contracts both — a function that says it doesn't allocate, or is safe to call concurrently, needs to keep being true after your change, not just compile.
- **Check for structural contradictions between a type choice and a stated requirement before writing the implementation.** If a requirement says "reject X" and the type you've chosen makes X unrepresentable in the first place, that's not automatically fine — it means the requirement is enforced somewhere *else* (typically the parse/construction boundary), and you must say where explicitly, not silently drop the requirement or write a test that can't actually exercise it. Concrete pattern: a validator taking `price: u64` cannot test "reject negative price" internally, because a negative value can never reach it — the rejection has to happen when raw/signed input is parsed into that `u64` in the first place, or via a newtype (`PositivePrice`) whose only constructor enforces it. Prefer "parse, don't validate" — make illegal states unrepresentable by construction rather than checking for them after the fact — over adding a redundant runtime check for something the type system already prevents.
- **State complexity claims accurately, not aspirationally.** "O(1)" and "zero-allocation" are claims that need to be true, not goals stated as if already achieved — see the "Complexity claims" field in the required Plan template (Section 3).

## 7. Framework Knowledge

Framework-specific rules live in the domain files (React/Flutter patterns in `references/client-ui/frontend.md`), but the general principle applies everywhere: **use the framework the way its own idioms intend, don't fight it with patterns imported from a different framework or language.** If you're not confident about a specific framework API's current behavior (a hook's exact semantics, a Flutter widget lifecycle detail), say so rather than asserting confidently from partial memory — framework APIs change across versions and getting this wrong compiles but misbehaves.

## 8. Language Expertise

- **Rust**: ownership and borrowing should shape the design, not be fought against with excessive `.clone()`/`Rc<RefCell<>>` as a way to avoid thinking about lifetimes — see `references/language-runtime/rust-backend.md` for the hot-path-specific rules (allocation discipline, concurrency, data structures).
- **Go**: errors are values, checked and wrapped, not exceptions — see `references/language-runtime/go-backend.md` for goroutine ownership/shutdown discipline and GC-pressure awareness for services near the hot path.
- **Java**: prefer immutability (records, `final`), constructor injection over field injection, and `java.util.concurrent` primitives over hand-rolled synchronization — see `references/language-runtime/java-backend.md` for GC/latency discipline on latency-sensitive services and the `BigDecimal`-not-`double` rule for money.
- **Dart (Flutter) / TypeScript (React)**: use the type system fully — avoid `dynamic`/`any` as an escape hatch from a type error you don't understand; understand why the type doesn't fit before working around it.
- When multiple languages are involved in one task (any backend language + Dart/TS frontend, or two backend services in different languages), keep the shared contract (wire format, field types, especially numeric precision) consistent across the language boundary explicitly — this is the single most common source of cross-language bugs in a full-stack or cross-service change, and `references/testing-verification/integration-testing.md` covers how to actually test that consistency rather than assume it from two independent unit-test suites.

## 9. Performance Awareness

- **Know the complexity of what you're writing.** An O(n²) operation on data that's small today but grows is a debt, not a bug — flag it if you're accepting it as a tradeoff, don't let it pass silently as if it were O(n).
- **Backend hot path**: see `references/language-runtime/rust-backend.md` for the latency-budget baseline (allocation, locking, socket tuning, serialization), and `references/performance-correctness/performance-engineering.md` for deeper techniques (cache-line layout, false sharing, benchmarking methodology) once the baseline is in place and profiling justifies going further. Any concurrent hand-off or shared structure on the hot path also needs `references/performance-correctness/concurrency-patterns.md` — lock-free code has its own correctness risks that "no locks" alone doesn't cover.
- **Frontend**: rendering cost matters at scale (long lists, high-frequency updates) even though the frontend isn't on the backend's latency clock — see `references/client-ui/frontend.md` for coalescing/virtualization rules.
- **Database/network calls**: never issue a query or network call inside a loop without considering whether it should be batched — this is the single most common accidental performance bug across both frontend (waterfalled API calls) and backend (N+1 queries) work.
- **Don't optimize speculatively.** Performance work should be driven by a measured or clearly foreseeable problem, not a guess — see Section 16 (self-verification) for how to actually measure rather than assume.

## 10. Security Awareness

Full detail in `references/compliance-safety/security-review.md` (Rust `unsafe`-boundary review, differential review mindset, footgun/"sharp edges" awareness) and the `references/compliance-safety/security check/` domain guides (`authentication-patterns`, `idor`, `senstive-data-exposure`, `sql-injection`). The headline rules, inline because they're too important to be one hop away:

- Input validated at the boundary, not deep in business logic.
- Authorization checked server-side, always — never trust a client's claim about itself or another user's data (see `references/compliance-safety/security check/idor/SKILL.md`).
- Authentication, JWT, and session handlers must adhere to secure credential & token management patterns (see `references/compliance-safety/security check/authentication-patterns/SKILL.md`).
- No secrets, tokens, or PII in logs, error messages, or client-visible responses (see `references/compliance-safety/security check/senstive-data-exposure/SKILL.md`).
- Database access layers must use parameterized queries or safe ORM bindings to prevent injection vulnerabilities (see `references/compliance-safety/security check/sql-injection/SKILL.md`).
- Every `unsafe` Rust block carries a written justification for the invariant it relies on.
- Any new dependency added to the hot path is named and justified, not silently pulled in.

## 11. Testing Mindset

- **Default to test-first for new behavior**: write a failing test before the implementation, confirm it fails for the right reason, then implement. This is the default for genuinely new logic, not a rule to apply mechanically everywhere.
- **Scope the rigor to the task type, not uniformly**: a small, tightly-scoped bug fix or a one-line config change doesn't need a full red-green-refactor cycle for every sub-step — a single focused regression test that reproduces the bug is enough. For exploratory work where the shape of the solution isn't known yet, write a **characterization test** (pins down current/intended behavior) before restructuring, rather than forcing strict TDD onto code whose design is still being discovered. Reserve full step-by-step TDD for genuinely new hot-path logic where getting the behavior specified precisely, upfront, matters most (see Section 17 for the task-type breakdown).
- **Update existing tests when behavior intentionally changes** — a test that now fails because the old behavior was correct and the new behavior is also correct just needs its expectation updated, not deletion.
- **Identify missing coverage actively**: after implementing, ask "what input would break this that I haven't tested?" rather than considering the task done once the tests you thought of pass.
- **Test pyramid discipline**: most coverage at the unit level (fast, isolated), less at integration, least at end-to-end — if a task seems to need many E2E tests, that's often a sign the coverage belongs at a lower level instead.
- **Preserve behavior through refactors**: a refactor's test suite should be the same tests, still passing — new test failures during a refactor mean behavior changed, which means it's not a pure refactor anymore.
- **Running and verifying tests**: see `references/testing-verification/test-execution.md` for concrete unit-test tooling (test runner, fixtures, coverage measurement, fuzzing for boundary code) — this section establishes the discipline of writing tests first; that file covers actually running and verifying them, which is what turns "I wrote tests" into a checkable Verification report claim per Section 16.
- **Integration testing and per-file cadence are required, not optional, for any multi-file or cross-boundary task**: see `references/testing-verification/integration-testing.md` for what needs an integration test (cross-service, cross-language, or contract-touching changes) and the mandatory cadence — run each file's tests immediately after generating/editing it, fix before moving on, don't batch every file's tests to a single run at the end of the task.

## 12. Refactoring Capability

- **Never refactor and change behavior in the same commit/diff** — separate "restructure" from "change what it does."
- **Refactor under test coverage.** If the code being refactored has no tests, write characterization tests first (pinning current behavior) before restructuring.
- **Small steps, verified between each one** — rename, extract, inline, one at a time with tests run after each, not all changes followed by one test run at the end.
- **Common smells to watch for**: long functions, duplicated logic, deep nesting (favor early returns/guard clauses), primitive obsession (raw strings/numbers standing in for a real type), god objects that know about and touch everything.
- **"Sequential undo"**: a growing chain of conditionals where each new case partially undoes or special-cases the previous one is a structural symptom, not just a style issue. Replace it with a state machine, polymorphism, or an explicit dispatcher — but only when that actually makes the behavior simpler to follow than a well-organized conditional; don't add structure for its own sake. The goal is reducing complexity, not relocating it to a different pattern that's equally tangled.

## 13. Context Management

- **Read what's relevant, not everything.** Loading an entire large file to change three lines wastes context that could go toward understanding the parts that actually matter for the task.
- **Avoid context overflow on long tasks** by working in focused increments — for a multi-file change, complete and verify one coherent piece before moving to the next rather than holding the entire change in flight unverified.
- **Maintain state explicitly across a long task**: if a task spans many steps, keep track of what's done, what's pending, and what was decided (and why) — don't rely on it being implicitly recoverable from the diff alone if the task gets interrupted or handed off.

## 14. Decision Making

- **Name the tradeoff, don't hide it.** "Simplicity vs. flexibility," "ship now vs. handle the edge case properly," "extra abstraction vs. YAGNI" — when a real choice exists, say what you chose and why, not just what you chose.
- **Weight risk by consequence, not just probability.** A rare failure mode on the order-execution path deserves more caution than a common failure mode in a settings page — apply extra scrutiny where a mistake is expensive to recover from.
- **Consider future maintenance, not just present correctness.** Code that works today but that only the original author can safely modify is a liability in a team codebase — prefer the version a colleague could pick up without an explanation.

## 15. Tool Usage

- **Git**: atomic commits, one logical change each; imperative-mood messages; never commit debug prints, commented-out code, or secrets — check the diff before committing, every time.
- **Search before assuming**: use the codebase's own search/grep rather than guessing whether something already exists (a utility function, an existing validation helper) — reinventing something that already exists is wasted work and a maintenance liability (now two implementations to keep in sync).
- **Linters/formatters**: run them and respect their output rather than working around a warning with a suppression comment, unless the warning is genuinely a false positive — and if it is, say why in the comment rather than silently suppressing.
- **Build systems/package managers**: understand what a dependency addition actually pulls in (transitive dependencies, license, maintenance status) before adding it, especially for the Rust hot-path service.
- **MCP tools / other integrations**: use what's available (e.g. a connected issue tracker, CI status) rather than asking the user to manually relay information a tool could fetch directly.

### Dependency installation — automatic, paired with mandatory scanning

- **Install dependencies automatically as part of implementation** — `npm install`, `pnpm add`, `bun add`, `cargo add`, `go get`, `pip install`, `mvn dependency:add`, `flutter pub add`, and their lockfile-changing equivalents run automatically without asking the user which dependency to install.
- **Automated Dependency Security & Health Review** — Before finalizing installation, dependencies are reviewed for maintenance status, popularity, production readiness, licenses, deprecated status, and vulnerability history (`references/compliance-safety/security-scanning/dependency-vulnerability-scanning.md`).
- **Safe dependencies auto-install silently** — Packages with clean security profiles and permissive licenses are installed without pausing or prompting.
- **Dependency Security & Vulnerability Review Pause Protocol (MANDATORY)** — If any dependency or codebase scan reveals ANY vulnerability (Critical, High, Medium, or Low), is deprecated, or has security risks, **DO NOT silently install or auto-complete**. Generate the structured "Security & Vulnerability Review" table (showing Package/Target, Version, CVE/Issue, Severity, Details, Recommended remediation) and **STOP execution to explicitly ask the user for review and decision** before proceeding.
- **Name what was installed in the Verification report** — The report lists every package added/changed, exact install commands, and vulnerability scan results.

## 16. Self-Verification

Never report a task complete without having actually checked it:
- Run the tests — don't assume they pass because the logic looks correct on inspection.
- Re-read your own diff once specifically looking for what a reviewer would flag first: unhandled errors, unclear naming, leftover debug code, accidental scope creep.
- State what you verified and how ("ran the test suite," "manually traced the logic for the new branch") — a completion claim with no attached verification method isn't trustworthy.
- If something couldn't be verified (no test environment, external dependency unavailable), say so explicitly rather than reporting success anyway.
- Compile/build check is the floor, not the ceiling, of verification — code that compiles and has never been run against a realistic input has not been verified.

**Acceptance thresholds — fill in the actual project values below; these are placeholders, not defaults to leave unfilled:**
| Metric | Threshold | How to check |
|---|---|---|
| Backend hot-path latency | p99.9 ≤ 8ms end-to-end (order received → order acknowledged), under realistic burst load, not steady-state average | `<fill in your actual load-test command — e.g. a k6/custom harness replaying market-open burst patterns>` |
| Error rate on order path | `<fill in — e.g. 0% for unhandled panics; validation rejections must return a clean typed error, not a silent drop>` | `<fill in your error-tracking/log-query command>` |
| Reconciliation | `<fill in — e.g. order/position state matches expected ledger after test run, zero unexplained discrepancies>` | `<fill in your reconciliation script/command>` |
| Test suite | 100% of the affected test files pass, zero skipped without justification | `<fill in your actual test command, e.g. cargo test --release>` |
| Frontend render budget | No dropped frames / jank under realistic tick volume | `<fill in your perf-profiling command>` |

Use this required report format when declaring a task complete — don't substitute a prose paragraph for it:

```
## Verification report
Tests run: <exact command(s)> — <pass/fail>
Manually verified: <what you traced by hand, if anything, and how>
Acceptance thresholds met: <table above, filled in with actual measured values, or "not measured — reason">
Figma UI Fidelity Status: <"N/A — no UI work" | "Verified strictly against Figma URL: <url>" | "Paused — Figma URL missing/inaccessible">
Dependency status: <"none installed" | "installed: <packages + exact commands>, scanned: <result>" | "paused for approval: <Dependency Review table generated for Critical/High/Medium CVEs, awaiting user decision>">
Swagger / OpenAPI status: <"N/A — no REST endpoints" | "Verified live Swagger UI running at /swagger or /docs zero-config">
Security scan status: <SAST result + finding summary> | <dependency scan result + finding summary> | <secrets/exposure scan result + finding summary> — any critical/high finding named explicitly, not summarized as a pass/fail count alone
Not verified: <anything you could not check, and why>
```

## 17. Adaptability

The right approach differs by task type — don't apply "new feature" discipline to a one-line bug fix, or "quick patch" looseness to a matching-engine change:
- **Feature work**: full sequence — clarify, plan, TDD, implement, verify.
- **Bug fixes**: reproduce first (write a failing test that demonstrates the bug) before touching the fix — this both confirms you understand the actual bug and prevents "fixed" without evidence.
- **Refactoring**: see Section 12 — behavior-preserving, test-gated, small steps.
- **Performance optimization**: measure before optimizing (Section 9) — never optimize based on intuition alone.
- **Migration**: plan the rollback path before starting the migration, not after something goes wrong.
- **Prototyping/exploration**: it's acceptable to relax some of the above (less test coverage, less polish) *if the user has explicitly signaled this is throwaway/exploratory* — but say that assumption out loud rather than silently deciding a task is "just a prototype."

## 18. Communication

When reporting on completed work:
- **What changed** — concretely, not just "updated the order handling."
- **Why** — tie back to the original request, especially for any judgment call made along the way.
- **What you're not fully certain about** — flag real uncertainty plainly rather than burying it in confident-sounding prose.
- **What a human reviewer should specifically double-check** — point at the highest-risk part of the change, not a generic "please review."
- **Follow-up work identified but out of scope** — smells noticed, risks flagged, things deliberately not fixed now — so they don't silently disappear.

---

## Execution order (apply only the tier-appropriate steps; steps 7-8 are never tier-reducible)

**This sequence follows the six module categories in order: Foundation → Language/Runtime + Client/UI → Performance & Correctness (as needed) → Compliance & Safety (mandatory) → Testing & Verification (mandatory) → completion.**

1. **Foundation** — classify the task tier; locate and read referenced or discoverable upstream artifacts (`references/foundation/codebase-context.md`, `references/foundation/clarification-protocol.md` for any open question). Do not invent missing artifacts; escalate only a missing load-bearing decision.
2. Sections 1 & 3 (Problem Understanding, Implementation Strategy) — clarify and plan before code, using the required `## Plan` template.
3. **If scaffolding new structure**: read `references/foundation/project-structure.md`, state the planned structure in the `## Plan`, then create the full directory skeleton before writing a single implementation file (hard-ordered, see that file's "Hard rule" section).
4. **If this task adds/changes an HTTP endpoint's contract**: read `references/foundation/api-contract-design.md` and design/review the OpenAPI (Swagger) spec **before** implementing the endpoint — this is mandatory for any new or contract-changing endpoint, not optional polish added afterward.
5. **Language/Runtime + Client/UI** — Section 4 routing → read the matching domain file(s) (`rust-backend.md`/`go-backend.md`/`java-backend.md`/`frontend.md`). For UI work, also read `references/client-ui/design-system.md` and `references/client-ui/ux-design.md` before writing components.
6. **Performance & Correctness** (as routed) — apply Sections 11, 5, 6, 9 (Testing, Code Quality, Correctness, Performance) while implementing. Follow `references/testing-verification/integration-testing.md`'s per-file cadence throughout: test each file right after it's generated/edited, don't batch to the end. Load `performance-correctness/` files only where Section 4's routing table actually applies them.
7. **Compliance & Safety — MANDATORY, every task, no tier exception**: run `references/compliance-safety/security-scanning/sast-code-scanning.md`, `dependency-vulnerability-scanning.md` (scanning every dependency installed per the Tool Usage section), and `secrets-and-exposure-scanning.md`. Also apply `references/compliance-safety/security-review.md` and any routed `durability-and-audit.md`/`deployment-safety.md`. See "Mandatory Gates" above for what "mandatory" permits (run always; a finding can be acknowledged and accepted by the user, never silently omitted).
8. **Testing & Verification — MANDATORY, every task, no tier exception**: run the tier-appropriate suite — `test-execution.md`/`integration-testing.md` always, plus the applicable `comprehensive-testing.md` rows for Standard/Critical tasks. **If any test or Step 7 scan produces a failure or finding you're fixing (not user-accepting): loop back to step 5/6, fix at the root, re-run the specific check, then return here — do not proceed to completion with a known failure.** See "Failure loop-back" above for the full procedure, including when to stop looping and escalate.
9. Sections 16 & 18 (Self-Verification, Communication) — apply before calling anything done. Run the final gate: `references/testing-verification/validation-checklist.md` — this consolidates every checklist across every category above into one pass/fail pass.

Sections 13-15 (Context Management, Decision Making, Tool Usage) and 17 (Adaptability) aren't a separate phase — they're standing discipline that applies throughout all of the above, not a step completed once and left behind.

If you want to see what a fully compliant Plan → implementation → Verification report actually looks like end to end, `references/examples/limit-order-validator.md` is a complete worked example — it's the real validator task from this skill's own testing history, including the specific mistakes an earlier version made and how the corrected version avoids them. That example is deliberately *not* on the hot path, since it's a new, unprofiled component. For the full hot-path treatment — confirmed critical-path status, cache-line-aware ring buffer hand-off, O(log n) order-book insertion, and loom-based concurrency verification — see `references/examples/matching-engine-hot-path.md`. For the specific, easy-to-get-wrong case of adding compliance/audit logging without breaking the latency budget — including a naive-vs-correct contrast — see `references/examples/order-audit-logging.md`.
