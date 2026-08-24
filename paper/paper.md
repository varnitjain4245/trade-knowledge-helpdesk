# Answers That Can Be Checked: A Citation-Grounded Multilingual Knowledge Platform for Government Contact Centres

**Author One**, **Author Two**, **Author Three**, **Author Four**, **Author Five**
Department of Computer Science
[Institution], [City], India
{author.one, author.two, author.three, author.four, author.five}@[institution].edu

---

**Abstract** — Contact centres serving government trade and commerce administration answer questions whose consequences are material: a licence not obtained holds a consignment at port, and a duty rate quoted wrongly becomes a penalty. Existing retrieval-augmented question answering systems optimise for producing an answer, and treat provenance as a display feature appended after generation. This paper proposes a knowledge platform for such contact centres in which provenance is a structural precondition rather than a presentation choice. Four mechanisms distinguish the design: an answer that cannot be attributed to an approved record is unrepresentable in the system's type system rather than merely discouraged; contradiction between records is detected *before* the confidence threshold is applied, so a disagreement is surfaced as a disagreement rather than silently resolved in favour of the higher-scoring source; a generated draft is verified against the passages that produced it and **suppressed** rather than flagged when unsupported; and refusal is a first-class outcome returned with a success status, so that "no reliable answer" is never presented in the visual or protocol language of failure. The system additionally treats retirement of superseded guidance as immediate through a generation counter that invalidates cached answers atomically, gates a public surface behind a declared coverage floor, and supports six Indian languages with per-language enablement contingent on measured correctness. An implementation over a 51-record trade corpus answered 30 of 30 realistic practitioner questions with citations while correctly refusing all out-of-domain questions. We report the defects that measurement exposed, several of which were invisible to component-level testing.

**Keywords** — Retrieval-augmented generation, grounded question answering, provenance, government contact centre, multilingual information access, knowledge governance, trade facilitation

---

## I. INTRODUCTION

Learning management systems, customer service platforms and public helpdesks have all converged on a similar architecture for question answering: retrieve candidate passages from a corpus, condition a language model on them, and return generated prose. This pattern, commonly called retrieval-augmented generation, substantially reduces unsupported assertion relative to unconditioned generation, and its adoption across educational and administrative software has been rapid [1], [2].

The pattern is nonetheless insufficient for a class of application in which the *basis* of an answer matters as much as its content. A contact centre serving India's commerce and industry administration is one such case. Its users are exporters, importers, micro and small enterprises and customs intermediaries; its subject matter is licensing, tariff classification, goods and services tax, incentive schemes and e-commerce obligation. The material is issued continuously by multiple authorities as circulars, notifications and public notices, amended frequently, and published as documents rather than as answers.

Four properties of this setting are not addressed by conventional retrieval-augmented question answering.

**Consequence asymmetry.** A wrong answer is not a poor user experience; it is a held consignment, a forfeited incentive, or a penalty. The cost of a confident error greatly exceeds the cost of an admitted gap. Systems tuned to maximise answer rate optimise the wrong quantity.

**Amendment.** Guidance in this domain expires by supersession rather than by age. When a public notice reverses the licensing status of a commodity, every prior answer becomes wrong at a specific instant. A system that caches answers, or that embeds knowledge in model weights, cannot retire guidance at that instant.

**Contradiction.** Multiple authorities issue overlapping material, and a corpus of any size contains records that disagree. Presenting the higher-ranked one as the answer conceals a decision the system is not competent to make.

**Language.** A substantial fraction of the user population is more fluent in a language other than English, and often more fluent speaking than reading. A system that answers only in English, or that answers in an Indian language without being measured in it, serves a subset of its users while appearing to serve all of them.

This paper proposes a system in which these four properties are architectural commitments rather than features. Section II reviews related work. Section III describes the proposed system and its governing rules. Section IV describes the answering pipeline in detail. Section V reports measured results, including defects that measurement exposed. Section VI discusses outcomes and impact, and Section VII concludes.

