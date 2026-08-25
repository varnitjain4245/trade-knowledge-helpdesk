# Answers That Can Be Checked: A Citation-Grounded Multilingual Knowledge Platform for Government Contact Centres

Varnit Jain, Tanu, Yash Yadav, Swarna Chaudhary, Prof. Sunil
Computer Science
KIET Group of Institutions, Ghaziabad, Delhi-NCR, India

---

**Abstract** — Contact centres serving government trade administration answer questions whose consequences are material: a licence not obtained holds a consignment at port, and a duty rate quoted wrongly becomes a penalty. Existing retrieval-augmented question answering systems optimise for producing an answer and treat provenance as a display feature appended after generation. This paper proposes a platform in which provenance is a structural precondition. An answer that cannot be attributed to an approved record is unrepresentable in the type system; contradiction between records is detected *before* the confidence threshold, so disagreement is surfaced rather than silently resolved in favour of the higher-scoring source; an unsupported draft is **suppressed** rather than flagged; and refusal is a first-class outcome returned with a success status. We further report a conflict these mechanisms make unavoidable — a sentence in one language cannot be lexically verified against a passage in another — and resolve it by ordering rather than by weakening either property: generation and verification occur in the passage language, only verified text is translated, and the cited passage is never translated at all. This raised script fidelity from 0.00 to between 0.80 and 1.00 across four languages while citation integrity remained 1.00 throughout; a fifth language that fails its threshold is reported and withheld. An implementation over a 51-record trade corpus answered 30 of 30 practitioner questions with citations, refused all out-of-domain questions, and scored 1.00 faithfulness under reference-free evaluation. We report the defects measurement exposed, including a class we name *claims without mechanisms*: properties the system asserted that no code enforced and no test could fail.

*Index Terms* — Retrieval-augmented generation, grounded question answering, provenance, cross-language information retrieval, government contact centre, multilingual information access, knowledge governance, trade facilitation

---

## I. INTRODUCTION

Public helpdesks and enterprise search systems have converged on a common architecture for question answering over a private corpus: retrieve candidate passages, condition a language model on them, return generated prose [1], [2]. The pattern reduces unsupported assertion relative to unconditioned generation, whose failure modes are documented at length [3], and its adoption across administrative software has been rapid.

The pattern is insufficient where the *basis* of an answer matters as much as its content. A contact centre serving India's commerce and industry administration is such a case. Its users are exporters, importers, micro and small enterprises and customs intermediaries; its subject matter is licensing, tariff classification, goods and services tax, incentive schemes and e-commerce obligation. The material is issued continuously by multiple authorities as circulars, notifications and public notices, amended frequently, and published as documents rather than as answers.

Four properties of this setting are not addressed by conventional retrieval-augmented question answering. **Consequence asymmetry:** a wrong answer is not a poor user experience but a held consignment, a forfeited incentive or a penalty, so the cost of a confident error greatly exceeds that of an admitted gap, and systems tuned to maximise answer rate optimise the wrong quantity. **Amendment:** guidance expires by supersession rather than by age, and a system that continues citing a reversed notice is worse than one that admits ignorance. **Contradiction:** two authorities can disagree, and presenting the higher-ranked one as the answer conceals a decision the system is not competent to make. **Language:** a substantial fraction of users is more fluent in a language other than English, and a system answering only in English, or answering in an Indian language without being measured in it, serves a subset of its users while appearing to serve all.

This paper proposes a system in which these properties are architectural commitments rather than features. Section II reviews related work; Section III the governing rules and architecture; Section IV the answering pipeline; Section V measured results, including the defects measurement exposed; Section VI outcomes; Section VII concludes.

---

## II. RELATED WORK

Conditioning a generator on retrieved passages gives a model access to knowledge it was not trained on [1] and is now standard for question answering over a private corpus [2]. Retrieval reduces unsupported assertion [3] without eliminating it, because nothing in the architecture requires a generated sentence to follow from the passages supplied.

The gap between citing a source and being supported by it is formalised as attribution, with a definition and annotation protocol for deciding whether a statement is entailed by the source ascribed to it [4]; automated frameworks score a related notion of faithfulness per response [11], and benchmarks exist for citation quality in generated text [15]. In each case the signal is a *measurement*, computed after generation and reported alongside the answer. This system differs in what the signal is used for: a draft failing verification is discarded rather than annotated. Verification is a gate, not a metric.

