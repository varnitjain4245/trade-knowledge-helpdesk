# Recovery Protocol — Handling Broken Planning, HLD, or LLD Inputs

This protocol is used when upstream planning, HLD, or LLD is missing, contradictory, stale, or too weak to support safe implementation. Its purpose is to let this skill recover conservatively instead of silently inventing architecture or scope.

## When to trigger recovery

Use this protocol when any of the following is true:
- The task lacks a clear Planning ticket or acceptance criteria.
- The HLD/LLD is missing, inaccessible, or obviously outdated.
- The architecture decision needed for the task is not captured upstream.
- The request depends on a service boundary, API shape, schema, auth model, or state model that the upstream docs do not define.
- The implementation would otherwise require guessing.

## Recovery goal

Recover the minimum safe implementation path using evidence from the codebase, not assumptions. The goal is to preserve behavior, minimize blast radius, and make the gap explicit for upstream follow-up.

## Recovery workflow

1. Detect the gap explicitly.
   - Name the missing or conflicting artifact: Planning ticket, HLD, LLD, interface contract, schema, or architectural decision.
   - State why the gap matters to the task.

2. Gather evidence from the codebase.
   - Read similar modules, existing APIs, recent commits, tests, schemas, and any referenced implementation examples.
   - Prefer existing patterns over introducing a new design.

3. Reconstruct the smallest safe path.
   - Implement the narrowest change that satisfies the visible requirement without broad architectural changes.
   - Preserve existing contracts and behavior unless the task explicitly requires change.

4. Make assumptions explicit.
   - If the upstream gap cannot be closed from code evidence, record the assumption in the plan.
   - Mark it as assumed, not as verified fact.

5. Ask only one focused question when the gap is load-bearing.
   - Use this when the decision affects public contracts, state transitions, auth, money movement, persistence, or service boundaries.
   - Attach a recommended default and state what happens if no answer arrives.

6. Leave a clear upstream follow-up note.
   - Record what remains unresolved and what should be clarified by Planning/HLD/LLD.
   - Do not pretend the issue is solved if it is only deferred.

## Recovery template

Use this structure when reporting recovery:

```
## Recovery note
Gap: <what is missing or inconsistent>
Evidence used: <code/tests/docs that were consulted>
Fallback decision: <the conservative implementation path taken>
Assumptions: <what was inferred without upstream confirmation>
Outstanding upstream issue: <what should be clarified by Planning/HLD/LLD>
```

## Recovery rules

- Never invent a service boundary, schema, or public API shape without saying so.
- Prefer extension over redesign when the existing structure is adequate.
- Do not proceed with a large refactor just to make an underspecified task "clean".
- If the gap is architectural and high-risk, pause and surface it clearly rather than shipping a guess.
- If the gap is low-risk and local, proceed with the smallest safe implementation and document the assumption.
