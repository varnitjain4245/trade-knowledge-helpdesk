---
title: "PRD Review — Smart Contact-Center Knowledge Platform"
stage: 2
skill: prd-reviewing
scope: fullstack
version: "1.0"
reviews: requirements.md v1.0
---

# PRD Review: requirements.md v1.0

**Reviewer:** `prd-reviewing` (Stage 2)
**PRD Version:** 1.0
**Scope under review:** fullstack

---

## Summary

**Status:** APPROVE WITH CHANGES

**Overall Assessment:** The PRD is structurally complete and unusually disciplined about its own evidence gaps — it labels unvalidated claims as assumptions instead of dressing them as research, and every numeric target carries a sourcing tag. It is not yet implementable as written, for one reason above all others: the two decision thresholds the entire product hangs on (the answer bar and the classification bar) are named repeatedly but never given a value or an owner, which makes roughly a third of the acceptance criteria untestable. That plus one genuine internal contradiction about launch languages must be resolved before Stage 3. Everything else is fixable in parallel with design work.

---

## Findings by Severity

### Blockers (Must Fix Before Approval)

None. No missing problem statement, no solution-in-disguise, no absent user stories, no missing scope boundaries.

### Critical (Should Fix Before Implementation)

- [ ] **[REQ-005, REQ-003, REQ-011, REQ-012, REQ-016 / NFR]** The "answer bar", "classification bar", "low-volume threshold" and "group-size threshold" are referenced as if defined, but no value, range or owner exists anywhere in the document. Acceptance criteria such as "IF answer confidence is below the answer bar" cannot be tested, and QA at Stage 10 has nothing to assert against. → Either give each a value with a stated basis, or mark each explicitly as a launch-tunable with a named owner and a starting value, and state that the starting value is set during Phase 1d against the acceptance question set. A tunable with a starting value is testable; an unnamed bar is not.
- [ ] **[REQ-001 vs Risk R-1 mitigation]** Direct contradiction. REQ-001's first criterion states the system SHALL accept queries in all six launch languages. R-1's mitigation states a language ships only once it clears the 85% correctness bar, i.e. some of the six may not ship. Both cannot be true. → Resolve deliberately: either make REQ-001 conditional on per-language enablement (with the per-language bar as the gate, and a stated fallback behaviour for a language held back), or drop the R-1 mitigation and accept a language shipping below the bar. The first is the safer reading, but the choice belongs to the sponsor, not to the reviewer.
- [ ] **[REQ-014 / Audit]** The audit trail records "every answer shown" but never the text the agent actually sent to the customer. Since REQ-006 explicitly allows the agent to edit a suggestion before sending, the record can show a correct cited suggestion while the customer received something materially different. That defeats the document's own central promise — that a wrong answer can be traced. → Add a criterion recording the final sent reply against the conversation, alongside the suggestion and citations it was derived from.
- [ ] **[Cold start / whole document]** No requirement describes behaviour when the knowledge base is empty or thin, which is its state on day one and during Phase 1a. Every flow assumes at least one approved item exists, and Flow 1's precondition says so outright without saying what happens otherwise. → Add explicit cold-start behaviour: what agents and customers see, whether the self-serve assistant is exposed at all below a coverage floor, and who decides when it goes live.

### Major (Fix Soon)

