# PRD-to-Prod Workflow — LOCKED SKILL MODE (Default Agent Driver)

## Governing Rule

This workflow is the **sole and exclusive driver** of agent behavior for any feature request in this project. There is no other mode of operation. If the user asks to build, fix, add, or change a feature, this workflow runs — start to finish, stage by stage, using **only** the skills named below. No other skill, tool, or freeform approach may be substituted, blended in, or used as a fallback, regardless of how well-suited it might seem for the task at hand.

If a stage's locked skill cannot handle some part of the task, you do NOT reach for another skill to cover the gap. You HALT and report the limitation to the user. Silently substituting or supplementing with an unlisted skill is a violation of this workflow, not a helpful workaround.

---

## Scope Declaration (resolved at Stage 1, gates Stages 3 and 5)

Every feature entering this pipeline must be classified into exactly one scope before HLD begins, recorded as an explicit field in `requirements.md`:

`scope: backend | frontend | fullstack`

### How scope gets set:
1. If the user states it explicitly ("this is a backend-only change", "frontend only, API already exists", "full feature, both sides") — use that.
2. `prd-generator` MUST ask mandatory clarifying questions to confirm scope (`backend`, `frontend`, or `fullstack`), target behavior, edge cases, and constraints before finalizing `requirements.md`.

This field is a hard switch. Stage 3 (High-Level Design) and Stage 5 (Low-Level Design) each split into a backend sub-stage and a frontend sub-stage below; only the sub-stage(s) matching the declared scope may run. Getting scope wrong wastes an entire sub-stage's work, so do not guess past genuine ambiguity — ask once, then lock it. If a later stage discovers scope was wrong (e.g. Stage 5a discovers the backend change requires a UI change too), HALT and ask the user to explicitly confirm scope should change — never start running frontend skills unilaterally because it seemed necessary.

---

## Locked Skill Map (exhaustive — nothing else may run)

| Stage | Name | Runs When | Skill(s) — ONLY these, nothing else |
|---|---|---|---|
| 1 | Requirement Analysis | always | `prd-generator` |
| 2 | PRD Review | always | `prd-reviewing` |
| 3a | High-Level Design — Backend | scope = backend or fullstack | `backend-hld-architect` |
| 3b | High-Level Design — Frontend | scope = frontend or fullstack | `frontend-hld-designer` |
| 4 | HLD Review | always (reviews whichever of 3a/3b ran) | `hld-reviewer` |
| 5a | Low-Level Design — Backend | scope = backend or fullstack | `backend-lld-architect` |
| 5b | Low-Level Design — Frontend | scope = frontend or fullstack | `frontend-lld-designer` |
| 5c | LLD Consistency Pass | scope = fullstack only | no skill — orchestrator cross-checks API contract sections between 5a and 5b outputs; not a regeneration |
| 6 | LLD Review | always (reviews whichever of 5a/5b/5c ran) | `frontend-lld-review`, `lld-reviewer` — run only the side(s) matching scope: backend-only → `lld-reviewer` alone; frontend-only → `frontend-lld-review` alone; fullstack → both |
| 7 | Planning | always | `edited-plan-skill` |
| 8 | Implementation | always | `trading-platform-coding` |
| 9 | Code & Architecture Review | always | `code-reviewer` |
| 10 | QA Testing & Browser Validation | always | `full-stack-test-suite` |
| Multi | Traceability Matrix | incremental across pipeline | no skill — orchestrator-maintained running table (`traceability.md`); not a separate skill invocation |

Any skill folder that exists in `.ai/skills/` but is NOT listed above is **explicitly disabled for this workflow**. Their presence in `.ai/skills/` does not authorize their use here. They may exist for other purposes but must never be invoked by this workflow.

---

## Non-Negotiable Rules

