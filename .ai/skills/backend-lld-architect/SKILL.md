---
name: backend-lld-design
description: "Generate exhaustive, implementation-ready Low-Level Design (LLD) documents for backend systems, using a PRD (Product Requirements Doc) and/or HLD (High-Level Design) as source input. Use this skill whenever the user asks to 'create an LLD', 'design the backend in detail', 'low-level design for X', wants class diagrams, database schemas, design patterns, SOLID breakdowns, interface/skeleton code, or concurrency & thread-safety analysis for a backend system or feature. Also trigger when the user uploads or references a PRD/HLD document and asks to turn it into a detailed backend design, or asks for 'production-grade', 'FAANG-style', or 'principal engineer level' system design. Push to use this skill even if the user only says 'design the backend for X' without explicitly saying LLD."
risk: unknown
source: custom
date_added: "2026-07-30"
---

# Backend LLD Design Workflow

Generate a complete, implementation-ready Low-Level Design document for a backend system or feature, grounded in a provided PRD and/or HLD, following a strict Principal-Architect-quality structure.

[Extended thinking: This skill turns upstream product/architecture artifacts (PRD, HLD) into a concrete, code-adjacent LLD. It never invents scope beyond what the PRD/HLD imply without flagging assumptions, and it flags when the design itself is proposing a new bounded context rather than implementing an already-ratified one. It always produces a Mermaid class diagram, a real database schema, an explicit API contract (endpoints, DTOs, auth enforcement), interface-driven skeleton code with real pseudocode for core orchestration methods and explicit repository contracts, a SOLID justification, a concurrency/edge-case section, and a test strategy — never generic prose. The target reader is a senior engineer who will start implementing directly from this document.]

## Use this skill when

- The user asks to design, or produce an LLD for, a backend system, service, or feature
- A PRD and/or HLD (uploaded, pasted, or described) needs to be translated into a detailed backend design
- The user wants class diagrams, DB schemas, design patterns, SOLID analysis, interface code, API contracts, test strategy, or concurrency handling for a backend
- The user references "production-grade", "principal engineer", "FAANG-style", or similar quality bars for a design

## Do not use this skill when

- The task is frontend/UI design only (route to `fullstack-hld-architect` or `frontend-design` instead)
- The user wants a PRD or HLD *written* rather than an LLD (route to `requirements-engineering` or `fullstack-hld-architect`)
- The user wants a project plan/timeline rather than a technical design (route to `project-planning`)

## Step 0: Gather Inputs

Before writing anything, establish grounding. Do not skip this — an LLD invented without source material is guesswork, not design.

1. **Look for a PRD and/or HLD** in the conversation or uploads (`/mnt/user-data/uploads`). If found, read it fully (use `file-reading` skill routing if content isn't already in context).
2. If no PRD/HLD exists and the user hasn't described the feature in enough detail to design against, ask **one** targeted clarifying question covering the biggest gap (e.g., "What's the core entity this system revolves around, and roughly what scale — requests/sec, data volume — should it support?"). Otherwise, proceed with clearly stated assumptions rather than blocking.
3. Extract and explicitly restate, before designing:
   - Core functional scope (what the PRD says the system must do)
   - Any non-functional targets already stated (SLAs, scale, latency, availability)
   - Any architectural decisions already made in the HLD (chosen containers/services, tech stack, communication protocols, existing bounded contexts) — the LLD must be **consistent with the HLD**, not reinvent it. If the HLD picks Postgres and REST, the LLD schema and interfaces should reflect that unless there's a stated reason to deviate (state the reason if so).
4. If the PRD/HLD conflicts with what's being asked, or a critical decision required for the LLD is genuinely unresolved upstream (e.g., HLD doesn't say sync vs. async), do not silently invent it — flag it in the "Open Assumptions" note and pick the most defensible default to proceed.
5. **Check for un-ratified bounded contexts.** If the design being requested introduces a new service, module, or bounded context (e.g., a "Simulation" or "Backtest" engine) that is not named or scoped in any existing HLD/RFC, do not silently treat it as pre-approved architecture. Flag this explicitly in "Open Assumptions": state that the LLD is *proposing* a new bounded context rather than implementing one already ratified upstream, and separately call out any non-default consistency, availability, or isolation requirement it carries (e.g., an independent strong-consistency requirement) as a decision this LLD is making on its own — one that will need architecture/HLD sign-off, not just LLD-level approval.

## Step 1: Requirements & Scope

Write this section first, always derived from Step 0's extraction, never invented from scratch when a PRD/HLD exists:

- **Functional Requirements**: Core features, strictly scoped to what this LLD covers (a single service/feature, not the whole system, unless asked).
- **Non-Functional Requirements**: Scalability, concurrency, expected latencies, extensibility points, maintainability targets. Pull real numbers from the PRD/HLD where given; otherwise state reasonable assumptions explicitly (e.g., "Assuming ~500 RPS peak per the HLD's stated container sizing").
- **Out of Scope**: Explicitly state what is excluded, to keep the LLD sharp. This is not optional — every LLD must say what it deliberately does NOT cover.
- **Open Assumptions**: A short bullet list of anything inferred rather than confirmed by the PRD/HLD.

## Step 2: Core Entities & Data Modeling

- List key domain models and their single responsibility each (one line per entity — what it *is*, not what it does).
- **Database Schema**: Provide a real SQL (or NoSQL document shape) schema:
  - Field names, precise data types, primary keys, foreign keys, indexes (and why each index exists — what query it serves)
  - Note constraints (unique, not null, check constraints) and any denormalization decisions with a one-line justification
  - If the HLD specifies a particular datastore, use that datastore's idioms (e.g., don't propose a relational schema if the HLD says DynamoDB — propose a partition-key/sort-key design instead)

## Step 3: Class Diagram & Object-Oriented Design

