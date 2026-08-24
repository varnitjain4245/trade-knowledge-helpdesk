# Paper

`paper.md` — the paper, in the section order of an IEEE conference submission
(Abstract, Keywords, I Introduction, II Related Work, III Proposed System,
IV Working Principle, V Results and Discussion, VI Expected Outcomes and Impact,
VII Conclusion, References).

`figures.md` — specifications and captions for Fig. 1 and Fig. 2.

## Preparing it for submission

The reference paper uses the IEEE conference Word template. To produce that format:

1. Open the IEEE template and paste each section in order.
2. Set the paper to two columns, 10 pt Times New Roman.
3. Replace the author block with the real author list and affiliations.
4. Draw Fig. 1 and Fig. 2 from `figures.md` and place them at the top of a column.
5. Tables I–III are already in IEEE caption style (caption above the table).

## What is measured and what is not

Reported figures come from the implementation in `backend/`. Section V-F states the
limitations explicitly: the corpus is illustrative, correctness was assessed by the
authors rather than by independent domain experts, and per-language correctness was not
separately measured. These qualifications should not be removed when the paper is
formatted — they are the difference between a claim and an overclaim.