1. **Skill lock is absolute.** Each stage may invoke only the skill(s) listed for it above. Not "primarily," not "mostly" — only.
2. **No silent skipping, no silent reuse.** Every stage is a hard gate. An artifact existing on disk is never itself approval — it must be shown to the user and explicitly approved this session before the workflow proceeds.
3. **No fabrication.** If a required input is missing, halt and state exactly what's missing. Never generate a stand-in or infer content to keep moving.
4. **No unauthorized jump-backs.** If a locked skill discovers a blocker mid-stage, halt and ask the user to explicitly confirm the next step. Never decide this unilaterally.
5. **No default entry-point guessing.** Only start at a stage other than 1 if the user explicitly names it this session.
6. **Verdict gates are hard-blocking.** A `CHANGES_REQUESTED` verdict cannot be worked around by proceeding anyway.
7. **This workflow is the only behavior.** The agent does not switch into generic assistant mode, general coding help, or ad hoc skill invocation for feature-development requests in this project. Every feature request routes through this pipeline.
8. **No unauthorized scope changes.** Scope, once set in Stage 1, does not silently change downstream — a scope change requires explicit user confirmation, same as a jump-back does.
9. **ZERO LAZINESS & ZERO SHORTCUTS POLICY ACROSS ALL STAGES:**
   - The agent MUST exhaustively analyze, think through, and document every stage without taking shortcuts, using placeholders, summarizing prematurely, or generating partial templates.
   - Speed or quick completion is strictly secondary to completeness and rigorous technical depth.
   - Any attempt to produce "high-level summaries" where detailed specs are required, or "sample code/scaffolds" instead of production-ready implementations, is a direct workflow violation.
   - This policy applies identically to every sub-stage (3a, 3b, 5a, 5b, 5c) — splitting a stage into sub-stages does not permit shallower output in either half; each sub-stage is held to full depth on its own.

---

## Approval Protocol (Interactive UI Mode)

At the completion of EACH AND EVERY gate (especially after generating or reviewing an artifact), the agent MUST use the **`ask_question` tool** to present an interactive UI modal with the following options. 

**DO NOT wait for text input in the chat.** You MUST invoke the `ask_question` tool (`is_multi_select: false`) with these exact options as the answers:

1. **APPROVE** — record stage complete; proceed to next stage.
2. **REJECT** — explicitly reject the artifact; halt the workflow or rollback.
3. **ITERATE** — fix issues or re-run current stage's locked skill(s) with stated changes.
4. **JUMP** — explicitly name target stage to jump to.
5. **CANCEL** — completely abort the workflow.

**ABSOLUTE MANDATORY RULE:** You must literally pop up the interactive UI using `ask_question`. If the user chooses anything other than APPROVE, you follow their selection. This ensures a strict, click-to-approve gating system for all stages.

This applies individually to 3a, 3b, 5a, and 5b as well — each sub-stage that actually runs gets its own `ask_question` gate. A fullstack feature does not get a single combined approval covering both backend and frontend design; it gets one gate per sub-stage that ran, plus one for the 5c consistency pass if applicable.

---

## Required Inputs Per Stage

| Stage | Requires | Produces |
|---|---|---|
| 1. Requirement Analysis | — (raw user input) | `requirements.md` (with scope field), `traceability.md` (initial table) |
| 2. PRD Review | `requirements.md` | `prd-review.md` |
| 3a. High-Level Design — Backend | `prd-review.md` (APPROVED), scope includes backend | `hld-backend.md`, `traceability.md` (updated) |
| 3b. High-Level Design — Frontend | `prd-review.md` (APPROVED), scope includes frontend | `hld-frontend.md`, `traceability.md` (updated) |
| 4. HLD Review | output of 3a and/or 3b (whichever ran), `tech-stack.md`, `requirements.md` (or `requirements.md` + `prd-review.md` if it exists) | `hld-review.md` |
| 5a. Low-Level Design — Backend | `hld-review.md` (APPROVED), scope includes backend | `lld-backend.md`, `traceability.md` (updated) |
| 5b. Low-Level Design — Frontend | `hld-review.md` (APPROVED), scope includes frontend | `lld-frontend.md`, `traceability.md` (updated) |
| 5c. LLD Consistency Pass | 5a and 5b both APPROVED, scope = fullstack | `lld.md` |
| 6. LLD Review | output of 5a/5b/5c (whichever ran), HLD output (`hld-backend.md` / `hld-frontend.md`, whichever exist per scope) | `lld-review.md` |
| 7. Planning | `lld-review.md` (APPROVED) | `planning.md`, `tasks.json` |
| 8. Implementation | `planning.md` / `tasks.json` (APPROVED) | Source Code, `traceability.md` (updated) |
| 9. Code & Architecture Review | Source Code, LLD output + `tasks.json` | `review.md` |
| 10. QA Testing & Browser Validation | `review.md` (APPROVED), `requirements.md`'s acceptance criteria section specifically | `test-report.md`, `browser-report.md`, `traceability.md` (updated) |
| Incremental | Artifact produced in stages 1, 3a/3b, 5a/5b, 8, 10 | `traceability.md` (appended per stage) |

