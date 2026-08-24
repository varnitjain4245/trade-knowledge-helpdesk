# Project Structure — Folder Layout Generation

This governs how a new service, app, or project on this platform gets its file/folder structure — required reading before scaffolding anything from scratch (a brand-new service, a new frontend app, a new module inside an existing monorepo). Retrofitting structure onto an existing codebase is different: per Section 2 (SKILL.md), match what's already there rather than imposing this file's layout over an established convention — this file governs **new** scaffolding decisions, not a mandate to restructure working code.

## Decide the repo topology first, explicitly

Before creating a single folder, state which of these this task actually is — don't default to one without deciding:
- **New service/app inside an existing monorepo** — the layout must match the monorepo's existing top-level convention (see below); don't invent a parallel convention next to it.
- **New standalone repo** — full freedom, but still separate backend and frontend at the top level per the pattern below, and state the choice of monorepo-vs-polyrepo explicitly if it's ambiguous which this should be (a genuinely open question worth a clarifying question — see `clarification-protocol.md`).
- **Adding a module/package to an existing service** — this isn't a topology decision at all; follow that service's existing internal layout (`go-backend.md`/`java-backend.md`/`rust-backend.md` internal-layout notes), don't create a new top-level structure for it.

## Top-level separation: backend and frontend never share a root

Regardless of monorepo or polyrepo, backend and frontend code live in clearly separated top-level directories — never interleaved, never a shared `src/` with language-based subfolders mixed at the same level as feature folders. A representative monorepo root for this platform:

```
platform-root/
├── backend/
│   ├── matching-engine/        # Rust — hot path
│   ├── order-gateway/          # Go or Rust — order intake/routing
│   ├── risk-service/           # Go or Java — adjacent to hot path
│   ├── settlement-service/     # Java — back-office, transactional
│   └── shared/                 # cross-service contracts (proto/schema defs), NOT shared mutable code
├── frontend/
│   ├── web/                    # React trading UI
│   └── mobile/                 # Flutter app
├── docs/
│   ├── architecture/           # HLD/LLD artifacts this skill consumes, per Pipeline Position (SKILL.md)
│   └── api-contracts/          # OpenAPI/Swagger specs + wire-format schemas — source of truth, see api-contract-design.md
├── infra/                      # IaC, deployment config — owned by infra team per this skill's Boundaries
├── scripts/                    # repo-level tooling (not application code)
└── .github/ (or equivalent CI config)
```

