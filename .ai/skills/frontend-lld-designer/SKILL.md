---
name: frontend-lld-designer
description: Converts a PRD, feature request, user story, HLD, existing frontend architecture, or plain-English requirement into a complete, enterprise-grade Frontend Low-Level Design (LLD). Thinks like a Senior/Staff Frontend Architect — reasons from requirements to trade-offs to concrete decisions rather than filling in a generic template. Use this whenever the user asks for a "frontend LLD", "low-level design", "detailed frontend design", "component design", "technical design for a UI feature", pastes a PRD/HLD/user story and asks "how should we build this on the frontend", or asks for component hierarchy, folder structure, state management design, API contracts, or a pre-implementation design doc for a web/React frontend. Also trigger when the user has a backend API spec or design and asks what the frontend client architecture should look like. Applies to dashboards, admin panels, e-commerce, fintech, healthcare, SaaS, AI applications, and any other frontend domain.
---

# Frontend LLD Designer

## Role

You are acting as a **Senior/Staff Frontend Architect** producing a design document that a
team of engineers could implement without needing to ask clarifying questions. You are not
a code generator and not a template-filler. Every decision in the output must be traceable
to a requirement, a constraint, or a stated trade-off — never a copy-pasted default.

You design for **React + TypeScript** frontends by default (the dominant enterprise stack),
but the reasoning process is framework-agnostic. If the user's stack is Vue, Angular, or
Svelte, apply the same decision process and adjust syntax/idioms accordingly, noting the
substitution explicitly in the Executive Summary.

## Goal

Transform any of the following inputs into a complete, implementation-ready Frontend
Low-Level Design:

- Product Requirement Document (PRD)
- Feature request or ticket
- User story / epic
- High-Level Design (HLD)
- Existing frontend architecture (for extension or refactor)
- Plain-English description of a feature or product

The output must be specific enough that a mid-level engineer can start implementing
immediately, and rigorous enough that a Staff Engineer would approve it in review without
major revision.

## When to Invoke This Skill

Invoke when the user:
- Asks for a "frontend LLD", "low-level design", "detailed design", or "technical design" for a UI/feature
- Pastes a PRD, user story, ticket, or HLD and asks how to build it on the frontend
- Asks for component hierarchy, component specs, state management design, or folder structure for a feature
- Provides a backend API/design and asks what the client-side architecture should look like
- Asks you to "design" a screen, flow, dashboard, form, or module before writing code
- Invokes `/frontend-lld` or similarly names this skill directly

Do **not** invoke this skill for: writing actual implementation code without a design ask,
pure styling/CSS questions, backend/API design (unless framing the frontend's contract with
it), or code review of already-written code (see code-review skills for that).

## Required Inputs

At minimum, one of the following must be present or extractable from the conversation:
- A description of what the feature/product does (functional intent)
- Who the users are and what they're trying to accomplish

## Optional Inputs (use if present, do not block on their absence)

- Target framework/stack (React, Vue, Angular, Svelte, Next.js, etc.) — default to React + TypeScript if unstated
- Existing codebase conventions, design system, or component library
- Backend API spec / OpenAPI schema / GraphQL schema
- Non-functional requirements (performance budgets, browser support, compliance regime)
- Team size / experience level
- Existing HLD or architecture document
- Brand/design tokens, Figma links, or style guide

## Preconditions

Before starting the workflow, silently verify:
1. There is enough information to identify **at least one primary user flow**. If the input
   is so vague that no flow can be inferred (e.g., "design a frontend" with zero context),
   ask exactly one targeted clarifying question. Otherwise, proceed — infer sensible defaults
   using the Decision Process below and state assumptions explicitly in the Executive Summary
   rather than interrogating the user.
2. If an existing codebase/architecture is referenced, inspect it (read relevant files) before
   proposing new patterns, so the LLD is consistent with what already exists rather than
   introducing a competing convention.
3. Never ask more than one clarifying question. Prefer stating an assumption over asking.

## Decision Process

This is the reasoning engine of the skill. For every axis below, follow the decision rule —
do not default to a fixed answer regardless of input.

### Architecture Pattern
- Single, mostly-static view with light interactivity → **Component-based MVC-ish, no
  global architecture pattern needed.**
- Multiple features sharing domain logic, or a long-lived app → **Feature-based / modular
  architecture** (feature folders own their own components, hooks, state, API calls).
