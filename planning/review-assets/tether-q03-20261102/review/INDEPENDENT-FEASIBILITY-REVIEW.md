# Q03 independent source-feasibility review

2 November 2026 UTC. **Pass within the bounded source-reporting scope. No new
scientific or model experiment is justified by this feasibility result alone.**

This follows the earlier [route review](ROUTE-REVIEW.md). The later assignment
explicitly permitted original-row verification; this reviewer then inspected the
eight selected source rows and three identifier labels. No candidate answers,
human responses, clinical outcomes or model/backend calls were used. The source
designer's frozen initial specification remains unchanged.

## What was independently checked

The [checker](verify_feasibility_independent.py) imports neither the source-audit
producer nor the TETHER engine. Its [retained result](INDEPENDENT-FEASIBILITY-CHECK.json)
records metadata pins, footer and receipt comparisons, an independent selection
calculation, original physical-row reconstruction and selected missingness. The
1,160 assertions are overlapping software/data checks, not independent scientific
observations.

| Property | Independent result | Limit |
| --- | --- | --- |
| Source inventory and receipts | Exact manifest/queue/catalog path sets, current acquisition-state hashes, receipt identities/URLs/releases/sizes and manifest SHA values agree | The source agent's 125-file, 2,768,160,958-byte raw SHA scan is inherited; this reviewer did not repeat full payload hashing or authenticate publisher hashes |
| Footer counts | All 136 evidence/credible-set/target/disease file footers checked: 1,753,850 evidence rows; 2,862,043 credible-set rows; 78,726 target rows; 39,530 disease rows | Footers do not qualify scientific fields |
| First eligible tuple | An independent four-ID-column pass across all 100 evidence shards reproduces the bound disease and distinct ordered targets | No effect/score/label fields used for selection; this remains a deterministic feasibility example |
| Selected-slice completeness | Independently scanned matching target/disease/locus row multiplicities equal the four retained evidence rows | Credible-set global key uniqueness is inherited from the source agent's full key scan; this review reread the four selected credible-set rows |
| Original locators and labels | All eight source rows and three labels exactly reproduce at seven original physical row groups | Projected fields only; no full locus/LD arrays or upstream study/cohort data read |
| Nulls, object counts and QC context | Four evidence rows have null study/variant IDs; four credible-set objects have three reported study IDs and three reported lead-variant IDs; one study ID is reused across target groups | Neither four objects nor three labels is an independent-replication count |
| Attempt accounting | A retrospective attempt record describes a terminal-telemetry failure followed by success; successful-pass counters agree | It does not recover overwritten failed-pass projections, first-pass resource totals or a contemporaneous code pin |

The 125-file source manifest and the two label-source files have different
scopes. The source agent separately hashed the two label originals; this review
verified those label receipt/manifest bindings and original rows without another
full-file hash pass. Exact catalog/queue agreement establishes the declared local
universe, not all provider studies or completeness against an independently
acquired publisher listing.

## Selection result and denominator clarification

The independently reproduced tuple is disease `EFO_0000094`, target A
`ENSG00000009413`, target B `ENSG00000026297`. The labels independently reproduced
from the original reference rows are B-cell acute lymphoblastic leukemia, REV3L
and RNASET2. They were not selection keys or a proposed therapeutic comparison.

The narrow selection pass decoded four identifier columns for 1,753,850 rows,
then converted only 172 rows with disease ID no later than the chosen disease to
Python. That prefix contains one disease and 100 target groups. Its 4,950 distinct
ordered-target combinations contain 4,894 eligible pairs under the frozen
at-least-two-distinct-loci rule. **The selected pair is already the first distinct
pair; there are zero earlier pairs to reject in this observed frame.** A claim
that this audit empirically exercised an earlier-ineligible-pair branch would be
incorrect. The independent implementation retains complete locus sets and
enumerates distinct combinations rather than reusing the producer's capped
two-locus selection calculation.

These 4,894 possible pairs are highly overlapping compositions of 172 rows, not
4,894 independent samples or ready experimental cases. No broad biological
availability conclusion follows from them. The feasible selected slice is four
evidence rows, one for A and three for B, with four referenced source-object keys.

The source audit's two 1,753,850-row evidence passes are repeated traversals of
the same evidence universe. Its 2,862,043-row credible-set traversal is a
different key universe. The 70,001 evidence-detail rows and 126,062 credible-set
detail rows are the projected row groups decoded to extract eight selected
records; they are not additional selected evidence. The label scan visits
118,256 rows to locate three labels. These denominators must remain separate.

