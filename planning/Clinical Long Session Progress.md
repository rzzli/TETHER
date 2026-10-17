---
title: Clinical Long Session Progress
date: 2026-10-17
status: completed-with-scientific-gates
tags: [asof, clinical, aact, feasibility]
---

# Long-session completion and remaining gates

The prepared execution queue is complete. The three supplied intermediate AACT archives are restored, verified and stopped; the frozen 24-trial review now includes five registry dates. The complete selected literature inputs produced ten new source-verified contemporary dossiers after an explicitly diagnosed packet-size failure and bounded-packet correction. Clinical training remains **no-go for this development set**. Independent program/event labels, censoring and power are not established.

Open [the local results page](../data/benchmark/cohorts/clinical-long-session-20261017T064802Z/Review.html) for the integrated clinical review, timeline, origin-arm evidence and all ten dossiers. Read `data/derived/active-clinical-session.json` before resuming. No work in this completed batch should be automatically repeated.

## Restored snapshots and clinical review

| Requested date | Actual dump date | Studies | Table rows | Import time |
| --- | --- | ---: | ---: | ---: |
| 2023-07-01 | 2023-07-02 | 457,254 | 41,208,592 | 24.02 min |
| 2024-01-01 | 2024-01-01 | 477,238 | 43,274,501 | 25.56 min |
| 2024-07-01 | 2024-07-01 | 499,882 | 45,244,729 | 28.92 min |

Each new restore has 50 tables, all 24 selected NCT IDs, validated constraints/indexes and no checked identifier exceptions. The earlier January 2023 restore retains its nine unmatched stored-record rows; no originals were repaired. July 2023 is actually a July 2 dump. These dates do not establish exact first-public availability or event times.

The five observations are January 1, 2023; July 2, 2023; January 1, 2024; July 1, 2024; January 1, 2025. All 120 trial/snapshot observations are retained and deterministic timeline replay passed. The full ZIP and extracted-member hashes were independently rechecked after restoration. The optional January 2026 archive passed CRC, member-hash and dump-header checks but was **not restored or used in this endpoint**.

The review retains 24 exact-NCT publication searches, 18 structured source reports, and eight origin-scope checks covering 22 treatment arms. Reports are not independent incident events: 11 are in the reporting window, three predate origin and four follow the endpoint. Outcome, individual censoring and independent program labels remain unset. The review is AI-assisted, purposive and unblinded; a frozen protocol does not make it preregistered or independent gold.

Content qualifications distinguish eight primary reports/manuscripts, nine publication metadata/abstract records, six unavailable full contents, eight challenge pages, two generic NCI pages and one quarantined incompatible trial linkage. HTTP success alone is not usable article content. The original transport receipts and the initial failed mobile render are preserved. The final local HTML passed desktop/mobile layout and link checks.

Specific scientific distinctions retained:

- Vixarelimab phase 2a predates origin; phase 2b reporting and primary-completion dates answer different timing questions.
- The semaglutide–dapagliflozin paper reports a treatment difference and a nonsignificant subgroup interaction; stale UNKNOWN status did not establish absent evidence.
- N1303K results separate a nonsignificant primary sweat-chloride endpoint from improved secondary clinical measures.
- TAMARACK treatment cessation, registry follow-up and later development discontinuation are different events.
- PMID 41051123 links an incompatible retrospective rhinosinusitis study to the vixarelimab trial identifier; it is quarantined, with cause unknown.

## Complete selected literature inputs and ten dossiers

The new manifest has **2,206 files / 9,038,960,079 bytes**: 10 target, one disease, 2,194 evidence and one HGNC file. All 65 previously missing files are now checked: 16 already existed and 49 were downloaded under unique IDs into a separate supplemental directory. The previous worker, state and receipts are unchanged. All 2,205 Open Targets files match publisher SHA-1 checksums; download receipts and SHA-256 hashes were separately verified.

The publisher's manifest records a failed `coding_variant_view` step. Selected target/disease/evidence tables are separate paths; the broader upstream impact is unassessed. Matching checksums are not a claim of whole-release pipeline success or scientific validity.

