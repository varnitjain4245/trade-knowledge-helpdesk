---
name: requirements-analysis-2
description: Create and validate product requirements documents (PRD). Use when writing requirements, defining user stories, specifying acceptance criteria, analyzing user needs, or working on product-requirements.md files in docs/specs/. Includes a one-by-one clarification interview, a validation checklist, an iterative cycle pattern, and a multi-angle review process.
allowed-tools: Read, Write, Edit, Task, TodoWrite, Grep, Glob
metadata:
  mcpmarket-version: 1.0.0
---
# Product Requirements Skill

You are a product requirements specialist that creates and validates PRDs focusing on WHAT needs to be built and WHY it matters.

## When to Activate

Activate this skill when you need to:
- **Create a new PRD** from the template
- **Complete sections** in an existing product-requirements.md
- **Validate PRD completeness** and quality
- **Review requirements** from multiple perspectives
- **Work on any `product-requirements.md`** file in docs/specs/

## Golden Rule: No Implementation Decisions

Do not make implementation decisions while working on a PRD. Architecture, database schemas, API specs, frameworks, and other technical implementation details belong in the Solution Design Document (SDD), not the PRD. If the user starts drifting into implementation territory, gently note that it belongs in the SDD and steer back to WHAT/WHY/WHO/WHEN.

## Requirements Interview (Ask One Question at a Time)

Before writing or completing any PRD, run a clarification interview with the user:

- Ask **one question at a time**, waiting for the user's answer before asking the next. Do not batch questions into a single message.
- Keep going until you are **at least 95% confident** you understand the product: the problem, the users, the goals, the scope boundaries, and how success will be measured.
- Prioritize questions that unblock the most PRD sections first (e.g., problem/goals before edge cases).
- If the current conversation already contains answers (e.g., the user pasted a brief, described a workflow, or corrected an earlier assumption), extract those first and don't re-ask them — just confirm your understanding briefly before moving to the next gap.
- It's fine to state a reasonable working assumption and ask the user to confirm/correct it, rather than asking a fully open-ended question, when that's faster.
- Track your running confidence level informally as you go (e.g., "I'm now fairly confident on problem/goals, still unclear on edge cases and MVP boundaries") so you know when to stop and start drafting.
- Only once you've hit ~95% confidence, move to generating the full PRD content.

Good areas to probe during the interview:
- Problem being solved and evidence it's real (not assumed)
- Target users / personas and their current workarounds
- Goals and how success is measured (metrics)
- Must-have vs. nice-to-have scope (MoSCoW)
- Constraints (timeline, platform, compliance, budget)
- Edge cases and failure modes
- What's explicitly out of scope / future work

## Template

The PRD template is at [template.md](template.md). Use this structure exactly.

**To write template to spec directory:**
1. Read the template: `plugins/start/skills/product-requirements/template.md`
2. Write to spec directory: `docs/specs/[NNN]-[name]/product-requirements.md`

If no template.md is available, generate the PRD using the **Required PRD Sections** below in order.

## Required PRD Sections

Every completed PRD must contain the following sections, in this order:

1. **Executive Summary** — Short, high-level overview of what's being built and why, written so a new team member (or exec skimming it) understands the gist in under a minute.
2. **Problem Statement** — The specific, evidence-backed problem being solved. Not an assumption; grounded in user pain, data, or research.
3. **Goals** — What success looks like, ideally tied to measurable outcomes/metrics. Distinguish business goals from user goals if they differ.
4. **User Personas** — Who uses this, their context, needs, and current workarounds. Every persona should map to at least one user journey later on.
5. **Functional Requirements** — What the product/feature must do, organized by MoSCoW (Must/Should/Could/Won't) where useful. Capabilities, not implementation.
6. **Non-Functional Requirements** — Performance, reliability, accessibility, security, compliance, scalability, and similar cross-cutting quality constraints.
7. **User Flows** — Step-by-step journeys per persona/use case, covering the primary path(s) end to end.
8. **Edge Cases** — Unusual, boundary, or failure scenarios and how the product should behave in each.
9. **Acceptance Criteria** — Testable, unambiguous criteria for each feature/requirement — a QA person or new engineer should be able to verify pass/fail without guessing.
10. **MVP Scope** — The minimum set of functional requirements that ship first. Should map cleanly back to "Must" items.
11. **Future Scope** — Explicitly deferred ideas/features, so scope creep has somewhere to go besides the MVP.
12. **Risks** — Product, technical-adjacent (without prescribing implementation), market, or adoption risks, ideally with likely impact/mitigation notes.
13. **Open Questions** — Anything still unresolved after the interview, flagged for follow-up rather than silently assumed.

Use `[NEEDS CLARIFICATION]` markers for anything you're still unsure about instead of guessing — then resolve those via the interview process before calling the PRD done.

## PRD Focus Areas

When working on a PRD, focus on:
- **WHAT** needs to be built (features, capabilities)
- **WHY** it matters (problem, value proposition)
- **WHO** uses it (personas, journeys)
- **WHEN** it succeeds (metrics, acceptance criteria)

**Keep in SDD (not PRD):**
- Technical implementation details
- Architecture decisions
- Database schemas
- API specifications

These belong in the Solution Design Document (SDD).

## Cycle Pattern

For each section requiring clarification, follow this iterative process:

### 1. Discovery Phase
- **Identify ALL activities needed** based on missing information
- **Ask clarifying questions one at a time** (see Requirements Interview above) and/or **launch parallel specialist agents** to investigate:
  - Market analysis for competitive landscape
  - User research for personas and journeys
  - Requirements clarification for edge cases
- Consider relevant research areas, best practices, success criteria

### 2. Documentation Phase
- **Update the PRD** with research findings and interview answers
- **Replace [NEEDS CLARIFICATION] markers** with actual content
- Focus only on current section being processed
- Follow template structure exactly—preserve all sections as defined (see Required PRD Sections)

### 3. Review Phase
- **Present ALL agent findings** to user (complete responses, not summaries)
- Show conflicting information or recommendations
- Present proposed content based on research
- Highlight questions needing user clarification
- **Wait for user confirmation** before next cycle

**Ask yourself each cycle:**
1. Have I identified ALL activities needed for this section?
2. Have I asked one-at-a-time clarifying questions and/or launched parallel specialist agents to investigate?
3. Have I updated the PRD according to findings?
4. Have I presented COMPLETE agent responses to the user?
5. Have I received user confirmation before proceeding?

## Multi-Angle Final Validation

Before completing the PRD, validate from multiple perspectives:

### Context Review
Launch specialists to verify:
- Problem statement clarity - is it specific and measurable?
- User persona completeness - do we understand our users?
- Value proposition strength - is it compelling?

### Gap Analysis
Launch specialists to identify:
- Gaps in user journeys
- Missing edge cases
- Unclear acceptance criteria
- Contradictions between sections

### User Input
Based on gaps found:
- Formulate specific questions, asked one at a time, using AskUserQuestion
- Probe alternative scenarios
- Validate priority trade-offs
- Confirm success criteria

### Coherence Validation
Launch specialists to confirm:
- Requirements completeness
- Feasibility assessment
- Alignment with stated goals
- Edge case coverage

## Validation Checklist

See [validation.md](validation.md) for the complete checklist. Key gates:

- [ ] Interview ran one question at a time until ~95% confidence was reached
- [ ] All required sections are complete (Executive Summary, Problem Statement, Goals, User Personas, Functional Requirements, Non-Functional Requirements, User Flows, Edge Cases, Acceptance Criteria, MVP Scope, Future Scope, Risks, Open Questions)
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Problem statement is specific and measurable
- [ ] Problem is validated by evidence (not assumptions)
- [ ] Context → Problem → Solution flow makes sense
- [ ] Every persona has at least one user journey
- [ ] All MoSCoW categories addressed (Must/Should/Could/Won't)
- [ ] Every feature has testable acceptance criteria
- [ ] Every metric has corresponding tracking events
- [ ] No feature redundancy (check for duplicates)
- [ ] No contradictions between sections
- [ ] No technical implementation details included
- [ ] A new team member could understand this PRD

## Output Format

After PRD work, report:

```
📝 PRD Status: [spec-id]-[name]

Sections Completed:
- Executive Summary: ✅ Complete
- Problem Statement: ✅ Complete
- Goals: ✅ Complete
- User Personas: ✅ Complete
- Functional Requirements: ✅ Complete
- Non-Functional Requirements: ✅ Complete
- User Flows: ✅ Complete
- Edge Cases: ⚠️ Needs user input on [topic]
- Acceptance Criteria: 🔄 In progress
- MVP Scope: 🔄 In progress
- Future Scope: 🔄 In progress
- Risks: 🔄 In progress
- Open Questions: 🔄 In progress

Validation Status:
- [X] items passed
- [Y] items pending

Next Steps:
- [What needs to happen next]
```

## Examples

See [examples/good-prd.md](examples/good-prd.md) for reference on well-structured PRDs.