## Interpretation of the selected original rows

All four evidence `id` and `studyLocusId` values are present. Evidence `studyId`
and `variantId` are explicitly null in all four; they are not mismatches or
agreement with the credible-set values. The two field comparisons therefore
have four `not_assessable` dispositions each. The credible-set table's reported
study and variant identifiers can still be attributed to that table without
inventing the missing evidence-side assertions.

The four matched credible-set rows all report `studyType=gwas`, method `PICS`,
and a confidence description of top-hit-based fine mapping. Every selected row
carries the provider's three flags: a study-level QC flag, fine mapping without
an in-sample LD reference, and origin from a curated top hit. These flags are
retained source context, not this review's new QC adjudication or a blanket
declaration that each source is invalid.

The selected four rows lack beta, standard error, effect frequency and sample
size, and the evidence rows lack inspected cohort/ancestry fields. This blocks
effect comparison, harmonization and independence assessment **for this selected
slice**. It does not establish that all 2,862,043 credible-set rows lack effects
or that every possible task on the release is infeasible. The absent local study
table is an inventory-level gap; even acquiring it would not automatically prove
participant independence or causal validity.

Three reported study IDs and three reported lead variants across four objects
are source-reuse facts. They neither prove nor disprove common participants,
independent replication, shared causal variants, colocalisation or target
superiority. No variant-string parsing was used to invent a build/allele contract.

## Read and resource accounting

The final peer pass independently traversed 1,753,850 four-column evidence rows
(161,504,140 Arrow logical bytes) and seven selected row-group projections
(243,440 decoded rows; 60,271,349 Arrow logical bytes), reconstructing 11 retained
records. It did not rescan the full credible-set ID columns. Metadata/receipt
reads and 136 footers are additional, not included in those Arrow-byte figures.

There were two successful peer passes: the first record is preserved as
`INDEPENDENT-FEASIBILITY-CHECK-initial.json` with its checker source. The second
added the explicit slice-completeness assertion and pair counters. Thus this peer
review performed 3,507,700 identifier-row visits and 486,880 selected-row-group
row visits in total, with 443,550,978 Arrow logical bytes across those passes.
Repeated visits do not increase the number of selected observations. No peer
peak-memory or physical-I/O measurement was made. Per-pass elapsed times are in
the JSON records; they are validation timings, not model or platform benchmarks.

The source agent's retrospective attempt record describes two attempts: a terminal
Windows telemetry error after source reads, followed by a corrected rerun. Its 16.14 seconds,
524,574,720-byte peak working set and 570,220,997 decoded Arrow bytes describe the
successful source-audit pass only. The corrected attempt record confirms that
the second attempt overwrote the first attempt's three projections, source
manifest and input binding at unversioned paths. Their first-attempt bytes,
hashes and binding timestamp are unavailable. The retained text record does not
recover those failed-attempt artifacts. Neither measured attempt has a retained
contemporaneous code pin; one must not reconstruct it from the current script.

An explicit inventory-hash guard was added after the measured run and checked by
the retained locator verification. Later no-clobber/output-publication changes,
if introduced, also require their own software checks and must not inherit the
16.14-second measurement as their qualification. These recordkeeping limits do
not invalidate the present original-row matches or independent selection pass;
they do limit execution-history and resource claims. Neither a post-run guard
nor this peer audit is retroactively called prospective execution.

The final [metadata-only delta](FINAL-METADATA-DELTA.json) binds these corrections.
The changed excerpt manifest adds retention provenance; removing that addition
reproduces its earlier pinned bytes under the original encoding. Source-count,
selection, input-manifest and retained-projection hashes are unchanged. The old
attempt record is separately retained. The new no-clobber helper's fixture record
reports four checks and zero raw-source reads; this peer delta checks its exact
file pins and declared scope, not a new end-to-end source execution. No original
source file was opened during this final metadata check.

## Route disposition

Q03 establishes a reproducible, scoped source-composition feasibility example,
with substantive identity and scientific-input limits. It does not supply a
locked scientific reference set, unseen benchmark, independent-study sample or
model-comparison result. The fully sufficient deterministic baseline still
leaves no demonstrated faithfulness or abstention advantage for an LLM.

Proceed to Q06's narrow technical-paper reconciliation unless a distinct,
predeclared technical estimand justifies Q04/Q05. Do not automatically download
more sources, recruit experts, manufacture benchmark labels or rerun closed
model cells to make this case appear scientifically stronger. Broader genetics
readiness remains unqualified; it is not declared universally impossible.
