# Frontend — Trading UI Implementation (Flutter / React)

The frontend is not on the backend's 5-8ms clock. Its job is: don't add avoidable lag on top of a fast backend, and never present data to a trader that's stale, rounded, or inconsistent with what the backend actually holds. A beautiful UI that shows a price that's 400ms old with no indication of staleness is a worse outcome than a plain UI that's honest about latency.

**This file covers functional/behavioral correctness only.** For visual and structural design quality — avoiding a generic/templated look, typography and density decisions, color use for gains/losses — see `references/client-ui/design-system.md`.

**Figma-First Precedence**: Whenever a Figma URL is provided, `references/client-ui/figma-design-engine.md` is the **PRIMARY source of truth** (`Figma > written prompt`). Strictly parse design tokens (colors, typography, padding, radius, grid) and build clean, reusable components matching the Figma layout without inventing custom visual styles. If Figma specs are missing or inaccessible when requested, prompt the user before generating frontend code.

## Real-time data handling (both Flutter and React)
- **Coalesce, don't render every tick.** Market data can arrive far faster than the screen can usefully update (60fps = ~16ms budget). Buffer incoming ticks and flush to the UI on an animation frame boundary, not on every WebSocket message. Rendering every individual tick as a separate frame update causes jank and wastes CPU that could go to keeping the connection healthy.
- **Never interpolate or smooth price/quantity values.** If the backend hasn't sent an update, show the last known value plus a visible staleness indicator (e.g. a timestamp or "last updated Xs ago") — don't animate/tween toward a guessed value.
- **Reconnect and resync explicitly.** On WebSocket disconnect, show a clear "reconnecting" state — don't silently freeze on stale data and let the trader think it's live. On reconnect, request a full snapshot before resuming incremental updates; don't assume the incremental stream picked up where it left off.
- **Money is never a float.** Use a fixed-point/decimal type (not `double`/JS `number`) for price and quantity end to end, matching the backend's minor-unit representation. Format for display only at the final render step.

## React-specific
- Use a state management approach with **granular subscriptions** (Zustand selectors, Redux with reselect, or React Query for server state) so a price update for one symbol doesn't re-render the entire watchlist/order book — only the row(s) that changed.
- Virtualize the order book and any long list (react-window/react-virtual) — rendering hundreds of DOM rows on every tick will visibly lag.
- Offload WebSocket message parsing to a Web Worker if the message volume is high enough to compete with the main thread for UI responsiveness — keep the main thread free for paint/interaction.
- Memoize expensive derived values (spread calculation, depth aggregation) with `useMemo`, keyed on the actual data that changed, not on every parent re-render.

## Flutter-specific
- Use `ValueNotifier`/`Bloc`/`Riverpod` with narrowly-scoped listeners so a price tick rebuilds only the specific widget showing that price — wrap hot-updating widgets in `RepaintBoundary` to isolate their repaint cost from the rest of the tree.
- Move WebSocket message parsing/decoding to a separate `Isolate` if message volume is high — Dart's single-threaded event loop means parsing on the main isolate competes directly with frame rendering.
- Avoid rebuilding entire `ListView`s on tick updates — use `ListView.builder` with keyed items and update only the changed item's data source.
- Batch state updates per frame (e.g. via a throttled stream transformer) rather than calling `setState`/notifying listeners on every individual message.

## Shared UI correctness rules for a trading interface
- Order entry forms: disable the submit control immediately on submit (prevent double-submission), and don't re-enable until a definitive response (ack/reject) — never on a timeout guess.
- Confirmations must reflect the backend's actual response, not an optimistic assumption of success.
- Any displayed P&L, balance, or position must be traceable to a specific backend snapshot/timestamp — if the frontend computes anything derived (e.g. unrealized P&L from live price × position), label it clearly as client-computed/estimated if the backend isn't the source of truth for that exact number.

## Review checklist before calling frontend trading-UI work "done"
- [ ] No float/double used for price, quantity, or money anywhere
- [ ] Rendering is throttled to frame rate, not driven 1:1 by incoming message rate
- [ ] Stale data is visibly indicated, never silently shown as current
- [ ] Reconnect flow requests a fresh snapshot rather than trusting resumed incremental updates
- [ ] Order submission is disabled until a definitive backend response, not a timeout guess
- [ ] Long lists (order book, watchlist) are virtualized

## Behavioural Flow Audit — required for any stateful or async UI change

Static review misses state-management bugs that only show up when you trace actual execution order — and this platform's WebSocket-driven real-time state is exactly the kind of surface where these bugs hide. For any change touching state, subscriptions, or async data (which is most of this frontend), do this before calling the change done:

1. **Map state stores**: for the store/component this change touches, list what it reads, what it writes, and — critically — what it *resets* and when. A price-tick handler that writes but never has a defined reset path (e.g. on symbol switch, on reconnect) is a likely source of stale-data bugs.
2. **Trace touchpoints in actual call order**: for every interactive element or subscription involved, trace the real sequence of calls, not the sequence you'd expect from reading the component top to bottom — async code frequently executes out of textual order.
3. **Hunt for these specific patterns by name**, since they're the ones that pass a casual read and fail in production:
   - **Async races**: two in-flight updates (e.g. a REST snapshot fetch and an incoming WebSocket tick for the same symbol) resolving out of order, with the older one winning and silently overwriting newer data.
   - **Stale closures**: a callback (event handler, subscription callback) capturing a variable's value at subscription time and never seeing later updates — common in React `useEffect`/Flutter stream-listener setups when a dependency is missing from the effect's dependency list or the listener isn't rebuilt on the relevant state change.
   - **`useEffect` interference (React)** / **listener lifecycle interference (Flutter)**: two effects/listeners both reacting to the same state change and stepping on each other's writes, or a cleanup function not actually canceling the async work it was meant to cancel (e.g. an in-flight fetch continuing after the component/widget unmounted).
   - **Sequential undo** (see `process`/refactoring guidance): a chain of conditionals in a reducer/state handler where each new case partially undoes a previous one — signals the state transitions need a proper state machine, not more branches.

## Testing async/real-time UI behavior

- Use **condition-based readiness checks** when testing (e.g. wait for a specific price update to actually render, or a specific WebSocket message to be processed) rather than a fixed delay or "network idle" — this platform's WebSocket/polling traffic means the network never truly goes idle, so idle-based waits will hang or produce flaky tests.
- Identify real selectors from the actually-rendered DOM/widget tree before writing test actions against them — don't guess at a selector from the component's source code, since conditional rendering can mean the element you're targeting isn't present yet.
