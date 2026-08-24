# Design Quality — Avoiding the "Obviously AI-Generated" Look

`frontend.md` covers *functional* correctness for a real-time trading UI (staleness, virtualization, no floats). This file covers *visual and structural* design quality — the difference between a UI that a trader trusts and one that reads as a generic template, regardless of whether it's technically correct. A screen can pass every checklist in `frontend.md` and still look like an unstyled scaffold shipped without a design pass — that is also a defect on this platform, not a cosmetic nice-to-have, because trader trust in the interface is part of the product.

## Why this needs its own file

Left to defaults, generated UI converges on a small set of recognizable patterns — not because they're wrong individually, but because *stacking all of them together, on every screen, with no variation* is what makes output read as templated rather than designed. The goal below isn't "never use a gradient" — it's "make deliberate choices instead of falling back to the first default that compiles."

**Figma Design Engine Integration**: Whenever a Figma URL is provided, `references/client-ui/figma-design-engine.md` is the **PRIMARY source of truth** (`Figma > written prompt`). Convert Figma tokens into reusable code variables before component building. If Figma specs are provided, follow Figma tokens, typography, and spacing strictly rather than inventing custom visual themes.

**This file covers visual/aesthetic quality specifically. For usability, flow, accessibility, and interaction quality — the "does it work well for the user" half of a good interface — see `references/client-ui/ux-design.md`, required reading alongside this file for the same reason: a visually distinctive screen that's confusing or inaccessible is not a finished result any more than a usable-but-generic one is.**

## The default-pattern trap — recognize these, don't reach for them reflexively

- **The purple/blue gradient hero, everywhere.** A gradient can be right for one accent moment; used as the background of every card, button, and header, it's a tell, not a style.
- **`shadow-lg` + `rounded-2xl` + `p-6` on every single container**, with no variation in elevation, radius, or density between a dense data table and a marketing card — a trading UI in particular has genuinely different density needs (order book rows vs. a settings panel) that a single card recipe can't serve.
- **Emoji as section icons and bullet markers** (📈 for "Performance," 🔒 for "Security") in place of an actual icon set — reads as placeholder content, not a finished product, and doesn't belong in a financial interface at all.
- **Centered-everything, generic sans-serif, default Tailwind palette** (`indigo-600`, `gray-50/100/900`) used untouched, with no project-specific palette or type choice — this is the single fastest way to look like every other generated app, because it *is* every other generated app's literal starting point.
- **Uniform spacing with no rhythm** — every gap is `gap-4`, every section `py-12`, regardless of content density or hierarchy. Real designed layouts vary spacing deliberately to signal grouping and importance; uniform spacing signals "no one made a decision here."
- **Icon-plus-headline-plus-paragraph feature grids, three or four across, repeated for every section** regardless of whether the content actually has that shape — this pattern gets reached for because it's easy to fill, not because every piece of content fits a 3-up grid.

None of these individually is forbidden. The failure mode is applying the *default* version of all of them at once with no adaptation to what this specific screen needs — that combination is what "looks AI-generated" actually means in practice.

## What to do instead