"APPROVED" means explicitly approved this session via the UI Approval Protocol.

---

## Traceability Matrix Artifact (`.ai/artifacts/traceability.md`)

The traceability matrix is a single running table, NOT regenerated from scratch each stage, only appended to:

| Requirement ID | Requirement Summary | HLD Coverage | LLD Coverage | Code Coverage | Test Coverage |
|---|---|---|---|---|---|
| REQ-001 | ... | hld-backend.md#section-X | lld-backend.md#section-Y | src/services/X.ts | test-report.md#REQ-001 |

### Rules for this artifact:
- Stage 1 creates the table with Requirement ID + Summary columns populated, other columns empty.
- Each subsequent stage (3a/3b, 5a/5b, 8, 10) fills in ONLY its own column for rows it covers, using its own artifact as the source — it does not re-derive or re-check earlier columns.
- Before Stage 9 hands off to Stage 10, add one check (not a full skill invocation, similar in spirit to the existing 5c Consistency Pass) that scans `traceability.md` for any requirement row with a gap (an empty HLD/LLD/Code column despite the requirement being in scope) and HALTs with that gap listed if found, rather than letting it silently proceed to QA.
- This is the mechanism that gives you end-to-end "nothing missed" coverage cheaply — one scan of a table, instead of every reviewer re-reading the entire upstream chain from scratch.

---

## The 10-Stage Pipeline (Locked)

1. **Stage 1 — Requirement Analysis** (`requirements.md`)
   - *Skill*: `prd-generator` only.
   - *STRICT MANDATORY DIRECTIVE*: No shortcuts. The agent MUST ask clarifying questions to the user during this stage to flesh out functional/non-functional requirements, edge cases, user personas, failure modes, acceptance criteria, and exact scope (`backend` | `frontend` | `fullstack`). Generic or surface-level PRDs are forbidden.
   - This stage must also resolve and explicitly state the `scope` field (`backend` | `frontend` | `fullstack`) per the Scope Declaration section above.
   - *Gate*: HALT. Present `requirements.md`. Use `ask_question` tool for approval.

2. **Stage 2 — PRD Review** (`prd-review.md`)
   - *Skills*: `prd-reviewing` only.
   - *STRICT MANDATORY DIRECTIVE*: Exhaustively audit every requirement for ambiguities, missing edge cases, security flaws, and feasibility issues. Rubber-stamp reviews are strictly prohibited.
   - *Gate*: HALT. Present `prd-review.md`. Use `ask_question` tool for approval.

3. **Stage 3a — High-Level Design: Backend** (`hld-backend.md`)
   - Runs only if `scope` = `backend` or `fullstack`. If `scope` = `frontend`, this sub-stage is skipped entirely — do not run it "just in case."
   - *Skill*: `backend-hld-architect` only.
   - *STRICT MANDATORY DIRECTIVE*: Must map complete component hierarchies, system context, sequence diagrams, integration boundaries, and technology stacks for the backend. High-level hand-waving or skipping architectural diagrams is prohibited.
   - *Gate*: HALT. Present `hld-backend.md` & `tech-stack.md` (backend portion). Use `ask_question` tool for approval.

4. **Stage 3b — High-Level Design: Frontend** (`hld-frontend.md`)
   - Runs only if `scope` = `frontend` or `fullstack`. If `scope` = `backend`, this sub-stage is skipped entirely — do not run it "just in case."
   - *Skill*: `frontend-hld-designer` only.
   - *STRICT MANDATORY DIRECTIVE*: Must map complete component hierarchies, system context, sequence diagrams, integration boundaries, and technology stacks for the frontend. High-level hand-waving or skipping architectural diagrams is prohibited.
   - *Gate*: HALT. Present `hld-frontend.md` & `tech-stack.md` (frontend portion). Use `ask_question` tool for approval.

5. **Stage 4 — HLD Review** (`hld-review.md`)
   - *Skills*: `hld-reviewer` only.
   - Reviews whichever of 3a/3b actually ran, per scope. A backend-only run is reviewed on its backend HLD alone; do not flag a missing frontend HLD as a defect if scope was declared backend.
   - *STRICT MANDATORY DIRECTIVE*: Rigorously red-team the proposed system architecture for scalability bottlenecks, security gaps, and maintainability concerns. The reviewer must explicitly check each functional requirement in `requirements.md` maps to something in the HLD, and flag any requirement with no corresponding architectural coverage.
   - *Gate*: HALT. Present `hld-review.md`. Use `ask_question` tool for approval.

