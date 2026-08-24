# Clarification Protocol — Asking Open Questions Well

Section 1 (SKILL.md) establishes the headline rule: resolve what the codebase already answers, ask only what you genuinely can't resolve, one focused question at a time with your own recommendation attached. This file is the concrete mechanics of doing that well — the difference between a question that unblocks a decision and a question that just relays the ambiguity back to the user unprocessed.

## The core failure modes this protocol prevents

- **Asking things the codebase already answers.** Every question costs the user time and breaks their flow — asking "what error-handling pattern should I use?" when three existing modules already show a consistent pattern is a research failure, not genuine ambiguity.
- **Open-ended dumps instead of a decision.** "What do you want this to do?" or a wall of five unrelated questions at once forces the user to do the design work this skill exists to do. A good question narrows a specific fork, it doesn't hand the whole problem back.
- **Silent invention.** The opposite failure — deciding something that was genuinely unknowable from the codebase or task, without asking or flagging it, and hoping it doesn't matter. Section 1 already forbids this; this file's job is to make sure genuine gaps actually surface instead of getting quietly guessed past.
- **Blocking on things that don't need blocking.** Not every open question needs to stop implementation — see "When to ask vs. state an assumption and proceed" below. Over-asking is its own failure mode, not just under-asking.

## Before asking anything: the resolution pass

Run this before formulating a single question:
1. **Search the codebase for a comparable precedent.** A similar feature, a similar validation pattern, a similar UI form — if one exists and answers the question, use it and note in the Plan's "Codebase state: Verified" field that you did, rather than asking.
2. **Check upstream artifacts** — HLD/LLD documents, the ticket/ask itself, any linked design doc — per Pipeline Position (SKILL.md): this skill consumes those decisions, it doesn't re-derive them, but it also shouldn't ask a question those documents already answer.
3. **Check whether the ambiguity is actually load-bearing.** Some ambiguities don't change what you'd build (either interpretation leads to the same code) — those don't need a question at all, just proceed and don't mention it. Only things that genuinely branch the implementation are candidates for a question.

Only what survives all three steps becomes a candidate question.

## Formulating a question that's actually easy to answer

A well-formed clarifying question has four parts — missing any of them turns it into the "open-ended dump" failure mode:
1. **The specific fork**, stated concretely, not abstractly: not "how should validation work?" but "should a zero-quantity limit order be rejected at the API boundary with a 400, or accepted and rejected downstream by the risk-check service?"
2. **Why it matters** — the concrete consequence of each branch, briefly: "rejecting early means less load on the risk service but duplicates validation logic there and in the gateway."
3. **A recommended default**, with reasoning — never just a bare list of options with no lean. "I'd default to rejecting at the boundary, since duplicating a single cheap check is cheaper than the round-trip cost of a rejection surfacing downstream" — this lets the user answer with a one-word confirmation instead of doing the analysis themselves.
4. **What happens if there's no response** — for a genuinely blocking decision, say implementation is paused pending an answer; for a lower-stakes one, say you'll proceed with the stated default unless told otherwise, and actually do that rather than stalling on something that didn't need to block.

## One question at a time, sequenced — not a batch

Per Section 1: walk decision branches sequentially. If resolving question A changes what question B even needs to ask (or eliminates it entirely), asking both up front wastes the user's time answering a B that A's answer would have made moot. Concretely:
- Ask the single highest-leverage open question first — the one whose answer most changes the shape of the implementation.
- Only surface the next question once the first is resolved, and only if it's still relevant given that answer.
- Exception: if two questions are provably independent (neither's answer affects the other), it's fine to ask both together rather than manufacturing artificial sequencing — the rule is "don't hide a real dependency by batching," not "never ask more than one thing at once."

## When to ask vs. state an assumption and proceed

Not every open question warrants stopping and waiting. Use judgment based on cost of being wrong:
- **Ask and block** when the decision is expensive to reverse (a wire-format field layout, a public API shape, a database schema choice, anything Section 3 already flags as "never break an existing contract silently") or when it's genuinely ambiguous which of two materially different features is being requested.
- **State the assumption explicitly and proceed** when the decision is cheap to reverse (an internal function's parameter order, a variable name, a private helper's exact structure) — per Section 3's "Codebase state: Assumed" field, name the assumption in the Plan so it's checkable, but don't block implementation waiting for confirmation of something trivial to change later.
- **When genuinely uncertain which bucket a decision falls into**, default to asking — a wrongly-blocked trivial question costs one exchange; a wrongly-assumed expensive one costs a rework.

## Mid-task questions, not just upfront

New genuine ambiguity can surface after implementation has started (a code path reveals an edge case the original request didn't anticipate). The same rules apply mid-task as upfront: resolve from the codebase first, ask only what's genuinely unresolved, one focused question with a recommendation — don't silently improvise a resolution to something that surfaces new information the user hasn't seen, and don't stockpile several mid-task questions to ask all at once at the end when surfacing them as they arise would have kept the user's answer relevant to the specific point in the implementation where it was needed.

## Format for presenting a clarifying question

```
## Open question
Context: <the specific code/requirement location this affects>
The fork: <option A> vs <option B> — <what concretely differs>
Recommendation: <your default, and the one-sentence reason>
If no response: <"pausing implementation here" | "proceeding with the recommendation above">
```

Use this same structure whether the question is asked via a chat message or, if the interface supports it, a structured choice/options prompt — the content discipline (specific fork, stated consequence, recommended default) matters more than the delivery mechanism.

## Review checklist before sending any clarifying question
- [ ] The codebase, HLD/LLD, and ticket were actually checked for an answer first — not assumed absent
- [ ] The ambiguity is load-bearing (branches the implementation), not cosmetic
- [ ] The question names a specific fork, not an open-ended "what do you want"
- [ ] A recommended default with reasoning is attached, not a bare list of options
- [ ] It's the single highest-leverage question right now, not a batch that hides a sequencing dependency
- [ ] The cost of being wrong was weighed — if it's cheap to reverse, consider stating an assumption and proceeding instead of blocking
