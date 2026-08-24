---
name: High-Level Design (HLD)
description: Transform validated requirements into a complete High-Level Design (HLD) document.
version: 2.0
---

# Purpose

Design system context, macro-architecture, component boundaries, domain models, and architectural decisions (ADRs).

# Inputs
- `requirements.md`
- `scope.md`
- `constraints.md`

# Process
1. **architecture-designer**: Produce system context diagram (Mermaid) and subsystem boundaries.
2. **tech-selector**: Select frameworks, data stores, and communication protocols.
3. **frontend-design**: Establish design system guidelines, visual identity, and layout concepts.

# Output
`hld.md` containing:
- Executive Summary & System Overview
- System Context Diagram (Mermaid)
- Subsystem & Service Boundaries
- Technology Stack Selection & Justifications
- Architectural Decision Records (ADRs)
- Non-Functional & Security Guarantees
