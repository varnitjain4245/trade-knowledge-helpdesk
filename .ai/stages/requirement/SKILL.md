---
name: Requirement Analysis
description: Transform raw input into validated, implementation-ready requirements.
version: 2.0
---

# Purpose

Convert an incomplete idea, PRD, feature request, or bug report into a
complete set of implementation-ready requirements. This stage is the
source of truth for every downstream stage.

It must never produce architecture, code, or implementation details.

---

# Inputs

- Raw PRD, user description, feature request, or bug report.

---

# Process

Execute these skills in strict order:

1. **requirement-extractor** — Parse the input and extract every explicit
   requirement into `requirements.md` using structured IDs (FR-001, NFR-001, CON-001).
2. **ambiguity-detector** — Scan `requirements.md` for gaps, contradictions,
   undefined behavior, and missing edge cases. Produce `ambiguities.md`.
3. **question-generator** — Convert CRITICAL and HIGH ambiguities into
   targeted questions. Produce `questions.md`.

**Loop**: Present questions to the user. Incorporate answers. Re-run
ambiguity-detector. Repeat until no CRITICAL ambiguities remain or the
user explicitly accepts remaining assumptions.

---

# Outputs

All outputs are written to the project root or `.ai/artifacts/`:

| Artifact | Description |
|---|---|
| `requirements.md` | Structured functional, non-functional, and constraint requirements with unique IDs |
| `ambiguities.md` | Ranked ambiguity findings (CRITICAL/HIGH/MEDIUM/LOW) |
| `questions.md` | Targeted clarification questions with selectable options |
| `scope.md` | Explicit in-scope and out-of-scope boundaries |
| `assumptions.md` | All assumptions made during the process |
| `constraints.md` | Technical, business, and regulatory constraints |

---

# Success Criteria

Proceed to Architecture only when:

- Every functional requirement has acceptance criteria.
- Non-functional requirements have measurable targets.
- Zero CRITICAL ambiguities remain.
- Scope boundaries are explicitly documented.
- All assumptions are documented and accepted.

---

# Failure Handling

If requirements cannot be understood or critical information is missing:
**HALT** and request clarification from the user. Do not guess. Do not
proceed to Architecture with unresolved CRITICAL gaps.

---

# Constraints

- Never design architecture.
- Never choose technologies.
- Never generate code.
- Never estimate implementation effort.
- Never skip ambiguity detection.
- Prefer asking questions over making assumptions.
- Document every assumption explicitly.
