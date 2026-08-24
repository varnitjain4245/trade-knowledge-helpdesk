---
name: Implementation
description: Implement planned tasks into production-ready code, one task at a time.
version: 2.0
---

# Purpose

Transform implementation tasks into production-quality code. This stage
implements exactly ONE task at a time. Never implement multiple unrelated
tasks simultaneously.

---

# Inputs

| Artifact | Source | Required |
|---|---|---|
| `tasks.json` | Planning | Yes |
| Current Task (from build order) | Planning | Yes |
| `requirements.md` | Requirement Analysis | Yes |
| `architecture.md` | Architecture | Yes |
| `database.md` | Architecture | Yes |
| `apis.md` | Architecture | Yes |
| `tech-stack.md` | Architecture | Yes |
| Existing Codebase | Project | Yes |
| `review.md` | Review (feedback loop) | Only on retry |
| `test-report.md` | Testing (feedback loop) | Only on retry |

When `review.md` or `test-report.md` is present (feedback loop retry),
pass its findings directly to the code-generator as additional context
so it can address the specific issues without re-running the full
implementation-planner.

---

# Process

For each task in build order:

1. **context-loader** — Load only the relevant source files for this task.
   Output: `context.md`, `file-list.json`.
2. **implementation-planner** — Plan the exact changes: files to create/modify,
   functions to add, imports needed, risks. Output: `implementation-plan.md`.
3. **code-generator** — Write the code following the plan. Compile and verify.
   Output: source files + `implementation-report.md`.
4. **code-validator** — Validate: build passes, architecture respected, contracts
   honored. Output: `validation.md`.

If code-validator returns FAIL: run **code-fixer** with `validation.md`
as input, then re-run code-validator. Maximum 3 attempts before halting.

On feedback loop retries (when `review.md` or `test-report.md` is
present): skip context-loader and implementation-planner, and instead
run **code-fixer** directly with the feedback artifact, then re-run
code-validator.

After task completion, the **orchestrator** (not any skill) is
responsible for updating `tasks.json`: setting the task's status
to `done` or `failed`.

---

# Frontend UI Tasks

If the current task involves UI/frontend work, the code-generator MUST
load and strictly follow `.ai/skills/frontend-design/SKILL.md`. This is
not optional. The design skill defines the visual language, typography,
color palette, and signature element. Any UI code that ignores these
guidelines will be rejected in Review.

---

# Outputs

| Artifact | Description |
|---|---|
| Source code files | Created or modified project files |
| `implementation-report.md` | Files changed, build status, notes |
| `validation.md` | Build, architecture, and contract compliance results |
| Updated `tasks.json` | Task status set to `done` |

---

# Success Criteria

- Task completed per its definition of done.
- Project compiles with zero errors.
- Architecture is respected (no boundary violations).
- Coding standards followed.
- All existing tests still pass.

---

# Failure Handling

If a task cannot be implemented (missing context, architecture
contradiction, compilation failure after 3 attempts): mark the task
as `failed` in `tasks.json`, document the reason in
`implementation-report.md`, and report to the orchestrator.

---

# Constraints

- Never implement multiple unrelated tasks simultaneously.
- Reuse existing code and patterns.
- Never duplicate logic across files.
- Keep changes minimal and focused.
- Respect project conventions.
- Never ignore compilation errors.
- Do not proceed to Review until validation passes.
