# Q03 source-only task specification

Status: initial semantics frozen before biological row inspection, 2026-11-02. This file is a task design, not an answer or experiment result. The designer has read official provider documentation and schema-only metadata, and has not read local biological rows, prior answers, human/expert responses, outcome labels, or evaluation results.

## One question

**For the two predeclared target IDs `T_A` and `T_B` and the one exact disease ID `D`, how much of their direct Open Targets 25.09 GWAS evidence refers to shared versus target-specific provider credible-set objects, what study and lead-variant identities can be verified from the linked records, and does this establish independent genetic support for either target?**

This is a source-composition and identity-consistency question. “Target-specific” means present for only one of the two targets within this exact data slice. It does not mean biologically unique to that target. Inputs must bind the three identifiers before answer generation. Human-readable labels are annotations, never join keys. No target ranking, causal effect, drug efficacy, clinical probability, MR result, or intervention direction is requested.

## Fixed scope and inputs

- Release: Open Targets Platform 25.09 only; require a manifest that identifies every admitted evidence and credible-set shard and its checksum, and states whether evidence coverage is exhaustive for the specified slice. An incomplete manifest permits only a supplied-subset answer.
- Evidence filter: `datasourceId = gwas_credible_sets` (or its verified source partition), `targetId IN {T_A,T_B}`, and `diseaseId = D` by exact string equality. No ontology descendants, ancestors, phenotype similarity, symbol-based expansion, or score threshold added by the task.
- Join: exact, non-null `evidence.studyLocusId = credible_set.studyLocusId`, within the same release. No chromosome/position/region proximity fallback, rsID substitution, or inferred study match.
- All filtered evidence records remain in the audit, including missing IDs, unjoinable records, or conflicting duplicates. Missingness must not silently become zero support.
- A fixture is eligible for a nontrivial Q03 only if both targets have at least one in-scope evidence record and their union contains at least two distinct non-null `studyLocusId` values. This eligibility rule is fixed before values. It does not require a particular overlap pattern or answer. If no eligible predeclared pair is available, report Q03 infeasible rather than changing semantics after seeing the result.

## Exact required fields

| Source | Required fields / provenance | Purpose |
|---|---|---|
| Task manifest | `release`, `T_A`, `T_B`, `D`, admitted relative paths and checksums, coverage assertion | Fix universe and reconstruct the slice |
| `evidence/sourceId=gwas_credible_sets` | `id`, `targetId`, `diseaseId`, `studyLocusId`; source partition or `datasourceId`; row locator | Define evidence and membership |
| Same evidence | `studyId`, `variantId` | Direct identity comparisons; nulls are allowed and meaningful |
| `credible_set` | `studyLocusId`, `studyId`, `variantId`, `studyType`; row locator | Resolve provider object, reported study ID, and lead variant |
| Target and disease reference | target `id`/`approvedSymbol`, disease `id`/`name` if present | Label exact input IDs; missing labels do not block the ID-level answer |

Source `resourceScore`, `score`, coordinates, fine-mapping confidence, and variant membership arrays are not needed to decide the question. They must not be used as undocumented tie-breakers, evidence weights, or criteria for selecting the pair. Study metadata, named cohorts, ancestry, participant overlap, and original study design are outside the confirmed input contract. Evidence columns with cohort-like names do not establish that these fields are populated or complete for this source.

## Required answer structure

1. State the exact IDs, release, direct disease scope, and exhaustive-versus-supplied-subset coverage.
2. Give each target's raw evidence row count; unique valid evidence-ID count; non-null distinct referenced `studyLocusId` count; and separately the counts with missing keys, missing credible-set matches, or ambiguous/conflicting matches. Preserve locators for every record. Repeated identical source rows are reported as duplicates, not new evidence IDs.
3. Partition the distinct referenced IDs into `shared = L_A intersect L_B`, `A_only = L_A minus L_B`, and `B_only = L_B minus L_A`, listing IDs and evidence IDs for all three groups. These are membership facts even if a credible-set join is unresolved; distinguish *referenced objects* from *resolved objects*.
4. For each referenced ID, list the linked credible-set `studyId`, lead `variantId`, and `studyType` when uniquely resolvable, plus the source locators. If multiple matched rows are identical on the required projection, collapse for reporting and disclose their multiplicity. If required values conflict, retain the alternatives and mark the object unresolved; do not choose a preferred row.
5. For every evidence-to-credible-set link, independently classify `studyId` and `variantId` as `equal`, `different`, or `not_assessable`. Compare exact strings only when both values are present and the credible-set projection is unambiguous. A missing value or ambiguous join is `not_assessable`, not agreement. `different` is a recorded identity discrepancy requiring explanation, not proof of biological contradiction. Only credible-set `variantId` is called a lead variant under the provider contract; do not assume every other variant-valued column is a lead-variant measurement.
6. Report distinct non-null linked `studyId` values across the resolved shared/A-only/B-only groups and explicitly show study-ID reuse across groups. Distinct study IDs count provider study labels, not independent studies. A missing study ID prevents the corresponding study-identity statement.
7. Conclude narrowly: describe source reuse and unresolved checks; state that this slice does **not establish independent genetic replication or target superiority**. An additional study table would improve traceability but would not by itself prove participant independence.

## Valid answers and abstention