Retrieval here combines probabilistic lexical ranking [5] with judging by a language model, whose agreement with human assessment and characteristic biases are documented [7] and which supersedes the fine-tuned cross-encoder originally used for the purpose [6]. Rewriting a query before retrieval helps retrieval-augmented systems generally [14] and is standard for retrieving documents written in another language, where the translation exists to find documents rather than to be read [13]. Declining to answer below a calibrated confidence is studied as selective prediction [8], which does not address how an abstention should be *delivered* — treated here as a correctness concern. Where passages disagree, models are receptive to coherent external evidence yet show confirmation bias when part of the context agrees with parametric knowledge [9], so generating from the highest-scoring passage resolves disagreements silently.

Multilingual representations for the major Indian languages exist [10], but availability of a model is not evidence that a pipeline answers correctly in a given language. Ratings are informative yet biased, more reliably read as relative evidence than absolute labels [16], and human-in-the-loop arrangements formalise what a system decides automatically and what it defers [17]. Review of e-government chatbots finds deployments largely confined to simple informational responses, with transparency and trust the recurring barriers [12].

The contribution is not retrieval-augmented generation [1], [2], nor attribution measurement, which is defined [4] and benchmarked [15]. It is the enforcement of those ideas as structural properties of a serving system — citation unrepresentable in its absence, contradiction ordered before confidence, grounding failure resolved by suppression, refusal returned as success, answerability read from a record's lifecycle at query time — together with the ordering of verification and translation reported in Section IV.F.

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

The system follows a modular client-server architecture. Three browser-based surfaces — an agent console, a public assistant, and a curation and oversight console — communicate with a service layer over a documented interface. The service layer comprises a retrieval component, a relevance judging component, a generation component with two interchangeable strategies, a grounding verifier, a contradiction detector, and a lifecycle service governing the corpus. Persistent state is held in a relational store; corpus records, their lifecycle status, user accounts and the audit record share a single transactional boundary.

A single component is the sole producer of answers. Every surface calls it, which is what makes rules R1 to R4 enforceable at one point rather than replicated across three consumers and liable to drift between them.

### C. Corpus Governance

Records progress through an explicit lifecycle: processing, pending review, approved, stale, superseded, retired, rejected. Only *approved* and *stale* records are answerable. A stale record — one past its review date — continues to answer while carrying a review-pending indication, on the reasoning that dated guidance accompanied by a warning serves a user better than silence, provided the warning is present.

Supersession takes effect immediately. A monotonic generation counter is incremented within the same database transaction as any lifecycle change, and every cached answer is keyed on that counter. A change therefore renders all prior cache entries unreachable atomically, with no invalidation scan to implement incorrectly. Where the counter cannot be read, the cache is bypassed rather than trusted, so a database outage cannot cause a stale answer to be served against an unverifiable knowledge state.

---

## IV. WORKING PRINCIPLE OF THE PROPOSED SYSTEM

Fig. 1 shows the answer pipeline and the position at which each rule of Section III.A takes effect. The ordering is the contribution: contradiction detection precedes the confidence threshold, and grounding verification precedes citation assembly.

```
              question
                 │
                 ▼
          coverage gate ──▶ language check ──▶ cache
                                                │
                                                ▼
                                    retrieval  (R5)
                                                │
                                                ▼
                                    relevance judging
                                                │
                                                ▼
                            contradiction? ── yes ──▶ show both,
                                (R2)                 choose neither
                                                │ no
                                                ▼
                            ≥ answer bar? ── no ──▶ refuse,
                                (R4)                as success
                                                │ yes
                                                ▼
                                         generation
                                                │
                                                ▼
                                 grounded? ── no ──▶ discard draft,
                                   (R3)              quote record
                                                │ yes
                                                ▼
                        citations non-empty by construction (R1)
                                                │
                                                ▼
                                        persist, return
```

Fig. 1. Answer pipeline. Rules R1–R5 are enforced at the marked positions. Contradiction detection precedes confidence thresholding, so a disagreement is reported irrespective of either record's score; grounding failure suppresses the draft rather than annotating it.

### A. Retrieval, Judging and Contradiction