6. **Stage 5a — Low-Level Design: Backend** (`lld-backend.md`)
   - Runs only if `scope` = `backend` or `fullstack`.
   - *Skill*: `backend-lld-design` only.
   - *STRICT MANDATORY DIRECTIVE*: Must detail 100% of data models, DB schemas, exact API signatures, request/response bodies, state management patterns, and error handlers for the backend. No placeholder schemas or "TBD" parameters allowed.
   - *Gate*: HALT. Present `lld-backend.md`. Use `ask_question` tool for approval.

7. **Stage 5b — Low-Level Design: Frontend** (`lld-frontend.md`)
   - Runs only if `scope` = `frontend` or `fullstack`.
   - *Skill*: `frontend-lld-designer` only.
   - *STRICT MANDATORY DIRECTIVE*: Must detail 100% of component specs, state management, TypeScript models, and API contracts for the frontend. No placeholder schemas or "TBD" parameters allowed.
   - *Gate*: HALT. Present `lld-frontend.md`. Use `ask_question` tool for approval.

8. **Stage 5c — LLD Consistency Pass** (`lld.md`)
   - Runs only if `scope` = `fullstack`, after both 5a and 5b are individually APPROVED.
   - No locked skill runs here — this is the orchestrator cross-checking that the backend LLD's API specs and the frontend LLD's API Contracts section actually agree in shape. This is not a regeneration of either document and must not be treated as an excuse to shorten either one.
   - *Gate*: HALT. Present the consistency findings (agreements/discrepancies) as `lld.md`. Use `ask_question` tool for approval.

9. **Stage 6 — LLD Review** (`lld-review.md`)
   - *Skills*: `frontend-lld-review`, `lld-reviewer` only — run only the side(s) matching scope. Backend-only → `lld-reviewer` alone. Frontend-only → `frontend-lld-review` alone. Fullstack → both.
   - *STRICT MANDATORY DIRECTIVE*: Perform line-by-line verification of API definitions, state mutations, and data integrity. Every missing field or state edge case must be flagged. The reviewer must check the LLD doesn't drift from what the approved HLD specified.
   - *Gate*: HALT. Present `lld-review.md`. Use `ask_question` tool for approval.

10. **Stage 7 — Planning** (`planning.md`)
    - *Skill*: `edited-plan-skill` only.
    - *STRICT MANDATORY DIRECTIVE*: Construct complete, atomic, granular implementation tasks in `tasks.json` with clear dependencies and file targets. Broad or vague umbrella tasks are forbidden.
    - *Gate*: HALT. Present `planning.md`. Use `ask_question` tool for approval.

11. **Stage 8 — Implementation** (Source Code)
    - *Skill*: `trading-platform-coding` only.
    - *STRICT MANDATORY EXECUTION DIRECTIVES*:
      1. **No Short-cuts or Speed Rushing**: The agent MUST thoroughly inspect `lld.md` (or `lld-backend.md` / `lld-frontend.md`, whichever exist per scope), `hld.md`, and `tech-stack.md` before writing a single line of code. Rushing through implementation to trigger approval gates is strictly forbidden.
      2. **Complete & Rigorous Production Code First**: The agent MUST write 100% of all controllers, services, repositories, models, DTOs, configurations, and framework annotations (`@RestController`, `@RequestMapping`, `@PostMapping`, etc.) up-front. Partial, sample, or unannotated code scaffolds are strictly prohibited.
      3. **Quality Over Velocity**: The goal is to deliver complete, production-ready, fully functional software. Speed or pipeline progression is NEVER a justification for incomplete code.
    - *Gate*: HALT. Verify that every task in `tasks.json` has its full, annotated source files written. Present a comprehensive summary of all created files with clickable file links. Use `ask_question` tool for approval.

12. **Stage 9 — Code & Architecture Review** (`review.md`)
    - *Skill*: `code-reviewer` only.
    - *STRICT MANDATORY DIRECTIVE*: Thoroughly inspect all written source files for bug risks, memory leaks, missing error handling, and style violations. Must reject code containing stubs or placeholders. The reviewer must check implementation actually matches the LLD's API signatures/schemas and that every task in `tasks.json` has corresponding code.
    - *Gate*: HALT. Before presenting `review.md` for approval, scan `traceability.md` for any Requirement ID that is in-scope (per the declared scope field) but has an empty HLD, LLD, or Code Coverage column. If any gap is found, HALT and present the specific gap(s) via `ask_question` instead of presenting `review.md` — do not proceed to the standard Stage 9 approval gate until this scan passes clean. If changes are requested, route back to Stage 8. Use `ask_question` tool for approval.

