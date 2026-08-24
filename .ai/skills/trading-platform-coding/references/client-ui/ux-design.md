# UX Design — Usability, Flow, and Interaction Quality

`design-system.md` governs how the UI *looks* (tokens, typography, avoiding the generic-AI aesthetic). This file governs how it *works* for the person using it — whether a trader can actually complete a task quickly, correctly, and without anxiety. A screen can be visually distinctive and still be bad UX (confusing flow, no feedback on a critical action, an error message that doesn't say what to do next). Both files are required for any UI work; neither substitutes for the other.

**The standard for this platform is high: "usable" is the floor, not the target.** A trading interface has a higher cost of confusion than most software — a misread confirmation dialog or an ambiguous button label can cost the user real money. Treat UX quality with the same rigor Section 10 (SKILL.md) applies to security: not a nice-to-have pass at the end, but a set of checkable requirements.

## Usability heuristics — apply Nielsen's 10, made concrete for this platform

1. **Visibility of system status.** Every action gets immediate feedback: an order submission shows a pending state instantly, not just eventually a result. Connection status (live / reconnecting / stale, per `frontend.md`) is always visible, not something the user has to infer from a frozen screen.
2. **Match between system and the real world.** Use trading terminology the way traders actually use it (limit/market/stop, bid/ask, not internal system field names) — see the "write from the end user's side of the screen" principle below.
3. **User control and freedom.** Every non-trivial action has a clear way to cancel or back out *before* it's committed — an order entry form should be easy to abandon or amend before submission. After submission, freedom is bounded by reality (a filled order can't be un-filled) — the UI should be honest about that boundary, not imply a false undo.
4. **Consistency and standards.** The same action always uses the same label and produces the same kind of feedback everywhere it appears (see the "Publish→Published" consistency example below) — a "Cancel" button that closes a modal in one screen and cancels an order in another is a direct hazard on this platform, not just an inconsistency.
5. **Error prevention over error messages.** Prefer disabling an invalid action and explaining why (e.g. greying out "Submit" with a visible reason when quantity is zero) over letting the user submit and then telling them it failed — this is the UX-layer expression of Section 6's "handle edge cases explicitly."
6. **Recognition over recall.** Show the information needed to make a decision on-screen (current position, buying power, last price) rather than requiring the user to remember it from a different screen or hold it in their head.
7. **Flexibility and efficiency of use.** Support both a careful novice path (guided order entry, confirmations) and an efficient expert path (keyboard shortcuts, hotkeys for common order types, saved order templates) — don't force an expert trader through the same friction a first-time user needs.
8. **Aesthetic and minimalist design.** Every element on a dense trading screen should earn its place — see `design-system.md`'s density guidance; UX and visual design converge here.
9. **Help users recognize, diagnose, and recover from errors.** See the error-writing rules below — plain language, what happened, what to do next.
10. **Help and documentation.** Where a feature has genuine complexity (a less-common order type, a margin calculation), a contextual explanation should be reachable from the point of use, not buried in a separate help center the user has to go find mid-task.

## Information architecture and flow

- **Map the user's actual task before laying out the screen**, not the other way around. For order entry specifically: what does a trader need to see, in what order, to place a correct order with confidence? Symbol and current price first, then the decision inputs (side, type, quantity, price), then a clear confirmation of what's about to happen, in that order — don't organize the form by how the backend's fields happen to be structured.
- **Progressive disclosure for complexity.** Advanced order types (stop-limit, trailing stop, OCO) shouldn't clutter the default entry path for a simple market/limit order — surface them behind an explicit "advanced" affordance rather than presenting every possible field at once to every user.
- **Critical, hard-to-reverse actions get an explicit confirmation step that shows the real consequence**, not a generic "Are you sure?" — a large or unusual order should show the actual notional value and any relevant risk context in the confirmation, not just repeat the form fields back unchanged.
- **Keep a consistent navigation and layout structure across screens** — a trader building muscle memory around where the order book, positions, and order entry live should not have that structure shift between sections without a strong reason.

## Feedback, loading, and empty states