Retrieval combines a lexical index with domain-specific query expansion. Passages are indexed under BM25 [5] with the record title weighted into the document representation, since a record whose title matches a query but whose body does not would otherwise be unreachable. Three query-side transformations proved necessary: suffix stemming with an irregular-form table, acronym expansion mapping the forms practitioners type (IEC, RoDTEP, SCOMET) to expanded terms, and hyphen normalisation so *ecommerce* meets *e-commerce*. Candidate scores are attenuated by the square root of the proportion of query terms a passage addresses, since unattenuated BM25 rewards a single rare term heavily, letting a lookalike record answer on one shared word.

Confidence is then derived by a language model judging whether each passage answers the question asked, rather than from lexical overlap [7]. This distinction is the subject of Section V.B: lexical similarity and answerhood are different quantities, and thresholding the first while intending the second is not correctable by tuning.

Contradiction detection runs *before* the confidence threshold. Two passages are contradictory when they address the same subject, are comparable in kind, and differ in polarity or in a stated value. Detecting this after thresholding would allow the higher-scoring of two disagreeing records to answer alone, presenting a resolution the system is not competent to make.

Every generated draft is verified before display. Each sentence is checked for support within a *single* passage — not the union, since a claim assembled from fragments of several sources is supported by none of them. A failed draft is discarded and the extractive strategy substituted: a designed degradation, and the destination of every failure in the generation path.

### E. Query Rewriting, and Where Its Trigger Belongs

Both retrieval components match surface form, so both fail on questions asking about the right subject in different vocabulary: "faster clearance for a trusted trader" shares no stemmed term with *Authorised Economic Operator*. The remedy — rewriting before retrieval [14] — is established. What the deployment established is *when*, and two triggers were falsified before a third survived.

A low lexical score never fired: scores for such questions were 0.58–0.69, the index being confident and confidently wrong. A low score does not mark a missed subject, since a wrong record can be lexically strong — the retrieval-side analogue of a model attending to plausible but irrelevant context [18].

Triggering below the answer bar also never fired, revealing a defect rather than a mistuning: the judge's scale defines 0.7 as *answers partially* and the bar was also 0.7, so partial matches landed exactly on it and passed. "My goods are stuck at the port" was being answered from a pre-shipment inspection record at precisely 0.7.

The surviving trigger is *partial-or-worse*, evaluated after judging, so the retry fires only where the request was heading for a refusal or a partial answer (Fig. 2). The rewrite is a **retrieval key only** — never reaching the generator, never displayed, so it cannot introduce a claim — and the second pass is judged against the user's original words.

```
        question
           │
           ▼
      retrieval ──── nothing found ─────┐
           │ candidates                 │
           ▼                            │
   relevance judging                    │
           │                            │
      best score?                       │
      ┌────┴─────┐                      │
    >0.7       ≤0.7 ────────────────────┤
      │                                 │
      ▼                                 ▼
  answer path            rewrite into corpus terms
                                        │
                                        ▼
                          retrieve + judge, scored
                          against the ORIGINAL words
                                        │
                              better or equal?
                                 ┌──────┴──────┐
                                yes            no
                                 │              │
                                 ▼              ▼
                            answer path   keep first pass

  falsified triggers:
    low lexical score  never fired (wrong records score 0.58-0.69)
    below the bar      never fired (partial sits exactly ON the bar)
```

Fig. 2. Where the retrieval retry belongs. The trigger is evaluated after relevance judging, because a lexical score does not distinguish a confident match from a confidently wrong one. The same path bridges a question asked in a language the corpus is not written in.

### F. Cross-Language Retrieval and the Ordering of Translation

The same mechanism resolves a separate failure. The index holds English and Hindi vocabulary, so a Bengali question shares no term with any record and retrieval returns nothing — the classical cross-language retrieval problem, where translating the query is standard and translating for retrieval differs from translating for a reader [13]. Restating the question in corpus vocabulary bridges it.

A deeper conflict then appears between two properties the system already had. Grounding verification checks each generated sentence against the passage that produced it; a Bengali sentence, however faithful, shares no tokens with the English passage it came from. Verification fails, the draft is correctly suppressed, and the extractive fallback quotes English. Measured on the acceptance sets this produced a system answering Bengali questions in English at 0.00 script fidelity.