13. **Stage 10 — QA Testing & Browser Validation** (`test-report.md`)
    - *Skill*: `full-stack-test-suite` only.
    - *STRICT MANDATORY DIRECTIVE*: Execute comprehensive automated tests and browser checks. Fake test reports or skipped edge-case validations are strictly prohibited. The QA skill must test against those acceptance criteria explicitly, not just general functionality.
    - *Gate*: HALT. Use `ask_question` tool for approval.

---

## Dependency Update Note

If upstream artifacts change after downstream stages were approved, all downstream stages are immediately marked UNVERIFIED and must be re-approved through the UI Approval Protocol before continuing. For fullstack features, a change to 5a (backend LLD) also marks the 5c Consistency Pass and Stage 6 review UNVERIFIED, even if 5b (frontend LLD) itself did not change. If `requirements.md` changes, `traceability.md`'s requirement rows must be reconciled (new/changed/removed requirement IDs), not just downstream artifacts marked stale.

---

## Antigravity Hook Guards

This workflow is protected by deterministic Antigravity 2.0 hooks (`.agents/hooks.json`). These hooks enforce workflow rules at runtime — the agent **cannot** violate stage ordering, artifact integrity, or approval gates even if the LLM drifts.

| Hook | Script | Purpose |
|---|---|---|
| **PreToolUse** | `hooks/pre-tool.js` | Blocks invalid writes before execution (JSON validity, schema compliance, artifact ownership, status transitions) |
| **PostToolUse** | `hooks/post-tool.js` | Updates artifact metadata, generates checksums, cascades staleness to downstream artifacts after writes |
| **Stop** | `hooks/stop.js` | Prevents premature workflow termination by verifying artifacts exist, no staleness, and current stage is approved |

### HOOK UPDATE REQUIRED:
`pre-tool.js`, `post-tool.js`, and `stop.js` must validate against sub-stage keys `3a`, `3b`, `5a`, `5b`, `5c` and the `scope` field, so that:
- A skipped sub-stage (e.g. `3b` on a backend-only run) is not flagged as a missing/stale artifact.
- `stop.js` does not block workflow termination waiting for an artifact that scope correctly says should never be produced.
- `post-tool.js`'s staleness cascade correctly propagates from `5a` into `5c` and Stage 6, and from `5b` into `5c` and Stage 6, per the Dependency Update Note above.
- `post-tool.js` should also update `traceability.md`'s relevant column when a stage artifact is written, using the same pattern as its existing artifact-metadata update logic.

---

## Artifact Versioning

Every artifact automatically maintains: `version`, `createdAt`, `updatedAt`, `stage`, `status`, `checksum` (SHA-256), `lastModifiedBySkill`, `approvalStatus`. This metadata is stored in `.ai/state/workflow-state.json`. This includes a `scope` field at the top level of the state file, and a `subStage` field per artifact where applicable (e.g. `"5a"`, `"5b"`, `"5c"`).

---

## Dependency Cascade

If an upstream artifact changes (e.g., `requirements.md` is regenerated), all downstream artifacts (`prd-review.md` → `hld.md` → … → `test-report.md`) are automatically marked STALE. Stale artifacts are never deleted — they must be regenerated and re-approved. If `requirements.md` is regenerated and its `scope` field changes, this cascade also applies retroactively to whichever sub-stages (`3a`/`3b`, `5a`/`5b`) newly become in-scope or newly become out-of-scope — an out-of-scope sub-stage's prior artifact (if one exists from before the scope change) is marked STALE, not deleted, and must not be silently reused if scope later reverts. `traceability.md` updates are cumulative and never deleted, consistent with the existing "stale artifacts are never deleted" rule already in that section.

---

## Structured Logging

All hook decisions are logged to `hooks/logs/hook-events.jsonl` with: `timestamp`, `hook`, `stage`, `skill`, `artifact`, `action`, `decision`, `reason`, `duration`. Log entries include a `subStage` field (`null` for non-split stages) and a `scope` field.

These hooks enforce — not replace — the workflow rules above. See `hooks/` for implementation.