- Produce a clean **Mermaid.js class diagram** (` ```mermaid classDiagram ` block) covering the core classes for this feature — not the whole codebase.
- Show relationships explicitly: composition (`*--`), aggregation (`o--`), inheritance (`<|--`), and interface realization (`..|>`).
- For each significant class, detail fields (with `+`/`-`/`#` visibility) and methods with real parameter/return types — no `foo()`, no `doStuff()`.
- Explicitly name every **Design Pattern** used (Strategy, Factory, Observer, Singleton, Decorator, Repository, State, etc.) and justify *why* — tie each one to a concrete extensibility or decoupling need surfaced by the requirements (e.g., "Strategy for pricing rules because the PRD states new pricing tiers will be added quarterly").
- Avoid monolithic "Manager"/"Helper"/"Util" classes — decompose by responsibility.

## Step 4: API Contract & Edge Layer Design

Every LLD must define how the outside world (or an upstream service) actually talks to this system — a class diagram alone is not a contract.

- **Endpoints**: List every endpoint this feature/service exposes (REST routes with verb + path, or RPC method names if the HLD specifies gRPC/similar) — one line each stating purpose, not just a path list.
- **Request/Response DTOs**: For each endpoint, define the request and response shape as real typed structures (fields, types, required/optional) — matching the language chosen in Step 6, not generic JSON blobs.
- **Validation**: State what's validated at the edge (input shape, business-rule validation) vs. deeper in the domain layer, so validation logic isn't duplicated or skipped.
- **Auth & Authz enforcement**: State explicitly, per endpoint or per endpoint group, what authentication is required and what authorization check gates access (role, ownership, scope) — "auth handled elsewhere" is not acceptable; name the mechanism (e.g., JWT middleware validating a claim, an ownership check comparing the authenticated user to the resource's owner field).
- **Error responses**: Map the domain's error/exception cases (detailed fully in the Concurrency & Edge Cases section) to the status codes/error payloads returned at this layer, so every thrown domain exception has a defined edge-facing representation.
- If the HLD already fixes the protocol/style (REST/gRPC/GraphQL, versioning scheme), this section must be consistent with it; if the HLD is silent, state the assumption and pick a default matching the rest of the design.

## Step 5: SOLID Principles Breakdown

For this specific design (not generic textbook definitions), explain in 1-3 sentences each how:
- **SRP** — which class boundaries exist because of it, and what would break the principle if merged
- **OCP** — which extension point (interface/strategy) lets new variants be added without modifying existing code
- **LSP** — which subtype relationships are safe substitutions, and how
- **ISP** — which interfaces were split to avoid forcing unused methods on implementers
- **DIP** — which high-level modules depend on abstractions instead of concrete classes, and where that's wired up (constructor injection, factory, DI container)

## Step 6: Interface & Contract Definitions

- Provide interface-driven skeleton code in the language the user specifies, or Java by default if unspecified (ask only if truly ambiguous and it would materially change the deliverable — otherwise pick Java and state the assumption).
- Use strict typing, abstract classes/interfaces, and correct access modifiers.
- Real method signatures with realistic parameter and return types matching Step 3's diagram — no `// TODO`, no `...`, no placeholder bodies where logic is the point. Method bodies can be a few lines of real logic outline (validation calls, delegation to collaborators, actual control flow) rather than empty stubs.
- Keep classes modular. No class should own more than one clear responsibility.
- **Pseudocode for core orchestration/state-changing methods.** Identify the entry-point methods that drive the feature's main flow (orchestrator/engine "run"/"evaluate"/"execute" methods, and any method that resets, cancels, or re-triggers state — e.g., an account reset, an order cancellation, a resting-order re-trigger). For each of these specifically, a thin one-line body is not sufficient: write step-by-step pseudocode (loop/branch structure, calls to collaborators in order, where locks/transactions from Step 8 are acquired, what triggers early return/rollback) so a reader could implement the method from it directly.
- **Method contracts for repository/data-access interfaces.** For every repository or DAO interface (e.g., `OrderRepository`, `StrategyRepository`, `PositionRepository`, `CostRuleRepository` or their equivalents in this design), document each method's contract, not just its signature: preconditions, what it returns on a not-found case (null vs. `Optional` vs. exception), which exceptions it can throw and when, and its transactional/consistency guarantee (e.g., "runs inside the caller's transaction, does not commit"; "read-committed is sufficient"; "must be called under the row lock acquired by the caller").

## Step 7: Concurrency, Thread-Safety & Edge Cases

- Identify concrete thread-safety concerns specific to this design (e.g., "two concurrent requests updating the same wallet balance row" — not generic "race conditions may occur").
- Show the actual mechanism chosen and why: optimistic locking (version column + retry), pessimistic locking (`SELECT ... FOR UPDATE`), atomic/CAS operations, distributed locks (Redis/Zookeeper), idempotency keys, or DB transactions with the correct isolation level — pick the mechanism that fits the entity's access pattern, don't default to the same one everywhere.
- Detail error handling: custom exception hierarchy relevant to this domain, and where each is thrown/caught.
- If the entity has meaningful lifecycle states, model state transitions explicitly (a **State pattern** or an explicit state-machine table: valid transitions, invalid-transition handling, and who triggers each transition).

## Step 8: Test Strategy

Every LLD must say how the design gets verified — a design without a test strategy leaves correctness to chance.

- **Unit test scenarios**: For the core classes from Step 3 (especially orchestration/engine classes and anything with a state machine from Step 7), list concrete scenarios to cover — happy path, each documented error/exception case, and boundary conditions specific to this domain (not generic "test edge cases").
- **Integration test scenarios**: Cover the flows that cross a boundary defined in Step 4 (API → domain → DB) or touch concurrency controls from Step 7 (e.g., "two concurrent cancellation requests for the same order resolve to exactly one success").
- **Mocking approach**: State what gets mocked/stubbed vs. run against a real (or in-memory/test-container) dependency for each layer — e.g., repositories mocked in unit tests, a real test database in integration tests, external services replaced with fakes — and why that boundary was chosen.
- Tie at least one test scenario back to each major concurrency mechanism named in Step 7, so the concurrency design isn't left unverified on paper.

## Output Format

Always output as a single well-structured Markdown document (or `.md` file via the docx/md file-creation flow if the user wants it downloadable — check `file-creation` conventions: standalone LLD documents the user will keep/share should become a file, not just stay inline in chat). Section order is fixed:

1. Requirements & Scope (+ Open Assumptions)
2. Core Entities & Data Modeling (+ DB Schema)
3. Class Diagram (Mermaid) & Design Patterns
4. API Contract & Edge Layer (Endpoints, DTOs, Auth)
5. SOLID Breakdown
6. Interface & Skeleton Code (incl. orchestration pseudocode & repository contracts)
7. Concurrency, Thread-Safety & Edge Cases
8. Test Strategy

## Quality Bar (Execution Rules)

- **No placeholders.** Every signature, schema field, and state transition must be realistic and specific to the system being designed.
- **Production mindset.** For every major design decision, silently sanity-check: "what if we need to add a new payment gateway / pricing strategy / notification channel tomorrow?" — and make sure the chosen pattern actually accommodates that without a rewrite.
- **Consistency with upstream docs.** Every choice must trace back to something in the PRD/HLD or be flagged as an explicit assumption. Never contradict a decision the HLD already made without calling it out.
- **Depth over breadth.** If the feature is large, it's better to fully design the core flow (e.g., order placement) with real rigor than to shallowly cover ten flows. Ask the user to prioritize if scope is too large for one pass.
- **No skipped sections.** All 8 sections in Output Format are mandatory, including the API contract and test strategy — a thin one-line placeholder for either (e.g., "standard REST CRUD" or "unit tests as appropriate") does not satisfy the requirement; both need the same specificity as the rest of the document.

## Limitations

- This skill produces a design document, not working, tested code — treat all skeleton code as a contract to implement against, not a finished implementation.
- Does not replace security review, capacity planning, or a formal architecture review board sign-off for high-stakes systems.
- If the PRD/HLD is missing, ambiguous, or internally inconsistent on a point critical to the LLD, stop and flag it rather than guessing silently.
