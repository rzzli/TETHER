# SciFact descriptive error decomposition

Descriptive post hoc analysis of frozen public-development predictions. The ordered partition is a reporting convention, not a causal attribution, ablation, retuning, new model run, or biological/clinical conclusion. False positives and negatives are relative to benchmark annotations; unannotated documents are not established biological negatives. This analysis does not replace the retained official metrics.

All 2 scheduled claims are retained. Native strict correctness: 2/2; evidence-bearing claims: 1.

## Mutually exclusive first-failure partition

This fixed order assigns each claim once. It does not estimate causal contributions.

| First observed failure | Claims |
|---|---:|
| operational_failure | 0 |
| retrieval_miss | 0 |
| selection_omission | 0 |
| selection_extra | 0 |
| label_mismatch | 0 |
| rationale_incomplete | 0 |
| strict_correct | 2 |

## Overlapping observations

The following counts overlap; do not add them as an error total.

| Flag | Claims |
|---|---:|
| operational_failure | 0 |
| retrieval_miss | 0 |
| selection_omission | 0 |
| retrieved_gold_not_selected | 0 |
| selection_extra | 0 |
| label_mismatch | 0 |
| rationale_incomplete | 0 |
| correct_label_incomplete_rationale | 0 |
| incomplete_even_full | 0 |
| complete_full_but_not_capped | 0 |
| rationale_extra_outside_gold_union | 0 |
| not_admitted | 0 |

## Document and rationale counts

| Observation | Count |
|---|---:|
| gold | 1 |
| retrieved_gold | 1 |
| unretrieved_gold | 0 |
| retrieved_non_gold | 1 |
| selected | 1 |
| selected_gold | 1 |
| selection_false_positive | 0 |
| selection_false_negative | 0 |
| retrieved_gold_not_selected | 0 |
| selected_gold_label_correct | 1 |
| selected_gold_label_wrong | 0 |
| selected_gold_rationale_complete_capped | 1 |
| selected_gold_rationale_incomplete_capped | 0 |
| selected_gold_correct_label_incomplete_rationale | 0 |
| selected_gold_rationale_complete_full_but_not_capped | 0 |
| selected_gold_rationale_incomplete_even_full | 0 |
| extra_sentences_on_selected_gold_full | 0 |
| extra_sentences_on_selected_gold_capped | 0 |

## Strata

| Stratum | Scheduled | Produced | Strict correct |
|---|---:|---:|---:|
| SUPPORT | 1 | 1 | 1 |
| CONTRADICT | 0 | 0 | 0 |
| NEI | 1 | 1 | 1 |
| MIXED | 0 | 0 | 0 |

NEI outcomes: {"produced_empty_correct": 1}.

Native rationale correctness requires any one complete annotated rationale within the original ordered prediction prefix of length max(3, shortest annotated rationale length), with an exact evidence-document set and correct document labels. Extra rationale sentences alone are permitted; extras can coexist with strict correctness. Full-list completeness with cap incompleteness identifies ordering/cap displacement descriptively. NEI retrieval recall is not applicable. Labels and rationales are assessed only for selected annotated documents.

Retrieval non-gold documents and selected false positives are annotation-relative. These counts do not establish biological falsehoods. All per-claim document IDs, ordered sentences, rationale-set differences, flags and statuses are retained in DECOMPOSITION.json. Official metrics remain in the sealed baseline evaluation; none are replaced or recomputed here.
