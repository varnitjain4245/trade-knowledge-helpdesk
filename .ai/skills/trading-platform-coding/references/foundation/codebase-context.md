# Codebase Context — Understanding Before Changing

Before implementing anything in an unfamiliar or large part of the codebase, build a working model of it rather than pattern-matching from the first file you open.

## Orientation pass
- Identify what kind of component you're touching (hot-path service, UI component, shared library, config/infra) — the rules that apply differ by type, and `rust-backend.md`/`frontend.md` only trigger correctly if you've identified which one you're in.
- Find the actual entry point and trace one real request/data flow through it end to end before making changes — don't infer behavior from function names alone.
- Note existing conventions as you go: naming patterns, error-handling style, how this codebase already solves the problem you're about to solve elsewhere. Matching existing convention beats introducing a new one you personally prefer.

## Dependency and contract mapping
- Before changing a shared type, struct, or function signature, find every caller — a change that looks local can break a distant, non-obvious consumer.
- Identify implicit contracts, not just explicit ones: a function that's never supposed to be called concurrently, a field that's assumed non-null by convention rather than by the type system. These are the changes most likely to cause a regression that compiles cleanly and fails at runtime.
- Flag single points of failure you notice in passing (a shared utility everything depends on, a piece of business logic duplicated in three places that's about to become four) — even if fixing it isn't in scope for the current task, noting it is valuable.

## Risk profile before proposing a change
Once you understand the area, state explicitly:
- What you traced and verified directly.
- What you're inferring rather than having confirmed (e.g. "I'm assuming this cache is safe to invalidate here because I don't see another reader, but I didn't check the full call graph").
- What you deliberately didn't explore, so the reviewer knows the boundary of what's actually been checked versus assumed safe.

This matters more in this codebase than most: a plausible-looking but locally-scoped view of a shared matching-engine data structure is exactly the kind of gap that turns into a production incident.