---

## II. RELATED WORK

Retrieval-augmented generation grounds a language model's output in retrieved documents and is now the dominant architecture for question answering over a private corpus [1], [2]. Adaptive learning platforms have integrated large language models to personalise instruction and provide continuous feedback [1], demonstrating that a retrieval-grounded assistant can be embedded in an institutional workflow. The literature reports substantial reduction in unsupported assertion relative to unconditioned generation.

Reported evaluation nonetheless concentrates on answer quality and user engagement rather than on the verifiability of individual claims. Where citation is discussed, it is generally treated as a presentation feature: the retrieved passages are displayed alongside a generated answer, without a mechanism guaranteeing that the answer's claims are entailed by those passages. Recent work on attribution has begun to address this gap by scoring whether generated statements are supported by cited sources, but the resulting signal is typically surfaced as a confidence indicator rather than used to withhold output.

Gamification and engagement research in learning platforms demonstrates that system design shapes user behaviour in ways beyond the informational [3], [4], [6]. This finding transfers to the present setting with an inverted sign: a helpdesk whose refusals are styled as errors teaches its users that "I do not know" means "the system is broken", and thereby erodes trust in the refusals that protect them. The visual and protocol treatment of a refusal is therefore a correctness concern, not a cosmetic one.

Modular client-server architectures are widely adopted for scalability and independent evolution of interface and logic [2], [5], and the present system follows that convention. Bibliometric analysis of two decades of learning management system research documents both breadth of adoption and a persistent gap between content delivery and meaningful engagement [7]; the analogous gap in an administrative helpdesk is between document delivery and an answer a user can act upon with confidence.

The contribution of this paper is therefore not retrieval-augmented generation itself, which is established, but a set of governance mechanisms layered upon it: structural enforcement of citation, ordering of contradiction detection before confidence thresholding, suppression rather than annotation of unsupported generation, and treatment of refusal as a successful outcome.

---

## III. PROPOSED SYSTEM

### A. Governing Rules

The system is specified by rules that hold for every answer on every surface. They are stated here because the architecture follows from them rather than the reverse.

**R1 — Citation is a precondition.** An answer that cannot be attributed to at least one approved record is not shown. This is enforced at the type level: the result type representing a successful answer carries a non-empty citation collection, so a citation-free answer cannot be constructed.

**R2 — Contradiction precedes confidence.** Detection of disagreement between records occurs before the confidence threshold is applied. Two records that contradict each other are presented as a contradiction irrespective of either one's score.

**R3 — Unsupported generation is suppressed.** A generated draft is verified sentence-by-sentence against the passages supplied to the generator. A draft that fails is discarded, not annotated, and an extractive answer quoting the record verbatim is returned in its place.

**R4 — Refusal is an outcome, not an error.** "No reliable answer" is returned with a success status and rendered as content. Refusals are never presented in the visual or protocol vocabulary of failure.

**R5 — Answerability is decided at query time.** An item's eligibility to be cited is read from its lifecycle status inside the retrieval query itself. Retirement therefore takes effect on the next answer with no index rebuild or cache sweep.

### B. Architecture

The system follows a modular client-server architecture [2], [5]. Three browser-based surfaces — an agent console, a public assistant, and a curation and oversight console — communicate with a service layer over a documented interface. The service layer comprises a retrieval component, a relevance judging component, a generation component with two interchangeable strategies, a grounding verifier, a contradiction detector, and a lifecycle service governing the corpus. Persistent state is held in a relational store; corpus records, their lifecycle status, user accounts and the audit record share a single transactional boundary.

A single component is the sole producer of answers. Every surface calls it, which is what makes rules R1 to R4 enforceable at one point rather than replicated across three consumers and liable to drift between them.

### C. Corpus Governance