- **`backend/<service-name>/` per service**, each one a genuinely independent, independently-buildable/deployable unit with its own dependency manifest (`Cargo.toml`, `go.mod`, `pom.xml`/`build.gradle`) — don't let two services share a build file "for convenience," since that couples their release cycles.
- **`shared/` holds contracts, not code to import and mutate.** Cross-service/cross-language contracts (protobuf/FlatBuffers schemas, wire-format specs, OpenAPI definitions) belong in a shared location precisely because both sides need the *same* definition — but this is schema/interface, not a shared mutable library that creates a hidden coupling between otherwise-independent services. If genuine shared logic is needed (not just a contract), that's an explicit architectural decision to flag upstream (HLD/LLD, per Pipeline Position) rather than something to default into.
- **Never put backend and frontend code in the same package/module** even for small utilities — a `utils/` folder shared across both invites exactly the kind of hidden coupling (e.g. an accidental Node-only import creeping into what's meant to be an isomorphic type) that's hard to catch until a build breaks in production.

## Per-service internal layout, by language

Each backend service follows its language's idiomatic internal layout — don't impose one language's convention on another's service:

- **Rust** (see `rust-backend.md`): Cargo workspace for a service with multiple crates so the hot-path logic, the wire format, and the binary entrypoint can be tested/versioned independently.

```
matching-engine/
├── Cargo.toml                 # workspace manifest
├── engine-core/                # hot-path logic — lib crate, no I/O
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs
│   │   ├── order_book.rs
│   │   └── matching.rs
│   └── tests/
├── wire-protocol/               # explicit byte-format encode/decode — separately versionable
│   ├── Cargo.toml
│   └── src/lib.rs
└── engine-bin/                  # thin binary entrypoint — wires I/O to engine-core
    ├── Cargo.toml
    └── src/main.rs
```

- **Go** (see `go-backend.md`): the community-standard layout — `cmd/` as a thin entrypoint, `internal/` compiler-enforced as not importable outside this module, `pkg/` reserved only for genuinely reusable exported code.

```
order-gateway/
├── go.mod
├── cmd/
│   └── order-gateway/
│       └── main.go              # thin — wires config, starts server, no business logic
├── internal/
│   ├── router/
│   ├── validation/
│   └── riskclient/               # calls out to risk-service
├── pkg/                          # only if genuinely meant to be imported by other services
└── api/                          # this service's OpenAPI/proto defs, if not in the shared contracts folder
```

- **Java** (see `java-backend.md`): standard Maven/Gradle module layout, package-by-feature rather than package-by-layer at the top level for anything beyond a trivial service.

```
settlement-service/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/platform/settlement/
    │   │   ├── SettlementApplication.java
    │   │   ├── trades/            # feature package — controller, service, repository together
    │   │   ├── reconciliation/
    │   │   └── reporting/
    │   └── resources/
    │       └── application.yml
    └── test/
        └── java/com/platform/settlement/...   # mirrors main/, package-by-feature
```

## Frontend internal layout

- **React**: feature-based folders, each containing its own components, hooks, and feature-scoped state.

```
web/
├── package.json
├── src/
│   ├── features/
│   │   ├── order-entry/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── OrderEntryForm.tsx
│   │   │   └── OrderEntryForm.test.tsx    # test next to what it tests
│   │   └── order-book/
│   │       ├── components/
│   │       └── OrderBook.tsx
│   ├── shared/                             # deliberately small — genuinely cross-feature only
│   │   ├── components/
│   │   └── api-client/
│   └── App.tsx
```

- **Flutter**: mirror the same feature-first principle.

```
mobile/
├── pubspec.yaml
├── lib/
│   ├── features/
│   │   ├── order_entry/
│   │   │   ├── widgets/
│   │   │   ├── state/                      # Bloc/Riverpod providers scoped to this feature
│   │   │   └── order_entry_screen.dart
│   │   └── order_book/
│   │       ├── widgets/
│   │       └── order_book_screen.dart
│   ├── core/                               # theming/design tokens, networking client, routing
│   └── main.dart
└── test/
    └── features/order_entry/...             # mirrors lib/features/ structure
```

- **Tests live next to what they test** (`Component.tsx` + `Component.test.tsx` in the same folder as shown above, or a mirrored `test/` tree — match whichever convention the project has already established) rather than in one disconnected top-level test folder that loses the association between a file and its tests, which also makes the per-file testing cadence in `integration-testing.md`/`test-execution.md` easier to actually follow.

## Naming conventions across the structure

- Folder and file names in `kebab-case` for cross-language-shared areas (`docs/`, `infra/`, top-level service folder names) since this is safe across every OS/tool; inside a language's own tree, follow that language's own convention (Go: lowercase short package names; Rust: `snake_case` modules; Java: lowercase dotted packages; React: `PascalCase` component files, `camelCase` hooks/utilities; Dart: `snake_case` files, `PascalCase` classes).
- Service folder names should be the service's actual domain name (`order-gateway`, `matching-engine`) — never `service1`/`backend2`/generic placeholders, the structural equivalent of the generic-naming problem `design-system.md` calls out for code.

## When scaffolding a brand-new structure, state the plan before creating files

Treat the folder structure itself as part of the `## Plan` (SKILL.md Section 3) for any task that creates a new service or app — list the top-level directories you're about to create and why, the same way "Files touched" is required for an ordinary change. A structure decided silently while generating files is exactly the kind of undiscoverable decision Section 13 (Context Management) warns against losing track of on a longer task.

## Hard rule: create the directories before creating a single file inside them

This is a strict ordering requirement, not a preference — violating it is the same class of error as writing code before reading the codebase (Section 2, SKILL.md):

1. **Create the full top-level skeleton first**: `backend/`, `frontend/`, and the specific service/app subfolders under each (e.g. `backend/order-gateway/`, `frontend/web/`) — as empty directories (or with just the language's minimal manifest stub, e.g. an initial `Cargo.toml`/`go.mod`/`package.json`), before generating any real implementation file inside any of them.
2. **Never interleave folder creation with implementation** — don't create `backend/order-gateway/`, immediately write `main.rs` into it, and only then create `frontend/web/`. Finish the full intended skeleton (every top-level and service-level directory this task needs) before the first line of actual implementation code is written anywhere.
3. **If the full scope of services/apps needed isn't yet known** (a genuinely open architectural question), that's a `references/foundation/clarification-protocol.md` question to resolve first — don't create a partial skeleton and expand it ad hoc file-by-file as you go, since that produces exactly the "decided silently mid-generation" problem this section exists to prevent.
4. **This applies to both a from-scratch project and adding a new service/app to an existing monorepo** — for the latter, step 1 is just the new service's own subfolder(s), created before that service's first file, even though the surrounding `backend/`/`frontend/` roots already exist.
5. **State that the skeleton was created, and list it, as its own line in the `## Plan`** (e.g. "Skeleton created: `backend/risk-service/{cmd,internal,api}`, `frontend/web/features/risk-panel/`") — this makes the ordering a checkable claim, not an assumed-followed convention.

## Review checklist before calling new scaffolding "done"
- [ ] Backend and frontend are separated at the top level, never interleaved
- [ ] Each backend service has its own independent dependency manifest — no shared build file coupling unrelated services
- [ ] `shared/`, if present, contains contracts/schemas only, not shared mutable application code, unless that was an explicit, upstream-flagged architectural decision
- [ ] Each service's internal layout matches its language's idiomatic convention (Cargo workspace / `cmd`+`internal`+`pkg` / Maven-Gradle package-by-feature)
- [ ] Frontend layout is feature-based, not a global components/hooks/store split fighting the feature boundaries
- [ ] No generic/placeholder folder or service names (`service1`, `utils2`)
- [ ] The structure was stated in the Plan before files were created, not decided silently mid-generation
- [ ] The full intended directory skeleton was created before the first implementation file was written anywhere in it — not interleaved
