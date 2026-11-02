# Q03 design clarification 01

Date: 2026-11-02. This separate addendum responds only to an independent review of the frozen task logic. The task designer remains blind to local biological rows, selected target/disease values, reference answers, response outputs, outcomes, and evaluation results. The initial `SOURCE-ONLY-TASK.md` remains unchanged at SHA-256 `25e6d7e577cd0bad3fbb029f0f7b54a8497783f36f22b334ca18de86ade59847`.

## Pair selection and difficulty

Require `T_A != T_B`, with ordered target IDs `T_A < T_B` by exact lexicographic string order. Freeze the admitted evidence-file universe by path/checksum manifest before inspecting values to select the pair. If a source-neutral pair and disease were already fixed before inspection, use them and apply the original eligibility rule. Otherwise select the lexicographically first eligible tuple `(D,T_A,T_B)` in that manifest's universe. Eligibility is exactly the initial rule: at least one direct in-scope row per target, with at least two distinct non-null referenced study-locus IDs in the union. Never search for a preferred overlap pattern, discrepancy, missingness pattern, interesting biological label, or model failure. If no eligible tuple exists, report infeasibility.

If bounded scanning is necessary, its file/row bounds and selection order must be declared before values determine the pair; freeze that supplied-subset universe and use the same deterministic selection rule inside it. Subsequent answer generation may not quietly expand or truncate the scope. The eligibility rule ensures multiple-record composition only. It does not establish difficulty, scientific novelty, or that an LLM adds value; an easy but eligible case remains easy.

## Two separate coverage assertions

Record **evidence coverage** and **credible-set join coverage** separately:

- Evidence coverage: are all source evidence rows in the declared release/source universe admitted, or only a stated subset? Target-specific and absence claims are relative to this evidence universe.
- Credible-set coverage: are all credible-set shards from the admitted release present and validated, or only a stated subset? A missing match under partial coverage means “not found in admitted credible-set shards,” not a proven dangling reference in the complete provider release.

An evidence-exhaustive result may still have incomplete credible-set linkage. Report that state explicitly. A complete join search with no match can establish a dangling reference only relative to the verified complete snapshot, not all releases or the live provider service. An arbitrary collection of complete files is not automatically a complete provider release.

## Exact accounting units

For each target, distinguish:

| Count | Unit and definition |
|---|---|
| `raw_evidence_rows` | Every admitted in-scope physical row, including duplicates |
| `missing_evidence_id_rows` | Physical rows whose `id` is absent/null/empty |
| `distinct_evidence_ids` | Distinct non-null/nonempty `id` strings |
| `conflicting_evidence_ids` | Distinct evidence IDs with more than one required-field projection across their admitted rows |
| `missing_locus_key_rows` | Physical rows whose `studyLocusId` is absent/null/empty |
| `distinct_referenced_locus_ids` | Distinct non-null/nonempty `studyLocusId` strings |
| `resolved_locus_ids` | Distinct keys with exactly one distinct required credible-set projection, regardless of duplicate copies |
| `unmatched_locus_ids` | Distinct keys with no admitted credible-set match; label join coverage |
| `conflicted_locus_ids` | Distinct keys with multiple different required credible-set projections |
| `rows_with_resolved_join` / `rows_with_unmatched_join` / `rows_with_conflicted_join` | Physical evidence rows whose nonmissing key has the corresponding key-level status |

Thus `raw_evidence_rows = missing_locus_key_rows + rows_with_resolved_join + rows_with_unmatched_join + rows_with_conflicted_join`, and `distinct_referenced_locus_ids = resolved_locus_ids + unmatched_locus_ids + conflicted_locus_ids`. Neither accounting identity equates row counts with independent observations. An unambiguous join with a missing or non-GWAS `studyType` still has a unique table match, but it is not a verified GWAS-type object. Keep join status, type verification, and field-comparison status separate.

## Baseline and allowable evaluation claims

The frozen deterministic baseline can produce the complete required structured answer, including every missingness branch and interpretation limit. There is no demonstrated additional LLM role in faithful explanation or abstention. This design alone supports technical conformance checks and, if separately measured under matched inputs/outputs, resource or latency comparisons. It does not establish an agent advantage, scientific discovery, target prioritisation, or usefulness to researchers. Any usability claim needs a separately specified and justified measurement design; an AI judge's preference is not sufficient evidence of usability.

These clarifications tighten selection, accounting, and claims without changing the source-composition question. They are not informed by a result or a reference answer.
