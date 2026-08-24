---
title: "Smart Contact-Center Knowledge Platform for Commerce & Industry (SIH)"
status: draft
version: "1.1"
stage: 1
scope: fullstack
skill: prd-generator
---

# Product Requirements Document

> **Tech-Agnostic Rule:** This document describes WHAT users need and WHY — never HOW it is built.

## Validation Checklist

### CRITICAL GATES (Must Pass)

- [x] All required sections are complete
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Domain Invariants Gate has been run (see Supporting Research → Domain Invariants) and every table-stakes item has a feature/NFR or an explicit Out-of-Scope entry with a reason
- [x] No Must-Have feature's acceptance criteria depend on an unresolved Open Question (see Engineering Digest → Must-Haves with unresolved dependencies)
- [x] Problem statement is specific and measurable
- [x] Every feature has testable acceptance criteria (EARS format)
- [x] Every primary user flow has a happy path, at least one alternate/branch path, and at least one error path
- [x] No contradictions between sections; requirements live in exactly one source section and are cross-referenced elsewhere
- [x] No technology, architecture, or implementation detail anywhere in the document

### QUALITY CHECKS (Should Pass)

- [x] Problem is validated by evidence where evidence exists; unverified items are logged as Assumptions and Open Questions
- [x] Context → Problem → Solution flow makes sense
- [x] Every persona has at least one user flow
- [x] MVP Scope, Future Scope, and Out of Scope are mutually exclusive
- [x] Every Non-Functional Requirement number has a stated basis or a `[PROPOSED: pending eng confirmation]` marker
- [x] Every metric has corresponding tracking events, evidenced by the metric-to-event mapping table
- [x] No feature redundancy
- [x] Engineering Digest is populated and matches the detailed sections it summarizes
- [x] A new team member could understand this PRD without asking what a term means

---

## Engineering Digest

**Features at a glance (Must Have — MVP):**

| ID | Feature | One-line description |
|---|---|---|
| REQ-001 | Multilingual query understanding | Accepts a query typed in any of the six launch languages and resolves it to the same knowledge regardless of the language it was asked in. |
| REQ-002 | Knowledge ingestion | Takes in documents, resolved ticket history, portal pages and hand-written FAQ entries, and makes their content answerable. |
| REQ-003 | Automatic classification | Files every ingested item under a sector, a topic and an issuing authority, with a confidence value and a human override. |
| REQ-004 | Cited answer generation | Returns a short answer plus the exact passage and source it came from; an answer with no citation is never shown. |
| REQ-005 | Answer confidence & no-answer behaviour | Below the confidence bar, the system says it does not know and routes onward instead of guessing. |
| REQ-006 | Agent assist console | Shows the agent suggested answers, citations and a copy-into-reply action while the customer conversation is open. |
| REQ-007 | Customer self-serve assistant | Lets a customer ask in their own language and get a cited answer, with a one-step handover to a human. |
| REQ-008 | Handover with context | Carries the full customer conversation, detected language and attempted answers to the receiving agent. |
| REQ-009 | Knowledge curation console | Lets a knowledge manager review, correct, approve, retire and re-classify knowledge items. |
| REQ-010 | Freshness & supersession control | Marks knowledge past its review date as stale and suppresses answers from retired or superseded items. |
| REQ-011 | Feedback loop & gap queue | Turns agent/customer feedback and unanswered queries into a ranked queue of knowledge gaps. |
| REQ-012 | Supervisor analytics | Reports deflection, resolution time, answer quality, language mix and top unanswered topics over a chosen period. |
| REQ-013 | Roles & access control | Restricts every action to the roles entitled to it, across four defined roles. |
| REQ-014 | Audit trail | Records who changed what knowledge, when, and what the customer was ultimately told. |
| REQ-015 | Personal-data protection | Detects and masks personal identifiers before conversation content is stored or reused as knowledge, at a measured recall bar. |
| REQ-023 | Cold start, coverage gating and fair use | Keeps the public assistant closed until a declared coverage floor is met, and limits abusive volume on the public surface without ever removing the path to a human. |

**Decision thresholds (all launch-tunable, see Decision Thresholds section):** answer bar 0.70 · classification bar 0.60 per field · low-volume warning under 100 conversations · gap group-size 5 queries. Every one is `[PROPOSED: pending eng confirmation]`.

**Features at a glance (Should Have — Phase 2):**

| ID | Feature | One-line description |
|---|---|---|
| REQ-016 | Ticket-history mining | Turns clusters of resolved tickets into proposed FAQ entries for a knowledge manager to approve. |
| REQ-017 | Scheduled portal re-crawl | Re-checks registered government portal pages on a schedule and flags changed pages for review. |
| REQ-018 | Answer comparison across languages | Shows a manager the same answer rendered in each supported language, side by side, for verification. |
| REQ-019 | Bulk import & bulk re-classification | Handles large document batches and mass corrections in one operation. |

**Features at a glance (Could Have — Phase 3):**

| ID | Feature | One-line description |
|---|---|---|
| REQ-020 | Additional scheduled languages | Extends support to the remaining scheduled Indian languages beyond the launch six. |
| REQ-021 | Messaging-channel access | Makes the self-serve assistant reachable from a consumer messaging channel. |
| REQ-022 | Proactive answer suggestions | Suggests likely follow-up questions before the customer asks them. |

**Hard numbers:**

| Target | Value | Sourcing |
|---|---|---|
| Agent-assist suggestion appears after query submission | ≤ 5 s at the 95th percentile | Based on the persona tolerance stated in the Support Agent persona — an agent will abandon a suggestion tool if it is slower than searching a document themselves. `[PROPOSED: pending eng confirmation]` |
| Self-serve answer returned to customer | ≤ 8 s at the 95th percentile | Chat-abandonment tolerance is higher than an agent's because the customer is not being timed. `[PROPOSED: pending eng confirmation]` |
| Document available for answering after upload | ≤ 15 min for items up to 200 pages | Derived from the knowledge manager's stated working pattern of uploading a circular then testing it in the same sitting. `[PROPOSED: pending eng confirmation]` |
| Concurrent live conversations supported | 200 concurrent, 50 agents | Derived from the demonstration deployment size stated in Constraints. `[PROPOSED: pending eng confirmation]` |
| Availability during published support hours | 99.5% | `[PROPOSED: pending eng confirmation]` |
| Citation coverage | 100% of shown answers | Hard requirement from the "every answer must cite a source" constraint — not a tunable target. |
| Answer correctness on the acceptance question set | ≥ 85% judged correct-and-cited | `[PROPOSED: pending eng confirmation]` — the acceptance question set is defined in Success Metrics. |
| Wrong-answer (confidently incorrect) rate | ≤ 2% of shown answers | `[PROPOSED: pending eng confirmation]` |
| Deflection rate at 90 days | ≥ 30% of self-serve conversations closed without a human | `[PROPOSED: pending eng confirmation]` |
| Knowledge review interval | 180 days before an item is marked stale | Matches the typical validity window of a trade circular before amendment. `[PROPOSED: pending eng confirmation]` |
| Launch languages | 6 target (English, Hindi, Bengali, Tamil, Telugu, Marathi); English + Hindi guaranteed, remaining four gated on clearing 85% each | Largest-speaker subset covering the majority of the target base; per-language gate resolves the launch-scope question rather than promising six unconditionally (REQ-001, R-1). |
| Personal-identifier masking recall | ≥ 98% on a held-out sample | `[PROPOSED: pending eng confirmation]` — the highest-consequence failure in the document needed a measurable bar. |
| Conversation transcript retention | 12 months | `[PROPOSED: pending eng confirmation]` — paired with audit retention so deletion-on-request is defined in practice (OQ-4). |
| Self-serve inactivity boundary (abandoned) | 15 minutes | `[PROPOSED: pending eng confirmation]` |
| Fair-use limit, unidentified customer | 30 queries per hour | `[PROPOSED: pending eng confirmation]` |
| Language parity guardrail | No enabled language more than 10 points below English correctness | `[PROPOSED: pending eng confirmation]` |

**Must-Haves with unresolved dependencies:** None. Every Must-Have's acceptance criteria are answerable from this document. The two `BLOCKING` open questions (OQ-1, OQ-2) affect Should-Have features and deployment sizing, not Must-Have behaviour.

**Estimation Blockers (see full section below):** Five — corpus size and quality unknown, no confirmed source list for portal crawling, translation-quality acceptance criteria not yet owned, no confirmed volume baseline for deflection measurement, and the ongoing knowledge-maintenance obligation is unstaffed.

---

## Revision Note (v1.1)

This version answers Stage 2's review (`prd-review.md` v1.0). Changes: the four decision thresholds now have starting values, bases and owners (new Decision Thresholds section); REQ-001 replaces its unconditional six-language promise with a per-language enablement gate, resolving the contradiction with Risk R-1; REQ-014 now records the reply an agent actually sent, not only the suggestion shown; a new Must-Have REQ-023 covers cold start, coverage gating and fair use on the public surface; REQ-007 gains an "abandoned" outcome; REQ-015 gains a masking-recall bar and deletion semantics; guardrail metrics are added; the NFR cost constraint is restated as an outcome covering data control; and the timeline drops week-level precision it had not earned. Minor gaps in REQ-002, REQ-009, REQ-012 and REQ-013 are closed. Total Must-Have count is now 16 (REQ-001 to REQ-015 plus REQ-023).

## Executive Summary

Businesses dealing with India's commerce and industry administration — exporters, importers, MSMEs, customs brokers, and the officers who support them — get their answers today from contact-center agents who must hunt through scattered circulars, notifications, tariff schedules and past ticket threads while a caller waits. This product gives that contact center a single searchable body of knowledge that a machine reads, files by sector and topic, and answers from in the user's own language, always quoting the source passage it used. Support agents get a suggested, cited answer inside the conversation; customers get a self-serve assistant that hands over cleanly to a human when it cannot help; knowledge managers get a queue of what the system could not answer; supervisors get evidence of whether any of it worked. It matters because the cost of a wrong answer in this domain is not a bad experience — it is a shipment held at a port or a benefit claimed incorrectly, and today nothing in the process makes the basis of an answer visible.

## Problem Statement