- **Establish a real design token set before writing components**, not per-component ad hoc values: a small type scale (not "whatever size looks fine right now"), a spacing scale used consistently, a palette with actual named roles (not just "primary/secondary" mapped to whatever the framework's default primary/secondary happen to be). See `references/client-ui/frontend.md`'s existing rules for how tokens interact with real-time rendering; this section is about choosing the tokens deliberately in the first place.
- **Typography does real hierarchy work.** Pick one distinctive typeface pairing (or a well-considered single family with real weight/size variation) rather than the default system sans at default weights everywhere — hierarchy should be visible from typography and spacing alone, before color is even involved.
- **Density should match the data, not a generic content-page rhythm.** An order book or watchlist is a *dense, information-first* surface — tight row height, monospaced/tabular figures for numeric alignment, minimal decorative chrome. A settings or onboarding screen can be roomier. Don't apply one spacing/density recipe to both.
- **Numeric data in a trading UI needs tabular/monospaced figures and consistent decimal alignment** — prices and quantities that don't align vertically in a column are harder to scan at speed, which matters specifically for this platform's users. This is a design rule with a direct correctness angle, not just aesthetics.
- **Color communicates state deliberately, and colorblind-safely.** Gains/losses, buy/sell, and alert states are the highest-stakes color use on this platform — don't rely on red/green alone without a secondary cue (icon direction, sign, weight) for users with red-green color vision deficiency, and don't reuse the same red/green pair for unrelated UI states (e.g. form validation) where it would visually compete with P&L coloring.
- **Motion should be restrained and purposeful** on a data-dense real-time screen — a price tick can flash/highlight briefly to draw the eye to a change, but avoid decorative animation (bouncing entrances, parallax, spring-heavy transitions) competing for attention with numbers a trader needs to read accurately and fast.
- **Vary the layout to fit the actual content shape** — if a section genuinely has four parallel items, a 4-up grid is correct; don't force unrelated content into that shape just because it's a familiar pattern to generate. Ask what this specific screen needs before reaching for a stock layout.
- **Use this bundled design process before writing UI code**. It intentionally has no dependency on another installed skill, so this package remains portable:
  1. **Brainstorm a token system first** (4-6 named palette colors with hex values, 2+ typefaces by role, a layout concept, one signature element) before writing any component — for a trading UI, the "signature element" is more likely to be something functional-and-distinctive (a particular treatment of the price ticker, the order-book depth visualization) than decorative, since restraint matters more here than on a marketing page.
  2. **Check the plan against common defaults** before building: a warm-cream/serif/terracotta scheme, near-black with one neon accent, and a hairline-rule broadsheet look can be appropriate, but revise if the brief does not justify them.
  3. **Critique and revise the plan before implementing**, and critique the built result again after — this two-pass discipline is what the skill calls "brainstorm, explore, plan, critique, build, critique again," and skipping straight to code is the single most common way output ends up generic.
  4. **Apply its writing guidance** (name things by what the user controls, active voice, consistent action-vocabulary through a flow) to every piece of interface copy this task produces — this overlaps directly with `ux-design.md`'s "Writing for the interface" section; treat them as one discipline applied from two angles, not two separate copy passes.
  5. **Respect its stated quality floor**: responsive down to mobile, visible keyboard focus, reduced motion respected — these are also required by `ux-design.md`'s accessibility section, so satisfying one satisfies both.

## Backend "design quality" — architecture that doesn't look like a first draft

Design quality isn't frontend-only. The backend-side equivalent of "looks AI-generated" is a service that technically works but has no real architectural shape — everything in one file, no layering, naming that doesn't reflect the domain:

- **Layer by responsibility, not by accident**: a clear separation between transport/API (HTTP handler, gRPC service, message consumer), domain/business logic, and persistence/integration — a handler function that parses a request, runs business logic, and issues a database call inline, all in one function, is the backend equivalent of the uniform-gradient-card frontend problem: it technically works, and it's a first draft, not a finished design.
- **Domain types reflect the actual domain**, not a generic CRUD scaffold — `Order`, `Position`, `RiskCheckResult` with real fields and real invariants, not `Entity`/`Item`/`Record` generics reused across unrelated features because it was faster to copy-paste than to model the actual domain.
- **Naming should read like this specific system, not a tutorial.** `processData()`, `handleRequest()`, `doAction()` are the backend equivalent of Lorem Ipsum — they compile, and they tell a reviewer nothing. Match the specificity bar Section 5 (SKILL.md) already sets for naming.
- **Consistent architectural pattern across the codebase, not a different structure per file** invented fresh each time — see Section 2 (Codebase Understanding, SKILL.md): match existing conventions rather than introducing a new personally-preferred structure per feature, which is exactly how a codebase ends up looking like several disconnected first drafts stapled together.

## Review checklist before calling any UI or service-structure work "done"
- [ ] No default/unmodified framework palette (raw Tailwind `indigo-600`/`gray-50` etc.) used without a project-specific token layer on top
- [ ] No emoji used as functional icons or section markers
- [ ] Spacing and card/elevation treatment vary deliberately by content density, not copy-pasted uniformly across every section
- [ ] Numeric/price columns use tabular figures with consistent decimal alignment
- [ ] Gain/loss and buy/sell color coding has a non-color-only secondary cue
- [ ] Layout shape (grid, list, table) was chosen because it fits this content, not defaulted to a generic 3-up/4-up pattern
- [ ] Backend: transport, domain logic, and persistence are in distinguishable layers, not inlined into one handler function
- [ ] Naming (frontend components and backend functions/types) is domain-specific, not generic-tutorial naming
