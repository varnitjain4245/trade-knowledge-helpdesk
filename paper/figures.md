# Figure specifications

Two figures, matching the reference paper's convention (Fig. 1 architecture, Fig. 2 data
flow). Both are described here as diagrams to be drawn in the paper's own template.

## Fig. 1 — Answer pipeline with its governing rules

The point of the diagram is that the rules are positions in the pipeline, not annotations
on it. Draw it as a vertical flow with the two decision diamonds placed where they
actually sit, because their *order* is the contribution.

```
                     ┌──────────────────┐
                     │  Question        │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ Coverage &       │   public surface only
                     │ fair-use gate    │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ Language check   │   enabled languages only
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ Answer cache     │   keyed on generation counter
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ BM25 retrieval   │   answerable records only  ── R5
                     │ + expansion      │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ Relevance        │   confidence is derived here,
                     │ judging          │   not from lexical overlap
                     └────────┬─────────┘
                              ▼
                        ╱───────────╲
                       ╱ Contradict? ╲──── yes ──▶ show both, choose neither
                       ╲             ╱             ── R2: BEFORE the bar
                        ╲───────────╱
                              │ no
                              ▼
                        ╱───────────╲
                       ╱ ≥ answer    ╲──── no ───▶ refuse, offer a person
                       ╲   bar?      ╱             ── R4: returned as success
                        ╲───────────╱
                              │ yes
                              ▼
                     ┌──────────────────┐
                     │ Generation       │
                     └────────┬─────────┘
                              ▼
                        ╱───────────╲
                       ╱  Grounded?  ╲──── no ───▶ discard draft,
                       ╲             ╱             quote record verbatim ── R3
                        ╲───────────╱
                              │ yes
                              ▼
                     ┌──────────────────┐
                     │ Citations        │   non-empty by construction ── R1
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ Persist, then    │   an unrecorded answer is not shown
                     │ return           │
                     └──────────────────┘
```

**Caption.** Fig. 1. Answer pipeline. Rules R1–R5 are enforced at the marked positions.
Contradiction detection precedes confidence thresholding, so a disagreement is reported
irrespective of either record's score; grounding failure suppresses the draft rather than
annotating it.

## Fig. 2 — Record lifecycle and immediate supersession

```
   processing ──▶ pending review ──▶ approved ──▶ stale
        │               │               │  │        │
        ▼               ▼               │  │        │
     failed          rejected           │  └────────┴──▶ retired
        │                               │                   ▲
        └──▶ (resubmission)             └──▶ superseded ─────┘
                                                 │
                                                 └──▶ approved (reversal, reason required)

   answerable set = { approved, stale }

   every transition ──▶ generation counter += 1  (same transaction)
                    ──▶ audit record             (same transaction)
                    ──▶ all cached answers unreachable
```

**Caption.** Fig. 2. Record lifecycle. Only approved and stale records may be cited. A
stale record continues to answer with a review-pending indication. Every transition
increments a generation counter within the same transaction as the state change and as
the audit write, so supersession takes effect on the next answer and no cached answer can
outlive the knowledge state that produced it.