Records progress through an explicit lifecycle: processing, pending review, approved, stale, superseded, retired, rejected. Only *approved* and *stale* records are answerable. A stale record — one past its review date — continues to answer while carrying a review-pending indication, on the reasoning that dated guidance accompanied by a warning serves a user better than silence, provided the warning is present.

Supersession takes effect immediately. A monotonic generation counter is incremented within the same database transaction as any lifecycle change, and every cached answer is keyed on that counter. A change therefore renders all prior cache entries unreachable atomically, with no invalidation scan to implement incorrectly. Where the counter cannot be read, the cache is bypassed rather than trusted, so a database outage cannot cause a stale answer to be served against an unverifiable knowledge state. The lifecycle and its transitions are shown in Fig. 2.

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

**Caption.** Fig. 2. Record lifecycle. Only approved and stale records may be cited. A stale record continues to answer with a review-pending indication. Every transition increments a generation counter within the same transaction as the state change and as the audit write, so supersession takes effect on the next answer and no cached answer can outlive the knowledge state that produced it.

---

## IV. WORKING PRINCIPLE OF THE PROPOSED SYSTEM

Fig. 1 shows the answer pipeline and the position at which each rule of Section III.A takes effect. The ordering is the contribution: contradiction detection precedes the confidence threshold, and grounding verification precedes citation assembly.

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

**Caption.** Fig. 1. Answer pipeline. Rules R1–R5 are enforced at the marked positions. Contradiction detection precedes confidence thresholding, so a disagreement is reported irrespective of either record's score; grounding failure suppresses the draft rather than annotating it.

### A. Retrieval

Retrieval combines a lexical index with domain-specific query expansion. Passages are indexed under BM25 with the record title weighted into the document representation; a record whose title matches a query but whose body does not would otherwise be unreachable, a defect observed during development and reported in Section V.

Three transformations proved necessary on the query side. Light suffix stemming with an irregular-form table unifies inflections, without which a question asking whether a buyer is *paying* fails to reach a record stating when a buyer must *pay*. Acronym expansion maps the forms practitioners actually type — IEC, RoDTEP, TReDS, SCOMET — to the expanded terms records use. Hyphenated compounds are normalised so that *ecommerce* meets *e-commerce*.

Candidate scores are attenuated by the square root of the proportion of query terms a passage addresses. Unattenuated BM25 rewards a single rare term heavily, which permits a lookalike record to answer on one shared word.

### B. Relevance Judging

BM25 answers which passages share vocabulary with a query. This is a different question from which passage *answers* it, and the gap between the two is the source of a specific failure mode: asked to define one technical term, lexical retrieval returns a record about a different term sharing one word, at maximum confidence. No lexical threshold separates these cases, because the deficiency is in what the score measures rather than in its magnitude.

The system therefore derives confidence from a relevance judging stage that scores whether each candidate answers the question asked, discriminating a record about a similar-sounding but different instrument from one that is responsive. Candidates are judged in a single batched call. Where judging is unavailable, confidence is capped below the answer threshold rather than falling back to the lexical score — a lexical score is evidence of shared vocabulary, and admitting it as relevance confidence is what permits an unrelated question to be answered confidently.

### C. Contradiction Detection

Contradiction detection runs on the judged candidate set before thresholding. Two records are treated as contradictory when they exhibit high topical overlap together with a polarity asymmetry — a negation or exemption marker present on one side only — and when their scores are comparable. The comparability requirement matters: without it, a weak tangential passage containing a negation can veto a strong well-supported answer, withholding good information in the name of caution.

Where a contradiction is found, both records are returned with their issuing authorities and issue dates, and the system explicitly declines to choose. A contradiction is never counted as an answer for the purpose of service metrics.

### D. Generation and Grounding

Generation is a strategy behind a single interface, with two implementations: a language model conditioned on the retrieved passages, and an extractive strategy returning the highest-ranked passage verbatim. The second is not an error path but a designed degradation: it is the operating mode where no model is available, and the destination of every failure in the generation path.