The first complete-input build failed at the unchanged 64 MiB packet limit. Its directory and failure journal remain intact. An opt-in `--packet-layout bounded` now writes complete observations across the existing v2 artifact list. The default single-packet mode still fails explicitly, as does any individual oversized observation. No records, source fields, limits or budget defaults were silently changed. Normalization stays at recipe 2.2; layout/limit/code fingerprints are recorded separately.

The replacement scanned 29,823,171 physical rows, selected 26,985 distinct matching source rows and retained **31,554 case records**. It preserves every prior source object and observation, adding 14,640 case-level literature observations. Shared records repeat across action/modality cases and are not independent studies. There are 11 packets; the largest is 67,104,865 bytes, below 64 MiB. CFTR uses two packets.

| Case | Records | Packets | Total packet MiB |
| --- | ---: | ---: | ---: |
| cd276-efo_0003060-delivery_antigen-adc | 188 | 1 | 1.18 |
| osmr-efo_0000729-inhibit-antibody | 15 | 1 | 0.08 |
| erbb2-efo_0000305-inhibit-antibody | 2,339 | 1 | 13.85 |
| erbb2-efo_0000305-delivery_antigen-adc | 2,339 | 1 | 13.85 |
| pcsk9-efo_0004911-inhibit-antibody | 2,230 | 1 | 12.19 |
| pcsk9-efo_0004911-reduce_expression-sirna | 2,230 | 1 | 12.19 |
| il6r-efo_0000685-inhibit-antibody | 21 | 1 | 0.13 |
| cftr-mondo_0009061-activate-small_molecule | 12,549 | 2 | 75.63 |
| glp1r-mondo_0005148-activate-peptide | 9,616 | 1 | 59.04 |
| scn9a-efo_0005762-inhibit-small_molecule | 27 | 1 | 0.16 |

All ten dossiers passed source-inclusive semantic verification and a fresh audit of **20 distinct original rows**. An additional 20-row audit checks newly acquired literature projections. Numerical prediction features remain empty and all probabilities are null. Complete selected-file collection is not complete biological coverage or absence-of-evidence proof.

Canonical build: `data/derived/literature-coverage-20261017T082208Z`. Canonical pilot: `runs/literature-coverage-20261017T082208Z`. The explicit `planning/run-registry.json` preserves the previous canonical runs and failed build. Catalog scope is five AACT archives and the complete selected 2,194-file evidence unit; independent scientific validation remains `not_run`.

## Resources and verification

- AACT batch: 98.91 minutes; 51.54 GiB retained across the three restores. Database peak memory was not instrumented and remains null.
- Replacement snapshot: 63.203 seconds, 1.81 GiB peak process memory.
- Offline ten-case execution/audit: 377.500 seconds, 2.80 GiB parent-process peak. This metric excludes separate child-process peaks.
- **149 tests passed, zero skips**, all ten required probes, PowerShell syntax and dependency-free installed-wheel demonstration/verification passed. Five timeline regressions passed again after a subsequent display-only refinement; the final HTML passed responsive QA.
- Full-cis IL6R revision: 2,979 QC variants, 503 EUR LD samples and 3,600 independently recalculated LD entries. See [[Full Cis Genetics Revision]]. No MR or colocalization.
- At closeout, approximately 1.61 TiB remained free on D: and 1.60 TiB on E:.
- $0 model-provider spending; no live model adapter, scorer training, paid access or recurring monitoring. Disk capacity is sufficient for retained work; it is not a full-inventory capacity guarantee.

## Historical input route checked