Three resolutions exist and one is admissible. Weakening verification for non-English trades the central guarantee for a cosmetic one, for the users least able to check a result. Verifying in the answer language means comparing a claim against a machine translation of the evidence, at which point the evidence is no longer the record. The third — **verify first, then translate** — generates in the passage language, verifies unchanged, and translates only what passed (Fig. 3). Translation therefore operates on text already proved to follow from the record: a mistranslation can garble an answer but cannot manufacture a claim. The citation is never translated, and the answer is labelled as translated.

```
  WRONG — translate, then verify
  ──────────────────────────────
   English passage
        │
        ▼
   generate in Bengali
        │
        ▼
   verify against English passage ──▶ no shared tokens: FAILS
        │
        ▼
   draft suppressed, English quoted     (0.00 script fidelity)

  ALSO WRONG — verify against a translated passage
  ────────────────────────────────────────────────
   the claim is checked against a machine translation,
   so the evidence is no longer the record

  CORRECT — verify, then translate
  ────────────────────────────────
   English passage
        │
        ▼
   generate in the PASSAGE language
        │
        ▼
   verify sentence-by-sentence ──▶ fails ──▶ suppress, quote
        │ passes
        ▼
   translate the VERIFIED answer ──▶ Bengali answer, labelled
        │
        └─▶ citation passage untouched, shown in English
```

Fig. 3. Verify-then-translate. Translation operates only on text already proved to follow from the record, so a mistranslation can garble an answer but cannot manufacture a claim. The cited passage is never translated, because a translated quotation is not evidence.

### G. The Language Acceptance Gate

A language is offered only after a recorded measurement on its own acceptance set, scored on answer rate, citation integrity, and *script fidelity* — whether the answer returned in the script it was asked in. The third was added after a first round in which a language answering every question in English passed a gate counting only answer rate; a language answering in another language is not the language it claims to be.

Two properties matter more than the thresholds. Enforcement: before the gate was mechanised the enabled set could be assigned by request, so an enablement backed by a measurement and one ignoring the gate were indistinguishable. Derivation: the enabled set is computed *from* recorded scores rather than configured alongside them, since when the two were maintained separately a language that had passed remained unavailable.

The gate also separates *passing* from *certified*. An acceptance set written by someone who does not speak the language measures pipeline self-consistency, not correctness; certification additionally requires a speaker's review, and the interface distinguishes the two.

The quoted passage always appears in its source language, labelled, and is never translated. Interface typography is keyed on *script* rather than language, because Devanagari and Tamil need greater line height than Latin at equal nominal size, and Hindi and Marathi share a script.

### H. Voice and Self-Updating Knowledge

A hands-free mode serves users more fluent speaking than typing, and for whom composing a question in Devanagari or Tamil on a mobile keyboard is itself a barrier. The loop is explicit — listen until a natural pause, transcribe, answer, speak, listen again — and the system never listens while speaking, which would transcribe its own output. What is spoken differs from what is displayed: a citation's reference and date support visual checking, and reading them aloud buries the answer, so the source is named once in prose.

Unanswerable questions are logged and a record may be drafted automatically, under two constraints. A machine-drafted record carries its own authority attribution and is visually distinguished wherever cited, since auto-drafted knowledge indistinguishable from a published circular would defeat the provenance argument entirely. And drafting is refused for any question turning on a specific figure — a rate, ceiling, deadline or monetary threshold — because a model asked for such a figure will supply one, and a plausible invented number is precisely the harm the citation rule exists to prevent. The refusal and its reason are displayed rather than hidden.

### J. Acting on Ratings

A rating recorded and never read asks users to spend attention and spends none in return; the deployment carried such a control until it was measured. Ratings are informative but biased, better treated as relative evidence than absolute labels [16], so the action taken is deliberately the weakest that helps.

Two *independent* negatives on the same question-and-record pairing withhold that record **from that question only**. It is not retired: being wrong for one question is not being wrong, and one click must not remove a correct circular. One negative is noise. Raters are distinguished so nobody manufactures a consensus by clicking twice — which on an anonymous public surface requires separating anonymous raters, or the threshold is unreachable.

Every negative opens a curation task closed as *record wrong*, *retrieval wrong* or *rating wrong*; the last lifts the suppression and clears the votes behind it. This is a human-in-the-loop division [17] at its cheapest point: the system withholds automatically and corrects only under human judgement. Ratings never edit a record, change its lifecycle state, or move the answer bar. A suppression bumps the generation counter, so cached answers become unreachable exactly as on a lifecycle change.

### K. Channels and Bounded Actions