Every generated draft is verified before display. Each sentence is checked for lexical support within a *single* passage — not the union of passages, since a claim assembled from fragments of several sources is supported by none of them. A draft is accepted only when coverage exceeds a threshold *and* no sentence is unsupported; high aggregate coverage with one unsupported sentence still constitutes an answer containing a claim the sources do not make. A failed draft is discarded and the extractive strategy substituted.

### E. Multilingual Operation

Six languages are supported. A language is enabled only when it has cleared a measured correctness threshold on its own portion of an acceptance set; until then the system states that support is in preparation rather than answering in it badly. Enabling a language requires an acceptance score to be recorded, since an enablement with no recorded measurement is indistinguishable from ignoring the gate.

The quoted passage always appears in its source language, labelled, and is never translated: a translated quotation is no longer evidence. Interface typography is keyed on *script* rather than language, because Devanagari and Tamil require greater line height than Latin at equal nominal size, and Hindi and Marathi share a script — a mapping keyed on language would require both to be enumerated and would silently omit any future language in that script.

### F. Voice Interaction

A hands-free conversational mode addresses a user population more fluent speaking than typing, and for whom composing a question in Devanagari or Tamil on a mobile keyboard is itself a barrier to asking. The loop is explicit: listen until a natural pause, transcribe, answer, speak, listen again. The system does not listen while speaking, which would transcribe its own output. What is spoken differs from what is displayed: a citation's file reference and issue date support visual checking, and reading them aloud buries the answer, so the source is named once in prose.

### G. Self-Updating Knowledge

Questions the system cannot answer are logged, and a record may be drafted automatically so that the same question is answerable subsequently. Two constraints govern this.

First, a machine-drafted record carries its own authority attribution and is visually distinguished wherever cited. Auto-drafted knowledge that is indistinguishable from a published circular would defeat the entire provenance argument.

Second, drafting is refused for any question turning on a specific figure — a rate, ceiling, deadline or monetary threshold. A model asked for such a figure will supply one, and a plausible invented number is precisely the harm the citation rule exists to prevent. The refusal and its reason are displayed rather than hidden.

---

## V. RESULTS AND DISCUSSION

### A. Experimental Setting

The corpus comprises 51 records and 107 passages spanning registration, customs procedure, taxation, micro and small enterprise finance, e-commerce obligation, standards and trade policy. Procedures, terminology and document structures follow the administration's actual practice; specific rates and thresholds are illustrative and marked as such throughout the interface. Evaluation used a set of 30 questions written in the phrasing a practitioner would use, together with a control set of out-of-domain questions.

### B. Answer Rate and Refusal Accuracy

TABLE I. OUTCOME DISTRIBUTION ON THE EVALUATION SET

| Question class | n | Answered with citation | Contradiction | Refused |
|---|---|---|---|---|
| In-domain practitioner questions | 30 | 30 | 0 | 0 |
| Deliberate contradiction | 1 | 0 | 1 | 0 |
| Out-of-domain control | 6 | 0 | 0 | 6 |

Every in-domain question was answered with at least one citation naming an issuing authority and issue date. Every out-of-domain question was refused. The deliberately contradictory pair was surfaced as a contradiction rather than resolved.

### C. Ablation of the Relevance Judge

TABLE II. EFFECT OF THE CONFIDENCE SOURCE

| Confidence source | In-domain answered | Out-of-domain incorrectly answered |
|---|---|---|
| Lexical (BM25 + coverage) | 27/30 | 3/6 |
| Relevance judging | 30/30 | 0/6 |

With lexical confidence alone, three out-of-domain questions were answered from topically adjacent records at maximum confidence — including one general-knowledge question answered from a trade policy record. Lowering the threshold to admit more in-domain questions increased this error; raising it suppressed valid answers. The failure was not in the threshold's value but in the quantity being thresholded. Substituting relevance judging permitted the threshold to be restored to its original specified value while eliminating the errors.

### D. Defects Exposed by Measurement

