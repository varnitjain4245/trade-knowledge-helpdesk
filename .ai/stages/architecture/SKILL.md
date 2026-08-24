---
name: Architecture
description: Transform validated requirements into a complete software architecture with justified decisions.
version: 2.0
---

# Purpose

Design a scalable, maintainable, and production-ready software architecture.
Consume the artifacts produced by Requirement Analysis. Never generate
implementation code.

---

# Inputs

| Artifact | Source |
|---|---|
| `requirements.md` | Requirement Analysis |
| `constraints.md` | Requirement Analysis |
| `scope.md` | Requirement Analysis |
| `assumptions.md` | Requirement Analysis |

---

# Process

Execute these skills in strict order:

1. **architecture-designer** — Design the system architecture: components,
   boundaries, data flow, communication patterns. Output: `architecture.md`.
2. **tech-selector** — Evaluate and select the technology stack. Output: `tech-stack.md`.
3. **database-designer** — Design data models, relationships, indexes,
   and migration strategy. Output: `database.md`.
4. **api-designer** — Design all API endpoints, request/response schemas,
   and error codes. Output: `apis.md`.

If the project has a frontend/UI component, also load
`.ai/skills/frontend-design/SKILL.md` and incorporate the visual
language guidelines into `architecture.md`.

---

# Outputs

| Artifact | Description |
|---|---|
| `architecture.md` | System context diagram (Mermaid), component definitions, data flow, ADRs, trade-offs |
| `tech-stack.md` | Selected technologies with version and justification |
| `database.md` | ER diagram (Mermaid), table definitions, indexes, migration strategy |
| `apis.md` | Endpoint definitions grouped by resource, error format, versioning strategy |

---

# Success Criteria

- Every requirement is traceable to at least one component.
- Every architectural decision has a documented justification (ADR format).
- Trade-offs are explicitly documented.
- The architecture remains implementation-independent (no code).

---

# Failure Handling

If requirements are found to be incomplete or contradictory during
architecture design: **HALT**, document the gap in a `blocking-issues.md`
artifact, and report to the orchestrator. The orchestrator will decide
whether to request user clarification or fall back.

Do NOT silently loop back to Requirement Analysis.

---

# Constraints

- Never write implementation code.
- Never skip trade-off analysis.
- Prefer simplicity over cleverness.
- Every component must have a single, clear responsibility.
- Reuse existing technologies before introducing new ones.
