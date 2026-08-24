---
name: frontend-lld-review
description: Review frontend Low-Level Design (LLD) documents, component architecture proposals, and system designs for UI features (e.g. autocomplete, infinite scroll, notification center, form builder, data table, chat widget). Use this whenever the user shares a frontend LLD, asks for a design/architecture review of a UI feature, wants feedback on component breakdown, state management design, or API/data-layer design for a frontend system. Also trigger for requests like "review my component design", "critique this frontend architecture", or "is this a good design for X UI feature". Push to use this even if the user just pastes a design doc, diagram description, or component tree without explicitly saying "review."
---

# Frontend LLD Review

A framework for rigorously reviewing frontend Low-Level Design (LLD) — the design of a single UI feature or app module, as opposed to High-Level Design (HLD), which covers system-wide architecture (CDN, backend services, infra). Frontend LLD review is a well-known step in real design-doc review at product companies. This skill gives Claude a consistent, expert lens to catch bugs and architectural flaws before implementation begins.

## What counts as frontend LLD

Typical subjects: autocomplete/search-as-you-type, infinite scroll / virtualized lists, notification center, file uploader, form builder / dynamic forms, data table with sort/filter/pagination, chat/messaging widget, comment thread, drag-and-drop board (kanban), image carousel, video player, multi-step wizard, real-time collaborative editor, polling/voting widget, e-commerce cart/checkout, dashboard with widgets.

A complete frontend LLD generally covers: component architecture, state management, data layer (API contracts, caching, real-time), rendering/performance strategy, edge cases, client-side security, testability, observability, and responsive/device constraints. Most docs are incomplete in at least one dimension — the review's job is to find which one(s).

## Applicability Rule

Frontend LLD reviews are contextual.

Not every review dimension applies to every feature.

Reviewers should only evaluate dimensions that are relevant to the feature being reviewed and explicitly mark non-applicable dimensions as out of scope.

Examples:

- A static settings page should not be criticized for lacking virtualization.
- A marketing page should not be criticized for lacking websocket recovery.
- A simple CRUD form should not be criticized for lacking offline synchronization unless offline requirements exist.

The goal is to find meaningful gaps, not manufacture checklist findings.

## How to run a review

1. **Understand what's being reviewed.** Is this a finished design doc, a partial sketch, or just a feature name with no design yet? If there's no design yet and the user wants one, produce one using the framework below rather than "reviewing" nothing — then invite critique.
2. **Identify the feature's defining constraints** before judging anything. Every UI feature has 1-3 constraints that should shape the whole design (e.g. autocomplete → latency + race conditions; infinite scroll → memory + scroll position restoration; chat → real-time ordering + optimistic updates; form builder → schema-driven extensibility). Name these explicitly; a design that nails everything else but misses the defining constraint should be flagged as the top issue.
3. **Walk the nine review dimensions** (below), noting strengths and gaps in each. Don't force every dimension into every review — a component-only sketch doesn't need a data-layer critique, but should be told what's missing.
4. **Prioritize findings.** Not all gaps are equal. Rank feedback as: 🔴 Critical (breaks correctness, causes bugs/vulnerabilities in production) / 🟡 Should address / 🟢 Nice-to-have / polish. Lead with 🔴 items.
5. **Give the fix, not just the flaw.** Every criticism pairs with a concrete alternative — a snippet of a better interface, a corrected data flow, or a named pattern to apply. "This will cause X" is half a review; "...use Y instead, here's the shape" is the whole thing.
6. **Close with what's genuinely good.** Reviews that are 100% critique read as adversarial and are less useful — call out solid decisions specifically (not generic praise) so the person knows what to keep.

## The nine review dimensions