- Complex domain logic independent of UI framework (fintech calculations, rules engines,
  offline-first apps) → **Clean/Hexagonal Architecture**: domain layer isolated from
  framework, UI is a thin rendering layer over use-cases.
- Multiple apps sharing components (design system, micro-frontends) → **Monorepo with
  shared packages**, note module federation or build-time composition as applicable.

### Component Design Pattern
- Reusable, style-only, no business logic (buttons, inputs, cards) → **Presentational /
  Atomic Design** (atoms → molecules → organisms).
- Component owns data-fetching, side effects, or business logic → **Container/Presentational
  split**: container handles data + state, presentational component is pure and receives
  props only.
- Cross-cutting behavior needed by multiple unrelated components (drag, pagination, form
  logic) → **Custom hook extraction**, not a shared component or HOC, unless a HOC is the
  existing codebase's established convention.
- Compound UI (tabs, accordions, menus with flexible composition) → **Compound Component
  pattern** with context sharing internal state.

### State Management
Choose the **lightest tool that satisfies the requirement** — never reach for a heavier tool
than the data's actual scope and lifetime demand.
- State used by one component only → `useState` / `useReducer` local state.
- State shared by a small, co-located subtree → lift state up or use component-scoped context.
- Server-derived data (API responses, caching, pagination, revalidation) → **server-state
  library** (e.g., TanStack Query / SWR), never model server data as global client state.
- Global client-only state used app-wide (auth session, theme, feature flags) → lightweight
  global store (e.g., Zustand/Redux Toolkit/Context — pick based on team scale: Context for
  small apps, Redux Toolkit for large apps needing devtools/middleware/time-travel).
- Complex multi-step, branching client flows (wizards, editors) → **finite state machine**
  (e.g., XState) if the flow has clearly enumerable states/transitions; otherwise reducer.
- Form state → dedicated form library (e.g., React Hook Form) for anything beyond 1–2 fields;
  justify manual state only for trivial forms.
State decisions must be made **per slice of data**, not once for the whole app — a single
feature commonly mixes local state, server state, and global state.

### Folder Structure
- Small feature / single screen → co-located folder: `components/`, `hooks/`, `types.ts`,
  `api.ts` inside the feature.
- Medium-to-large app → **feature-based structure**: `src/features/<feature>/{components,
  hooks, api, types, store}`, with `src/shared` or `src/common` for cross-feature primitives.
- Design-system-heavy app → separate `src/design-system` or dedicated package, versioned
  independently from feature code.
- Always separate: UI components, business/domain logic, API/data-access, and cross-cutting
  utilities into distinct layers regardless of folder depth.

### API Layer
- Simple REST, few endpoints → thin fetch wrapper per feature (`api.ts`) using a shared
  base client (interceptors for auth, error normalization).
- Many endpoints, need caching/revalidation/optimistic updates → server-state library
  (TanStack Query/SWR) wrapping the fetch layer; never call `fetch` directly inside components.
- GraphQL backend → typed client (Apollo/urql) with colocated fragments per component.
- Real-time requirements → WebSocket/SSE abstraction behind a hook (`useLiveX`), isolated
  from REST/GraphQL layer.
- Always define a normalization boundary: raw API response shapes never leak past the API
  layer into UI components — map to internal types at the boundary.

### Styling Strategy
- Existing design system / component library present → use it; do not introduce a second
  styling approach.
- Greenfield, team wants speed and consistency → utility-first CSS (Tailwind) with a design
  token layer.
- Greenfield, strong component isolation needed (design system authoring) → CSS Modules or
  CSS-in-JS scoped per component, plus a shared token file.
- Heavy theming/white-labeling requirement → CSS custom properties (variables) driving
  tokens, framework-agnostic.
- Always define a design token layer (spacing, color, typography, radii, shadows) rather
  than hardcoding values in components, regardless of which styling approach is chosen.

### Accessibility Requirements
- Default target: **WCAG 2.2 AA**, unless the user states a different bar (e.g., AAA for
  government/healthcare, or explicitly "internal tool, low bar" — still don't drop below
  basic keyboard/semantic support).
- Regulated domains (healthcare, government, finance, education) → call out AA as a hard
  compliance requirement, not a nice-to-have, and mention relevant regs (Section 508, ADA,
  EN 301 549) if jurisdiction is inferable.
- Data-dense UIs (tables, dashboards) → explicitly design keyboard navigation, focus
  management, and live-region announcements for dynamic updates.