- A complete valid answer supplies the partition, row/key accounting, source locators, per-field consistency states, and the interpretation limits. A partially answerable instance should return verified membership facts and abstain only on the unavailable study/variant claims.
- Missing `studyId` on the evidence side still allows reporting the *credible-set record's reported study ID* if available. It prevents checking agreement between evidence and credible-set study identities. Missing study metadata prevents auditing original phenotype/cohort/sample overlap; an opaque `studyId` alone does not repair this.
- A `studyLocusId` join establishes provider object identity in the admitted release. It does not establish equality of separately reported variant/study fields when those fields are missing. Coordinate or region overlap establishes neither.
- A complete empty slice means no records in this source/release/direct-ID scope; it does not mean absence of genetic association. An incomplete slice cannot establish exhaustive absence or exhaustive A-only/B-only membership. Label all groups as “within the supplied subset.”
- Abstain from the whole composition answer only if target/disease IDs cannot be fixed, source/release provenance is indeterminate, required membership fields are absent, or the manifest does not allow a reproducible admitted subset. Otherwise give a partial answer with explicit unresolved parts.
- Do not harmonise unequal variants using rsIDs, coordinates, allele flips, or builds: these inputs do not establish a shared harmonisation contract. Missing/unequal lead-variant IDs do not show that the full credible sets are disjoint.

## Dependence and overlap caveats

The evidence and credible-set tables are related outputs of the same provider pipeline, not independent evidentiary sources. Reusing the same `studyLocusId` for two targets is source reuse, not two replications. Different credible-set IDs can arise from one study, including different signals or processing methods. Different study IDs can reuse participants, named cohorts, controls, summary statistics, or related traits. Equal lead variants alone neither establish colocalisation nor prove the same causal gene; unequal lead variants do not exclude shared credible-set variants or LD. These issues require appropriate underlying study, variant, LD, and colocalisation information. Neither overlap counts nor target-specific counts justify stronger causal support for one target.

## Faithful deterministic baseline (specification only)

Use a transparent table operation, without an LLM or learned scorer:

```text
validate manifest; load admitted release-matched source projections
filter evidence by exact source, two target IDs, and exact disease ID
retain source locators; audit missing IDs and duplicate/conflicting evidence IDs
for each target: L[target] = distinct non-null referenced studyLocusId values
compute shared / A_only / B_only by exact set operations
index credible_set by studyLocusId, preserving all matched rows
collapse only identical required credible-set projections; mark conflicting projections unresolved
left-join every evidence record to this index; never drop unmatched evidence
for studyId and variantId independently:
    not_assessable if join unresolved or either comparison value missing
    else equal if exact string equality; else different
group resolved objects by non-null reported studyId; retain group provenance
render stable ID-sorted tables, accounting totals, and fixed interpretation limits
```

Missing means absent/null/empty string, never string coercion into a valid key. Duplicate evidence IDs with conflicting required fields are reported as conflicts and kept in membership accounting by their observed rows; unique-ID count must not be mislabeled a count of independent evidence. A conflicting `studyType`, a missing `studyType`, or a value other than `gwas` is explicitly flagged and prevents calling that joined object a verified GWAS-type object. No scripts or experiments are executed by this design task.

The deterministic baseline is capable of the entire answer. An LLM system must therefore demonstrate an improvement in faithful explanation, abstention, or usability beyond this baseline; a correct join and partition alone do not establish an agent advantage. This task cannot validate a causal inference engine or clinical calibration.

## Scientific and provider basis

Official documentation was read on 2026-11-02. These are live methodological pages, not a frozen 25.09 schema guarantee; local 25.09 schemas and manifests control field availability and release provenance.

- [Open Targets: target-disease evidence](https://platform-docs.opentargets.org/evidence): target/disease identifiers are standardised; GWAS evidence links credible sets to genes through the L2G workflow. This motivates distinguishing a target-linked evidence row from a separate study.
- [Open Targets: credible sets](https://platform-docs.opentargets.org/credible-set): a credible-set object includes study and lead-variant context; its identifier is opaque. The documentation separates variant overlap from colocalisation analysis and states that fine-mapping confidence is not association strength or effect size. These distinctions motivate exact object linkage and narrow identity claims.
- [Open Targets: studies](https://platform-docs.opentargets.org/study): a study may contain outputs of different fine-mapping workflows; study annotations can include cohort, ancestry, sample-size, phenotype, and publication information. Their availability varies. This motivates refusing to equate credible-set counts or distinct provider study labels with independent replication.
- [Open Targets: associations](https://platform-docs.opentargets.org/associations): direct associations use exact target-disease terms, while indirect associations can propagate evidence through disease descendants. Q03 fixes direct scope so changing ontology scope cannot silently alter the composition.

## Reporting-only assessment

This is honestly a reporting/verification benchmark with scientific interpretation constraints. It can test whether a system faithfully composes two related source tables, accounts for scope and missingness, and avoids overstating independence. Without original study identities where missing and suitable cohort/variant metadata, it cannot decide independent replication, causal-target identity, effect agreement, or intervention value. Describe it as source consistency and scoped evidence composition; claiming scientific target prioritisation would exceed the available information.

## Freeze and schema-only record

Before this file was written, source-feasibility supplied names/types for the relevant fields and reported no `study` directory under the 25.09 output. It also reported credible-set files in core and an isolated completion location. No file is automatically admitted on that basis: checksum and release provenance are manifest requirements. The designer has not inspected biological row values or answer outputs. The full initial file is frozen by its SHA-256 in `INITIAL-SEMANTICS.sha256`; later findings must be separate, dated addenda and must not rewrite this initial specification.
