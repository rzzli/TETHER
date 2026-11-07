# TETHER SciFact full-context results — SC03

**SC03 is complete. The stronger solver improves F1 and strict correctness on
the exposed 300-claim development set, but loses rationale recall. The harness
admits all outputs and adds no answer-correctness gain. SC04–SC09 remain open.**

This report closes the [prospective protocol](<TETHER SciFact Full Context Protocol 2026-11-06.md>)
through [root acceptance](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/sc03/root-acceptance-attempt01/ROOT-ACCEPTANCE.json).
There were 9,305 acceptance checks, 30,220 independent reconstruction checks,
62 component tests and five supplemental event controls, all passing. The earlier
actual-model fictional rehearsal and independently reconstructed source inputs
remain required supporting evidence. These counts describe engineering checks,
not independent scientific annotations.

## What was compared

The original top-five retrieved documents, claim text and document order were
held fixed for all 300 questions. The new solver reads each complete title and
abstract jointly with the claim and predicts a label and rationale sentences.
There are 1,500 claim/document forwards per condition. This is complete-abstract
context, not full-paper reading or joint reasoning across five papers.

The qualified MultiVerS `fever_sci` checkpoint uses FP32, batch size one,
4,096-token maximum, fixed rationale threshold 0.5, no forced rationale and
no label threshold. There was no training, tuning, recalibration, truncation,
automatic retry or dev-label selection during execution. Its external FEVER,
PubMedQA and Evidence Inference supervision differs from the old linear model.
Accordingly, the contrast is between solver conditions, not an isolated
architecture effect. The SciFact-finetuned checkpoint was excluded. Possible
pretraining/model-selection exposure remains; this is not a contamination-free
or clinical-generalization claim. See [solver qualification](<TETHER MultiVerS Qualification Results 2026-11-06.md>).

## Primary performance

All metrics below use the complete scheduled denominator. Percentages are
rounded for presentation; retained JSON holds unrounded values.

| Endpoint | Original baseline | MultiVerS | Difference, percentage points | Paired 95% interval for difference |
|---|---:|---:|---:|---:|
| Strict correct / 300 | 27 (9.00%) | 127 (42.33%) | +33.33 | +27.21 to +39.74 |
| Abstract label F1 | 13.51% | 54.40% | +40.89 | +34.19 to +47.54 |
| Abstract rationalized F1 | 8.70% | 19.20% | +10.50 | +4.47 to +17.08 |
| Sentence selection F1 | 7.86% | 19.23% | +11.37 | +5.85 to +17.42 |
| Sentence label F1 | 4.81% | 17.79% | +12.98 | +7.77 to +18.73 |

Strict correctness requires the exact annotated document set, correct labels
and a complete allowed rationale within the native prefix cap. Of the 127
strict successes, **98 are correct no-evidence (NEI) answers and 29 are
evidence-bearing answers**. The baseline had 26 and one, respectively. Thus
72 of the 100 additional strict successes are NEI; reporting the entire gain
as improved evidence-grounded biological reasoning would be misleading.

The tradeoff matters: abstract rationalized precision rises from 5.39% to
21.69%, but recall falls from 22.49% to 17.22%. Sentence label precision rises
from 2.68% to 74.00%, while recall falls from 23.22% to 10.11%. Sentence
selection precision rises from 4.38% to 80.00%, while recall falls from 37.98%
to 10.93%. Many useful rationales are still missed. Improved F1 is insufficient
to establish comprehensive evidence coverage.

There are 300 produced and admitted outputs, zero policy rejections, zero
failure placeholders and 162 native NEI predictions. Native NEI is a completed
scientific prediction, not a missing execution. Raw and checked metrics are
identical, including 127 correct-and-admitted outputs; filtering has not
created the semantic improvement.

Intervals use 10,000 paired resamples of the existing 247 source/text components,
seed 20261106, pooled native counts and percentile intervals with linear
interpolation. They quantify variation within this exposed benchmark. They do
not make this a fresh holdout or correct all possible dependencies. All 13
endpoints, including precision and recall, are retained in the acceptance JSON.

## Evidence-use diagnostics

Each condition executed all 300 claims and 1,500 pairs. Primary performance
above is scored on original evidence only; these interventions are separate.

