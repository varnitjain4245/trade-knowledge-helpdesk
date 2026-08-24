# PRD Validation Checklist

Use this checklist to validate PRD completeness before proceeding to a technical/solution design document (SDD).

## Structure Validation

- [ ] **All required sections are complete** - No empty or placeholder sections
- [ ] **No [NEEDS CLARIFICATION] markers remain** - All markers replaced with content
- [ ] **Template structure preserved** - No sections added, removed, or reorganized
- [ ] **Every section that maps to another is consistent** - MVP Scope ↔ Must Have Features, Future Scope ↔ Should/Could Have, Out of Scope ↔ Won't Have (see Cross-Section Consistency below)
- [ ] **Domain Invariants Gate was run** - The 5-8 domain table-stakes items were listed (see SKILL.md), and each has either a requirement/NFR or an explicit Out-of-Scope entry with a stated reason
- [ ] **Engineering Digest is populated and accurate** - Features, hard numbers, and blockers listed there match the detailed sections; no persuasive narrative leaked into it

## Content Quality

### Executive Summary
- [ ] **Stands alone** - A reader who only reads this section understands what's being built, for whom, and why
- [ ] **Consistent with the rest of the document** - No claim here contradicts Problem Statement, Goals, or MVP Scope

### Problem Definition
- [ ] **Problem statement is specific and measurable** - Clear metrics for problem impact
- [ ] **Problem is validated by evidence** - Data, user research, or market analysis (not assumptions)
- [ ] **Context → Problem → Why Now flow makes sense** - Logical narrative
- [ ] **Problem passes the Reality-Check Gate** - demand reality, status quo, desperate specificity, narrowest wedge, direct observation, and future-fit have each been addressed, or explicitly logged as an Assumption/Open Question if unresolved (see SKILL.md → "Reality-Check Gate")
- [ ] **Goals are qualitative, Success Metrics are quantitative** - No numeric target hiding in Goals; no vague aspiration hiding in Success Metrics

### Stakeholders
- [ ] **Every stakeholder has a stated interest** - Not just a name/role with no "why they're listed"
- [ ] **Approval requirements are explicit** - Clear who must sign off before this PRD is final

### User Understanding
- [ ] **Every persona has demographics** - Age, role, technical expertise
- [ ] **Every persona has goals** - What success looks like for them
- [ ] **Every persona has pain points** - Current frustrations
- [ ] **Every persona has formal user stories** - "As a [persona], I want [action], so that [benefit]" format, not prose
- [ ] **Every persona has at least one user flow** - End-to-end, not just a story

### User Flow Rigor
- [ ] **Every flow has a trigger and preconditions** - Clear on what starts it and what must already be true
- [ ] **Every flow has a happy path with numbered steps** - Written as user action → system response
- [ ] **Every flow has at least one alternate/branch path** - Not just the ideal case
- [ ] **Every flow has at least one error/exception path** - What happens when something goes wrong, and how the user recovers
- [ ] **Every flow states its postcondition/success state** - Clear definition of "done"
- [ ] **Flows are written in plain, user-facing language** - No UI component names, no system-internals language

### Requirements Quality
- [ ] **All MoSCoW categories addressed** - Must/Should/Could/Won't all defined
- [ ] **Every feature has a formal user story** - As a [user], I want [action] so that [benefit]
- [ ] **Every feature has testable acceptance criteria (EARS format)** - Specific, verifiable conditions
- [ ] **No Must-Have feature depends on an unresolved Open Question** - Either answered, downgraded to Should-Have, or marked BLOCKING with an owner and date
- [ ] **No feature redundancy** - Check for duplicates or overlapping features
- [ ] **No duplication across Acceptance Criteria, Business Rules, and User Flows** - Each requirement has one source of truth; other sections reference it rather than restate it
- [ ] **No contradictions between sections** - Consistent throughout
- [ ] **Non-Functional Requirements are outcome-based** - Performance/reliability/security/scalability described as user-observable targets, never as a named technology or mechanism
- [ ] **Every NFR number has a stated basis** - Or carries the `[PROPOSED: pending eng confirmation]` marker; no invented numbers presented as settled

### Success Criteria
- [ ] **KPIs defined for adoption** - User acquisition/activation targets
- [ ] **KPIs defined for engagement** - Usage frequency/depth targets
- [ ] **KPIs defined for quality** - Error rate, satisfaction targets
- [ ] **KPIs defined for business impact** - Revenue, retention targets
- [ ] **Every metric has corresponding tracking events** - How to measure
- [ ] **Metric-to-event coverage is evidenced, not asserted** - The mapping table is actually printed with a row for every metric; a ticked box with no table behind it fails this gate

### Timeline & Roadmap
- [ ] **Phases/milestones are described by what ships, not how it's engineered** - No sprint numbers, no build-order detail
- [ ] **Sequencing is consistent with MVP Scope / Future Scope** - Phase 1 shouldn't include a Future Scope item, and vice versa

### Estimation Blockers
- [ ] **Section exists and reflects reality** - Every item an engineering lead couldn't size is listed, with a reason, an owner, and a target date
- [ ] **No blocker is silently absent** - Cross-check against Open Questions, Stakeholders, and Detailed Feature Specifications for anything with no clear owner or an unbounded scope (e.g., an ongoing maintenance obligation) that isn't captured here

### Constraints & Risks
- [ ] **Constraints identified** - Budget, timeline, legal/compliance (not technical architecture)
- [ ] **Assumptions documented** - Explicit about what we're assuming
- [ ] **Risks identified with mitigations** - What could go wrong and how to handle it, with impact and likelihood rated

## Boundary Validation (Tech-Agnostic Gate)

- [ ] **No technical implementation details included** - No code, architecture, database, or infrastructure design
- [ ] **No API specifications** - Belongs in the SDD
- [ ] **No named technologies, frameworks, or vendors anywhere** - Including inside Non-Functional Requirements and Detailed Feature Specifications, where technical language most often leaks in
- [ ] **Focus on WHAT and WHY, not HOW** - Business and user requirements only

> Note: this gate applies to the document only. Tech-stack recommendations given conversationally in chat (e.g., because the user asked "what would you build this with?") are fine and don't need to be scrubbed from the conversation — they just must never be written into the PRD itself.

## Clarity Validation

- [ ] **A new team member could understand this PRD** - Self-contained and clear
- [ ] **Jargon is defined** - Domain terms explained
- [ ] **Acronyms are expanded** - First use includes full form

## Cross-Section Consistency

Run these checks across the entire document:
- [ ] **User personas match user flows** - All personas have at least one flow
- [ ] **Features align with user goals** - Each feature maps to a persona goal or a stated Product Goal
- [ ] **Metrics map to features** - Success measured for key features
- [ ] **Risks relate to requirements** - Identified risks are relevant
- [ ] **A feature appears in exactly one of: MVP Scope, Future Scope, Out of Scope** - Never zero, never two
- [ ] **Stakeholders' interests are reflected somewhere in Goals, Risks, or Success Metrics** - No stakeholder listed with no visible influence on the document

## Completion Criteria

✅ **PRD is complete when:**
- All checklist items pass
- User has reviewed and approved content
- No open questions remain unresolved (or are explicitly deferred with an owner and date)
- Ready for technical specification (SDD)