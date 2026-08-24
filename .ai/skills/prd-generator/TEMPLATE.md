---
title: "[NEEDS CLARIFICATION: Feature title]"
status: draft
version: "1.0"
---

# Product Requirements Document

> **Tech-Agnostic Rule:** This entire document describes WHAT users need and WHY — never HOW it is built. No frameworks, languages, databases, cloud providers, APIs, or architecture diagrams belong here. If you find yourself naming a technology, stop and rewrite the sentence as a user-facing outcome. (See SKILL.md → "Core Principle: Tech-Agnostic Always" for examples.)

## Validation Checklist

### CRITICAL GATES (Must Pass)

- [ ] All required sections are complete
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Domain Invariants Gate has been run (see SKILL.md) and every table-stakes item has a feature/NFR or an explicit Out-of-Scope entry with a reason
- [ ] No Must-Have feature's acceptance criteria depend on an unresolved Open Question
- [ ] Problem statement is specific and measurable
- [ ] Every feature has testable acceptance criteria (EARS format)
- [ ] Every primary user flow has a happy path, at least one alternate/branch path, and at least one error path
- [ ] No contradictions between sections, and no duplication of the same requirement across Acceptance Criteria / Business Rules / User Flows
- [ ] No technology, architecture, or implementation detail anywhere in the document

### QUALITY CHECKS (Should Pass)

- [ ] Problem is validated by evidence (not assumptions)
- [ ] Context → Problem → Solution flow makes sense
- [ ] Every persona has at least one user flow
- [ ] MVP Scope, Future Scope, and Out of Scope are mutually exclusive (no feature appears in two)
- [ ] Every Non-Functional Requirement number has a stated basis or a `[PROPOSED: pending eng confirmation]` marker
- [ ] Every metric has corresponding tracking events, evidenced by a printed metric-to-event mapping table
- [ ] No feature redundancy (check for duplicates)
- [ ] Engineering Digest is populated and matches the detailed sections it summarizes
- [ ] A new team member could understand this PRD without asking what a term means

---

## Engineering Digest

> Write this section LAST, after every other section is final — but it goes FIRST in the document. It exists so an engineering lead can scope the work without reading the full narrative. No persuasive prose here: features, numbers, and blockers only, each as a short line or table row referencing the fuller section below it.

**Features at a glance:**
[NEEDS CLARIFICATION: One line per Must/Should/Could-Have feature — name + one-sentence description. Pull directly from Functional Requirements.]

**Hard numbers:**
[NEEDS CLARIFICATION: Every numeric NFR target and KPI target, each with its sourcing tag — e.g., "Order confirmation: <2s (based on X)" or "Uptime: 99.5% [PROPOSED: pending eng confirmation]".]

