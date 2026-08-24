---
name: Low-Level Design (LLD)
description: Transform High-Level Design (HLD) into granular Low-Level Design (LLD) specifications.
version: 2.0
---

# Purpose

Define internal component structures, data schemas, class/struct definitions, API payload shapes, and algorithm pseudocode.

# Inputs
- `hld.md`
- `requirements.md`
- `tech-stack.md`

# Process
1. **database-designer**: Design entity relationships (ER diagram), table schemas, and state structs.
2. **api-designer**: Define precise REST request/response JSON payloads and WebSocket message schemas.
3. **component-designer**: Define UI component prop shapes, state stores, and utility functions.

# Output
`lld.md` containing:
- Component Specs & Class/Struct Schemas
- Data Schemas & State Models
- REST Endpoint Contracts & WebSocket Message Payload Shapes
- Algorithm & Financial Logic Pseudocode
- Error Handling & Edge Case Matrix