### 1. Component architecture
- **Decomposition**: Is the component tree broken along natural seams (data ownership, reuse boundaries, independent re-render needs) rather than arbitrary visual grouping? A component should generally have one reason to change.
- **Container/presentational split**: Are data-fetching/stateful concerns separated from pure rendering? This isn't mandatory in every modern codebase (hooks blur the line) but the *separation of concerns* it implies should still exist somewhere.
- **Prop API design**: Are props minimal, composable, and free of "boolean soup" (many independent booleans that produce invalid combinations)? Prefer discriminated unions/variants over `isX`, `isY`, `isZ` flags. Watch for prop drilling more than 2-3 levels deep — that's a signal state should move up, into context, or into a store.
- **Composition vs configuration**: For flexible UI (e.g. a table, a form builder), does the design lean on composition (children, render props, slots) where extensibility is needed, vs. a giant config-object API that will need new fields forever?
- **Reusability boundary**: Is there a clear line between the generic/reusable primitive and the feature-specific wrapper? Mixing business logic into a primitive component (e.g. a `Table` that knows about "users") kills reuse.
- **Rendering strategy (SSR/CSR/RSC)**: For frameworks/prompts where it's relevant (Next.js, Remix, any "must be fast on first load" or SEO-sensitive prompt), does the design state where each piece renders — server vs. client — and why? Look for: awareness of **hydration mismatches** (content that differs between server-rendered HTML and client's first render, e.g. from `Date.now()`, `window`, or locale-dependent formatting) and how the design avoids them; a clear **client/server component boundary** in RSC-style architectures (what needs interactivity vs. what's static/data-only); and whether interactive-but-non-critical pieces are deferred (streaming/suspense boundaries, progressive hydration) rather than blocking the whole page on one slow piece.
- **Design tokens & theming**: Does the design consume shared design tokens (colors, spacing, typography) rather than hard-coding values, and does it say how dynamic theming (light/dark, brand/white-label, user-customizable themes) is implemented — CSS custom properties, a theme-provider/context, or per-component style props? For a design-system-adjacent prompt, ad hoc hard-coded values instead of tokens is a 🟡 gap.
- **Feature flags & experimentation**: If the feature plausibly ships behind a flag or A/B test, does the design show flags being read at a clean boundary (e.g. one hook/config read per feature area) rather than sprinkled `if (flag)` checks through deep children (which causes prop drilling of flag values)? Does variant rendering avoid **layout shift** between variants (e.g. reserving space, avoiding a flash of the control variant before the flag resolves)?

### 2. State management
- **Colocation**: Is state kept as close as possible to where it's used, lifted only as far as necessary? Flag state hoisted to global/app-level that's only consumed by one subtree.
- **Local vs. global vs. server state**: Are these three kept distinct? Server-cache data (from an API) shouldn't be duplicated into ad hoc global state that can drift out of sync — that's a common critical gap in candidate designs; call it out as 🔴 when found.
- **Derived state**: Is anything stored that could instead be computed on render from existing state (e.g. filtered/sorted lists, counts, "isValid")? Stored derived state is a sync-bug generator.
- **Normalization**: For collections (lists of items, especially with relationships — e.g. comments with replies, a normalized entity table), is data normalized (by-id map + id arrays) rather than deeply nested, so updates to one item don't require deep cloning?
- **State machine clarity**: For anything with distinct modes (loading/success/error/empty; idle/uploading/paused/failed), is there an explicit finite set of states, or an implicit sprawl of independent booleans that can combine into impossible states? Prefer a single `status` enum/discriminated union.
- **Multi-tab/window consistency**: For state a user could plausibly have open in two tabs at once (auth session, cart, a doc, notification read-state), does the design address cross-tab sync — e.g. `BroadcastChannel`, a shared worker, or storage events — or at least explicitly scope that out? Silent divergence between tabs (e.g. one tab shows "logged in," another still shows "logged out" after logout) is a common missed 🟡-🔴 depending on how stateful the feature is.
- **Validation architecture** (for forms/form builders): Is validation timing specified (on-blur vs. on-change vs. on-submit)? For async validation (uniqueness checks, server-side rules), is it debounced and does it handle out-of-order responses the same way search does? Are **cross-field dependencies** (password confirmation, date-range ordering, conditional required fields) modeled explicitly rather than left as ad hoc handler logic? For schema-driven form builders, is schema parsing/validation overhead considered (parse once vs. per-keystroke)?

### 3. Data layer & API design
- **Contract shape**: Are request/response shapes specified concretely (even briefly), not hand-waved? For paginated/infinite data: cursor vs. offset, and why. For search: debounce strategy and what triggers a request.
- **Race conditions**: For any feature with fast successive requests (search-as-you-type, tab switching, filters), does the design handle out-of-order responses (e.g. via request ID/token, `AbortController`, or "ignore stale response")? This is the single most commonly missed critical issue in autocomplete/search designs — always check for it explicitly.
- **Caching & staleness**: Is there a caching layer (even a simple in-memory map) for repeated queries, and a stated invalidation strategy? Distinguish cache-first vs. network-first vs. stale-while-revalidate where it matters.
- **Real-time/streaming**: For chat, notifications, live collaboration: WebSocket vs. polling vs. SSE, and does the design account for reconnection, message ordering, and de-duplication (especially with optimistic updates)?
- **Optimistic updates**: If used, is there a rollback path on failure, and is the reconciliation with the server's authoritative response addressed (not just "assume success")?
- **Error handling**: Are network failure, empty result, and partial failure treated as distinct, designed states — not folded into a generic catch-all?

### 4. Performance & rendering
- **Re-render scope**: Will a state update in one part of the tree cause unrelated siblings to re-render? Look for missing memoization (`memo`, `useMemo`, `useCallback`) *only where profiling would justify it* — flag over-memoization too; it's not free and shouldn't be prescribed reflexively.
- **List virtualization**: For any list that can grow large/unbounded (feeds, tables, chat history), is windowing/virtualization part of the design? If absent and the list is unbounded, this is 🔴.
- **Code splitting**: Are heavy, conditionally-shown pieces (modals, rich editors, charts) lazy-loaded rather than bundled into the initial chunk?
- **Debounce/throttle**: Are expensive triggers (search input, scroll/resize handlers, drag) rate-limited?
- **Layout thrash / jank**: For drag-and-drop, resizing, or animation-heavy features, does the design account for using transforms/GPU-friendly properties over layout-triggering ones?
- **Bundle budget & dependency weight**: For any new third-party library the design pulls in (rich text editor, charting lib, date library, animation lib), is its size acknowledged against a rough budget, and is there a lighter alternative considered? Heavy dependencies pulled into the initial/critical bundle (rather than lazy-loaded alongside the code-split feature that needs them) should be flagged, especially for a "must be fast on first load" or mobile-first prompt.

### 5. Edge cases, a11y, and resilience
- **The standard state set**: loading, empty, error, partial-error, offline, and slow-network (skeletons vs. spinners) — which of these does the design explicitly cover, and which are silently assumed away?
- **Offline-first architecture** (when the feature implies it — collaborative editors, note/doc apps, mobile-first or "works on a plane" prompts): Is offline treated as a first-class mode, not just an error state? Look for: a **Service Worker** (or equivalent) for asset/shell caching so the app loads at all without network; local persistence (**IndexedDB**, not just localStorage, for any non-trivial amount of structured/offline-editable data); a **sync queue** that captures writes made while offline and replays them on reconnect; and a stated **conflict-resolution strategy** for when local and server state have diverged (last-write-wins, operational transform/CRDT, or manual merge) — for a "design Google Docs"-style prompt, absence of a conflict-resolution answer is 🔴. If the feature is offline-agnostic (e.g. a simple settings page), don't force this bullet — note it as out of scope instead.
- **Accessibility — interaction**: Keyboard navigation (especially for custom widgets like autocomplete, carousels, drag-and-drop, comboboxes — these need full keyboard + ARIA patterns per WAI-ARIA APG), focus management on mount/unmount/modal-open, screen-reader announcements for dynamic content (`aria-live` for notifications/async results).
- **Accessibility — visual**: For anything visually dense (dashboards, data tables, charts, form validation states), does the design consider color-contrast ratios (WCAG AA/AAA text and UI-component contrast), a high-contrast/dark-mode-safe palette, and — critically — that color is never the *only* signal for meaning (e.g. an error/success state or a chart series distinguished by color alone, with no icon, label, or pattern backup)? Flag color-only error/status indicators as 🟡-🔴 depending on how central the feature is to task completion.
- **Accessible virtualized lists**: Windowing/virtualization (dimension 4) and screen-reader accessibility are in direct tension — off-screen items are unmounted, so a screen reader can't see list length or announce position the way it would for a fully-rendered list. If the design virtualizes a list, does it also address this — e.g. `aria-setsize`/`aria-posinset` on rendered items, an `aria-live` region or rowcount announcement, or a documented trade-off/fallback (render fully for assistive tech, or cap virtualization to very large lists only)? A virtualized list with no mention of this tension is a gap worth surfacing even if not always 🔴.
- **Reduced motion**: For any animation-heavy feature (page transitions, drag-and-drop, carousels, skeleton shimmer), does the design respect `prefers-reduced-motion` (disabling or substantially reducing non-essential animation for users who request it), or is motion treated as always-on?
- **Error boundaries**: Is failure in one widget/section isolated so it doesn't blank the whole page?
- **Concurrency edge cases**: rapid double-submits, back-button/navigation during an in-flight action, component unmounting mid-request (leaked state updates).
- **Internationalization**: text expansion, RTL layout, if relevant to the feature.

### 6. Security & client-side safety
- **XSS surface**: Does anything render user-generated or third-party content as HTML (`dangerouslySetInnerHTML`, `v-html`, raw `innerHTML`, markdown/rich-text rendering)? If so, is there a sanitization step (e.g. DOMPurify) or does the design rely on the framework's default escaping instead? Unsanitized HTML injection from user content is 🔴.
- **Unsafe URLs/attributes**: Are user-supplied links rendered as `href`/`src` without validating scheme (blocking `javascript:`/`data:` where inappropriate)? Relevant for comment threads, chat, file uploaders, rich text.
- **CSRF & auth boundaries**: For any state-changing request the design implies (submit, delete, pay), is there at least an acknowledgment of CSRF protection (SameSite cookies, tokens) rather than assuming it's someone else's problem? This can be brief for pure frontend LLDs but shouldn't be silently absent for auth/payment-adjacent features.
- **Sensitive data handling**: Are tokens/PII kept out of `localStorage`/`sessionStorage` and client-side logs where an httpOnly cookie or in-memory store would be safer? Flag storing auth tokens in localStorage as 🟡-🔴 depending on stakes.
- **Third-party embeds (incoming)**: iframes/widgets/ads sandboxed (`sandbox` attribute, CSP) rather than given free rein over the page?
- **Embeddable widget isolation (outgoing)**: If the feature *is* an embeddable widget meant to run on a host site (a chat widget, a support bubble, an analytics snippet), does the design address the reverse problem — protecting the widget and host from each other? Look for: CSS isolation (Shadow DOM, or at minimum a strict scoped/namespaced class prefix) so the widget's styles don't leak into the host page and the host's global styles don't leak in; JS namespace protection (avoiding global variable/prototype pollution); and running in an iframe where feasible for the strongest isolation, with a documented postMessage contract for host↔widget communication. A widget styled with plain global CSS and no isolation strategy is a 🔴 for this specific "design an embeddable widget" prompt type.

### 7. Testability
- **Logic/rendering seam**: Is business logic (validation, formatting, derived calculations, state transitions) extracted into plain functions or hooks that can be unit-tested without mounting a component tree?
- **Isolation**: Can components be rendered and tested with mock props/data alone, or do they reach into global singletons, ambient context, or hard-coded API calls that make isolated component testing hard?
- **Data-layer mocking**: Is the API/data-fetching layer abstracted behind a hook or service interface that tests can substitute, rather than `fetch`/`axios` calls inlined directly in components?
- **E2E-friendly hooks**: For interaction-heavy flows, does the design leave room for stable test selectors (test ids/roles) instead of relying on implementation details like CSS class names or DOM order?
- Calibrate depth to context: an LLD doesn't need a full test plan, but it should leave the *seams* for testing — call out when an architecture makes testing structurally hard, not just "add tests."

### 8. Observability & telemetry
- **Error tracking**: Do error boundaries / global handlers report to an error-tracking service (Sentry-style) with useful context (component, user action), rather than only `console.error` or a silent catch?
- **Performance logging**: Are key production metrics identified (e.g. Core Web Vitals, time-to-first-result for search, API latency) so regressions are visible after ship, not just observable in local devtools?
- **Product analytics**: Are meaningful user actions (search performed, item selected, upload failed) named as trackable events, kept distinct from debug/error logging?
- **Failure visibility for critical flows**: For high-stakes features (checkout, auth, payments), does the design at least gesture at what "this is broken in production" would look like from a monitoring dashboard?

### 9. Responsive design & device constraints
- **Layout across breakpoints**: Does the design account for mobile/tablet/desktop rather than being implicitly desktop-only? For data-dense UI (tables, dashboards) is there a stated mobile strategy (reflow, priority columns, card view) rather than silence?
- **Touch vs. hover**: Any hover-dependent interaction (tooltips, hover menus, drag-to-reorder) needs a touch-equivalent (tap, long-press, explicit control) — flag hover-only affordances as a gap for mobile-web contexts.
- **Safe areas & viewport quirks**: For full-bleed or fixed-position UI (bottom nav, sticky composer), does the design consider safe-area insets (notch/home-indicator) on modern mobile devices?
- **Virtual keyboard occlusion**: For text inputs low on the screen (chat composer, forms, comment boxes), does the design address the on-screen keyboard covering the input or shifting layout (scroll-into-view, resize handling)?
- **Device APIs & permissions**: If the feature touches camera, geolocation, clipboard, or push notifications, are permission-denied and unsupported-device fallback states designed, not just the happy path?

## Common Critical Findings

The following issues frequently cause production incidents and should always be checked when applicable:

🔴 Missing race-condition handling for concurrent requests

🔴 Unbounded list rendering without virtualization

🔴 Impossible state combinations caused by boolean-state explosion

🔴 Unsanitized user-generated HTML

🔴 Cross-feature coupling through shared mutable state

🔴 Missing rollback strategy for optimistic updates

🔴 Missing accessibility support for custom interactive controls

🔴 Browser APIs used without compatibility or fallback consideration

## Output format

When reviewing a design, output the review strictly in the following format. Do not use generic backend architecture terms; align the findings with the 9 Frontend LLD dimensions above.

```text
# LLD Review Report: <design name>

## 1. Verdict
[Ready for Implementation / Not Ready / Ready with Conditions]
[One-paragraph summary of why]

## 2. Requirement Traceability (Three Doors)
[Name the 1-3 defining constraints this design is judged against]
- Door 1 - Coverage: [Pass / Pass with concerns / Fail]
- Door 2 - Fidelity: [Pass / Pass with concerns / Fail]
- Door 3 - Readiness: [Pass / Pass with concerns / Fail]
[Requirement-by-requirement coverage table if a PRD or explicit constraints were supplied]

## 3. Findings by Category
[One Severity/Category/Observation/Impact/Recommendation block per finding, grouped under the applicable 9 Frontend LLD dimensions (e.g., Component Architecture, State Management, API & Data Layer, Performance, Security, etc.)]

## 4. Missing Information
[Bullet list of anything the LLD should have specified but didn't]

## 5. Risks Identified
[Bullet list, cross-referencing severities above]

## 6. Questions for the Author
[Direct questions the author needs to answer before this can be approved]

## 7. Suggested Improvements
[Concrete, actionable — not "consider improving performance" but exactly what to add/change]