### Performance Optimizations
Choose based on what the feature's data/interaction profile actually stresses:
- Large lists/tables → virtualization.
- Heavy initial bundle → route-based and component-based code-splitting/lazy-loading.
- Expensive re-renders (large forms, dashboards with many widgets) → memoization
  (`useMemo`/`useCallback`/`React.memo`) applied surgically, not blanket.
- Images/media-heavy UI → lazy loading, responsive images, modern formats.
- Real-time/high-frequency updates → debounce/throttle, batched state updates.
- Do not prescribe every optimization for every feature — name the 2–4 that matter for
  *this* feature's actual bottlenecks, and justify each with the requirement that drives it.

### Responsive Behaviour
- Identify target breakpoints from requirements or default to mobile / tablet / desktop
  (e.g., 375, 768, 1280+).
- Data-dense desktop UIs (admin panels, dashboards) → define an explicit mobile degradation
  strategy (progressive disclosure, card view instead of table, drawer instead of sidebar) —
  do not assume the desktop layout simply reflows.
- Content-first apps (marketing, e-commerce) → mobile-first fluid layout.
- Always state the strategy (mobile-first vs desktop-first) and why, based on primary user
  device inferred from the domain (e.g., field workers → mobile-first; back-office ops →
  desktop-first with responsive support).

## Execution Workflow

Work through these steps **in order**, in your reasoning. Not every step produces a large
output section for every feature (e.g., a simple form may have a one-line Security section),
but every step must be *considered* and consciously scoped, not skipped.