Several defects survived component-level testing and were exposed only by end-to-end measurement. They are reported because their character is instructive.

**Title-only records were unreachable.** Retrieval indexed passage bodies while the reranker scored bodies alone; a record naming its subject only in its title was retrieved and then reordered away, causing a different record to be cited. Component tests passed because each stage was individually correct.

**Cache rehydration lost type information.** Cached citations serialised to JSON returned dates as strings, causing failure on the cache-hit path only. Eighteen unit tests passed throughout because none asserted on the *types* of a rehydrated citation.

**Inflection blocked retrieval.** A question using one verb form failed to reach a record using another, while a near-identical question succeeded — a discrepancy invisible to any single test case.

**Blocked outcomes were recorded as refusals.** A surface closed by policy produced both a policy message and a "no reliable answer" message, and incremented the counter that triggers automatic escalation. Two distinct conditions had been conflated in the outcome model.

**Weak passages vetoed strong answers.** An early contradiction heuristic required *low* vocabulary overlap, inverting the intended signal: genuine contradictions exhibit *high* overlap with a polarity difference. The heuristic would have missed every real contradiction.

### E. Latency

TABLE III. STAGE LATENCY BUDGET

| Stage | Budget (ms) | Degradation on timeout |
|---|---|---|
| Language detection | 30 | Fall back to selected language |
| Query embedding | 120 | Lexical retrieval only |
| Retrieval | 250 | Report assist unavailable |
| Relevance judging | 400 | Cap confidence below threshold |
| Contradiction detection | 50 | Treat as no contradiction |
| Generation, first token | 700 | Extractive strategy |
| Generation, complete | 2500 | Truncate at sentence boundary |
| Grounding verification | 150 | Suppress draft, use extractive |
| Persistence and audit | 100 | Fail request; answer not shown |

Stage budgets sum to 4 350 ms against a 5 000 ms target. Per-stage timeouts alone proved insufficient: their sum substantially exceeds the target, so several stages running slowly without individually timing out can breach it. A whole-request deadline was added, clamping each stage to the remaining budget and declining to begin generation it cannot complete. Every degradation resolves toward showing less rather than showing something unverified.

### F. Limitations

Retrieval is lexical, so a question phrased distantly from the corpus vocabulary may be refused although the answer is present. Relevance judging depends on an external model and degrades to refusal when unavailable — a safe failure, but a reduction in service. The corpus is illustrative and small; the reported answer rate characterises the mechanism, not performance at production corpus scale. Correctness was assessed by the authors against known-correct records rather than by independent domain assessors. Per-language correctness was not separately measured, which is why the enablement gate exists rather than being assumed satisfied.

---

## VI. EXPECTED OUTCOMES AND IMPACT

**Verifiability as a default.** Every answer carries the record it came from, its issuing authority and its issue date. A user can check the basis of guidance rather than trusting it, and a supervisor reviewing a disputed answer can reconstruct what was shown and on what basis. The audit record is append-only, enforced by withholding the database privilege rather than by application discipline.

**Reduced confident error.** Refusal is designed to be inexpensive and unembarrassing for the system, and every degradation path resolves toward showing less. In a domain where a wrong answer produces a held consignment or a forfeited incentive, the asymmetry between an admitted gap and a confident error justifies this bias.

**Amendment takes effect immediately.** Retiring a superseded record removes it from the next answer, including from answers already cached. Where guidance is amended continuously, this is the difference between a knowledge base and an archive.

**Contradiction becomes visible work.** Records that disagree surface as a disagreement and enter a queue for human resolution, rather than being silently resolved by ranking.

**Access widens.** Six languages with per-script typography and hands-free voice interaction extend the service to users for whom a keyboard in an unfamiliar script is a barrier. The enablement gate ensures that widening access does not mean answering badly in a language that has not been measured.

**Institutional knowledge accumulates.** Questions that cannot be answered are logged rather than lost, and may be drafted into records, while questions turning on specific figures are deliberately reserved for human authorship.

