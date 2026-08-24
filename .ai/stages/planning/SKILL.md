---
name: Planning
description: Convert the architecture into a deterministic, dependency-ordered implementation plan.
version: 2.0
---

# Purpose

Transform the approved architecture into an execution plan: what will
be built, in what order, and what depends on what. This stage never
writes production code.

---

# Inputs

| Artifact | Source |
|---|---|
| `architecture.md` | Architecture |
| `database.md` | Architecture |
| `apis.md` | Architecture |
| `tech-stack.md` | Architecture |
| `requirements.md` | Requirement Analysis |

---

# Process

Execute these skills in strict order:

1. **task-breakdown** — Decompose the architecture into independently
   completable development tasks. Output: `tasks.md` + `tasks.json`.
2. **dependency-planner** — Map task dependencies, detect cycles, compute
   topological build order. Output: `dependencies.md`.
3. **milestone-generator** — Group tasks into value-delivering milestones.
   Output: `milestones.md`.

---

# Outputs

| Artifact | Description |
|---|---|
| `tasks.md` | Human-readable task list with IDs, descriptions, and definitions of done |
| `tasks.json` | Machine-readable task list (see schema below) |
| `dependencies.md` | Dependency graph (Mermaid), build order, parallel groups |
| `milestones.md` | Milestones with task lists, deliverables, and validation criteria |

---

# tasks.json Schema

```json
{
  "tasks": [
    {
      "id": "TASK-001",
      "title": "string",
      "description": "string",
      "inputs": ["string"],
      "outputs": ["string"],
      "definition_of_done": ["string"],
      "complexity": "LOW | MEDIUM | HIGH",
      "category": "backend | frontend | database | infra | test",
      "dependencies": ["TASK-ID"],
      "status": "pending | in_progress | done | failed"
    }
  ]
}
```

---

# Success Criteria

- Every requirement is covered by at least one task.
- Zero circular dependencies.
- Every task has a measurable definition of done.
- Build order respects all dependencies.
- No task touches more than 5 files.

---

# Failure Handling

If the architecture has gaps that prevent task decomposition (e.g.,
undefined modules, missing API definitions): **HALT**, report the gap
to the orchestrator, and let the orchestrator request user guidance.

Do NOT silently loop back to Architecture.

---

# Constraints

- Never generate implementation code.
- Tasks must be independently completable.
- Tasks must be as small as possible.
- Prefer vertical slices (each task delivers testable functionality).
- Prefer many small tasks over few large ones.