### Context

A commerce-and-industry contact center answers queries from businesses about export-import procedure, licensing and registration, tariff and duty classification, incentive and subsidy schemes, standards and quality compliance, and grievance status. The knowledge those answers depend on is issued continuously by multiple authorities, in the form of circulars, notifications, public notices, tariff schedules, scheme guidelines and portal help pages. It arrives as documents, not as answers. Agents assemble the answer themselves, per call, from whatever they can find and whatever they remember.

The people asking are frequently not comfortable in English. The people answering are trained on a subset of the domain and rotate.

### Problem

Four specific failures follow from that setup, and this product exists to address them:

1. **Answers are reconstructed from scratch on every contact.** The same question is researched repeatedly by different agents, and the effort does not accumulate anywhere. Handle time is spent on retrieval, not on the customer.
2. **Answers cannot be traced to their basis.** A caller told "you need a licence for that" cannot be told which notification says so. Neither can the agent's supervisor, later, when the answer turns out to be wrong. Nothing in the current process forces the source to travel with the answer.
3. **Superseded knowledge stays in circulation.** When a circular is amended, the old understanding survives in agents' memory, in old ticket threads and in shared documents. There is no moment at which the old answer stops being given.
4. **Language is a hard filter on who gets a usable answer.** A business owner who works in Tamil or Bengali either finds an agent who shares the language, accepts a worse answer in English, or gives up.

The consequences are unequal service, avoidable escalations, and — in a domain of licences, duties and deadlines — costly downstream errors from confidently wrong answers.

**Evidence status.** These four failure modes are drawn from the problem statement issued for this project and from the publicly observable structure of the source material (multiple issuing authorities, frequent amendment, document-first publication). They have **not** been validated against this contact center's own ticket data, because that data has not been provided. That gap is logged as Assumption A-1 and Open Question OQ-1 rather than presented as measured fact. Every baseline figure in Success Metrics is therefore a target to be set against a measured baseline in the first two weeks of operation, not a claimed improvement over a known number.

### Why Now

Three things have changed at once. Machine translation and question-answering across Indian languages are now good enough, in freely available form, to be usable without a per-query commercial dependency — which is what makes a multilingual system affordable for a government-facing service at all. Publication of commerce and trade material has largely moved online, so the corpus is reachable in bulk rather than on paper. And the volume of businesses interacting with these processes continues to grow, which makes per-contact manual research scale badly in exactly the way an accumulating knowledge base does not.

Delaying does not make the corpus smaller; it makes the backlog of unindexed amendments larger.

## Goals

### Product Goals

- Make every answer given by the contact center traceable to the passage it came from, so the answer can be checked rather than trusted.
- Make an answer researched once available to every agent and every customer thereafter, in every supported language.
- Make the system's ignorance visible: when it does not know, it says so and routes onward, and the gap enters a queue someone owns.
- Let a business get a usable answer in the language it actually works in.
- Give knowledge managers a way to retire wrong or superseded knowledge that actually takes it out of circulation.
- Give supervisors evidence about coverage and quality that is derived from what the system did, not from self-report.

### Non-Goals

- Not aiming to remove human agents from the service. The target is faster and better-sourced human answers, plus deflection of the genuinely routine.
- Not aiming to be the authoritative publisher of commerce policy. The issuing authorities remain authoritative; this system points at their material.
- Not aiming to give legal advice or a binding determination on classification, duty liability or eligibility. It reports what published material says.
- Not aiming to replace the ticketing, telephony or CRM systems the contact center already runs.
- Not aiming for exhaustive coverage of every scheduled language at launch.

## Stakeholders

| Stakeholder | Role | Interest / Stake | Approval Needed? |
|---|---|---|---|
| Ministry of Commerce & Industry sponsor | Product sponsor | Service quality and reach of the public-facing helpdesk; demonstrable answer traceability | Yes |
| Contact-center operations head | Operational owner | Handle time, escalation volume, agent ramp-up time, staffing | Yes |
| Knowledge management lead | Content owner | Accuracy and freshness of published knowledge; owns the correction queue | Yes |
| Support agents (represented by team leads) | Primary users | Whether the assist is faster than their current method; whether it is right | No — but adoption depends on them |
| Businesses / trade public | End users | Getting a correct, understandable answer in their own language | No |
| Data protection / compliance reviewer | Gatekeeper | Handling of personal data in conversations and stored knowledge | Yes |
| Evaluation panel (SIH) | Assessor | Working demonstration against the stated problem within the event timeframe | Yes |

## User Personas

### Primary Persona: Support Agent ("Anjali")

- **Demographics:** 23–35, contact-center agent, 6 months to 3 years tenure, comfortable with web tools, not a domain specialist, handles 40–70 contacts a day across chat and voice, typically fluent in English, Hindi and one regional language.
- **Goals:** Answer correctly on the first contact, without putting the customer on hold to search; avoid being the person who gave the wrong duty rate; get through the queue.
- **Pain Points:** Searching several document sets while a customer waits; not knowing whether the document she found is still current; being unable to help a caller in a language she does not speak; re-researching a question a colleague answered last week.
- **Formal User Stories:**
  - As a support agent, I want a suggested answer with its source passage while the conversation is open, so that I can reply without leaving the conversation to search.
  - As a support agent, I want to see how confident the system is and what it is unsure about, so that I know when to verify before replying.
  - As a support agent, I want to mark a suggestion as wrong, so that the next agent does not repeat my mistake.
  - As a support agent, I want a customer's earlier self-serve conversation handed to me with its context, so that I do not make the customer repeat themselves.

### Secondary Persona: Business Customer ("Ravi")

- **Demographics:** 28–55, proprietor or staff of an MSME/exporter/customs broker, variable digital literacy, often more fluent in a regional language than in English, contacts the helpdesk a few times a year around a specific transaction or deadline.
- **Goals:** Find out what he must do, by when, and on what basis; avoid a penalty or a held consignment; resolve it without waiting in a queue if it is a simple question.
- **Pain Points:** Being answered in English when he does not read it well; getting an answer with no way to check it; being passed between people and repeating himself; not knowing whether the guidance he found online is still current.
- **Formal User Stories:**
  - As a business customer, I want to ask in my own language and get an answer in that language, so that I can act on it confidently.
  - As a business customer, I want to see the official document an answer came from, so that I can verify it or show it to my accountant.
  - As a business customer, I want to reach a person in one step when the assistant cannot help, so that I am not stuck in a loop.

### Secondary Persona: Knowledge Manager ("Meera")

- **Demographics:** 30–50, domain specialist in trade/commerce procedure, 5–20 years experience, owns the correctness of published guidance, works with documents all day, moderate technical comfort.
- **Goals:** Get newly issued material answerable quickly; find and kill wrong or superseded answers; know what customers are asking that the system cannot answer.
- **Pain Points:** No visibility into what agents actually tell customers; no way to know which guidance is stale; corrections that do not propagate; classification of large document batches by hand.
- **Formal User Stories:**
  - As a knowledge manager, I want to upload a newly issued circular and have it filed and answerable the same day, so that agents stop giving the previous answer.
  - As a knowledge manager, I want to retire a superseded item and have it stop appearing in answers immediately, so that outdated guidance leaves circulation.
  - As a knowledge manager, I want a ranked list of questions the system could not answer, so that I know what to write next.
  - As a knowledge manager, I want to correct a mis-filed item's classification, so that it surfaces for the right queries.

### Secondary Persona: Contact-Center Supervisor ("Deepak")

- **Demographics:** 32–50, manages 15–60 agents, accountable for service levels and escalations, reports upward to the ministry sponsor, lives in dashboards and weekly reviews.
- **Goals:** Show whether the platform improved anything; find where quality is slipping; decide staffing and training from evidence.
- **Pain Points:** Quality data that is self-reported; no view of which topics generate repeat contacts; no early warning that a knowledge area has gone stale.
- **Formal User Stories:**
  - As a supervisor, I want deflection, handle time and answer-quality trends over a period I choose, so that I can report the platform's effect.
  - As a supervisor, I want the top unanswered topics, so that I can direct the knowledge team's effort.
  - As a supervisor, I want to see the language mix of incoming queries, so that I can staff and prioritise language coverage.

---

## User Flows

### Flow 1: Agent answers a live customer query with assist

- **Persona:** Support Agent
- **Trigger:** A customer conversation is assigned to the agent and the customer has stated a question.
- **Preconditions:** The agent is signed in and holds the agent role. At least one approved knowledge item exists.

**Main Flow (Happy Path)**
1. Agent opens the assigned conversation → System shows the conversation and an assist area.
2. Agent submits the customer's question to the assist area (typed or pulled from the conversation) → System detects the query language and searches approved knowledge.
3. System returns a suggested answer with the source passage, the source document's name, issuing authority and date, and a confidence indication.
4. Agent reads the source passage and accepts the suggestion → System places the answer text into the agent's reply, in the customer's language, with the source reference attached.
5. Agent sends the reply → System records which knowledge item was used for this contact.
6. Agent marks the suggestion helpful → System records positive feedback against that knowledge item.

**Alternate Flows / Branches**
- **Branch A — the suggestion is close but not right:** Agent edits the drafted reply before sending → System records the answer as "used with edit" and stores the edited text against the gap queue for review (REQ-011).
- **Branch B — several candidate answers are returned:** System presents them ranked with their sources → Agent picks one → flow continues from step 4.
- **Branch C — the customer's question spans two topics:** Agent submits each part separately → System answers each with its own citation → Agent composes one reply from both.
- **Branch D — the query is in a language the agent does not read:** System shows the suggested answer both in the customer's language and in the agent's working language → Agent verifies against the working-language version and sends the customer-language version.

**Error / Exception Flows**
- **If confidence is below the answer bar** → System states that it has no reliable answer, offers the closest related material as reading rather than as an answer, and logs the query to the gap queue → Agent researches and answers manually, and may submit the answer they gave to the knowledge manager.
- **If no knowledge item matches at all** → System states that nothing was found and logs the query to the gap queue → Agent proceeds manually.
- **If the assist service is unreachable** → System shows that assist is unavailable and keeps the conversation fully usable → Agent handles the contact without assist; no conversation content is lost.
- **If the only matching item is retired or stale** → System does not present it as an answer, states that the governing material is under review, and shows the item to the agent flagged as unverified reference only.