**Must-Haves with unresolved dependencies:**
[NEEDS CLARIFICATION: List any Must-Have feature whose acceptance criteria depend on an Open Question, with the question's BLOCKING status, owner, and date. If none, state "None."]

**Estimation Blockers (see full section below):**
[NEEDS CLARIFICATION: One line per blocker — what can't be sized and why. If none, state "None."]

---

## Executive Summary
[NEEDS CLARIFICATION: In 3-5 sentences, what is this product/feature, who is it for, and why does it matter? This is the "read this if you read nothing else" section — write it last, but put it first.]

## Problem Statement

### Context
[NEEDS CLARIFICATION: What situation exists today that sets up this problem? Who experiences it and when?]

### Problem
[NEEDS CLARIFICATION: What specific problem are users facing today? Why is this painful for them? What are the consequences of not solving this? Include data, not assumptions.]

### Why Now
[NEEDS CLARIFICATION: Why is this worth solving now rather than later? What's changed?]

> Before finalizing this section, run it through the Reality-Check Gate in SKILL.md (demand reality, status quo, desperate specificity, narrowest wedge, direct observation, future-fit). Anything that doesn't hold up gets logged as an Assumption or Open Question rather than stated as fact.

## Goals

### Product Goals
[NEEDS CLARIFICATION: What qualitative outcomes should this achieve for users? (Quantitative targets go in Success Metrics, not here.)]

### Non-Goals
[NEEDS CLARIFICATION: What is this explicitly NOT trying to achieve, even if related? Prevents scope creep from the very first read. Distinct from "Out of Scope" below, which lists excluded features rather than excluded goals.]

## Stakeholders
[NEEDS CLARIFICATION: Who has a decision-making, funding, or veto stake in this product? For each: name/role, their interest, and what they need from this PRD.]

| Stakeholder | Role | Interest / Stake | Approval Needed? |
|---|---|---|---|
| [Name/Role] | [e.g., Product sponsor] | [What they care about] | [Yes/No] |

## User Personas

### Primary Persona: [NEEDS CLARIFICATION: persona name]
- **Demographics:** [Age range, role/occupation, technical expertise level]
- **Goals:** [What are they trying to accomplish? What does success look like for them?]
- **Pain Points:** [What frustrates them about current solutions? What obstacles do they face?]
- **Formal User Stories:**
  - As a [persona], I want to [action], so that [benefit]
  - As a [persona], I want to [action], so that [benefit]

### Secondary Personas
[NEEDS CLARIFICATION: Are there other user types? If yes, define them the same way, including their own user stories. If no, remove this section.]

---

## User Flows

Each flow below must describe both the ideal path AND what happens when things branch or go wrong. Steps are written as user action → system response, in plain language — no UI widget names, no technical mechanisms.

### Flow 1: [NEEDS CLARIFICATION: Flow name, e.g. "First-time payment request"]
- **Persona:** [Which persona runs this flow]
- **Trigger:** [What causes the user to start this flow?]
- **Preconditions:** [What must be true before this flow can begin?]

**Main Flow (Happy Path)**
1. User [action] → System [response]
2. User [action] → System [response]
3. ...

**Alternate Flows / Branches**
- **Branch A — [condition, e.g. "customer has no email on file"]:**
  1. [step] → [step]
- **Branch B — [condition]:**
  1. [step] → [step]

**Error / Exception Flows**
- **If [failure condition]** → System [how it responds] → User [recovery action]
- **If [failure condition]** → System [how it responds] → User [recovery action]

**Postconditions / Success State**
[What must be true for this flow to be considered complete/successful?]

**Related Edge Cases**
[Reference relevant items from the Edge Cases section by name]

### Flow 2: [NEEDS CLARIFICATION: Flow name]
[Repeat structure as needed]

---

## Functional Requirements

Organize every feature under one MoSCoW category. A feature only appears once, in its highest-priority category.

### Must Have Features

#### Feature 1: [NEEDS CLARIFICATION: Feature name]
- **User Story:** As a [user type], I want to [action] so that [benefit]
- **Acceptance Criteria (EARS Format):**

  Use the pattern that fits each criterion:
  - UBIQUITOUS: `THE SYSTEM SHALL [action]` — always-on behavior
  - EVENT-DRIVEN: `WHEN [trigger], THE SYSTEM SHALL [action]` — user/system events
  - STATE-DRIVEN: `WHILE [state], THE SYSTEM SHALL [action]` — mode-dependent
  - OPTIONAL: `WHERE [feature enabled], THE SYSTEM SHALL [action]` — configurable
  - COMPLEX: `IF [condition], THEN THE SYSTEM SHALL [action]` — business rules

  **Good Example:** `WHEN the user submits a valid request, THE SYSTEM SHALL confirm completion within 2 seconds`
  **Bad Example:** `User can complete the request` _(vague, not testable)_
  **Also bad (too technical):** `THE SYSTEM SHALL write the record to the primary database` _(names implementation — describe the observable outcome instead)_

  Criteria:
  - [ ] [EARS-formatted criterion]
  - [ ] [EARS-formatted criterion]
  - [ ] [EARS-formatted edge case]

#### Feature 2: [NEEDS CLARIFICATION: Feature name]
[Repeat structure as needed]

### Should Have Features
[NEEDS CLARIFICATION: Significant improvements, not critical for launch. Same structure as above.]

### Could Have Features
[NEEDS CLARIFICATION: Nice-to-haves if time/resources permit. Same structure as above.]

### Won't Have (This Phase)
[NEEDS CLARIFICATION: Explicitly out of scope for this phase — see Out of Scope section for the full rationale.]

## Non-Functional Requirements

Describe the *quality of experience* users need — always as an observable, testable outcome, never as a named technology or implementation approach.

- **Performance:** [e.g., response/completion time targets, load expectations]
- **Reliability/Availability:** [e.g., uptime expectations, acceptable failure rate]
- **Usability/Accessibility:** [e.g., who must be able to use this without assistance, accessibility standards to meet]
- **Security & Privacy (outcomes only):** [e.g., what data must remain private, who can access what — not how it's enforced]
- **Scalability (outcomes only):** [e.g., how many concurrent users/transactions it must support]
- **Compliance:** [e.g., regulatory or legal standards that apply]

[NEEDS CLARIFICATION: Fill in each applicable dimension above; remove any that don't apply to this product.]

> **Sourcing rule:** every number above must carry either a one-line stated basis (e.g., "based on [benchmark/competitor/persona tolerance]") or the marker `[PROPOSED: pending eng confirmation]`. An unsourced number is an invented number — don't state one as settled fact.

## Detailed Feature Specifications

Use this section only for the most complex Must-Have features that need more than user story + acceptance criteria.

### Feature: [NEEDS CLARIFICATION: Pick the most complex feature from above]
**Description:** [Detailed explanation of how this feature behaves, in user-facing terms]

**Business Rules:**
- Rule 1: [When X happens, then Y should occur]
- Rule X: ...

**Feature-Specific Edge Cases:**
- Scenario 1: [What could go wrong?] → Expected: [How should the system respond?]
- Scenario X: ...

## Edge Cases

Cross-cutting edge cases that don't belong to a single feature (e.g., data conflicts across features, simultaneous actions by two users, boundary conditions on shared limits).

- [ ] [Edge case] → Expected behavior: [...]
- [ ] [Edge case] → Expected behavior: [...]

---

## MVP Scope
[NEEDS CLARIFICATION: State plainly what ships in v1. This should map directly to "Must Have Features" above — if it doesn't, reconcile the two. Include any minimum non-functional bar required for launch.]

## Future Scope
[NEEDS CLARIFICATION: What's intentionally planned for a later phase? Map to "Should Have" / "Could Have" features above, with rough sequencing if known (e.g., "Phase 2," "Post-launch").]

## Out of Scope
[NEEDS CLARIFICATION: What is explicitly excluded, with no current plan to build it, and why? This is different from Future Scope — these are deliberate exclusions, not a backlog. Maps to "Won't Have."]

## Estimation Blockers
[NEEDS CLARIFICATION: If an engineering lead tried to size this today, what would stop them? List every answer here, even if it's covered elsewhere in the document — this is a single scannable list for a scoping conversation. Include anything with no clear owner, no resolved dependency, or scope large enough to be its own project (e.g., an ongoing data-maintenance obligation).]

| # | What can't be sized yet | Why | Owner | Needed by |
|---|---|---|---|---|
| 1 | [Blocker] | [Reason] | [Who] | [Date] |

---

## Success Metrics / Business Metrics

### Key Performance Indicators
[NEEDS CLARIFICATION: How will we measure if this feature is successful?]

- **Adoption:** [Target number/percentage of users who try the feature]
- **Engagement:** [Target frequency of use or actions per user]
- **Quality:** [Target error rate, success rate, or satisfaction score]
- **Business Impact:** [Revenue, retention, or other business metric]

### Tracking Requirements
[NEEDS CLARIFICATION: What user actions and data points must we track to validate the KPIs above?]

| Event | Properties | Purpose |
|-------|------------|---------|
| [User action] | [What data to capture] | [Why we track this] |

## Timeline & Roadmap
[NEEDS CLARIFICATION: What are the major phases/milestones and target dates or sequencing? Describe in terms of what ships when — not how it's built (no sprint/engineering detail).]

| Phase | Milestone | Target Timing | Scope |
|---|---|---|---|
| [Phase 1] | [Milestone] | [Date/quarter/relative timing] | [What's included] |

---

## Risks & Constraints

### Constraints
[NEEDS CLARIFICATION: Budget, timeline, legal/compliance, or other limiting factors — not technical architecture constraints.]

### Assumptions
[NEEDS CLARIFICATION: What are we assuming about users, the market, or dependencies that isn't explicitly confirmed?]

### Risks
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk description] | [High/Medium/Low] | [High/Medium/Low] | [How to prevent or handle] |

## Open Questions
[NEEDS CLARIFICATION: What requires more input before this PRD can be considered final?]

- [ ] [Question that needs stakeholder input]
- [ ] [Decision that needs to be made]
- [ ] [Information that needs to be gathered]

---

## Supporting Research

### Competitive Analysis
[NEEDS CLARIFICATION: How do competitors solve this problem? What can we learn from them?]

### User Research
[NEEDS CLARIFICATION: What user research has been done? Key findings?]

### Market Data
[NEEDS CLARIFICATION: Any relevant market size, trends, or data points?]