# TETHER SciFact error decomposition

SC01 completed on 6 November 2026 UTC. The sealed baseline's weakness is not explained by retrieval alone: all annotated documents were retrieved for 147 of 188 evidence-bearing claims, yet only one of those claims met the declared strict criterion. Selection of unannotated documents, omission of retrieved annotated documents, label errors and rationale errors all occur. These are overlapping descriptive observations, not causal estimates of improvement from fixing a component.

The original predictions, receipts, source data and native scores are unchanged. All 300 public-development claims remain in the denominator. This analysis adds no model inference, tuning, scientific validation or new prediction result. Provider spending was $0.

## Results and interpretation

| Observation | Result | Meaning |
|---|---:|---|
| Strict-correct claims, raw and admitted | 27 / 300 | 26 NEI and one SUPPORT; zero CONTRADICT. Checks do not improve these answers. |
| Annotated document pairs retrieved | 159 / 209 | Retrieval misses remain substantial. |
| Evidence-bearing claims with all annotated documents retrieved | 147 / 188 | Retrieval success is insufficient for a correct final answer. |
| Annotated retrieved pairs omitted by selection | 47 / 159 | Useful retrieved evidence is also lost downstream. |
| Selected pairs belonging to the annotated evidence set | 112 / 872 | The other 760 are annotation-relative extra selections, not proven biological falsehoods. |
| Correct labels on selected annotated pairs | 73 / 112 | Conditional on selection; omitted documents have unobserved labels. |
| Complete native-capped rationales on selected annotated pairs | 77 / 112 | This does not require every alternative rationale. |
| Full rationale complete but displaced by native prefix cap | 11 pairs | Sentence ordering can change the result even with the evidence somewhere in the full prediction. |

The strongest asymmetry occurs on selected annotated CONTRADICT pairs: only 6 of 37 labels are correct, versus 67 of 75 selected SUPPORT pairs. These are conditional document-level counts, not accuracy estimates for all contradiction/support claims. A stronger joint label/rationale model is a targeted next comparison; the results do not establish that it will help.

Overlapping claim-level flags are: retrieval miss 41, selection omission 86, extra selected documents 242, incorrect observed label 38, and incomplete observed rationale 33. Adding these numbers would double-count claims. Within NEI, 26 of 112 predictions are correctly empty and 86 select documents.

For an exhaustive descriptive partition, the frozen precedence is operational failure → retrieval miss → selection omission → extra selection → label mismatch → incomplete rationale → strict correct. Its counts are **0, 41, 45, 183, 3, 1, 27**, respectively. The small final label/rationale categories do not mean those errors are rare: earlier categories take precedence.

All four official native metric families were independently reconstructed. Raw and admitted metrics remain identical, including abstract-rationalized F1 **0.08696**. Exact values are retained in the independent comparison and root acceptance. The stricter case criterion supplements rather than replaces these metrics.

## Validation and artifacts

- The analyzer passes **23 invented tests**, including alternatives, native sentence caps/order, NEI, operational failures, pins, schedule coverage and no-clobber publication. The initial missing-implementation failure is retained.
- A separate implementation passes **14 native boundary cases** against the pinned official evaluator and two additional fictional transport examples. These are engineering fixtures, not scientific samples.
- Original authority verification checks the externally anchored stage receipt, **all 1,601 output hashes and exact 1,602-file inventory**, all 12 preparation products, raw archive/member hashes and source bindings. Independently reconstructed corpus, development questions and development references match byte-for-byte.
- The actual independent reader agrees on all **300 cases**, **112 selected annotated-document details**, native raw/admitted metrics, strata, overlapping flags and the partition. It does not import the diagnostic analyzer.
- Root acceptance rechecks the old experiment and all frozen input/source/authority pins. The analyzer itself took **0.540 seconds**, excluding preflight, qualification and independent audit. This is diagnostic runtime, not a model or comparative-harness timing.

| Artifact | Location |
|---|---|
| Actual input/code/authority freeze | [INPUT-MANIFEST.json](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/decomposition/actual-freeze-attempt01/INPUT-MANIFEST.json) |
| Per-case diagnostic output | DECOMPOSITION.json (local artifact: `data/benchmark/scifact_diagnostics/20261106-attempt01/DECOMPOSITION.json`) |
| Readable full count tables | REPORT.md (local artifact: `data/benchmark/scifact_diagnostics/20261106-attempt01/REPORT.md`) |
| Original-source preflight | [PREFLIGHT.json](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/methods/source-preflight-attempt02/PREFLIGHT.json) |
| Independent comparison | [COMPARISON.json](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/methods/actual-comparison-attempt01/COMPARISON.json) |
| Root acceptance | [ROOT-ACCEPTANCE.json](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/decomposition/ROOT-ACCEPTANCE.json) |

The first new preflight failed because its byte total omitted the receipt while the historical total included it. The failed attempt is retained; the corrected fresh attempt passes. No baseline discrepancy was found or repaired. Independent review here means separately implemented AI-assisted analysis, not external scientific adjudication.

## Next stage and limits

SC02 is now active: qualify the released MultiVerS **fever_sci** full-context joint solver and a modern isolated runtime. Its pre-SciFact training stage avoids the documented target-fine-tuning concern, but does not certify absence of pretraining or model-development exposure. The SciFact-trained checkpoint is excluded from the primary public-development comparison because its reported training count strongly indicates inclusion of these 300 claims; exact checkpoint training IDs were not verified.

SC03 will prospectively compare the stronger solver using the same retrieved documents, with separate reference-informed evidence-use diagnostics. The already exposed public development set remains a development comparison. SC02–SC09 are incomplete; this diagnostic does not complete the semantic-capability goal.