| Intervention | Applicable pairs | Changed labels | Mean change in score for the primary predicted class | Synthetic sentences selected |
|---|---:|---:|---:|---:|
| Keep union of annotated rationale sentences | 159 | 25 | −0.1030 | 0 |
| Remove that union | 159 | 54 | −0.2800 | 0 |
| Append irrelevant fictional observatory sentence | 1,500 | 5 | −0.0014 | 0 |
| Append explicit counterfactual negation of claim | 1,500 | 1,396 | −0.9063 | 1,175 |

Unannotated retrieved documents remain unchanged in the first two conditions.
Titles remain present after removal; the intervention does not prove that all
potentially useful information has been removed. Both masks use gold annotations
and therefore are diagnostic-only, not available retrieval methods.

The synthetic conflict sharply changes predictions and is frequently selected
as rationale. It is a generic appended negation, not a natural conflicting
publication. A changed answer is not necessarily wrong, and this result does
not measure resolution of genuine scientific disagreements. All synthetic
sentences retain synthetic identity, never the original paper's sentence
locator. Per-pair source mappings, rationale overlap and score changes were
independently reconstructed for all 6,000 diagnostic pairs. These scores are
uncalibrated classifier outputs, not clinical probabilities or a causal
faithfulness measure.

## Resources and execution

| Condition | Worker wall seconds | Input tokens | Request JSONL bytes | Largest input, tokens |
|---|---:|---:|---:|---:|
| Primary | 165.32 | 531,675 | 2,327,959 | 1,634 |
| Rationale only | 155.41 | 485,257 | 2,120,849 | 1,634 |
| Evidence removal | 162.13 | 517,966 | 2,270,117 | 1,634 |
| Irrelevant context | 159.76 | 558,675 | 2,467,459 | 1,652 |
| Constructed conflict | 168.26 | 582,810 | 2,574,524 | 1,679 |

Five sequential workers consumed 810.88 seconds of worker wall time and
734.70 process CPU seconds. Analysis took another 118.37 seconds. These do not
include every acquisition, qualification, parent hashing or independent review
operation. Peak worker working set was 6,532,173,824 bytes. Highest observed
CUDA allocation was 2,159,775,744 bytes and reservation 2,854,223,872 bytes;
these allocator measurements are not whole-device memory measurements.

There were 7,500 actual model forwards, zero overlength/unavailable/failed pairs
and zero provider spending. This nonautoregressive classifier generates no
answer tokens; measured transformer input tokens are nevertheless retained.
Request-file sizes include serialized metadata, not only scientific text or
unique-source storage. Complete file sizes, forward timing and per-condition
memory are in the acceptance JSON. No energy-cost estimate is claimed.

## Verification correction and limits

An adversarial fictional probe found that the frozen production auditor could
accept an additional contradictory terminal journal event after valid commits.
Frozen sources were preserved. A separately qualified **mandatory exact-event
gate** now checks complete ordering and coverage, including supervisor signals.
All five conditions pass with 5,102 journal events and 604 signals each. Root
acceptance requires this supplement in addition to the original source-inclusive
audit and independent metric reconstruction. The original auditor alone is
insufficient. See the retained [amendment](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/sc03/ACCEPTANCE-AMENDMENT-01.md).

The original analysis report's `independent_reconstruction: pending` field
records its creation state. Its bytes remain sealed; the later independent
report and joined root acceptance supersede that status without rewriting it.
Original benchmark/source inventories and all 148 frozen execution pins were
checked again at acceptance. This establishes observed byte identity, not
continuous host attestation or biological correctness.

## Reproduction and next step

Retained controls and result anchors are in
[the production freeze](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/sc03/production-freeze-attempt01).
Bulk outputs remain in ignored local data paths:
`data/benchmark/scifact_comparison/production-20261106-attempt01/` and
`data/benchmark/scifact_comparison/analysis-20261106-attempt01/`.
Do not rerun inference to verify an existing result.

From the root, with the retained qualified stdlib environment, run
`planning/review-assets/tether-semantic-20261106/sc03/accept_results.py --output <fresh-directory>`
to recheck the joined acceptance. The independent script can separately rebuild
native scores, bootstrap intervals and diagnostic mappings with the frozen
frame/analysis hashes recorded by root acceptance. Its output must also use
a fresh directory. Source archives, model acquisition and original local
receipts must still be available; Git alone does not contain the full payload.

Next is SC04: qualify and freeze the full 199-question LitQA2 query-expansion
and reranking comparison plus the separately labelled supplied-source
diagnostic. The negative rationale-recall finding remains a result, not a reason
to change SciFact thresholds after inspecting this evaluation.
