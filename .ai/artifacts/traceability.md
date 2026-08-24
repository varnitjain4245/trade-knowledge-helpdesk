---
title: "Traceability Matrix — Smart Contact-Center Knowledge Platform"
stage: multi
scope: fullstack
version: "1.0"
---

# Traceability Matrix

Running table. Each stage fills only its own column. Never regenerated from scratch.

| Requirement ID | Requirement Summary | Priority | HLD Coverage | LLD Coverage | Code Coverage | Test Coverage |
|---|---|---|---|---|---|---|
| REQ-001 | Multilingual query understanding (6 launch languages, detection, cross-language retrieval) | Must | hld-backend.md#12-ai-components (§12.4 language handling), §13 + hld-frontend.md#9-internationalisation | lld-backend.md §6.1 step 2 (enablement gate), §4.3 Lang, §2.3 chunk_embedding [pass 1] + lld-frontend.md §19 (script tokens), §10 useEnabledLanguages
| REQ-002 | Knowledge ingestion (documents, ticket exports, portal pages, manual entries) | Must | hld-backend.md#7-ingestion-pipeline | lld-backend.md §2.3 (ingestion_job, source_document), §6.4, §7.4 [pass 1] + lld-frontend.md §7 F9, §14 (pre-transfer limit)
| REQ-003 | Automatic classification (sector, topic, authority, confidence, human override) | Must | hld-backend.md#7-ingestion-pipeline (classification job) | lld-backend.md §2.3 (taxonomy, item_classification), §4.2 [pass 1] + lld-frontend.md §7.5 ClassificationEditor
| REQ-004 | Cited answer generation (citation on every shown answer) | Must | hld-backend.md#6-answer-path--sequence, §12.2 + hld-frontend.md#7-data-fetching-real-time-and-error-semantics | lld-backend.md §6.1 steps 8-10, §4.3 (Citation DTO) [pass 1] + lld-frontend.md §7.2 CitationCard, §8 (non-empty citation tuple)
| REQ-005 | Answer confidence and no-answer behaviour | Must | hld-backend.md#123-confidence-honestly, §6 + hld-frontend.md#7 (no-answer as a first-class result) | lld-backend.md §6.1 steps 6-7, §4.6, §2.3 (threshold) [pass 1] + lld-frontend.md §15 (not-an-error category)
| REQ-006 | Agent assist console (in-conversation suggestions, ranking, feedback) | Must | hld-backend.md#5-component-architecture (Answer service), §16 + hld-frontend.md#5-routing, §8 | lld-backend-pass2.md §6.4 (sendReply), §4.1-4.2 [pass 2] + lld-frontend.md §7.3 AssistPanel, §7.4 ReplyComposer
| REQ-007 | Customer self-serve assistant (follow-ups, language switch, outcomes) | Must | hld-backend.md#5-component-architecture (Conversation service), §16 + hld-frontend.md#4-application-structure (assistant surface) | lld-backend-pass2.md §2.2 (four terminal states), §6.1 [pass 2] + lld-frontend.md §12-13
| REQ-008 | Handover with context (transcript, language, attempted answers) | Must | hld-backend.md#5-component-architecture (Conversation service) + hld-frontend.md#5-routing | lld-backend-pass2.md §6.2 (AssignmentEngine), §6.3 (buildContext), §2.3 presence/queue [pass 2] + lld-frontend.md §10 useHandover, §7 F5/F7
| REQ-009 | Knowledge curation console (review, correct, approve, retire, version) | Must | hld-backend.md#7-ingestion-pipeline, §8 + hld-frontend.md#4 (curation surface), §8 | lld-backend.md §2.3 (knowledge_item_version), §4.1 (If-Match), §7.1 [pass 1] + lld-frontend.md §7.6 LifecycleActions, §11 If-Match
| REQ-010 | Freshness and supersession control (stale vs retired, immediate effect) | Must | hld-backend.md#8-data-model (retirement invariant), §17 + hld-frontend.md#10-accessibility (staleness never colour-only) | lld-backend.md §2.2, §6.2, §7.3 (generation counter) [pass 1] + lld-frontend.md §9 (invalidation rule), §16
| REQ-011 | Feedback loop and gap queue (grouping, ranking, resolution types) | Must | hld-backend.md#5-component-architecture (Gap service), §17 + hld-frontend.md#4 (gaps feature) | lld-backend-pass3.md §6.1 (clustering), §6.2 (resolve), §2.2 [pass 3] + lld-frontend.md §25 F10
| REQ-012 | Supervisor analytics (deflection, handle time, quality, language mix, gaps) | Must | hld-backend.md#15-analytics + hld-frontend.md#4 (analytics feature), §6 | lld-backend-pass3.md §6.3 (period), §6.4 (guardrails), §2.2 analytics_daily [pass 3] + lld-frontend.md §7.7 GuardrailTile
| REQ-013 | Roles and access control (agent, knowledge manager, supervisor, administrator) | Must | hld-backend.md#11-authentication-and-authorisation + hld-frontend.md#5-routing (guards are UX only), §11 | lld-backend-pass3.md §4.3 (permission matrix), §6.7, §2.2 app_user [pass 3] + lld-frontend.md §21 (guards are UX only)
| REQ-014 | Audit trail (immutable record of knowledge changes and answers shown) | Must | hld-backend.md#18-audit-design | lld-backend-pass3.md §2.2 audit_record + REVOKE, §6.8 AuditRepository [pass 3]
| REQ-015 | Personal-data protection (masking before storage/reuse, deletion on request) | Must | hld-backend.md#19-privacy, §12.1 + hld-frontend.md#11-security | lld-backend-pass3.md §6.5 (Masker + withholding), §6.6 (deletion) [pass 3] + lld-frontend.md §21 (PII in telemetry)
| REQ-023 | Cold start, coverage gating and fair-use limiting on the public surface | Must | hld-backend.md#5-component-architecture (Coverage/fair-use gate), §21 + hld-frontend.md#7 (assist-unavailable and thin-knowledge states) | lld-backend.md §6.5 (CoverageGate), §6.1 step 1 [pass 1 — answering half] + lld-frontend.md §7 CoverageClosedNotice, §15
| REQ-016 | Ticket-history mining into proposed FAQ entries | Should | hld-backend.md#7-ingestion-pipeline (Phase 2) | Deferred — Phase 2, no LLD this phase
| REQ-017 | Scheduled portal re-crawl with change flagging | Should | hld-backend.md#17-scheduled-work (Phase 2) | Deferred — Phase 2, no LLD this phase
| REQ-018 | Cross-language answer comparison with per-language overrides | Should | Deferred to Phase 2 — no HLD coverage required this phase | Deferred — Phase 2, no LLD this phase
| REQ-019 | Bulk import and bulk re-classification | Should | hld-backend.md#7-ingestion-pipeline (queue accepts batches) | Deferred — Phase 2, no LLD this phase
| REQ-020 | Additional scheduled Indian languages | Could | Deferred to Phase 3 | Deferred — Phase 3
| REQ-021 | Messaging-channel access to the assistant | Could | Deferred to Phase 3 | Deferred — Phase 3
| REQ-022 | Proactive related-question suggestions | Could | Deferred to Phase 3 | Deferred — Phase 3