A messaging channel is served by the same answering component as the browser; one answering to a looser standard would be the worst thing to grow, since the person holding a phone has *less* ability to check a claim than one looking at an evidence panel. The consequence is structural: with no evidence panel, record title, issuing authority and issue date are composed into the message body, because an answer whose provenance did not survive the change of medium would be an uncited answer.

Commercial support agents resolve rather than explain, acting inside the account of the operator deploying them. That path is closed here for jurisdictional rather than technical reasons: this system explains the administration of trade and holds no authority within the departments administering it, and an action appearing to file a declaration would be believed. Actions are therefore confined to those within the system's own authority and reversible — lodging a tracked grievance, requesting a callback, setting a reminder, preparing an application checklist, and watching a cited record for change. The last exists only because of the lifecycle machinery: when a record is superseded, everyone who relied on it is notified. Preparation is explicitly not submission.

---

## V. RESULTS AND DISCUSSION

### A. Experimental Setting

The corpus comprises 51 records and 107 passages spanning registration, customs procedure, taxation, micro and small enterprise finance, e-commerce obligation, standards and trade policy. Procedures, terminology and document structures follow the administration's actual practice; specific rates and thresholds are illustrative and marked as such throughout the interface. Evaluation used a set of 30 questions written in the phrasing a practitioner would use, together with a control set of out-of-domain questions.

### B. Answer Rate, Refusal, and the Confidence Source

TABLE I. OUTCOMES, AND THE EFFECT OF THE CONFIDENCE SOURCE

| Confidence source | In-domain answered with citation | Contradiction surfaced | Out-of-domain incorrectly answered |
|---|---|---|---|
| Lexical (BM25 + coverage) | 27/30 | 1/1 | 3/6 |
| Relevance judging | 30/30 | 1/1 | 0/6 |

Every in-domain question was answered with at least one citation naming an issuing authority and issue date; every out-of-domain question was refused; the deliberately contradictory pair was surfaced rather than resolved.

With lexical confidence alone, three out-of-domain questions were answered from topically adjacent records at maximum confidence, including a general-knowledge question answered from a trade policy record. Lowering the threshold admitted more in-domain questions and increased this error; raising it suppressed valid answers. The failure lay not in the threshold's value but in the quantity being thresholded. Relevance judging permitted the threshold to be restored to its specified value while eliminating the errors.

### D. The Language Gate, Before and After

Enforcing the gate refused every non-English language, including one offered from the outset with no recorded score. Measurement showed the refusal was correct.

<!--CHART:languages-->

Fig. 4. Per-language acceptance, before and after the two repairs. Answer rate and script fidelity failed for different reasons and were repaired by different changes; the dashed line is the script-fidelity floor, which Marathi does not clear.

<!--CHART:heatmap-->

Fig. 5. The three gate measures across both panels. Citation integrity is uniformly 1.00 in each: the structural guarantee held while the tuned behaviour around it was wrong.

Thresholds: answer rate 0.70, citation integrity 1.00, script fidelity 0.80.

Two distinct defects account for the two halves. Low answer rates were empty retrievals, repaired by the cross-language bridge of Section IV.F. Zero script fidelity was grounding verification correctly rejecting drafts written in a language the passage was not, repaired by the verify-then-translate ordering. Citation integrity was 1.00 throughout: the guarantee held while the surrounding behaviour was wrong, which is the intended relationship between a structural invariant and a tuning failure. Marathi remains withheld at 0.75, since a threshold lowered when a language fails it is not a threshold.

### E. Reference-Free Evaluation

Scoring in the style of a reference-free retrieval-augmented evaluation framework [11], with two measures that framework does not define but this system promises.

<!--CHART:scores-->

Fig. 6. Reference-free scores. Solid bars are quantities the design guarantees structurally; hatched bars are measured but not guaranteed.

Faithfulness at 1.00 is the number the grounding verifier exists to hold: no answer asserted a claim its citation did not support. Relevancy and precision below 1.00 without a fall in faithfulness is the expected signature — retrieval returning passages that were not needed, and answers occasionally addressing a neighbouring question, while never stating anything unsupported. The judge is the model that also serves the pipeline [7], so faithfulness should be read as an upper bound; benchmarks for citation quality [15] provide a stronger external standard.

### F. Defects Exposed by Measurement

Several defects survived component-level testing and appeared only end to end. Their character is instructive.