**Postconditions / Success State**
The customer has a reply; the contact is linked to the knowledge item used (or explicitly to none); any feedback and any gap are recorded.

**Related Edge Cases** — "Conflicting sources", "Knowledge retired mid-conversation", "Mixed-language query".

### Flow 2: Customer self-serves and escalates

- **Persona:** Business Customer
- **Trigger:** Customer opens the self-serve assistant.
- **Preconditions:** The assistant is available; at least one approved knowledge item exists.

**Main Flow (Happy Path)**
1. Customer types a question in their own language → System detects the language and confirms it back to the customer.
2. System searches approved knowledge and returns a cited answer in the detected language, with the source document named and its issuing authority and date shown.
3. Customer indicates the answer resolved the question → System closes the conversation as self-resolved and records the outcome.

**Alternate Flows / Branches**
- **Branch A — customer asks a follow-up:** System answers the follow-up using the earlier turns as context, again with citations → flow continues from step 3.
- **Branch B — customer prefers a different language:** Customer selects a supported language → System re-renders the answer in that language, keeping the same citations.
- **Branch C — customer wants the source:** Customer opens the citation → System shows the quoted passage in its document context.

**Error / Exception Flows**
- **If confidence is below the answer bar, or nothing matches** → System says plainly that it cannot answer this one, does not offer a guess, and offers handover to an agent → Customer accepts → Flow 3 begins.
- **If the customer asks the same question a third time after two low-confidence responses** → System stops retrying and offers handover directly, without requiring the customer to ask for it.
- **If no agent is available** → System offers to record the question for callback and states the expected response window → Customer accepts or leaves; the question still enters the gap queue.
- **If the customer's language is outside the supported set** → System states which languages it supports, offers to continue in English or Hindi, and offers handover; it does not silently answer in a language the customer did not choose.

**Postconditions / Success State**
The conversation ends in exactly one recorded outcome: self-resolved, handed over, or recorded for callback.

**Related Edge Cases** — "Unsupported language", "Personal data in a customer message", "Abusive or out-of-domain input".

### Flow 3: Handover to an agent with context

- **Persona:** Business Customer → Support Agent
- **Trigger:** Handover is accepted in Flow 2, or requested by the customer at any point.
- **Preconditions:** An agent is available or a queue exists.

**Main Flow (Happy Path)**
1. Customer accepts handover → System places the conversation in the agent queue with its detected language attached.
2. System assigns the conversation to an available agent, preferring an agent who works in the detected language.
3. Agent opens it → System shows the full prior conversation, the detected language, every answer the assistant attempted, and why each was rejected or rated low-confidence.
4. Agent continues the conversation with assist available (Flow 1 from step 2).

**Alternate Flows / Branches**
- **Branch A — no agent works in that language:** System assigns to any available agent and shows the conversation in both the customer's language and the agent's working language.
- **Branch B — customer requests handover before asking anything:** System hands over with an empty transcript rather than forcing the customer through the assistant first.

**Error / Exception Flows**
- **If the queue wait exceeds the published threshold** → System tells the customer the current wait and offers callback instead → Customer chooses.
- **If handover fails to assign** → System keeps the conversation open, tells the customer it is still trying, and raises it to the supervisor view rather than silently dropping it.

**Postconditions / Success State**
The agent holds the conversation with complete context, and no customer statement has been lost or required restating.

**Related Edge Cases** — "Agent language mismatch", "Handover during a knowledge retirement".

### Flow 4: Knowledge manager publishes new material

- **Persona:** Knowledge Manager
- **Trigger:** A new circular, notification, scheme guideline or FAQ needs to be answerable.
- **Preconditions:** Manager is signed in with the knowledge-manager role.

**Main Flow (Happy Path)**
1. Manager uploads a document or enters an FAQ → System accepts it, records who submitted it and when, and begins processing.
2. System extracts the text, proposes a sector, topic and issuing authority with a confidence value for each, and detects the document's language and its date of issue.
3. System shows the proposed classification to the manager → Manager accepts or corrects it.
4. Manager sets a review date and approves the item → System marks it approved and makes it answerable to agents and customers.
5. Manager asks a test question → System answers from the new item, citing it.

**Alternate Flows / Branches**
- **Branch A — the item supersedes an existing one:** Manager marks which item it supersedes → System retires the superseded item, stops answering from it immediately, and keeps it readable in history.
- **Branch B — classification confidence is low:** System presents the item as requiring manual classification rather than proposing a guess → Manager classifies it.
- **Branch C — the document is in a regional language:** System processes it in its own language and makes it answerable to queries in any supported language, keeping the citation in the original language.
- **Branch D — manager rejects the item:** System discards it from the answerable set, retains the upload record and reason, and does not silently keep partial content.

**Error / Exception Flows**
- **If the document cannot be read (unreadable scan, corrupt, or encrypted)** → System reports which part failed, keeps the upload, and offers manual text entry → Manager pastes or re-uploads; nothing partially readable is published as if complete.
- **If the document exceeds the size limit** → System states the limit and the actual size before processing, rather than failing after a long wait.
- **If the item duplicates existing content** → System shows the near-duplicate and asks whether this supersedes it, replaces it, or coexists → Manager decides.

**Postconditions / Success State**
The item is either answerable with a full classification, an approver, a review date and an audit record, or explicitly rejected with a reason.

**Related Edge Cases** — "Conflicting sources", "Scanned document with no text layer".

### Flow 5: Knowledge manager works the gap queue

- **Persona:** Knowledge Manager
- **Trigger:** Scheduled review of unanswered queries.
- **Preconditions:** Gap entries exist.

**Main Flow (Happy Path)**
1. Manager opens the gap queue → System shows unanswered and negatively-rated queries, grouped by similar meaning, ranked by frequency, with each group's languages and example queries.
2. Manager selects a group → System shows every original query in the group and what the system did answer, if anything.
3. Manager writes an FAQ entry answering it, or uploads the governing document → Flow 4 from step 1.
4. Manager marks the group resolved → System links the group to the new knowledge item and stops counting it as an open gap.

**Alternate Flows / Branches**
- **Branch A — the group is out of the service's domain:** Manager marks it out of domain → System keeps it in reporting but out of the actionable queue.
- **Branch B — the knowledge exists but was not found:** Manager links the group to the existing item and marks it a retrieval failure → System records it separately from a content gap, so the two failure types are not conflated in reporting.

**Error / Exception Flows**
- **If a gap group turns out to mix unrelated questions** → Manager splits it → System re-ranks the resulting groups.
- **If resolving a gap requires knowledge nobody holds** → Manager marks it pending external input with an owner → System keeps it visible in reporting rather than closing it.

**Postconditions / Success State**
Every worked group ends in exactly one state: resolved with a linked item, retrieval failure, out of domain, or pending external input.

**Related Edge Cases** — "Repeated question with no possible answer".

### Flow 6: Supervisor reviews performance

- **Persona:** Contact-Center Supervisor
- **Trigger:** Weekly or ad-hoc review.
- **Preconditions:** At least one day of recorded activity.

**Main Flow (Happy Path)**
1. Supervisor opens analytics and picks a period → System shows deflection rate, average resolution time, assist-usage rate, answer-quality ratings, language mix and top unanswered topics for that period.
2. Supervisor opens a topic → System shows the underlying queries and the knowledge items involved.
3. Supervisor exports the period's summary → System produces a file of the same figures shown.

**Alternate Flows / Branches**
- **Branch A — comparison across periods:** Supervisor selects a second period → System shows both with the difference.
- **Branch B — drill into one agent:** Supervisor selects an agent → System shows that agent's assist usage and quality ratings, with a stated caution that ratings are a sample, not a census.

**Error / Exception Flows**
- **If the chosen period has too little activity to be meaningful** → System shows the figures with an explicit low-volume warning rather than presenting an unstable percentage as a trend.
- **If data for part of the period is missing** → System names the missing interval instead of silently averaging over a gap.

**Postconditions / Success State**
The supervisor has figures traceable to the underlying conversations.

**Related Edge Cases** — "Low-volume period", "Period spanning a knowledge retirement".

---

## Decision Thresholds

Four thresholds govern behaviour across several features. Each has a starting value, a stated basis, and a named owner who may change it. They are launch-tunables, not fixed constants — but a tunable without a starting value is untestable, so every one carries a value from day one, and every acceptance criterion that references a "bar" or "threshold" means the value below.

| Threshold | Governs | Starting value | Basis | Owner |
|---|---|---|---|---|
| **Answer bar** | Whether a generated answer is shown at all (REQ-005) | Confidence 0.70 on a 0–1 scale | `[PROPOSED: pending eng confirmation]` — set against the acceptance question set during Phase 1d, tuned so the wrong-answer rate stays within its 2% target | Knowledge management lead |
| **Classification bar** | Whether a proposed sector/topic/authority is offered or the field is sent for manual classification (REQ-003) | Confidence 0.60 per field | `[PROPOSED: pending eng confirmation]` — deliberately lower than the answer bar, because a wrong proposal a human corrects costs seconds while a wrong answer costs a customer | Knowledge management lead |
| **Low-volume threshold** | When analytics figures carry a low-volume warning (REQ-012) | Fewer than 100 conversations in the selected period | `[PROPOSED: pending eng confirmation]` — below this a single conversation moves a percentage by more than one point | Contact-center supervisor |
| **Gap group-size threshold** | Minimum group size before a gap group is proposed as actionable, and before ticket clusters become draft FAQs (REQ-011, REQ-016) | 5 queries in the group | `[PROPOSED: pending eng confirmation]` — below this the queue fills with one-offs and stops being a priority list | Knowledge management lead |

THE SYSTEM SHALL allow an authorised administrator to change any threshold above, and SHALL record who changed it, when, from what value and to what value (see REQ-014).

## Functional Requirements

### Must Have Features

#### REQ-001: Multilingual query understanding

