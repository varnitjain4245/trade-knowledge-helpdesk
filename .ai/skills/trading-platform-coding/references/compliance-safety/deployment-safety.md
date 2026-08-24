# Deployment Safety — Validating Hot-Path Changes Before They Touch Real Money

Everything else in this skill helps you write a hot-path change correctly. This file covers what happens between "the code is correct by every check available" and "it's live" — because on a trading system, the gap between those two is where an undetected bug costs the most, and testing alone (even loom-verified, benchmarked, reviewed) can't fully substitute for seeing real behavior against real traffic before it's the only path.

**Scope note**: this file covers code-level patterns (how to structure a change so it *can* be shadow-run or canaried). Actual traffic routing, rollout percentage, and go/no-go decisions are deployment actions — per this skill's Boundaries section, those are reported to infrastructure/whoever owns releases, not executed by this skill directly, unless explicitly in scope.

## Shadow mode (dual-run, compare, don't act)

- For a change to matching logic, risk checks, or anything where "does this produce the same decision as before, except where it's supposed to differ" matters: structure the new logic to run *alongside* the old logic on real traffic, without its output actually being used yet. Compare outputs; log discrepancies; the old logic still makes the real decision.
- This requires the new code path to be genuinely side-effect-free when run in shadow mode — if the new logic can't be run without mutating shared state (placing orders, changing the book), shadow mode isn't safe as designed and the comparison needs to happen on a copy/snapshot instead.
- Discrepancy logging here follows the same write-behind pattern as `durability-and-audit.md` — don't let a comparison-logging call become a new source of hot-path blocking I/O.

## Canary / gradual cutover

- Once shadow-mode comparison shows acceptable agreement (define "acceptable" concretely before starting — e.g. zero unexplained discrepancies over N trading sessions, not "looked fine"), a canary rollout routes a small, explicitly bounded slice of real traffic (e.g. one low-volume symbol, or a fixed small percentage) to the new logic for real, with fast rollback available.
- The code needs an explicit, cheap kill switch (a flag check, not a redeploy) to fall back to the old path — design this in from the start of the change, not added afterward under pressure if something looks wrong.
- State in the Plan what the rollback path actually is and how fast it can be exercised — "we can roll back" is not a plan; "flipping this config flag reverts within one order cycle, verified in shadow testing" is.

## What must never go through canary/shadow alone

- Anything where the *type* of risk is different in kind, not degree, from what shadow/canary comparison can catch — e.g. a change to how audit records are structured (a corrupted audit trail from day one isn't something a comparison against old behavior catches, since there's nothing to compare against for a new field). For this class of change, exhaustive testing (loom, characterization tests, manual review) has to carry the full weight — say so explicitly rather than implying shadow mode covers everything.

## Review checklist before proposing any hot-path change ships past canary
- [ ] Shadow-mode comparison ran against real traffic for a stated period with a concrete, pre-defined "acceptable agreement" bar — not just unit/integration tests
- [ ] The new logic is genuinely side-effect-free in shadow mode, or compares against a snapshot rather than mutating shared state
- [ ] A cheap, fast kill switch exists and its rollback speed has actually been exercised, not just asserted to exist
- [ ] Canary scope (which traffic, what percentage) is explicitly bounded and stated, not "roll out and see"
- [ ] Rollout/traffic-routing decisions themselves are reported to whoever owns deployment, not executed by this skill directly, per the Boundaries section in SKILL.md
