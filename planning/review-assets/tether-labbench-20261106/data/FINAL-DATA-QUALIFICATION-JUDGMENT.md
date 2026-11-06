# Independent data and qualification judgment

Reviewed 6 November 2026 UTC, before benchmark retrieval or inference. Scope: the data/source route, final prompt capacity, fictional semantic failure and whether a descriptive all-199 evaluation remains interpretable. No model call or network request was made for this review. SciFact and held LAB-Bench implementation files were unchanged.

## Decision

Proceeding under prospective protocol amendment A01 is scientifically defensible **as a descriptive evaluation of this exact weak solver**. It is not evidence that semantic answering was qualified. Measuring a poor solver is valid; silently relabelling its failed control or selecting a successful prompt after benchmark exposure would not be. The full 199-question schedule, fixed native choices, unchanged final prompt/model, source acquisition limits, exactly-once candidates and raw-versus-checked pairing must remain frozen.

The semantic fixture is unambiguous: its passage explicitly assigns cobalt to the queried invented object, corresponding to visible index 2. The model returned index 1 (insufficient information) while citing that passage. This is a failed expected-answer control, not a successful semantic abstention. The earlier actual semantic attempt also chose unsure. These are repeated observations of one fictional item under evolving implementation, not two independent statistical samples or an estimate of scientific-task accuracy.

The retained attempt04 prompt has explicit zero-based option mappings and a grammar permitting every visible option. Its native tokenizer returned 298 tokens, including three `im_start` tokens (151644) and two `im_end` tokens (151645); the generated response reports 298 evaluated prompt tokens. The role sequence and assistant prefix are consistent with the intended ChatML serialization. Transport replay, token accounting and server cleanup pass independently of the wrong answer. These observations rule out the obvious missing-role-token/index-permutation explanations; they do not prove the model understood the request or exclude every possible runtime defect. Refusal bias from wording such as “untrusted data” or the fictional setting is only a hypothesis, not an established cause. No further adaptive prompt tuning is recommended for this frozen baseline.

If the benchmark also produces only unsure answers, that is a valid negative measurement with zero substantive coverage. It would not demonstrate task competence, general model quality, an effective retrieval-augmented solver, or improved scientific reliability. A provenance gate may legitimately admit a well-formed, source-bound but incorrect/unsure candidate: no qualified entailment checker is present. Native answer-key accuracy and evidence-source access therefore remain separate from semantic source support. Completion of execution/reconstruction must stay distinct from the original task-capable-answering success criterion.

## Data and controller qualification

- The approved task projection contains only native IDs, question text and indexed displayed choices. References, correctness markers, source hints and key passages remain outside collector/model inputs. All 199 rows remain scheduled, including native duplicated distractor positions.
- Actual source accessibility and annotated-source recovery remain **unmeasured for this cohort**. The successful nonbenchmark Europe PMC probe establishes that the implemented API/license/transport route operates, not that three retrieved articles contain the required answer. OA/license restrictions and the bounded search policy materially narrow the task's evidence universe.
- Collector qualification comprises 12 passing fictional tests, including exclusive reservation, partial/all-case dispositions, hard process deadlines, unknown-transfer accounting and fully reconciled configuration/reservation/terminal journal events. The failing-first resealed-journal witnesses remain retained. Source/body hashes and exact character bindings verify what was provided, not whether it supports an answer.
- Collector SHA-256: `c646630fca96e7c339d318544fb786a14d5372c029394b55a3bd2e54507aced6`; shared runtime: `3ca200a3113e960fe2d3c13549ef5d0690fbfce1cb4d830633114cdf3f9fea8e`. These match the retained [collection qualification](../collection/COLLECTION-QUALIFICATION-01.json).

## Final prompt capacity

The [final task-only capacity report](TASK-CAPACITY-02.json), produced by [this retained helper](check_capacity_v2.py), binds final model source SHA-256 `2d78910c2a4c6b6b38393172b23e224b6b426f992fadf5bd22fd312cd7d4d5d8` and the exact approved query bytes. It supersedes only the older prompt's capacity measurement; original reports remain retained.

| Scenario | Queries passing | Largest UTF-8 prompt | Frozen prompt cap |
|---|---:|---:|---:|
| No passages | 199/199 | 1,910 bytes | 14,000 bytes |
| Eight fictional 1,000-byte ASCII passages | 199/199 | 10,333 bytes | 14,000 bytes |

No reference/source-hint file was opened by the capacity helper, and no native inference or acquisition occurred. The report SHA-256 is `6a0652694b1127d922f0370b4bfe15615713a5997a0fde507659797677cf3ad5`. Actual article text can contain Unicode that expands when JSON-escaped; these ASCII controls do not guarantee every actual prompt fits. Any overcapacity case must retain its explicit failure on the full denominator rather than being dropped, silently shortened or replaced.

## Remaining gates

Root-controlled protocol/source/environment freeze; one bounded all-199 question-only acquisition; source-inclusive collection verification; one local candidate-production schedule; paired native checks; post-seal native scoring and independent reconstruction; complete coverage/cost/failure reporting. Scientific capability remains unqualified until results are observed and appropriately interpreted. This note does not itself authorize dispatch or mark BG04 complete.