- **User Story:** As a business customer, I want to ask my question in my own language, so that I get a usable answer without translating it myself.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL support six launch languages — English, Hindi, Bengali, Tamil, Telugu and Marathi — each of which is enabled independently.
  - [ ] THE SYSTEM SHALL accept queries in every enabled language.
  - [ ] THE SYSTEM SHALL enable a language only once that language has cleared the correctness bar stated in Success Metrics on its own portion of the acceptance question set. English and Hindi are the guaranteed launch pair; the remaining four are enabled as each clears (see Risk R-1).
  - [ ] WHILE a launch language is not yet enabled, THE SYSTEM SHALL treat it as an unsupported language for answering purposes, SHALL state that support for it is in preparation rather than absent, and SHALL offer English, Hindi or handover.
  - [ ] WHERE an administrator enables or disables a language, THE SYSTEM SHALL record the change with actor and time, and SHALL NOT alter any knowledge item's own language or classification as a result.
  - [ ] WHEN a query is submitted, THE SYSTEM SHALL detect its language and make the detected language visible to the person who submitted it.
  - [ ] WHEN a query is submitted in any supported language, THE SYSTEM SHALL search the entire approved knowledge base regardless of the language each knowledge item is written in.
  - [ ] WHEN an answer is returned, THE SYSTEM SHALL render the answer text in the detected query language, subject to Business Rule BR-3 in Detailed Feature Specifications.
  - [ ] IF the detected language is not supported, THEN THE SYSTEM SHALL state which languages are supported and offer to continue in English or Hindi, and SHALL NOT answer in an unrequested language.
  - [ ] IF the user explicitly selects a supported language, THEN THE SYSTEM SHALL use that selection over the detected language for that conversation.
  - [ ] WHEN a query mixes two supported languages in one message, THE SYSTEM SHALL answer in the language of the majority of the message and offer the other supported language as a one-step switch.

#### REQ-002: Knowledge ingestion

- **User Story:** As a knowledge manager, I want to bring documents, past tickets, portal pages and hand-written entries into one place, so that everything the center knows is answerable from one search.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL accept knowledge from four sources: uploaded documents, exported resolved-ticket records, registered web page addresses, and manually authored entries.
  - [ ] WHEN a document is submitted, THE SYSTEM SHALL extract its readable text and record its title, issuing authority, issue date and language.
  - [ ] WHEN extraction is complete, THE SYSTEM SHALL make the item's content searchable within the time stated in Non-Functional Requirements → Performance.
  - [ ] IF a submitted document contains no extractable text, THEN THE SYSTEM SHALL report the failure with the reason, retain the upload, and offer manual text entry, and SHALL NOT publish a partially extracted item as complete.
  - [ ] IF a submitted item is a near-duplicate of an existing item — substantially overlapping text with the same issuing authority and subject — THEN THE SYSTEM SHALL present the existing item and require the submitter to choose supersede, replace or coexist before publishing.
  - [ ] THE SYSTEM SHALL record, for every ingested item, who submitted it, when, and from which source type.
  - [ ] WHILE an item is being processed, THE SYSTEM SHALL show its processing state and SHALL NOT return it in answers.

#### REQ-003: Automatic classification

- **User Story:** As a knowledge manager, I want new material filed automatically by sector and topic, so that I am not classifying hundreds of documents by hand.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN an item's text has been extracted, THE SYSTEM SHALL propose a sector, a topic and an issuing authority, each with a confidence value.
  - [ ] THE SYSTEM SHALL present every proposed classification for human acceptance or correction before the item becomes answerable.
  - [ ] IF classification confidence for any field is below the classification bar, THEN THE SYSTEM SHALL mark that field as requiring manual classification and SHALL NOT present a guess as a proposal.
  - [ ] WHEN a human corrects a proposed classification, THE SYSTEM SHALL store the correction against the item and record who made it.
  - [ ] THE SYSTEM SHALL allow an item to carry more than one topic.
  - [ ] WHERE a sector or topic taxonomy entry is added or renamed, THE SYSTEM SHALL keep existing items' classifications intact and attributable to the renamed entry.

#### REQ-004: Cited answer generation

- **User Story:** As a support agent, I want every answer to come with the passage it was drawn from, so that I can check it before I say it to a customer.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL attach to every shown answer at least one citation consisting of the quoted source passage, the source item's title, its issuing authority and its issue date.
  - [ ] IF an answer cannot be attributed to at least one approved knowledge item, THEN THE SYSTEM SHALL NOT show it, and SHALL instead follow the no-answer behaviour in REQ-005.
  - [ ] WHEN a citation is opened, THE SYSTEM SHALL show the quoted passage in the context of its source item.
  - [ ] WHEN an answer draws on more than one item, THE SYSTEM SHALL cite each item used.
  - [ ] WHEN the source item is written in a different language from the answer, THE SYSTEM SHALL show the citation in the source's original language and indicate that language.
  - [ ] THE SYSTEM SHALL exclude retired and superseded items from the material an answer may be drawn from (see REQ-010).

#### REQ-005: Answer confidence and no-answer behaviour

- **User Story:** As a support agent, I want the system to tell me when it does not know, so that I never pass on a confident guess.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN an answer is shown, THE SYSTEM SHALL show a confidence indication alongside it.
  - [ ] IF answer confidence is below the answer bar, THEN THE SYSTEM SHALL state that it has no reliable answer and SHALL NOT present its best guess as an answer.
  - [ ] WHILE below the answer bar, THE SYSTEM SHALL offer the closest related items explicitly labelled as related reading rather than as an answer.
  - [ ] WHEN the system returns no answer, THE SYSTEM SHALL record the query, its language and its context in the gap queue (REQ-011).
  - [ ] WHEN the system returns no answer in a customer conversation, THE SYSTEM SHALL offer handover to an agent (REQ-008).
  - [ ] THE SYSTEM SHALL allow an authorised administrator to change the answer bar, and SHALL record who changed it, when, and to what value.

#### REQ-006: Agent assist console

- **User Story:** As a support agent, I want suggestions and sources inside the conversation, so that I do not leave it to search.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHILE a conversation is open, THE SYSTEM SHALL let the agent submit a query and receive suggested answers without leaving the conversation.
  - [ ] WHEN suggestions are returned, THE SYSTEM SHALL rank them and show each one's citation and confidence.
  - [ ] WHEN the agent accepts a suggestion, THE SYSTEM SHALL place the answer text and its source reference into the agent's reply for editing before sending.
  - [ ] WHEN the agent sends a reply that used a suggestion, THE SYSTEM SHALL record which knowledge items were used, and whether the text was edited before sending.
  - [ ] WHEN the agent rates a suggestion helpful or unhelpful, THE SYSTEM SHALL record the rating against the knowledge item and the query.
  - [ ] WHERE the customer's language differs from the agent's working language, THE SYSTEM SHALL show the suggestion in both.
  - [ ] IF the assist function is unavailable, THEN THE SYSTEM SHALL keep the conversation fully usable and state that assist is unavailable.

#### REQ-007: Customer self-serve assistant

- **User Story:** As a business customer, I want to get a simple answer myself, so that I do not wait for an agent for a routine question.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL let a customer ask a question and receive a cited answer without a human being involved.
  - [ ] WHEN a customer asks a follow-up in the same conversation, THE SYSTEM SHALL use the earlier turns of that conversation as context for the answer.
  - [ ] WHEN a customer changes the conversation language, THE SYSTEM SHALL re-render the current answer in the newly chosen language while keeping the same citations.
  - [ ] WHEN a conversation ends, THE SYSTEM SHALL record exactly one outcome: self-resolved, handed over, recorded for callback, or abandoned.
  - [ ] WHEN a customer stops responding for longer than the inactivity boundary of 15 minutes, THE SYSTEM SHALL close the conversation as abandoned. `[PROPOSED: pending eng confirmation]`
  - [ ] THE SYSTEM SHALL exclude abandoned conversations from the self-resolved count wherever deflection is reported (REQ-012).
  - [ ] IF two consecutive answers fall below the answer bar, THEN THE SYSTEM SHALL offer handover without waiting to be asked.
  - [ ] IF the customer's input is outside the service's domain, THEN THE SYSTEM SHALL say so plainly and offer handover, and SHALL NOT answer from unrelated material.

#### REQ-008: Handover with context

- **User Story:** As a business customer, I want the agent to already know what I have said, so that I do not repeat myself.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN handover occurs, THE SYSTEM SHALL transfer the complete conversation transcript, the detected language and every attempted answer with its confidence to the receiving agent.
  - [ ] WHEN a conversation enters the queue, THE SYSTEM SHALL prefer assignment to an available agent who works in the conversation's language.
  - [ ] IF no agent works in that language, THEN THE SYSTEM SHALL assign to any available agent and show the transcript in both the customer's language and the agent's working language.
  - [ ] IF no agent is available, THEN THE SYSTEM SHALL offer the customer a recorded callback with a stated response window.
  - [ ] IF assignment fails, THEN THE SYSTEM SHALL keep the conversation open, inform the customer it is still in progress, and raise it in the supervisor view.
  - [ ] THE SYSTEM SHALL allow a customer to request handover at any point, including before asking anything.

#### REQ-009: Knowledge curation console

- **User Story:** As a knowledge manager, I want to review, correct, approve and retire knowledge, so that what the system says stays right.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL let a knowledge manager list, filter and open every knowledge item by sector, topic, authority, language, status and review date.
  - [ ] THE SYSTEM SHALL let a knowledge manager approve, reject, edit, re-classify and retire an item.
  - [ ] WHEN an item is approved, THE SYSTEM SHALL record the approver, the approval time and a review date.
  - [ ] WHEN an item is edited after approval, THE SYSTEM SHALL keep the previous version readable and record what changed and who changed it.
  - [ ] WHEN an item is rejected, THE SYSTEM SHALL require a reason and SHALL keep the record of the rejected submission.
  - [ ] IF two people save changes to the same item concurrently, THEN THE SYSTEM SHALL show the second person what changed since they began and require them to reconcile before saving, and SHALL NOT overwrite silently.
  - [ ] THE SYSTEM SHALL prevent an unapproved item from appearing in any answer.

#### REQ-010: Freshness and supersession control