- [ ] **[Success Metrics]** No guardrail metrics. Every KPI pushes in one direction — more deflection, less handle time — with nothing protecting against the obvious failure: deflection achieved by customers giving up, or handle time cut by agents sending unverified suggestions. → Add at least three guardrails: repeat-contact rate within 7 days must not rise; the wrong-answer rate must not rise as assist adoption rises; abandoned self-serve conversations must be counted separately from self-resolved ones (currently the outcome set in REQ-007 has no "abandoned" state at all, so an abandonment is silently absent from the deflection denominator).
- [ ] **[REQ-007 outcome set]** Related to the above and independently a gap: the three recorded outcomes (self-resolved, handed over, callback recorded) do not cover a customer who simply leaves. Every real chat product has this state. → Add "abandoned" as a fourth outcome with a defined inactivity boundary, and exclude it from the deflection numerator.
- [ ] **[REQ-015 / NFR Security]** Personal-data masking is required but carries no accuracy expectation and no verification method, while REQ-015's own fallback ("withhold when masking is uncertain") assumes the system reliably knows when it is uncertain. Masking that silently misses an identifier is the highest-consequence failure in the document and currently has no measurable bar. → State a target for masking recall on a held-out sample, name who verifies it, and add a periodic sampling check on stored gap entries.
- [ ] **[NFR / Compliance]** Audit retention is stated (3 years, flagged PROPOSED) but conversation-content retention is not stated at all — how long a customer transcript is kept, and whether gap entries derived from it outlive it. Given REQ-015 grants deletion on request, the two policies must be defined together or deletion is undefined in practice. → Add a conversation-retention period and state explicitly what survives a deletion request (the document currently says aggregate counts survive; it does not say what happens to gap entries).
- [ ] **[Missing feature — public-surface abuse control]** The self-serve assistant is customer-facing and, per OQ-6, may be anonymous, yet nothing addresses volume abuse, automated scraping of the knowledge base, or a single actor exhausting capacity. The 200-concurrent scalability figure is stated as if all traffic were legitimate. → Add a Must-Have or an NFR covering fair-use limiting on the public surface, expressed as an outcome.
- [ ] **[Timeline & Roadmap]** The twelve-week plan has had no engineering input and is presented with week-level precision it has not earned — while Estimation Blocker 1 concedes that the corpus size and condition, the single largest driver of Phase 1a effort, is unknown. Phase 1d in particular compresses acceptance testing across six languages, confirmation of every PROPOSED number, a pilot, and full launch into two weeks. → Re-present Phase 1 as sequenced milestones without week numbers until Phase 0 closes, or mark the whole table PROPOSED pending engineering sizing.
- [ ] **[NFR Cost]** "Freely available, self-hostable models" names an implementation approach inside a document whose own stated rule forbids exactly that. The intent — no per-query commercial fee, and processing under the operator's control — is a legitimate business constraint and belongs here; the phrasing is not. → Rewrite as an outcome: no per-query licence cost, and no requirement to send query or document content to a party outside the operator's control. That also happens to capture the data-residency implication, which the current phrasing leaves implicit.
- [ ] **[BR-6 vs REQ-005]** Conflict handling and confidence handling are specified independently and do not compose. If two approved sources disagree, is confidence high (two supporting passages) or below the bar (no reliable single answer)? BR-6 says show both; REQ-005 says show nothing below the bar. The order of evaluation is undefined. → State that conflict detection is evaluated before the answer bar, and that a detected conflict is shown as a conflict regardless of confidence.
- [ ] **[Personas / Assumption A-1]** Correctly flagged by the author, restated here because it is the document's largest single risk to correctness: no primary research exists, so every persona pain point and every tolerance figure derived from one is an inference. The document handles this honestly, but Stage 3 must not treat these as validated. → No document change required beyond what OQ-1 already carries; noted so that downstream stages inherit the caveat.

### Minor (Nice to Have)

- [ ] **[REQ-013]** Four roles are defined and their permissions listed, but nothing states that a user must be identified before taking any role-bound action — sign-in is assumed rather than required. Add one ubiquitous criterion so the requirement is self-contained.
- [ ] **[REQ-002]** "Near-duplicate" gates a mandatory user decision but is never characterised even loosely. A rough basis (substantially overlapping text, same issuing authority and subject) is enough to make it testable.
- [ ] **[REQ-012]** The agent drill-down carries a "ratings are a sample, not a census" caution in Flow 6 but not in the requirement itself. Move or duplicate the caution into REQ-012 so it survives if the flows are edited.
- [ ] **[Edge Cases]** "Two managers edit one item simultaneously" appears in Edge Cases but has no corresponding acceptance criterion in REQ-009. Every other edge case traces to a requirement.
- [ ] **[Engineering Digest]** The hard-numbers table omits the masking-accuracy and conversation-retention figures that this review adds. Regenerate the digest after the changes above, per the template's own "write it last" instruction.

---

## Section Ratings

| Section | Rating | Notes |
|---|---|---|
| Problem Statement | Strong | Specific, four named failure modes, and honest that its evidence is inferential rather than measured |
| User Stories | Strong | Four personas, each with a flow and concrete stories; user types are specific, not "as a user" |
| Acceptance Criteria | Weak | EARS format used correctly throughout, but the undefined thresholds make a large minority of criteria untestable as written — this is the single biggest gap |
| Scope | Strong | MVP / Future / Out of Scope are mutually exclusive and every exclusion carries a reason |
| Success Metrics | Adequate | Measurable and fully mapped to tracking events, but no baselines (acknowledged) and no guardrails (not acknowledged) |
| Non-Functional Requirements | Adequate | Every number sourced or marked PROPOSED; gaps in retention, abuse control and masking accuracy |
| Risks & Constraints | Strong | Nine risks with real mitigations; one mitigation contradicts a requirement (see Critical) |
| Edge Cases | Strong | Fourteen cross-cutting cases, nearly all traceable to a requirement |

---

## Feasibility Assessment

- **Technical:** Achievable in principle. The correctness bar in regional languages under a no-commercial-cost constraint is the one genuinely uncertain element, and the PRD already carries it as R-1 with a sane mitigation. The citation requirement, far from adding risk, reduces it — a system that can only answer from retrieved approved text has a much smaller failure surface than one generating freely.
- **Timeline:** Not assessable. See the Major finding — no engineering input, and the dominant effort driver is unmeasured.
- **Dependency:** Two blocking open questions (OQ-1 ticket data, OQ-2 portal list) affect only Should-Have features and baseline measurement, so neither blocks Must-Have design. Correctly structured.
- **Compliance:** Addressed but incomplete — retention and deletion semantics need the pairing described above.
- **Operational:** The document names its own worst operational risk (Estimation Blocker 5: knowledge maintenance is unstaffed). Design cannot fix this; it should not be allowed to disappear between here and launch.