**Title-only records were unreachable.** Retrieval indexed passage bodies while the reranker scored bodies alone, so a record naming its subject only in its title was retrieved and then reordered away. Component tests passed because each stage was individually correct.

**Cache rehydration lost type information.** Cached citations serialised to JSON returned dates as strings, failing on the cache-hit path only. Eighteen unit tests passed because none asserted on the *types* of a rehydrated citation.

**A threshold coincided with a scale point.** The judge's scale defines 0.7 as *answers partially*; the answer bar was also 0.7, so partial matches passed as answers. The defect lay in the relationship between two independently reasonable constants, and no component was misbehaving.

**A control collected a signal it never read.** Ratings were written to the audit record and consumed by nothing. No test can fail this: the endpoint returned correctly and the data was stored correctly. It is visible only by asking what *reads* a value after asking what writes it.

**A gate was policy rather than mechanism.** The set of offered languages could be assigned directly, so an enablement backed by a measurement and one ignoring the gate were indistinguishable afterwards. Enforcement revealed a language offered throughout with no score on file.

**A measurement changed nothing.** After enforcement, recorded scores and the offered set were maintained separately, so languages that had passed remained unavailable.

The last three share a shape worth naming: each is a **claim without a mechanism** — a property the system asserted, that no code enforced, and that no test could fail because there was nothing to execute. Such defects are not found by testing behaviour but by asking, for each stated property, which component would refuse if it were violated.

### G. Latency

Per-stage budgets sum to 4 350 ms against a 5 000 ms target, the largest being generation at 2 500 ms and relevance judging at 400 ms. Per-stage timeouts alone proved insufficient: several stages running slowly without individually timing out can breach the target together. A whole-request deadline was added, clamping each stage to the remaining budget and declining to begin generation it cannot finish. Every degradation resolves toward showing less rather than showing something unverified — retrieval timing out reports assist unavailable, judging timing out caps confidence below the bar, generation timing out falls back to extraction, and grounding timing out suppresses the draft.

### H. Limitations

Relevance judging, query rewriting and translation all depend on an external model and degrade to refusal or to an untranslated answer when it is unavailable — safe failures, but reductions in service. The corpus is illustrative and small, so the reported answer rate characterises the mechanism rather than performance at production scale. Correctness was assessed by the authors against known-correct records rather than by independent domain assessors, and the acceptance sets were written by the implementers rather than by speakers of each language, which is why the gate distinguishes a passing language from a certified one. Reference-free scoring uses the same model family that serves the pipeline, a known limitation of model-as-evaluator arrangements [7].

---

## VI. EXPECTED OUTCOMES AND IMPACT

**Verifiability as a default.** Every answer carries the record it came from, its issuing authority and its issue date, so a user can check guidance rather than trust it and a supervisor can reconstruct what was shown and on what basis.

**Reduced confident error.** Refusal is inexpensive for the system and every degradation path resolves toward showing less. Where a wrong answer produces a held consignment or a forfeited incentive, that bias is justified.

**Amendment takes effect immediately.** Retiring a superseded record removes it from the next answer, including from answers already cached, and everyone watching that record is told — the difference between a knowledge base and an archive.

**Contradiction becomes visible work.** Records that disagree enter a queue for human resolution rather than being resolved silently by ranking.

**Access widens on measured evidence.** Languages are offered only after a recorded per-language score, and one that fails its threshold is withheld, so widening access does not mean answering badly in a language nobody has measured.

---

## VII. CONCLUSION

Provenance in a government knowledge platform is better treated as a structural precondition than as a presentation feature. Making an uncited answer unrepresentable, ordering contradiction detection before confidence thresholding, suppressing rather than annotating unsupported generation, and returning refusal as a successful outcome together produce a system whose answers can be checked rather than merely trusted.

The multilingual result generalises beyond this deployment: grounding verification and multilingual answering conflict whenever evidence and answer are in different languages, and the conflict is resolvable by ordering — verify in the language of the evidence, translate only what passed, never translate the evidence — rather than by weakening either property.

The defects measurement exposed are the more transferable contribution. Several were invisible to component-level testing because every component behaved as specified, and three were *claims without mechanisms*: properties the system asserted that no code enforced and no test could fail. Finding them required asking, for each stated property, which component would refuse if it were violated.

---

## REFERENCES