- **User Story:** As a knowledge manager, I want superseded guidance to actually stop being given, so that amendments take effect the day they are published.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN an item is marked as superseded by another item, THE SYSTEM SHALL immediately stop using the superseded item as an answer source and SHALL keep it readable in history.
  - [ ] WHEN an item's review date passes, THE SYSTEM SHALL mark it stale and flag it in the curation console.
  - [ ] WHILE an item is stale, THE SYSTEM SHALL continue answering from it but SHALL show a review-pending indication on every answer citing it, per Business Rule BR-5.
  - [ ] WHEN an item is retired, THE SYSTEM SHALL stop using it as an answer source immediately, including for conversations already in progress.
  - [ ] WHEN an answer in an open conversation cited an item that was retired after the answer was given, THE SYSTEM SHALL flag that conversation to the agent handling it.
  - [ ] THE SYSTEM SHALL show a knowledge manager every item due for review within the next 30 days.

#### REQ-011: Feedback loop and gap queue

- **User Story:** As a knowledge manager, I want to see what the system cannot answer, ranked, so that I write what is actually needed.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN a query returns no answer, is rated unhelpful, or produces an answer the agent edited before sending, THE SYSTEM SHALL record it as a gap entry with its query text, language, timestamp and conversation reference.
  - [ ] THE SYSTEM SHALL group gap entries whose queries mean the same thing, and rank the groups by frequency.
  - [ ] WHEN a gap group is shown, THE SYSTEM SHALL show its example queries, its language spread and any answer that was attempted.
  - [ ] THE SYSTEM SHALL let a knowledge manager resolve a group as: resolved with a linked knowledge item, retrieval failure, out of domain, or pending external input.
  - [ ] THE SYSTEM SHALL let a knowledge manager split a group and re-rank the results.
  - [ ] WHEN a group is resolved with a linked item, THE SYSTEM SHALL stop counting it as an open gap and keep the link visible.

#### REQ-012: Supervisor analytics

- **User Story:** As a supervisor, I want evidence of what the platform changed, so that I can report and direct effort.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN a period is selected, THE SYSTEM SHALL report deflection rate, average resolution time, assist-usage rate, answer-quality ratings, language mix and top unanswered topics for that period.
  - [ ] WHEN a reported figure is opened, THE SYSTEM SHALL show the underlying conversations or knowledge items it was computed from.
  - [ ] THE SYSTEM SHALL let a supervisor compare two periods and show the difference.
  - [ ] WHEN per-agent figures are shown, THE SYSTEM SHALL state that quality ratings are a sample of that agent's conversations rather than a census of them.
  - [ ] IF the selected period's volume is below the low-volume threshold, THEN THE SYSTEM SHALL show the figures with an explicit low-volume warning.
  - [ ] IF activity data is missing for part of the period, THEN THE SYSTEM SHALL name the missing interval rather than averaging across it.
  - [ ] THE SYSTEM SHALL let a supervisor export the selected period's figures as a file containing exactly the figures shown.

#### REQ-013: Roles and access control

- **User Story:** As a compliance reviewer, I want each role limited to what it should do, so that knowledge cannot be altered by someone unaccountable for it.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL require every person to be identified before taking any role-bound action, and SHALL attribute that action to them.
  - [ ] THE SYSTEM SHALL define four roles: agent, knowledge manager, supervisor and administrator.
  - [ ] THE SYSTEM SHALL restrict knowledge approval, retirement and re-classification to the knowledge-manager and administrator roles.
  - [ ] THE SYSTEM SHALL restrict analytics across all agents to the supervisor and administrator roles.
  - [ ] THE SYSTEM SHALL allow the agent role to read approved knowledge, use assist, and submit feedback and gap entries, and nothing else.
  - [ ] THE SYSTEM SHALL require the customer-facing assistant to expose only approved knowledge and never any internal note, rating or gap entry.
  - [ ] IF a signed-in user attempts an action outside their role, THEN THE SYSTEM SHALL refuse it and record the attempt.

#### REQ-014: Audit trail

- **User Story:** As a compliance reviewer, I want to reconstruct what a customer was told and on what basis, so that a wrong answer can be traced.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL record every knowledge item creation, edit, classification change, approval, rejection, supersession and retirement, with actor and timestamp.
  - [ ] THE SYSTEM SHALL record, for every answer shown to a customer or agent, the query, the knowledge items cited, the confidence and the time.
  - [ ] WHEN an agent sends a reply to a customer, THE SYSTEM SHALL record the text actually sent, alongside the suggestion it was derived from (if any) and that suggestion's citations, so that an edited reply is distinguishable from the suggestion it started as.
  - [ ] WHEN the self-serve assistant shows an answer, THE SYSTEM SHALL record the text the customer saw, not only the items cited.
  - [ ] THE SYSTEM SHALL make an audit record readable but not editable or deletable by any role, including administrator.
  - [ ] WHEN an audit record is requested for a conversation, THE SYSTEM SHALL return the full sequence of answers shown and items cited in that conversation.
  - [ ] THE SYSTEM SHALL retain audit records for the period stated in Non-Functional Requirements → Compliance.

#### REQ-015: Personal-data protection

- **User Story:** As a business customer, I want my personal details not to end up inside the knowledge base, so that answering someone else's question never exposes mine.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN conversation content is stored for analytics, gap entries or knowledge reuse, THE SYSTEM SHALL mask personal identifiers within it, per Business Rule BR-7.
  - [ ] THE SYSTEM SHALL NOT publish any conversation content as knowledge without a knowledge manager's explicit approval.
  - [ ] WHEN a gap entry is shown, THE SYSTEM SHALL show the masked query text, not the raw text.
  - [ ] IF masking cannot be confidently applied to a piece of content, THEN THE SYSTEM SHALL withhold that content from reuse and flag it for manual review.
  - [ ] THE SYSTEM SHALL mask personal identifiers with a recall of at least 98% measured on a held-out sample of real conversation content, verified before launch and re-verified quarterly by the compliance reviewer. `[PROPOSED: pending eng confirmation]`
  - [ ] THE SYSTEM SHALL present a knowledge manager with a periodic sample of stored gap entries for manual masking verification, and SHALL record the result of each check.
  - [ ] THE SYSTEM SHALL let an administrator delete a specific customer's conversation records on request, while retaining the aggregate counts already reported.
  - [ ] WHEN a deletion request is executed, THE SYSTEM SHALL delete the conversation transcript and any unresolved gap entry derived solely from it, SHALL retain the audit record of the deletion itself, and SHALL retain any approved knowledge item that a knowledge manager already published from that content.

#### REQ-023: Cold start, coverage gating and fair use

- **User Story:** As a knowledge manager, I want the public assistant to stay closed until it can actually answer, so that the service's first impression is not a wall of "I don't know".
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL make agent assist available from the first approved knowledge item, and SHALL show an explicit thin-knowledge indication while the approved item count is below the coverage floor.
  - [ ] THE SYSTEM SHALL keep the customer self-serve assistant closed to customers until a knowledge manager declares the coverage floor met, and SHALL record who declared it and when.
  - [ ] THE SYSTEM SHALL define the coverage floor as: every Must-Have topic in the agreed taxonomy has at least one approved knowledge item, and the acceptance question set scores at or above the correctness bar in every enabled language. `[PROPOSED: pending eng confirmation]`
  - [ ] WHILE the self-serve assistant is closed, THE SYSTEM SHALL route customer contacts directly to the agent queue rather than showing a non-functional assistant.
  - [ ] IF the knowledge base holds no approved item matching a query's topic, THEN THE SYSTEM SHALL follow no-answer behaviour (REQ-005) and SHALL NOT present related reading drawn from an unrelated topic.
  - [ ] THE SYSTEM SHALL limit how many queries a single unidentified customer may submit within a rolling period, and SHALL state the limit when it is reached rather than failing silently.
  - [ ] IF the fair-use limit is reached, THEN THE SYSTEM SHALL still offer handover to an agent, so that limiting never removes the path to a human.
  - [ ] THE SYSTEM SHALL let an administrator set the fair-use limit, with a starting value of 30 queries per hour per unidentified customer. `[PROPOSED: pending eng confirmation]`

### Should Have Features

#### REQ-016: Ticket-history mining

- **User Story:** As a knowledge manager, I want proposed FAQs drawn from tickets we already resolved, so that existing effort turns into reusable knowledge.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN resolved-ticket records are ingested, THE SYSTEM SHALL group them by question similarity and propose a draft FAQ entry per group above the group-size threshold.
  - [ ] THE SYSTEM SHALL present every proposal for knowledge-manager approval and SHALL NOT make an unapproved proposal answerable.
  - [ ] WHEN a proposal is shown, THE SYSTEM SHALL show the tickets it was derived from, with personal identifiers masked per REQ-015.
  - [ ] IF the tickets in a group disagree about the answer, THEN THE SYSTEM SHALL show the disagreement rather than choosing one silently.

#### REQ-017: Scheduled portal re-crawl

- **User Story:** As a knowledge manager, I want to know when a registered page changes, so that I do not have to check portals by hand.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL let a knowledge manager register a page address with a re-check interval.
  - [ ] WHEN a registered page's content has changed since the last check, THE SYSTEM SHALL flag it for review and show what changed.
  - [ ] THE SYSTEM SHALL NOT make changed page content answerable until a knowledge manager approves it.
  - [ ] IF a registered page becomes unreachable for three consecutive checks, THEN THE SYSTEM SHALL flag it and mark the derived item stale.

#### REQ-018: Answer comparison across languages

- **User Story:** As a knowledge manager, I want to see one answer in every supported language at once, so that I can catch a translation that changes the meaning.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN a knowledge manager selects an answer, THE SYSTEM SHALL show it rendered in every supported language side by side.
  - [ ] THE SYSTEM SHALL let a knowledge manager record a per-language correction that overrides the rendered text for that language.
  - [ ] WHEN a per-language correction exists, THE SYSTEM SHALL use it in place of the rendered text for every answer in that language.

#### REQ-019: Bulk import and bulk re-classification

- **User Story:** As a knowledge manager, I want to handle a batch of documents in one operation, so that a large backlog is not a hundred separate uploads.
- **Acceptance Criteria (EARS Format):**
  - [ ] THE SYSTEM SHALL accept a batch of documents in one submission and report per-item outcome when processing completes.
  - [ ] THE SYSTEM SHALL let a knowledge manager apply a classification change to a selected set of items in one action.
  - [ ] IF some items in a batch fail, THEN THE SYSTEM SHALL complete the rest and report each failure with its reason, and SHALL NOT abandon the batch.

