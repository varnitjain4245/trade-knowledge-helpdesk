# Example: Well-Structured PRD

This example demonstrates a properly completed PRD, using the current template structure, for reference. Not every section is fully expanded (to keep this example readable) — a real PRD would flesh out all of them.

## Engineering Digest (Example)

> Written last, placed first. No narrative — just what an engineering lead needs to scope the work.

**Features at a glance:**
- One-Tap Payment Request — send a payment request to a present customer in one tap
- Tap-Card-to-Phone — accept a physical card tap when the customer has no smartphone on hand
- Split Payment — divide one request across up to 4 payers

**Hard numbers:**
- Request creation: <10s (based on target parity with handing over a paper receipt — see Non-Functional Requirements)
- Payment confirmation to both parties: <30s (based on card-network confirmation SLA)
- Payment success rate: >98% (based on industry-standard card-processing benchmarks)
- 10,000 active merchants in 6 months / $50M monthly volume by month 12 [PROPOSED: pending eng + finance confirmation — see Open Questions]

**Must-Haves with unresolved dependencies:**
- None. (Split Payment's payer cap depends on an Open Question, but the feature ships with a provisional cap of 4 rather than blocking on it — see Open Questions.)

**Estimation Blockers:**
- Card-network certification timeline is not yet confirmed — see Estimation Blockers below.

---

## Executive Summary (Example)
Tapace lets small business owners accept card payments using only a smartphone — no hardware, no contract, no waiting. It targets solo service providers who currently lose sales to customers without cash. Launching the MVP unlocks an estimated $50M in previously-missed monthly transaction volume across our existing merchant base within a year.

---

## Problem Statement (Example)

### Context
Small business owners running service businesses (cleaning, tutoring, personal training) typically collect payment in person, immediately after service, often at a customer's home or a public location.

### Problem
Small business owners lose an average of $2,400 annually in sales because they can only accept cash or checks. 73% of consumers prefer card payments, and businesses without card acceptance miss 1 in 4 sales opportunities. Existing card-acceptance solutions require expensive hardware ($300+), complex contracts, and take 2-3 weeks to set up — all of which are mismatched to how these businesses actually operate.

### Why Now
Smartphone-based tap-to-pay technology has matured enough that no additional hardware is required, removing the single biggest historical barrier to entry for this segment.

### Domain Invariants Gate (Example)
Table-stakes items a 15-year payments practitioner would expect, and how each is resolved:
- **PCI compliance for card data handling** → covered by Non-Functional Requirements (Security & Privacy)
- **Chargeback/dispute handling** → Out of Scope for MVP: disputes route to existing card-network process; in-app dispute management is Future Scope
- **Refunds** → Must-Have, see Functional Requirements (not expanded in this excerpt)
- **Tax/receipt requirements for the merchant's own bookkeeping** → Out of Scope for MVP, reason: merchants already reconcile through their existing bookkeeping tools; revisit if support tickets indicate otherwise
- **Card-network certification before going live** → Estimation Blocker, see below
- **Fraud/dispute liability shift rules** → covered by Non-Functional Requirements (Security & Privacy) in conjunction with card-network contract terms

## Goals (Example)

### Product Goals
- Let a solo business owner start accepting card payments the same day they decide to
- Make the payment moment feel as fast and natural as handing over a receipt
- Remove hardware and contracts as a barrier to entry

### Non-Goals
- This is not attempting to replace full point-of-sale systems for retail storefronts with inventory needs
- This is not aiming to support in-person cash-back or tipping-pool splitting in the first release

## Stakeholders (Example)

| Stakeholder | Role | Interest / Stake | Approval Needed? |
|---|---|---|---|
| VP of Product | Sponsor | Owns the merchant-growth roadmap this ships under | Yes |
| Payments Compliance Lead | Reviewer | Ensures the flow meets card-network and regulatory rules | Yes |
| Merchant Support Lead | Stakeholder | Will field the support tickets this generates | No, consulted |

---

## User Personas (Example)

### Primary Persona: Sarah the Solo Entrepreneur
- **Demographics:** Age 28-45, runs a service business (cleaning, tutoring, personal training), moderate tech comfort, uses smartphone daily
- **Goals:** Accept payment immediately after service, look professional to clients, minimize time spent on admin tasks
- **Pain Points:** Loses clients who don't carry cash, awkward payment conversations, delayed payments hurt cash flow
- **Formal User Stories:**
  - As a solo entrepreneur, I want to request payment with one tap, so that I get paid before the client leaves
  - As a solo entrepreneur, I want confirmation that payment succeeded, so that I don't have to awkwardly ask "did that go through?"

---

## User Flows (Example)

### Flow 1: First-Time Payment Request
- **Persona:** Sarah the Solo Entrepreneur
- **Trigger:** Sarah finishes a service and wants to collect payment on the spot
- **Preconditions:** Sarah has an active account; the customer is physically present

**Main Flow (Happy Path)**
1. Sarah opens the app and enters the amount owed → System displays the amount for confirmation
2. Sarah taps "Request Payment" → System generates a payment request and prompts for a delivery method
3. Sarah selects "text this phone" and hands her phone to the customer, or reads a code aloud → System sends the request
4. Customer confirms payment on their own device → System processes payment and notifies both parties within 30 seconds
5. Sarah sees "Paid" confirmation → Flow ends successfully

**Alternate Flows / Branches**
- **Branch A — customer has no smartphone on hand:** Sarah selects "tap card to phone" instead of sending a request; customer taps their physical card against Sarah's phone; flow rejoins at step 4.
- **Branch B — customer wants to split payment:** Sarah selects "split," enters number of payers; System generates one request per payer; flow rejoins at step 4 once all payers confirm.

**Error / Exception Flows**
- **If the customer's payment method is declined** → System notifies Sarah immediately with a plain-language reason → Sarah can request an alternate payment method or mark the amount as still owed.
- **If the request times out with no customer response (5 minutes)** → System cancels the request and notifies Sarah → Sarah can resend or collect payment another way.

**Postconditions / Success State**
Payment is confirmed to both parties, and the transaction appears in Sarah's activity log within 30 seconds.

**Related Edge Cases**
Declined payment method; request timeout; split-payment partial completion (see Edge Cases).

---

## Functional Requirements (Example)

### Must Have Features

#### Feature 1: One-Tap Payment Request
- **User Story:** As Sarah, I want to send a payment request with one tap so that I can get paid immediately after finishing a service
- **Acceptance Criteria:**
  - [ ] WHEN Sarah taps "Request Payment" with a valid amount entered, THE SYSTEM SHALL create the request in under 10 seconds
  - [ ] WHEN a customer confirms payment, THE SYSTEM SHALL notify both parties within 30 seconds
  - [ ] IF a payment request goes 5 minutes without customer action, THEN THE SYSTEM SHALL cancel the request and notify Sarah

## Non-Functional Requirements (Example)
- **Performance:** Payment confirmation must reach both parties within 30 seconds of customer action (based on card-network confirmation SLA)
- **Reliability:** Payment success rate must exceed 98% under normal network conditions (based on industry-standard card-processing benchmarks)
- **Usability:** A first-time user must be able to complete a payment request without instructions [PROPOSED: pending usability-testing confirmation]
- **Security & Privacy:** Customers' payment details are never visible to the merchant; only the transaction outcome is shown (based on card-network merchant-facing data rules)

---

## MVP Scope (Example)
One-tap payment request, tap-card-to-phone, and split payment for up to 4 payers, covering Sarah's core in-person collection moment.

## Future Scope (Example)
Recurring/subscription requests and invoicing for unpaid balances — planned for the phase after initial merchant adoption is validated.

## Out of Scope (Example)
Full point-of-sale/inventory management for retail storefronts — this product is scoped to service businesses collecting payment in person, not retail checkout.

## Estimation Blockers (Example)

| # | What can't be sized yet | Why | Owner | Needed by |
|---|---|---|---|---|
| 1 | Card-network certification timeline | Certification review is scheduled by the network, not us, and can take 4-10 weeks depending on their queue | Payments Compliance Lead | End of M1, or MVP timeline slips |
| 2 | Final split-payment payer cap | Depends on Open Question below; ships with a provisional cap of 4 in the meantime | VP of Product | Before Phase 1 code-complete |

---

## Success Metrics (Example)

### Key Performance Indicators
- **Adoption:** 10,000 active merchants in first 6 months (merchants who process at least 1 payment/month)
- **Engagement:** Average 8 transactions per merchant per month
- **Quality:** Payment success rate > 98%, support ticket rate < 2%
- **Business Impact:** $50M monthly payment volume by month 12

### Tracking Requirements
| Event | Properties | Purpose |
|-------|------------|---------|
| payment_request_created | amount, merchant_id, request_method | Measure adoption and behavior |
| payment_completed | amount, time_to_complete, payment_method | Measure success and speed |
| payment_failed | error_code, step_failed | Identify friction points |
| merchant_churned | last_active_date, total_processed | Understand retention |

## Timeline & Roadmap (Example)
| Phase | Milestone | Target Timing | Scope |
|---|---|---|---|
| Phase 1 | MVP launch | Q1 | One-tap request, tap-card-to-phone, split payment |
| Phase 2 | Recurring requests | Q3 | Subscription/invoicing features from Future Scope |

---

## Risks & Constraints (Example)

### Constraints
- Must comply with card-network rules on how payment confirmation is displayed
- Launch budget limits initial marketing to three metro areas

### Assumptions
- Assumes target merchants already own a smartphone with tap-to-pay hardware support
- Assumes customers are comfortable confirming payment on their own device

### Risks
| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Customers distrust tapping their card to a stranger's phone | High | Medium | Add clear on-screen reassurance and a support article; monitor decline/abandon rate at that step |

## Open Questions (Example)
- [ ] What is the maximum number of split payers we should support at launch?
- [ ] Does the compliance team require a minimum on-screen disclosure before card-to-phone tap?

---

## What Makes This PRD Good

1. **Engineering Digest up front** - Features, hard numbers, and blockers extracted to a one-page summary, written last but read first — no persuasive narrative in it
2. **Domain Invariants Gate run explicitly** - Payments-specific table stakes (PCI, chargebacks, fraud liability, certification) are each resolved to a requirement or a reasoned Out-of-Scope entry, not silently omitted
3. **Specific, evidence-backed problem statement** - Includes data (73%, $2,400, 1 in 4 sales)
4. **Clear personas with formal user stories** - Demographics, goals, pain points, and "As a / I want / so that" stories
5. **A fully-branched user flow** - Happy path, alternate branches, and error/exception paths, each with a clear next step
6. **Testable acceptance criteria (EARS format)** - Time limits, specific actions, measurable outcomes
7. **Outcome-based, sourced Non-Functional Requirements** - Describes what users experience, never a technology or mechanism, and every number carries a stated basis or a `[PROPOSED: pending eng confirmation]` marker
8. **Mutually exclusive scope sections** - Every feature lives in exactly one of MVP Scope / Future Scope / Out of Scope
9. **Estimation Blockers named with an owner and a date** - The card-network certification dependency is surfaced instead of being discovered mid-build
10. **Measurable KPIs with matching tracking events** - Numbers, timeframes, and the events needed to verify them
11. **No technical details anywhere** - Doesn't mention databases, APIs, or architecture
12. **User-centric language throughout** - Written from the user's and business's perspective, not the engineering perspective