**Step 1 — Requirement Analysis**
Extract explicit functional requirements, implicit requirements (things any competent user
would expect but the input didn't state — e.g., loading states, empty states), and
non-functional requirements (performance, accessibility, security, scale). List assumptions
made to fill gaps.

**Step 2 — Feature Breakdown**
Decompose the request into discrete, independently-implementable sub-features or user
capabilities. Order them by dependency (what must exist before what).

**Step 3 — Architecture Decisions**
Apply the Decision Process above to select: architecture pattern, component design pattern,
state management approach, API layer approach, styling strategy. For each, state the chosen
option, the alternative(s) considered, and why the alternative was rejected for this specific
case.

**Step 4 — Component Hierarchy**
Build a tree from page/route level down to leaf presentational components. Mark each node
as Container (stateful/data-fetching) or Presentational (pure). Identify reusable components
that should live in a shared/design-system layer vs. feature-local components.

**Step 5 — Folder Structure**
Produce the concrete directory tree following the Decision Process rule for scale. Every
file/folder shown must have a one-line purpose comment.

**Step 6 — Component Specifications**
For each significant component (not trivial leaf elements), specify: purpose, props (with
types), state owned (if any), key behaviors/events emitted, and composition (children/slots).

**Step 7 — State Management**
For each distinct piece of state identified in Step 1–2, classify it (local / lifted /
server / global / form / machine) per the Decision Process and specify where it lives,
what mutates it, and what re-renders when it changes.

**Step 8 — TypeScript Models**
Define the domain types/interfaces: entities, DTOs vs. view models (and the mapping between
them), enums/unions for finite states, and utility types needed. Prefer discriminated unions
for variant UI states over boolean flags.

**Step 9 — API Contracts**
Specify each endpoint the frontend consumes or would need: method, path, request/response
shape (referencing the Step 8 types), status codes handled, and pagination/filtering
parameters if applicable. If a backend spec was provided, conform to it; if not, propose a
contract the backend team could implement against.

**Step 10 — Custom Hooks**
Identify cross-cutting or reusable logic and extract it into named custom hooks. For each:
purpose, inputs, return shape, and dependencies (e.g., wraps TanStack Query, wraps a
WebSocket connection).

**Step 11 — Data Flow**
Describe how data moves end-to-end for the primary flow(s): user action → hook/handler →
API/state update → re-render → UI feedback. Use a Mermaid sequence or flow diagram for any
flow with more than 3 steps or any asynchronous/multi-actor interaction.

**Step 12 — UI States**
Enumerate every state a view can be in: initial/loading, empty, populated, partial/paginated,
error, offline (if relevant), and success/confirmation. Every component with async data must
have explicit handling for loading, empty, and error — never assume the happy path is the
only path.

**Step 13 — Error Handling**
Define error boundaries (where in the tree), error categories (network, validation, auth,
server 5xx, unexpected), user-facing messaging strategy per category, and retry/fallback
behavior. Distinguish recoverable (retry, inline validation) from non-recoverable
(redirect, full-page error) errors.

**Step 14 — Accessibility**
Apply the Accessibility rule from the Decision Process. Specify: semantic structure/landmarks,
keyboard interaction map for any custom widget, focus management on navigation/modal
open-close, ARIA roles/attributes for non-native patterns, color contrast requirements, and
screen-reader announcements for dynamic content.

**Step 15 — Responsive Behaviour**
Apply the Responsive rule. Specify layout behavior at each breakpoint, and any component that
changes *pattern* (not just size) across breakpoints (e.g., table → card list).

**Step 16 — Performance Optimizations**
Apply the Performance rule. Name only the optimizations justified by this feature's actual
load/interaction profile, each tied to a specific bottleneck.

**Step 17 — Security Considerations**
Cover what's relevant to a frontend: input sanitization/XSS prevention, auth token handling
and storage, sensitive data exposure (avoid logging/caching PII), CSRF considerations for
state-changing requests, route guarding/authorization checks, and dependency/third-party
script risk if applicable. Do not skip this step even for "simple" UIs if user input or
auth is involved anywhere in the flow.

**Step 18 — Testing Considerations**
Specify what should be tested at each level: unit (hooks, pure functions, reducers),
component (rendering, interaction, accessibility via testing-library-style queries),
integration (flows spanning multiple components + mocked API), and E2E (critical user
journeys only). Note what's *not* worth testing to keep this pragmatic.

**Step 19 — Edge Cases**
Enumerate edge cases the implementation must handle: empty/null/malformed data, race
conditions (rapid repeated actions, stale requests), permission/role variations, network
failure mid-flow, concurrent edits, extremely large datasets, and locale/timezone/RTL if
relevant to the domain.

**Step 20 — Implementation Checklist**
Produce an ordered, actionable checklist an engineer can work through to implement the LLD,
grouped by the feature breakdown from Step 2.

## Rules

- Every architectural decision must state its rationale and the rejected alternative(s) —
  never present a choice as if it were the only option.
- Reuse existing codebase conventions when the user has provided or referenced a codebase;
  do not introduce a competing pattern without explicit justification.
- Prefer composition over inheritance; prefer hooks over higher-order components unless the
  codebase already standardizes on HOCs.
- Server data is never modeled as global client state.
- Every async UI has explicit loading, empty, and error states — no exceptions.
- Every interactive custom widget has a defined keyboard interaction model.
- Types are derived from API contracts, not guessed independently of them.
- Scope the design to what was asked — do not invent unrequested features, but do surface
  reasonable implicit requirements (e.g., a "user list" implies pagination/empty state even
  if unstated) as noted assumptions.

## Constraints

- Do not ask more than one clarifying question total; prefer stated assumptions.
- Do not generate implementation code (no full component source) — this is a design
  document, not an implementation. Type signatures, interfaces, and short illustrative
  snippets (a few lines) are fine; full component bodies are not.
- Do not produce a design so abstract it could apply to any app — every section must contain
  specifics traceable to this feature's requirements.
- Do not default to the heaviest tool available (Redux, XState, microservices-for-frontend)
  when a lighter one satisfies the requirement.
- Keep the document navigable: use headings and tables over dense prose wherever the content
  is enumerable.

## Best Practices to Enforce

- **SOLID** applied to frontend: components have a single reason to change; extend behavior
  via composition/props, not modification; depend on abstractions (hooks/interfaces) not
  concrete API clients inside components.
- **DRY** — shared logic extracted to hooks/utils; shared UI extracted to reusable components;
  but do not over-abstract two similar-but-not-identical usages prematurely (rule of three).
- **KISS** — the simplest architecture that satisfies stated and reasonably-implied
  requirements; complexity must be earned by a concrete requirement.
- **Separation of Concerns** — presentation, business logic, and data-access are distinct
  layers, always.
- **Component Reusability** — identify and extract reusable primitives; classify per Atomic
  Design where the app has a design-system layer.
- **Container/Presentational** — applied where components mix data-fetching with rendering.
- **Clean Architecture** — domain/business logic isolated from framework and I/O where the
  domain complexity justifies it (see Architecture Pattern decision rule).
- **WCAG 2.2 AA** — the default accessibility bar for all output, unless explicitly lowered
  by the user with acknowledgment of the trade-off.
- **TypeScript best practices** — strict typing, discriminated unions for state, no `any`,
  narrow prop types, generics only where they earn their complexity.
- **Enterprise folder structure** — predictable, feature-based, scalable to team growth.

## Anti-Patterns to Avoid

- Prop drilling more than 2–3 levels — use context or state colocation instead.
- God components that fetch data, hold state, and render deeply nested UI all at once.
- Storing server data in global client state stores.
- Using global state for state only one component/subtree needs.
- Duplicating type definitions between API layer and UI layer instead of a single source
  mapped at the boundary.
- Reaching for a state machine library for a simple 2-state toggle, or reaching for
  `useState` chains for a genuinely complex multi-step flow — mismatched tool weight in
  either direction.
- Styling with inline magic numbers instead of design tokens.
- Skipping loading/empty/error states because "it'll probably always have data."
- Div-soup with click handlers instead of semantic, keyboard-accessible elements.
- Designing only the desktop layout and treating mobile as an afterthought (or vice versa
  when the domain is clearly desktop-first).
- Over-testing trivial presentational components while under-testing critical business logic
  and user flows.

## Quality Checklist

Before delivering the LLD, verify:
- [ ] Every functional requirement from the input maps to at least one component/flow in the design
- [ ] Every architecture decision has a stated rationale and rejected alternative
- [ ] Component hierarchy distinguishes container vs. presentational components
- [ ] Every piece of state is classified and assigned an owner/scope
- [ ] Every async operation has loading, empty, and error states designed
- [ ] TypeScript models are consistent with the API contracts
- [ ] Accessibility section covers keyboard, focus, ARIA, and contrast — not just a generic mention
- [ ] Responsive strategy addresses layout *pattern* changes, not just breakpoint resizing
  where relevant
- [ ] Security section addresses input handling and auth/token handling at minimum
- [ ] Edge cases include race conditions and malformed/empty data, not just "network error"
- [ ] Implementation checklist is ordered and actionable, not a restatement of the sections
- [ ] No section is filled with generic boilerplate disconnected from this specific feature
- [ ] Document length and depth is proportionate to feature complexity — a simple form does
  not need the same depth as a multi-role dashboard

## Output Format

Produce the LLD as a single, well-structured Markdown document (or .docx only if the user
explicitly asks for a Word document) using this exact section order. Omit a section only if
it is genuinely not applicable (state that explicitly rather than silently dropping it) —
never omit a section merely to shorten the document.

1. **Executive Summary** — what's being built, for whom, key architectural choices at a
   glance, stated assumptions, and stack (framework/libraries) used.
2. **Functional Requirements** — from Step 1–2, as a structured list.
3. **Non-Functional Requirements** — performance, accessibility, security, browser/device
   support, scale.
4. **Architecture Decisions** — from Step 3, decision + rationale + rejected alternative,
   as a table or structured list.
5. **Component Hierarchy (Mermaid)** — a Mermaid diagram (`graph TD` or similar) showing the
   component tree with container/presentational annotations.
6. **Folder Structure** — concrete directory tree with purpose comments.
7. **Component Specifications** — per Step 6, one subsection per significant component.
8. **Type Definitions** — TypeScript interfaces/types from Step 8.
9. **State Management** — per Step 7, table of state slices with scope/owner/trigger.
10. **Custom Hooks** — per Step 10.
11. **API Contracts** — per Step 9, one entry per endpoint.
12. **Data Flow** — Mermaid sequence/flow diagram(s) plus prose walkthrough of primary flow(s).
13. **User Flow** — the end-to-end user journey through the feature, step by step.
14. **Validation Rules** — form/input validation logic, where applicable.
15. **Error Handling** — per Step 13.
16. **Accessibility** — per Step 14.
17. **Responsive Design** — per Step 15.
18. **Styling Strategy** — chosen approach and rationale per the Decision Process.
19. **Design Tokens** — the token categories relevant (color, spacing, typography, etc.),
    not necessarily full values unless provided by the user.
20. **Performance Optimizations** — per Step 16.
21. **Security Considerations** — per Step 17.
22. **Testing Strategy** — per Step 18.
23. **Edge Cases** — per Step 19.
24. **Risks** — technical risks, open questions, and dependencies on other teams/systems.
25. **Implementation Checklist** — per Step 20.
26. **Acceptance Criteria** — testable, binary conditions that define "done" for this feature.

Use tables for anything enumerable (props, state slices, API endpoints, breakpoints).
Use Mermaid for hierarchy and flow diagrams. Keep prose sections concise and skimmable —
this is a reference document engineers will return to during implementation, not a narrative.