### Could Have Features

#### REQ-020: Additional scheduled languages

- **User Story:** As a business customer speaking a language outside the launch six, I want the same service, so that language does not decide the quality of help I get.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHERE an additional language is enabled, THE SYSTEM SHALL support it across query understanding, answering and the self-serve assistant to the same standard as the launch six.
  - [ ] THE SYSTEM SHALL let an administrator enable or disable a supported language without affecting existing knowledge items.

#### REQ-021: Messaging-channel access

- **User Story:** As a business customer, I want to reach the assistant from a messaging app I already use, so that I do not have to open a portal.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHERE a messaging channel is enabled, THE SYSTEM SHALL accept questions and return cited answers through it with the same answer bar and citation rules as REQ-004 and REQ-005.
  - [ ] WHERE a messaging channel is enabled, THE SYSTEM SHALL support handover to an agent from within that channel.

#### REQ-022: Proactive answer suggestions

- **User Story:** As a business customer, I want to see the obvious next question answered, so that I do not have to know what to ask.
- **Acceptance Criteria (EARS Format):**
  - [ ] WHEN an answer is shown, THE SYSTEM SHALL offer up to three related questions that the knowledge base can answer with citations.
  - [ ] THE SYSTEM SHALL NOT offer a related question it cannot answer above the answer bar.

### Won't Have (This Phase)

- Voice telephony handling — speech in, speech out (see Out of Scope).
- Replacement of the existing ticketing or CRM system (see Out of Scope).
- Binding determinations on classification, duty or eligibility (see Out of Scope).
- Payment, filing or any transaction on the customer's behalf (see Out of Scope).
- Agent workforce scheduling and rostering (see Out of Scope).

## Non-Functional Requirements

- **Performance:**
  - An agent-assist suggestion is shown within 5 seconds of query submission at the 95th percentile. Based on the Support Agent persona's stated tolerance — slower than her own document search and she stops using it. `[PROPOSED: pending eng confirmation]`
  - A self-serve answer is shown within 8 seconds at the 95th percentile. `[PROPOSED: pending eng confirmation]`
  - An uploaded document of up to 200 pages is answerable within 15 minutes of upload. Derived from the knowledge manager's working pattern of uploading and then testing in one sitting. `[PROPOSED: pending eng confirmation]`
  - Analytics for a one-month period are shown within 10 seconds. `[PROPOSED: pending eng confirmation]`

- **Reliability/Availability:**
  - 99.5% availability during published support hours. `[PROPOSED: pending eng confirmation]`
  - Loss of the assist function never blocks a conversation: agents and customers continue without it (REQ-006, and Flow 1 error path).
  - No customer message or knowledge submission is lost on failure; an interrupted upload is recoverable rather than silently dropped.

- **Usability/Accessibility:**
  - A new agent uses assist correctly with no more than 15 minutes of instruction. `[PROPOSED: pending eng confirmation]`
  - Customer-facing surfaces meet WCAG 2.1 Level AA.
  - Customer-facing text is written for a general-public reading level, not a specialist one.
  - Every supported language is rendered in its own script, correctly, in every surface that shows it.

- **Security & Privacy (outcomes only):**
  - Personal identifiers in conversations are masked before that content is stored for analytics, gap entries or reuse (REQ-015).
  - The customer-facing assistant exposes only approved knowledge — never internal notes, ratings, gap entries or unapproved items (REQ-013).
  - Audit records cannot be edited or deleted by any role (REQ-014).
  - Every knowledge-altering action is attributable to a named person.

- **Scalability (outcomes only):**
  - 200 concurrent conversations and 50 concurrent agents at launch, without breaching the performance targets above. Derived from the demonstration deployment size in Constraints. `[PROPOSED: pending eng confirmation]`
  - A knowledge base of 50,000 items without breaching the performance targets above. `[PROPOSED: pending eng confirmation]`
  - Fair-use limiting on the public surface holds the above targets for legitimate users under automated or abusive traffic (REQ-023).

- **Compliance:**
  - Audit records are retained for 3 years. `[PROPOSED: pending eng confirmation — retention period must be confirmed against the sponsoring ministry's records policy, see OQ-4]`
  - Conversation transcripts are retained for 12 months, after which only the masked gap entries and aggregate counts derived from them survive. `[PROPOSED: pending eng confirmation — must be confirmed alongside OQ-4]`
  - A deletion request removes the transcript and any unresolved gap entry derived solely from it; the audit record of the deletion and any published knowledge item survive (REQ-015).
  - Personal data handling follows India's applicable digital personal data protection obligations, including deletion on request (REQ-015).
  - Every answer's source remains attributable to its issuing authority; the system never presents its own text as the authority.

- **Cost & data control (outcome constraint):**
  - No component of question answering, translation or classification may incur a per-query or per-user licence cost. Fixed constraint from the sponsor, restated in Constraints.
  - No query text, conversation content or knowledge document may be sent to any party outside the operator's control in order to produce an answer. This makes the cost constraint and the data-residency expectation one requirement rather than two.

## Detailed Feature Specifications

### Feature: REQ-004 — Cited answer generation

**Description:** Every answer the system shows — to an agent or to a customer, in any language — carries the passage it was derived from, identified by source. The citation is the product; the generated sentence is a convenience wrapped around it. An answer that cannot point at approved material is not shown at all.

**Business Rules:**
- **BR-1 (Citation required):** An answer is shown only if at least one approved, non-retired, non-superseded knowledge item supports it. No exception, including for the self-serve assistant and for follow-up turns.
- **BR-2 (Citation content):** A citation consists of the quoted passage, the source item's title, its issuing authority and its issue date. A citation missing the issuing authority or issue date is incomplete and the item is flagged for curation rather than cited.
- **BR-3 (Answer language, citation language):** The answer text is rendered in the user's language; the quoted passage is always shown in its own original language, labelled with that language. A quoted passage is never re-worded into another language, because a translated quotation is no longer evidence.
- **BR-4 (Multiple sources):** If an answer draws on more than one item, every item used is cited. If two cited items disagree, see BR-6.
- **BR-5 (Stale source):** An answer citing a stale item is shown with a review-pending indication. An answer citing a retired or superseded item is not shown at all.
- **BR-6 (Conflicting sources):** Conflict detection is evaluated **before** the answer bar. If two approved items give different answers to the same query and neither supersedes the other, the system shows both with their dates and issuing authorities, states plainly that the sources differ, and does not choose between them — regardless of either item's confidence, and regardless of whether either would have cleared the answer bar alone. A shown conflict is never counted as an answer for the purpose of the correctness or deflection metrics. The query is recorded as a gap entry of type "conflict" for a knowledge manager.
- **BR-7 (No personal data in a citation):** A citation drawn from ticket-derived knowledge shows only masked content. If masking is uncertain, the item is not citable (REQ-015).

**Feature-Specific Edge Cases:**
- Scenario: The supporting passage is longer than the display allows → Expected: the system shows the most relevant portion, marks it as an extract, and offers the full passage in its document context.
- Scenario: The best-supporting item is in a language the user does not read → Expected: the answer is rendered in the user's language, the citation stays in the original language with its language labelled, and a rendered version of the passage is offered separately, marked as an unofficial rendering.
- Scenario: An item is retired between the answer being computed and being shown → Expected: the answer is withheld and recomputed from the remaining approved items; if none remain, no-answer behaviour applies (REQ-005).
- Scenario: The query matches an item's title but nothing in its body supports an answer → Expected: no answer is shown; the item may be offered as related reading only.

### Feature: REQ-010 — Freshness and supersession control

**Description:** Knowledge in this domain expires by amendment, not by age alone. The system tracks two independent states — stale (past its review date, still usable with a warning) and retired or superseded (not usable at all) — and enforces them at the moment an answer is assembled, not on a schedule.

**Business Rules:**
- **BR-8 (Supersession is immediate):** Marking item B as superseding item A takes A out of the answerable set at that moment, including for conversations already open.
- **BR-9 (Staleness is a warning, not a block):** Passing a review date marks an item stale. Stale items keep answering, with a review-pending indication (BR-5). This is deliberate: silence is worse than dated guidance in this domain, provided the user is told.
- **BR-10 (Retirement preserves history):** A retired or superseded item remains readable in the curation console and in audit records forever. Nothing is deleted.
- **BR-11 (Review date required at approval):** No item becomes answerable without a review date. The default review interval is 180 days from approval, and the approver may shorten or extend it.
- **BR-12 (Open conversation flagging):** If an item is retired while a conversation that cited it is still open, the handling agent is notified in that conversation, naming the item.

**Feature-Specific Edge Cases:**
- Scenario: An item supersedes another that has itself already superseded a third → Expected: the chain is preserved and readable; only the newest item answers.
- Scenario: A superseded item is later found to be the correct one → Expected: a knowledge manager can reverse the supersession, which restores the item to answerable and is recorded in the audit trail with a reason.
- Scenario: A whole batch of items passes its review date at once → Expected: all are marked stale and grouped in the curation console as one review batch rather than as hundreds of separate flags.
- Scenario: An item is retired with no replacement while queries continue to arrive for it → Expected: those queries fall to no-answer behaviour (REQ-005) and enter the gap queue as a high-frequency group.

## Edge Cases