---

## Verdict

**APPROVE WITH CHANGES.** The four Critical findings must be resolved in `requirements.md` before Stage 3a/3b begin, because each one changes what gets designed: undefined thresholds change the answering pipeline's shape, the language contradiction changes launch scope, the sent-reply audit gap changes the data recorded per conversation, and cold-start behaviour changes both consoles. The Major findings should be resolved in the same pass — none require new information from outside the document except the retention period, which is already tracked as OQ-4. The Minor findings can be folded in at any point before Stage 7.

---

# Re-Review: requirements.md v1.1

**Trigger:** Stage 2 gate returned ITERATE. `requirements.md` was revised to v1.1 against the findings above.

## Disposition of every finding

### Critical

| # | Finding | Status in v1.1 | Evidence |
|---|---|---|---|
| C-1 | Undefined thresholds | **Closed** | New "Decision Thresholds" section: answer bar 0.70, classification bar 0.60/field, low-volume under 100 conversations, gap group-size 5. Each carries a basis, an owner and a `[PROPOSED]` tag, plus a change-audit criterion. |
| C-2 | REQ-001 vs R-1 contradiction | **Closed** | REQ-001 now specifies independent per-language enablement, gated on that language clearing the correctness bar; English + Hindi guaranteed. R-1's mitigation restated to match. Held-back-language behaviour is specified rather than implied. |
| C-3 | Sent reply not audited | **Closed** | Two new REQ-014 criteria record the text actually sent by an agent (distinguishable from the suggestion) and the text the self-serve assistant showed. New "Reply sent by agent" tracking event. |
| C-4 | No cold-start behaviour | **Closed** | New Must-Have REQ-023: agent assist live from item one with a thin-knowledge indication, self-serve closed until a declared coverage floor is met, and the floor itself defined. Open Question OQ-7 added for the concrete topic list. |

### Major

| # | Finding | Status in v1.1 |
|---|---|---|
| M-1 | No guardrail metrics | **Closed** — five guardrails added (repeat contact, wrong-answer versus adoption, abandonment, handover quality, language parity), each framed as a failed launch criterion if breached. |
| M-2 | No "abandoned" outcome | **Closed** — fourth outcome added with a 15-minute inactivity boundary, and explicitly excluded from the self-resolved count. |
| M-3 | Masking has no accuracy bar | **Closed** — 98% recall on a held-out sample, verified before launch and quarterly, plus a periodic manual sampling check on stored gap entries. |
| M-4 | Conversation retention undefined | **Closed** — 12-month transcript retention paired with the audit period, and deletion semantics stated in both REQ-015 and the Compliance NFR. |
| M-5 | No abuse control on the public surface | **Closed** — fair-use limiting in REQ-023, with the rule that limiting never removes handover, plus a scalability clause and a tracking event. |
| M-6 | Timeline unearned precision | **Closed** — week numbers replaced by milestones, with an explicit note that durations are withheld until Phase 0 closes. |
| M-7 | NFR Cost names an implementation | **Closed** — restated as two outcomes: no per-query or per-user licence cost, and no content leaving the operator's control. |
| M-8 | BR-6 and REQ-005 do not compose | **Closed** — conflict detection now explicitly evaluated before the answer bar, and a shown conflict is excluded from correctness and deflection counts. |
| M-9 | Personas unvalidated | **Acknowledged, no change required** — already carried as A-1 and OQ-1. Downstream stages inherit the caveat: persona-derived tolerances are inferences, not measurements. |

### Minor

All five closed: identification-before-role-action (REQ-013), near-duplicate characterised (REQ-002), sample-not-census caution moved into REQ-012, concurrent-edit criterion added to REQ-009, Engineering Digest regenerated with the six new hard numbers and REQ-023.

## Re-check of the previously weak section

**Acceptance Criteria — now Adequate.** Every criterion that previously referenced an unvalued bar now resolves to a stated starting value, so QA at Stage 10 has something to assert. Rating is Adequate rather than Strong because those values are still `[PROPOSED]` and must be confirmed against the acceptance question set in Phase 1d before they can be called settled — that confirmation is exactly what Stage 10 is for.

## Revised Verdict

**APPROVED.** All four Critical and eight of nine Major findings are closed in v1.1; the ninth is an evidence limitation the document correctly carries rather than a defect it can fix. Must-Have count is 16 (REQ-001 to REQ-015, REQ-023). Scope remains `fullstack`. Cleared to proceed to Stage 3a and 3b.