[1] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems*, vol. 33, 2020, pp. 9459–9474.

[2] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, Y. Dai, J. Sun, M. Wang, and H. Wang, "Retrieval-augmented generation for large language models: A survey," *arXiv preprint* arXiv:2312.10997, 2024.

[3] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, "Survey of hallucination in natural language generation," *ACM Computing Surveys*, vol. 55, no. 12, art. 248, pp. 1–38, 2023.

[4] H. Rashkin, V. Nikolaev, M. Lamm, L. Aroyo, M. Collins, D. Das, S. Petrov, G. S. Tomar, I. Turc, and D. Reitter, "Measuring attribution in natural language generation models," *Computational Linguistics*, vol. 49, no. 4, pp. 777–840, 2023.

[5] S. Robertson and H. Zaragoza, "The probabilistic relevance framework: BM25 and beyond," *Foundations and Trends in Information Retrieval*, vol. 3, no. 4, pp. 333–389, 2009.

[6] R. Nogueira and K. Cho, "Passage re-ranking with BERT," *arXiv preprint* arXiv:1901.04085, 2019.

[7] L. Zheng, W. Chiang, Y. Sheng, S. Zhuang, Z. Wu, Y. Zhuang, Z. Lin, Z. Li, D. Li, E. P. Xing, H. Zhang, J. E. Gonzalez, and I. Stoica, "Judging LLM-as-a-judge with MT-Bench and Chatbot Arena," in *Advances in Neural Information Processing Systems 36: Datasets and Benchmarks Track*, 2023.

[8] A. Kamath, R. Jia, and P. Liang, "Selective question answering under domain shift," in *Proc. 58th Annu. Meeting of the Association for Computational Linguistics*, 2020, pp. 5684–5696.

[9] J. Xie, K. Zhang, J. Chen, R. Lou, and Y. Su, "Adaptive chameleon or stubborn sloth: Revealing the behavior of large language models in knowledge conflicts," in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, 2024.

[10] S. Khanuja, D. Bansal, S. Mehtani, S. Khosla, A. Dey, B. Gopalan, D. K. Margam, P. Aggarwal, R. T. Nagipogu, S. Dave, S. Gupta, S. C. B. Gali, V. Subramanian, and P. Talukdar, "MuRIL: Multilingual representations for Indian languages," *arXiv preprint* arXiv:2103.10730, 2021.

[11] S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, "RAGAs: Automated evaluation of retrieval augmented generation," in *Proc. 18th Conf. European Chapter of the Association for Computational Linguistics: System Demonstrations*, St. Julians, Malta, 2024, pp. 150–158.

[12] M. E. Cortés-Cediel, A. Segura-Tinoco, I. Cantador, and M. P. Rodríguez Bolívar, "Trends and challenges of e-government chatbots: Advances in exploring open government data and citizen participation content," *Government Information Quarterly*, vol. 40, no. 4, art. 101877, 2023.

[13] J.-Y. Nie, *Cross-Language Information Retrieval*, Synthesis Lectures on Human Language Technologies. San Rafael, CA: Morgan & Claypool, vol. 3, no. 1, pp. 1–125, 2010.

[14] X. Ma, Y. Gong, P. He, H. Zhao, and N. Duan, "Query rewriting in retrieval-augmented large language models," in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Singapore, 2023, pp. 5303–5315.

[15] T. Gao, H. Yen, J. Yu, and D. Chen, "Enabling large language models to generate text with citations," in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Singapore, 2023, pp. 6465–6488.

[16] T. Joachims, L. Granka, B. Pan, H. Hembrooke, and G. Gay, "Accurately interpreting clickthrough data as implicit feedback," in *Proc. 28th Annu. Int. ACM SIGIR Conf. Research and Development in Information Retrieval*, Salvador, Brazil, 2005, pp. 154–161.

[17] X. Wu, L. Xiao, Y. Sun, J. Zhang, T. Ma, and L. He, "A survey of human-in-the-loop for machine learning," *Future Generation Computer Systems*, vol. 135, pp. 364–381, 2022.

[18] F. Shi, X. Chen, K. Misra, N. Scales, D. Dohan, E. H. Chi, N. Schärli, and D. Zhou, "Large language models can be easily distracted by irrelevant context," in *Proc. 40th Int. Conf. Machine Learning (ICML)*, PMLR vol. 202, 2023, pp. 31210–31227.