- [ ] **Conflicting sources** — Two approved items disagree and neither supersedes the other → Expected: both shown with dates and authorities, difference stated plainly, no silent choice, conflict recorded as a gap entry (BR-6).
- [ ] **Knowledge retired mid-conversation** — An item is retired after being cited in an open conversation → Expected: the handling agent is flagged in that conversation, naming the item (BR-12).
- [ ] **Mixed-language query** — One message contains two supported languages → Expected: answered in the majority language, with a one-step switch to the other (REQ-001).
- [ ] **Unsupported language** — Query arrives in a language outside the enabled set → Expected: supported languages stated, English or Hindi offered, handover offered; no answer in an unrequested language (REQ-001).
- [ ] **Personal data in a customer message** — A customer pastes an identifier or document number → Expected: masked before storage for analytics, gap entries or reuse; withheld from reuse if masking is uncertain (REQ-015).
- [ ] **Abusive or out-of-domain input** — Input is hostile or unrelated to the service → Expected: plainly declined, handover offered, no answer assembled from unrelated material (REQ-007).
- [ ] **Scanned document with no text layer** — Upload contains images of text only → Expected: extraction failure reported with the reason, upload retained, manual text entry offered; nothing partial published (REQ-002).
- [ ] **Agent language mismatch** — Only an agent who does not read the customer's language is available → Expected: assigned anyway, transcript shown in both languages (REQ-008).
- [ ] **Two managers edit one item simultaneously** — Second save lands on a changed item → Expected: the second editor is shown what changed and must reconcile before saving; no silent overwrite.
- [ ] **Repeated question with no possible answer** — A gap group has no governing material anywhere → Expected: marked pending external input with an owner, stays visible in reporting rather than closed (Flow 5).
- [ ] **Low-volume period** — Analytics period has too little activity for stable percentages → Expected: figures shown with an explicit low-volume warning (REQ-012).
- [ ] **Period spanning a knowledge retirement** — Reported answers cite an item retired mid-period → Expected: the figures still reconcile, and opening the figure shows the item in its retired state rather than hiding it.
- [ ] **Handover during a knowledge retirement** — A conversation is handed over while its cited item is being retired → Expected: the receiving agent sees the attempted answers and the retirement flag together.
- [ ] **Duplicate upload of the same circular by two managers** — Same document submitted twice → Expected: near-duplicate detected, submitter must choose supersede, replace or coexist (REQ-002).

---

## MVP Scope

Ships in v1: REQ-001 through REQ-015 plus REQ-023 — the full Must-Have set (16 features). Concretely, that is: multilingual query and answer in six languages; ingestion from all four source types; automatic classification with human confirmation; cited answers with an enforced no-answer path; the agent assist console; the customer self-serve assistant with context-carrying handover; the knowledge curation console with freshness and supersession control; the feedback and gap queue; supervisor analytics; four roles with access control; an immutable audit trail; personal-data masking; and cold-start coverage gating with fair-use limiting on the public surface.

Minimum non-functional bar for launch: the performance, availability, accessibility, security and cost targets stated in Non-Functional Requirements, with every `[PROPOSED]` number confirmed or revised by engineering before launch is called.

## Future Scope

Phase 2 (post-launch): REQ-016 ticket-history mining, REQ-017 scheduled portal re-crawl, REQ-018 cross-language answer comparison, REQ-019 bulk import and bulk re-classification.

Phase 3 (later): REQ-020 additional scheduled languages, REQ-021 messaging-channel access, REQ-022 proactive answer suggestions.

## Out of Scope

- **Voice telephony (speech in / speech out).** Excluded because it multiplies the language problem by an accuracy problem in noisy conditions, and the text path must be trustworthy before speech is layered on it.
- **Replacing the ticketing/CRM/telephony systems.** Excluded because this product's value is knowledge, and rebuilding case management would consume the entire effort.
- **Binding determinations on classification, duty liability or scheme eligibility.** Excluded as a matter of policy: the system reports what published material says and cites it; it does not adjudicate. Non-Goal, restated here as a feature exclusion.
- **Transacting on the customer's behalf** — filing, paying, applying. Excluded because it requires authenticated identity and money movement, an entirely separate product.
- **Workforce scheduling and rostering.** Excluded as outside the knowledge problem.
- **Authoring new policy content of its own.** Excluded: the system may only surface and cite material a human approved.

## Estimation Blockers

| # | What can't be sized yet | Why | Owner | Needed by |
|---|---|---|---|---|
| 1 | Volume and condition of the initial document corpus | Nobody has stated how many documents exist, in what formats, or what proportion are scanned images with no text layer. Ingestion effort and answer quality both scale off this. | Knowledge management lead | Before Stage 7 (Planning) |
| 2 | The list of portal pages to register for crawling (REQ-017) | No confirmed source list exists; the effort differs by an order of magnitude between five pages and five hundred. | Knowledge management lead | Before Phase 2 |
| 3 | Acceptance criteria for translation quality | "The meaning did not change" is not yet a testable bar, and no one owns defining it. Affects every language target and the answer-correctness metric. | Knowledge management lead + evaluation panel | Before Stage 10 (QA) |
| 4 | Baseline volumes for deflection and handle time | No current-state measurement exists, so the 30% deflection target has nothing to improve against. | Contact-center operations head | Within 2 weeks of launch |
| 5 | Ongoing knowledge maintenance staffing | Reviewing stale items, working the gap queue and approving proposals is a permanent load, currently unstaffed. Its absence would make the product decay quietly. | Contact-center operations head | Before launch |

---

## Success Metrics / Business Metrics

### Key Performance Indicators

- **Adoption:** 70% of agents use assist in at least one conversation per shift, by day 30. `[PROPOSED: pending eng confirmation]`
- **Adoption (customer side):** 40% of incoming customer contacts start in the self-serve assistant by day 60. `[PROPOSED: pending eng confirmation]`
- **Engagement:** Assist is used in at least 50% of conversations handled by agents who have adopted it. `[PROPOSED: pending eng confirmation]`
- **Quality — correctness:** ≥ 85% of answers on the acceptance question set judged correct and correctly cited. The acceptance question set is a fixed set of at least 200 real queries — at least 25 in each launch language — with expected answers agreed by the knowledge management lead before launch; it is the same set used at Stage 10. `[PROPOSED: pending eng confirmation]`
- **Quality — wrong answers:** ≤ 2% of shown answers rated confidently incorrect by an agent or knowledge manager. `[PROPOSED: pending eng confirmation]`
- **Quality — citation coverage:** 100% of shown answers carry at least one citation. Not a target; a hard rule (BR-1) measured to prove it holds.
- **Business impact — deflection:** ≥ 30% of self-serve conversations end self-resolved by day 90, measured against the baseline established in Estimation Blocker 4. `[PROPOSED: pending eng confirmation]`
- **Business impact — handle time:** 20% reduction in average handle time for assist-used conversations versus the pre-launch baseline. `[PROPOSED: pending eng confirmation]`
- **Reach:** At least 25% of customer conversations occur in a language other than English, by day 90 — evidence that the multilingual capability reached the people it was for. `[PROPOSED: pending eng confirmation]`
- **Knowledge health:** Fewer than 10% of answerable items are stale at any time, by day 90. `[PROPOSED: pending eng confirmation]`

### Guardrail Metrics

Each KPI above pushes in one direction. These guardrails exist so that a KPI cannot be met by making the service worse; a breached guardrail is a failed launch criterion regardless of how the KPIs read.

- **Repeat contact:** the share of customers contacting again about the same topic within 7 days must not rise above its pre-launch baseline. Guards against deflection achieved by customers giving up rather than being answered.
- **Wrong-answer rate versus adoption:** the wrong-answer rate must not rise as assist adoption rises. Guards against handle-time gains bought by agents sending unverified suggestions.
- **Abandonment:** abandoned self-serve conversations are counted and reported separately from self-resolved ones, and their share must not rise above its pre-launch baseline for comparable contact types. Guards the deflection figure against being inflated by silence (REQ-007).
- **Handover quality:** conversations that reach an agent after a failed self-serve attempt must not take longer to resolve than conversations that started with an agent. Guards against the assistant becoming an obstacle on the way to help.
- **Language parity:** the correctness rate in any enabled language must not fall more than 10 percentage points below the English rate. Guards against the multilingual promise degrading into a two-tier service. `[PROPOSED: pending eng confirmation]`

### Tracking Requirements

| Event | Properties | Purpose |
|---|---|---|
| Query submitted | Query text (masked), detected language, selected language, surface (agent / self-serve), conversation reference, timestamp | Feeds language mix (Reach), volume baselines, and all latency measures |
| Answer shown | Conversation reference, items cited, confidence, answer language, stale-source indication, latency | Feeds citation coverage, correctness sampling, and the performance targets |
| No-answer returned | Query (masked), language, reason (below bar / no match / conflict), conversation reference | Feeds gap queue ranking and unanswered-topic reporting |
| Suggestion accepted | Conversation reference, item(s) used, edited before send (yes/no), agent reference | Feeds assist adoption and engagement, and identifies near-miss answers |
| Suggestion rated | Conversation reference, item(s), rating, rater role | Feeds correctness and wrong-answer rate |
| Conversation ended | Outcome (self-resolved / handed over / callback recorded), duration, language, assist used (yes/no) | Feeds deflection and handle time |
| Handover started | Conversation reference, trigger (customer request / low confidence / repeat failure), wait time, language match (yes/no) | Feeds handover quality and language-staffing decisions |
| Knowledge item ingested | Item reference, source type, submitter, extraction outcome, processing duration | Feeds the document-availability performance target |
| Classification proposed / corrected | Item reference, proposed values with confidence, corrected values, corrector | Measures classification accuracy over time |
| Item approved / rejected / retired / superseded | Item reference, actor, reason, review date | Feeds knowledge-health and the audit trail |
| Item marked stale | Item reference, review date passed | Feeds the knowledge-health metric |
| Gap group resolved | Group reference, resolution type, linked item, resolver | Measures whether gaps actually close |
| Access refused | Actor, attempted action, role | Security monitoring (REQ-013) |
| Reply sent by agent | Conversation reference, sent text, suggestion used, edited (yes/no), citations | Makes an edited reply traceable against the suggestion it came from (REQ-014) |
| Threshold changed | Threshold name, old value, new value, actor | Explains a step change in any metric that follows it |
| Language enabled / disabled | Language, actor, acceptance score at enablement | Evidence for the per-language gate (REQ-001) |
| Fair-use limit reached | Customer reference (masked), count in period | Distinguishes abuse from demand in volume figures (REQ-023) |
| Masking check performed | Sample size, misses found, checker | Evidence for the masking-recall target (REQ-015) |