| Candidate | Verified now | Remaining gate |
| --- | --- | --- |
| Open Targets 22.11 | Four actual Parquet samples parsed: target 326 rows, disease 99, molecule 76, mechanism 31; five product schemas checked. | One of 200 parts per sampled product; full collection is incomplete. Configuration and three selected upstream inputs are verified below; the exact EFO version remains unresolved. Twelve fields in the contemporary evidence projection are absent from the historical schema. |
| ChEMBL 31 | Archive listing, README and checksum listing retained; archived Open Targets ChEMBL 31 mechanism input parsed (6,656 rows), publisher SHA-256 matched. | Standalone ChEMBL distribution and target/molecule inputs not collected. Preserve historical drug/mechanism mapping separately from future clinical labels. |
| HGNC 2022-10-01 quarterly TSV | Complete 43,221-row archive parsed, provider object MD5 matched, all eight pilot symbols uniquely approved. Latest row modification is September 30, 2022. | Provider labels the historical version, but the current object was created in October 2024. Exact original public availability remains unverified; classify as reconstructed. |
| MONDO 2022-12-01 | Release/asset dates and internal version agree; 25,766 OBO terms parsed. | No publisher cryptographic digest, graph-reasoning validation or clinical indication mapping. |
| EFO 3.49.0 | Official release metadata gives December 15, 2022 publication. | Payload not collected; exact EFO version used by Open Targets 22.11 unresolved. Version 3.50.0 is January 16, 2023 and excluded at this origin. |

The [HGNC archive documentation](https://hgnc.genenames.org/download/), [MONDO release](https://github.com/monarch-initiative/mondo/releases/tag/v2022-12-01) and [EFO release](https://github.com/EBISPOT/efo/releases/tag/v3.49.0) support this scoped route. Retained payload hashes, receipt bytes and parser results are in `historical-sample-validation.json` and `historical-identifier-validation.json`. These checks do not admit historical agent inputs or repair missing historical annotations with current data.

Further archive inspection found the [Open Targets 22.11 SHA-256 manifest](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/22.11/release_data_integrity.sha256) and [release configuration](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/22.11/conf/22_11_2_platform.conf). All four sampled Parquet files plus three archived upstream files match provider hashes. The upstream EFO ontology and disease files each contain 22,274 consistent IDs; the ChEMBL mechanism input contains 6,656 rows. Configuration explicitly declares ChEMBL 31, Ensembl 108 and data version 22.11.2. The official [release notes](https://platform-docs.opentargets.org/release-notes) date 22.11 to November 24, 2022. Exact EFO version remains undeclared, but its archived input bytes are pinned. This supersedes the earlier upstream-provenance unknowns only for these inspected fields and files.

The historical HGNC entries agree with the target IDs in all 24 frozen records. Exact string matching yields candidates for 42 of 150 condition occurrences; these are study-level strings, often platform-wide, and **zero clinical indications are adjudicated**. Retain ambiguity instead of assigning a convenient ontology term. See `historical-provider-provenance.json`. ChEMBL target/molecule inputs and the standalone ChEMBL 31 distribution remain uncollected.


## Next work and stop conditions

| Area | Status | Next gate |
| --- | --- | --- |
| v0.2 offline T6 framework and ten dossiers | Implemented and technically verified | Independent scientific evaluation; no clinical-probability claim |
| Five-snapshot clinical feasibility review | Implemented as evaluator-only development evidence | Freeze origin-only program/arm/indication definitions, outcome estimand and censoring; independently count eligible events |
| Historical evidence inputs | Partially checked | Complete selected pre-origin input collection, annotation availability and historical adapter; never fill gaps from current data |
| Regional genetics | Full-window technical pilot complete | Resolve/qualify publisher metadata, study ancestry, cohort overlap and LD before replication or causal analysis |
| Additional molecular QTL | Scoped only | DICE supplement blocked by content challenge; OneK1K ancestry/sample differences unresolved; no association-driven source selection |
| Clinical scorer, MR, competitors, T2–T5 and H6 | Deferred | Separate scientific protocols, eligible inputs and validation; no inferred completion |

No additional user download is required for the next scoped public-data steps. Request a particular paper or monthly AACT snapshot only when a concrete ambiguity needs it. January 2026 supports a separately defined endpoint, not backfilling the frozen January 2025 outcome. The next useful step is program/arm/indication definition and an explicit feasibility decision, rather than manufacturing success labels or power from 24 purposively selected trial representatives.

The retained session contains protocols, all source receipts/qualifications, replay proofs, regression reports, original failed artifacts and measured resources. `data/manifests/public/` contains sanitized acquisition/normalization anchors. Read those records before any recovery; never re-import a completed database or resume into an existing output directory.
