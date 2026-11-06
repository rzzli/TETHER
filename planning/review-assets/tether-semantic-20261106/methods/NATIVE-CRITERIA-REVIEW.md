# Native SciFact decomposition methods review

Status: pre-analysis review, 6 November 2026. This review inspects the existing sealed baseline and evaluator implementation; it does not execute a new predictor, retune the old model, or edit any original data or run.

## Binding criteria

The completed baseline is `data/benchmark/scifact/native-20261105T234805Z-attempt01`. Its published result is 27/300 strict-correct cases: 1/188 with annotated evidence and 26/112 NEI. These retained totals are comparison anchors, not newly computed diagnostic results.

`experiments/scifact/evaluate.py::strict_correct` requires an actually produced prediction, the exact gold evidence-document ID set, the correct SUPPORT/CONTRADICT label on every selected gold document, and at least one complete annotated rationale per document within the first `max(3, shortest gold rationale length)` predicted sentences. A successful empty prediction is correct for an empty gold evidence set. Operational placeholders must never receive this strict NEI credit.

The pinned official evaluator is commit `66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb`, script SHA-256 `2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f`. A retained copy is `data/benchmark/scifact/reconstruction-20261105-attempt01/official/dev-raw/eval.py`.

| Family | Relevant denominator | Predicted denominator | Credit |
|---|---|---|---|
| Abstract label only | Annotated claim/document pairs | All selected claim/document pairs | Gold document selected with correct label |
| Abstract rationalized | Annotated claim/document pairs | All selected claim/document pairs | Correct document label and any complete rationale within the native cap |
| Sentence selection | Sum of lengths of all annotated rationale alternatives | All selected sentences, including extra documents | A selected gold sentence receives credit only if its entire annotated rationale is selected in the full list |
| Sentence label | Same as sentence selection | Same as sentence selection | Sentence selection credit plus correct document label |

The source validator rejects overlapping rationale alternatives. Their lengths are summed in the sentence recall denominator; the strict criterion needs only one complete alternative. The abstract cap does not apply to sentence metrics. Extra sentences outside the annotation union are diagnostic extras, not proof of biological irrelevance. They lower sentence precision and may displace a complete rationale beyond the abstract cap, but they do not independently make strict correctness false.

## Decomposition requirements

Retain all 300 scheduled IDs in original order, with producer status, check status and raw/checked strict results. The 188 nonempty-gold claims and 112 NEI claims are additional strata, never replacements for the all-scheduled denominator. The 209 annotated document pairs are a different unit from claims. Native corpus document identifiers are integers in retrieval records and decimal strings in evidence maps; normalize their representation explicitly before joining.

For nonempty gold, let G be the gold evidence-document set, R the original retrieved set, and P the selected evidence-document set. Report `G-R` retrieval misses, `(G & R)-P` retrieved-but-unselected evidence, `G-P` all missing selected evidence, and `P-G` extra selected documents. Preserve overlapping claim flags. Confirm `P <= R` for this baseline as a data-integrity condition, not a universal benchmark rule. Pair-score rows may explain omitted gold documents as predicted NEI, but do not assign new labels or scores.

On common documents `G & P`, record wrong labels independently of rationale performance. Record complete-any-rationale on both the full prediction list and the native cap prefix. Full-list complete but capped incomplete is a cap/order displacement diagnostic. Incomplete even in the full list is a rationale-selection miss. Report alternative-by-alternative missing sentence IDs and extras relative to the union; missing part of an unused alternative is not itself a strict error when another alternative is complete.

For a mutually exclusive display only, use operational nonproduction, retrieval miss, retrieved-but-unselected omission, extra selected document, wrong label, capped-rationale incompleteness, strict-correct. NEI requires separate produced-empty correct / produced-nonempty false-positive / operational-nonproduction accounting. Retrieval recall for NEI is not applicable, not a perfect score. If a single all-claim partition is needed, distinguish correct NEI and NEI false positives as named bins.

The first-failure order is conventional and suppresses later co-occurring defects; it is not a causal attribution or an estimate of gain from repairing that stage. Preserve the overlapping panel so a prevalent earlier failure does not hide downstream errors. Annotation-defined extras and omissions do not establish scientific falsehood or prove that an unannotated paper cannot support a claim.

## Information and execution boundary

This is an explicitly post hoc descriptive analysis of immutable public-development outputs. Gold references may be opened by this audit after the root's diagnostic freeze. They must not be exported into predictor prompts, used to select models, thresholds, exclusions, or candidate answers, or reused as fitting supervision. No provider calls, downloads, new model fitting, fresh predictions, or counterfactual gold repairs belong in this diagnostic run.

Before actual execution, bind source inputs, schema, category definitions, denominator rules, analyzer code, environment, output path and plan/protocol hashes. The independent reconstruction must not import the diagnostic analyzer. Run fictional boundary controls first; then use fresh output directories and UTF-8 writes. Verify every baseline receipt entry before and after analysis, and bind the new analysis receipt to the old receipt. Operational failure or weak measurement is retained, not rerun to obtain a desired result.

## Review gates for the broader semantic plan

Completion concerns executed measurements and honest reporting, not beating an accuracy threshold. A weak or negative stage remains a completed measurement and cannot silently narrow away subsequent user-requested stages. Any scientific-success threshold is reported separately from the execution gate.

The full-context joint solver, evidence-use interventions, LitQA2 query expansion/reranking/repair, and later ALCE/selectedScholarQA/R2E native evaluations must remain individually visible in the plan. Their dataset access, model feasibility, cost and analysis gates must be declared before their own execution. No new human expert is presumed, and no prior run is overwritten. Formal clinical validity, unexposed holdout claims and causal claims require evidence beyond this post hoc baseline decomposition.