Every KPI above maps to at least one event in this table: adoption and engagement to *Suggestion accepted* and *Query submitted*; correctness and wrong-answer rate to *Suggestion rated* and *Answer shown*; citation coverage to *Answer shown*; deflection and handle time to *Conversation ended*; reach to *Query submitted*; knowledge health to *Item marked stale* and *Item approved / rejected / retired / superseded*.

## Timeline & Roadmap

Sequencing is fixed; calendar dates are not. Durations are withheld deliberately until Phase 0 closes, because the corpus size and condition — the dominant effort driver — is unmeasured (Estimation Blocker 1) and no engineering sizing has been done. Any date attached to these milestones before then is `[PROPOSED: pending eng confirmation]`.

| Phase | Milestone | Target Timing | Scope |
|---|---|---|---|
| Phase 0 | Corpus and baseline established | Milestone 1 | Initial document set assembled and classified taxonomy agreed; current-state handle time and contact volume measured (Estimation Blockers 1 and 4) |
| Phase 1a | Answering core working | Milestone 2 | REQ-001 to REQ-005: multilingual query, ingestion, classification, cited answers, no-answer behaviour |
| Phase 1b | Both consoles working | Milestone 3 | REQ-006 to REQ-009: agent assist, self-serve assistant, handover with context, curation console |
| Phase 1c | Governance and evidence | Milestone 4 | REQ-010 to REQ-015 and REQ-023: freshness and supersession, gap queue, analytics, roles, audit, personal-data masking, cold-start gating and fair use |
| Phase 1d | Acceptance and launch | Milestone 5 | Acceptance question set run in all six launch languages; `[PROPOSED]` numbers confirmed; pilot with one agent team, then full launch |
| Phase 2 | Knowledge scale-up | Post-launch | REQ-016 to REQ-019 |
| Phase 3 | Reach expansion | After Phase 2 | REQ-020 to REQ-022 |

---

## Risks & Constraints

### Constraints

- **Cost:** No per-query commercial licence fee anywhere in question answering, translation or classification. Freely available, self-hostable models only. Stated by the sponsor; drives the quality ceiling in Risk R-1.
- **Language:** Six launch languages — English, Hindi, Bengali, Tamil, Telugu, Marathi — with additional scheduled Indian languages as Phase 3.
- **Citation:** Every shown answer must carry a source. This is non-negotiable and shapes the whole product (BR-1).
- **Deployment size at launch:** 200 concurrent conversations, 50 agents.
- **Timeline:** A demonstrable end-to-end system is required within the event timeframe; the twelve-week roadmap above is the full-build plan, of which Phases 1a–1b constitute the demonstrable core.
- **Compliance:** Government-facing service handling business and personal data under India's applicable data protection obligations.
- **Authority:** The system may never present itself as the issuing authority for any guidance.

### Assumptions

- **A-1:** The four problem failure modes are real for this specific contact center. Not yet validated against its ticket data (see OQ-1). Logged as an assumption, not evidence.
- **A-2:** A usable corpus of source documents exists and can be obtained in bulk (see Estimation Blocker 1).
- **A-3:** Freely available models are good enough for the six launch languages to hit the 85% correctness bar. Unproven at this stage (Risk R-1).
- **A-4:** Agents will use a suggestion tool that is fast and cited. Based on the persona's stated pain, not on measured behaviour.
- **A-5:** Customers will accept a self-serve assistant if handover is genuinely one step away.
- **A-6:** The knowledge team will be staffed to work the gap queue and review cycle (Estimation Blocker 5).
- **A-7:** Ticket exports can be obtained in a form that carries the question and its resolution together (affects REQ-016).

### Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| R-1: Freely available models underperform in regional languages, missing the 85% correctness bar | High | Medium | Per-language enablement gate is now a requirement, not just a mitigation (REQ-001): measure per-language on the acceptance question set, enable a language only when it clears the bar, and state plainly to users that support for a held-back language is in preparation. English and Hindi are the guaranteed pair |
| R-2: Confidently wrong answers reach customers | High | Medium | Answer bar with enforced no-answer behaviour (REQ-005); citation on every answer (BR-1); conflict handling that refuses to choose (BR-6); wrong-answer rate tracked as a launch KPI |
| R-3: The corpus is largely scanned images with no extractable text | High | Medium | Detect and report extraction failure explicitly (REQ-002); manual entry path; size the problem in Phase 0 (Estimation Blocker 1) |
| R-4: Knowledge decays after launch because nobody works the queue | High | Medium | Staleness marking and review-due list (REQ-010); knowledge-health KPI; staffing named as Estimation Blocker 5 before launch |
| R-5: Agents ignore assist and revert to manual search | Medium | Medium | 5-second suggestion target; in-conversation placement; adoption tracked from day 1; pilot with one team before full launch |
| R-6: Personal data leaks into knowledge via ticket mining | High | Low | Masking before any reuse, withholding when masking is uncertain (REQ-015); no ticket-derived item answerable without manager approval (REQ-016) |
| R-7: Superseded guidance keeps being given because supersession is not recorded | High | Medium | Supersession prompt on near-duplicate upload (REQ-002); immediate effect on marking (BR-8); review-due list |
| R-8: Sources conflict and the system picks one, giving a wrong-but-confident answer | Medium | Medium | BR-6 forbids choosing; both sources shown with dates; conflict enters the gap queue |
| R-9: Deflection is claimed without a baseline to measure against | Medium | High | Baseline measured in Phase 0 (Estimation Blocker 4); low-volume warnings in analytics (REQ-012) |

## Open Questions

- [ ] **OQ-1 `BLOCKING: required before Phase 0 completes`** — Can the contact center's historical ticket data be obtained to validate the four problem failure modes and set volume baselines? Owner: contact-center operations head. Needed by: end of Phase 0. Blocks Estimation Blockers 1 and 4, and REQ-016 (Should-Have). Does not block any Must-Have.
- [ ] **OQ-2 `BLOCKING: required before Phase 2 starts`** — Which portal pages are in scope for scheduled re-crawl? Owner: knowledge management lead. Needed by: start of Phase 2. Blocks REQ-017 (Should-Have) only.
- [ ] **OQ-3** — What is the testable acceptance bar for "the translation did not change the meaning"? Owner: knowledge management lead with the evaluation panel. Needed by: Stage 10.
- [ ] **OQ-7** — What is the coverage floor in concrete terms — which taxonomy topics must be covered before the public assistant opens (REQ-023)? Owner: knowledge management lead. Needed by: Phase 1b. Depends on OQ-5 (taxonomy ownership).
- [ ] **OQ-4** — What audit retention period does the sponsoring ministry's records policy require? Owner: compliance reviewer. Needed by: launch. Current value of 3 years is a placeholder marked `[PROPOSED]`.
- [ ] **OQ-5** — Who owns the sector/topic taxonomy, and is an existing official taxonomy to be adopted rather than invented? Owner: knowledge management lead. Needed by: Phase 0.
- [ ] **OQ-6** — Is the self-serve assistant to be reachable by anonymous users, or only by identified businesses? Affects personal-data handling and callback. Owner: product sponsor. Needed by: Phase 1b.

---

## Supporting Research

### Domain Invariants Gate

The eight things a long-serving contact-center and trade-knowledge practitioner treats as non-negotiable, and where each is resolved in this document:

1. **Every answer traceable to an issuing authority's published text** → REQ-004, BR-1 to BR-4.
2. **Superseded guidance stops being given the moment it is superseded** → REQ-010, BR-8.
3. **The system must be able to say "I don't know"** → REQ-005; a knowledge system that always answers is a liability in a regulated domain.
4. **A clean escape hatch to a human, at any moment** → REQ-007, REQ-008.
5. **Personal data never leaks from one contact into another's answer** → REQ-015, BR-7.
6. **Every knowledge change attributable to a named person, permanently** → REQ-009, REQ-014.
7. **Conflicting sources surfaced, not silently resolved** → BR-6.
8. **Language parity — a regional-language user gets the same answer quality, not a degraded one** → REQ-001's per-language enablement gate, and the language-parity guardrail in Success Metrics.
9. **A public surface must survive abuse without closing the path to a human** → REQ-023.
10. **A knowledge service does not open before it can answer** → REQ-023's coverage floor.

Two further invariants are handled by explicit exclusion rather than by a feature: **binding determination of duty/eligibility** (Out of Scope, as a policy decision — the system cites, it does not adjudicate) and **voice channel handling** (Out of Scope for this phase, because text must be trustworthy first).

### Competitive Analysis

Three approaches exist in this space, and this product's position is defined against them:

- **Traditional knowledge-base search inside a contact-center suite.** Returns documents, not answers, and leaves the reading and interpreting to the agent under time pressure. Strong on governance and audit; weak on speed and on any language the interface was not built for. Lesson taken: keep their governance discipline — approval, versioning, audit — and add the answering.
- **General-purpose assistants applied to support.** Fast and fluent, weak on provenance, and prone to a confident answer where none is warranted. Lesson taken: the citation requirement (BR-1) and the enforced no-answer path (REQ-005) are exactly the guards this class of product lacks, and they are what makes the product usable in a regulated domain.
- **Public-sector helpdesk portals with static FAQ pages.** Trustworthy and cheap, but they answer only the questions someone thought to write down, are rarely available in regional languages, and go stale invisibly. Lesson taken: the gap queue (REQ-011) and staleness marking (REQ-010) are the mechanisms that keep a knowledge base from becoming exactly this.

No competitor reviewed combines enforced citation, regional-language parity and an explicit ignorance path. That combination is this product's position.

### User Research

No primary user research has been conducted for this specific contact center. The personas here are constructed from the issued problem statement, the publicly observable structure of the domain's source material, and general contact-center role structure. This is stated plainly rather than dressed as findings — see Assumption A-1 and Open Question OQ-1, which together define what must be gathered to replace this section with real data. The first two weeks of operation (Phase 0) are the earliest point at which any figure in this document can be checked against reality.

### Market Data

The user base is the population of businesses interacting with India's commerce and industry administration — exporters, importers, MSMEs and their intermediaries — a base that is large, growing, and predominantly non-English-first outside the metros. Exact figures have not been sourced for this document and are deliberately not invented here; the roadmap does not depend on a market-size claim, since the deployment is a fixed helpdesk serving a defined contact volume rather than a product seeking a market.