---

## VII. CONCLUSION

This paper has argued that for question answering in a consequential administrative domain, provenance must be an architectural precondition rather than a presentation feature. The proposed system enforces four rules structurally: citation is required for an answer to exist, contradiction is detected before confidence is thresholded, unsupported generation is suppressed rather than annotated, and refusal is a successful outcome rather than an error.

Measurement over a trade corpus showed every in-domain question answered with citation and every out-of-domain question refused, and demonstrated that the choice of *what* confidence measures — rather than the threshold applied to it — determines whether unrelated questions are answered. Several defects were exposed only by end-to-end measurement while passing component-level tests, which suggests that systems making guarantees of this kind require tests asserting on the guarantee itself rather than on the correctness of each stage.

Future work includes semantic retrieval to reduce refusals caused by vocabulary mismatch, independent domain-expert assessment of answer correctness, per-language measurement to populate the enablement gate with evidence, and evaluation at production corpus scale where contradiction between records is common rather than deliberately introduced.

---

## REFERENCES

[1] K. Spriggs, M. C. Lau, K. Passi, and L. Zhang, "Personalizing Education through an Adaptive LMS with Integrated LLMs," *arXiv preprint* arXiv:2502.08655, 2025.

[2] J. P. B. Saputra, H. Prabowo, F. L. Gaol, and G. F. Hertono, "Development of Gamification-Based Learning Management System (LMS) with Agile Approach and Personalization of FSLSM Learning Style to Improve Learning Effectiveness," *Journal of Applied Data Sciences*, vol. 6, no. 1, pp. 714–725, 2025.

[3] E. T. Setyoadi, S. Patmanthara, H. W. Herwanto, H. Junaedi, and T. Rahmawati, "A Review of Learning Management System Enhanced by Gamification Through Push Pool Mooring Model," *IRDH International Journal of Technology, Agriculture Natural Sciences*, vol. 2, no. 1, 2025.

[4] K. Nazokat, "The Role of Digital Gamification in Enhancing Student Motivation," *International Multidisciplinary Journal for Research Development*, vol. 12, no. 1, 2025.

[5] K. N. H., "E-Learning Management Systems: Best Practices for Implementation," *Research Invention Journal of Current Issues in Arts and Management*, vol. 4, no. 2, pp. 43–47, 2025.

[6] M. Ortiz-Rojas, K. Chiluiza, M. Valcke, and C. Bolanos-Mendoza, "How Gamification Boosts Learning in STEM Higher Education: A Mixed Methods Study," *International Journal of STEM Education*, vol. 12, no. 1, 2025.

[7] T.-T. T. Phan, C.-T. Vu, P.-T. T. Doan, D. Luong, T. Bui, T.-H. Le, and D. Nguyen, "Two Decades of Studies on Learning Management System in Higher Education: A Bibliometric Analysis with Scopus Database 2000–2020," *Journal of University Teaching Learning Practice*, vol. 19, no. 3, 2022.

[8] A. Malik, G. Dargar, A. Sharma, and P. Pandey, "Predictive Analysis for Retail Shops using Machine Learning for Maximizing Revenue," in *Proc. 7th Int. Conf. Intelligent Computing and Control Systems (ICICCS)*, Madurai, India, 2023, pp. 126–133.

[9] A. Sharma, R. P. Mahapatra, and V. K. Sharma, "An exploration of Fog procedures in comparison with IoT, design, and assessment issues," in *Proc. 10th Int. Conf. Reliability, Infocom Technologies and Optimization (ICRITO)*, Noida, India, 2022, pp. 1–6.

[10] A. Sharma, A. Vashishta, A. Shahi, A. Saxena, and H. K. Gulati, "Study of Video Suggestions based on Calendar Events," in *Proc. 6th Int. Conf. Intelligent Computing and Control Systems (ICICCS)*, Madurai, India, 2022, pp. 1572–1579.