- **Every async action has three states minimum**: pending (with visible indication, not a frozen UI), success (with a clear, specific confirmation — "Order #1234 filled at $142.50," not just "Success"), and failure (with a specific, actionable reason — see error-writing below).
- **Loading states should match what's actually loading.** A full-screen spinner for a partial data refresh is worse UX than a scoped, local loading indicator on just the section that's updating — don't block the whole screen for a partial update.
- **Empty states are an opportunity to guide, not just an absence.** An empty watchlist or an account with no positions should tell the user what to do next ("Add a symbol to start tracking it") rather than showing a blank area with no explanation.

## Accessibility — required, not optional, for this platform

- **Keyboard navigation and visible focus states** for every interactive element — order entry in particular should be fully operable without a mouse, since keyboard-driven order entry is a real efficiency need for active traders, not just an accessibility nice-to-have.
- **Color is never the sole signal.** Beyond the gains/losses rule already in `design-system.md`, this applies to every status indicator (connected/disconnected, filled/rejected) — pair color with an icon, label, or shape difference.
- **Sufficient contrast** (WCAG AA at minimum — 4.5:1 for body text, 3:1 for large text/UI components) for all text and meaningful UI elements, including in dark mode, which most trading UIs default to.
- **Screen-reader-meaningful labels and live regions** for dynamically-updating content (price ticks, order status changes) — a screen-reader user needs to be told when a price or order status changes, not just have the visual DOM update silently.
- **Respect reduced-motion preferences** (`prefers-reduced-motion`) for any animation — a price-flash or transition effect should degrade gracefully to an instant state change when reduced motion is requested.

## Writing for the interface — the UX layer of copy

Apply these interface-writing rules to functional trading-UI copy, not just marketing or landing-page copy:

- **Name things by what the user controls, not by internal system structure.** "Order type," not "orderTypeEnum"; "Available balance," not "cash_available_qty."
- **Action labels stay consistent through the whole flow** — a button that says "Place order" should lead to a confirmation and a result that both still say "order," in the same voice, not "Submit" → "Transaction processed."
- **Errors are specific, in the interface's voice, and say what to do next**: "Order rejected: quantity exceeds available buying power" is usable; "An error occurred" or "Invalid input" is not. Never surface a raw backend exception message or stack trace to the end user (this is also a Section 10 security rule — no internal detail in client-visible errors) — translate it into the specific, actionable interface-voice message the user needs.
- **Plain, active, specific language throughout** — avoid vague verbs ("Process," "Handle") in favor of exact ones ("Cancel," "Amend," "Close position").

## Where UX and the platform's real-time correctness rules intersect

- A UX pattern is never allowed to imply certainty the backend doesn't have — an optimistic-UI pattern that shows an order as "filled" before the backend confirms it violates both `frontend.md`'s correctness rules and this file's "don't create false confidence" principle simultaneously. Where optimism is used for perceived responsiveness (e.g. instantly disabling the submit button, showing a "submitting…" state), it must never imply an outcome that hasn't actually happened yet.
- Staleness indicators (`frontend.md`) are also a UX requirement, not just a data-correctness one — the *way* staleness is communicated (a subtle timestamp vs. an alarming banner) should be proportionate to how stale the data actually is and how consequential a decision based on it would be.

## Review checklist before calling any UI work "done" for UX
- [ ] Every async action has a distinct pending / success / failure state, each with real, specific content
- [ ] Invalid actions are prevented (disabled + explained) where feasible, rather than only caught after submission
- [ ] Critical/hard-to-reverse actions have a confirmation step showing the real consequence, not a generic confirmation
- [ ] Full keyboard navigation and visible focus states work for every interactive element, especially order entry
- [ ] Color-coded status has a non-color secondary cue everywhere, not just in gain/loss display
- [ ] Contrast meets WCAG AA in both light and dark mode
- [ ] Error messages are specific, in plain interface language, and say what to do next — no raw backend errors surfaced
- [ ] Empty states guide the user to a next action instead of showing a blank area
- [ ] Reduced-motion preference is respected for any animated feedback
