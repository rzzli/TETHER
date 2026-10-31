# R08 existing-source feasibility — preparation only

The existing local data can support metadata-qualified immunology candidate discovery. This is not a fresh-case selection, source-sufficiency assessment, intervention recommendation or frozen benchmark. No model was run, and no candidate outputs, protected outcomes, labels or gold answers were consulted for this scan.

## Scope and verified availability

On 2026-10-26, all 112 selected original files and their 112 archived download receipts were freshly SHA256 checked: ten OT 25.09 target tables, one disease table, one HGNC snapshot dated 2026-10-10, and the existing 100 Europe PMC evidence shards across the original and supplemental directories. All hashes, sizes, recorded receipt paths, column-name schema fingerprints and row counts matched the retained inspection inventory. Original files total **8,221,772,460 bytes**; the full hash plus projected scan took **212.219 seconds**. Receipt hashing read another 96,561 bytes. All 112 paths and content hashes are distinct.

The inventory anchor is `data/derived/literature-coverage-20261017T082208Z/inspection.json` (SHA256 `f523b156957107afa0bfcd2fc111d70ef269950e367006ff70349effc56f1226`). Its original manifest digest is retained; original manifest bytes were not reopened. Current catalog SHA256 is `cac453e30dd3f21c9684ef2e84132fd3ab373949501ca349619567c8c6f345fb`. The inventory's selected-complete label is not whole-release completeness. Other evidence partitions are inventoried but not freshly parsed or scientifically qualified in this feasibility pass.

Evidence rows were Arrow-filtered before Python conversion, using only identifiers, source/datatype, article IDs, publication metadata and selected context fields. No text-mining sentences, clinical fields, scores or outcome values were projected. `known_drug` and `chembl` were explicitly excluded. The scan covered **22,881,069 physical literature rows**, producing **10,413 matching rows and distinct evidence IDs** across 70 provisional target/concept combinations. There were zero repeated evidence IDs and zero conflicting projected-metadata IDs; this says nothing about scientific contradictions in unread passages. Compressed sizes of projected Parquet column chunks total **1,359,265,184 bytes** (metadata estimate, not measured physical disk I/O). Selected Arrow arrays total 2,012,804 bytes. Hashing used 1 MiB chunks and Arrow batches were capped at 65,536 rows. Peak process memory was not measured.

## Reproducible, unranked identifier frame

All 14 proposed symbols uniquely resolve to approved HGNC records and matching OT target IDs. Four requested disease names resolve to **five** exact-name ontology records: EFO_0000685 rheumatoid arthritis, EFO_0000729 ulcerative colitis, EFO_0000384 Crohn's disease, EFO_0000676 psoriasis, and HP_0001370 Rheumatoid arthritis. Both RA concepts remain visible; a qualified concept-selection rule must resolve this ambiguity before case freeze. The table counts matching physical metadata rows, not strength or independent replications.

| Target | Pinned Ensembl ID | RA EFO | UC | Crohn | Psoriasis | RA HP |
|---|---|---:|---:|---:|---:|---:|
| BTK | ENSG00000010671 | 7 | 6 | 5 | 9 | 149 |
| CD80 | ENSG00000121594 | 9 | 47 | 14 | 23 | 132 |
| CD86 | ENSG00000114013 | 6 | 43 | 11 | 18 | 96 |
| CTLA4 | ENSG00000163599 | 19 | 104 | 18 | 69 | 387 |
| FCGRT | ENSG00000104870 | 3 | 3 | 0 | 3 | 5 |
| IL12B | ENSG00000113302 | 0 | 60 | 38 | 144 | 17 |
| IL12RB1 | ENSG00000096996 | 0 | 6 | 2 | 7 | 4 |
| IL12RB2 | ENSG00000081985 | 0 | 3 | 6 | 5 | 2 |
| IL17A | ENSG00000112115 | 205 | 682 | 328 | 4143 | 2090 |
| IL17RA | ENSG00000177663 | 2 | 18 | 13 | 178 | 58 |
| IL23R | ENSG00000162594 | 4 | 182 | 162 | 241 | 77 |
| ITGA4 | ENSG00000115232 | 1 | 9 | 9 | 1 | 9 |
| MADCAM1 | ENSG00000099866 | 0 | 102 | 33 | 3 | 2 |
| TYK2 | ENSG00000105397 | 3 | 48 | 28 | 228 | 74 |

Actions, modalities, tissues and final case keys are null throughout the machine-readable frame. No case is called unexposed or assigned to development/confirmation. Five combinations have zero matches in this selected literature subset; that does not establish biological absence. Sixty-five have one or more records, which does not establish adequate source text or action-specific evidence.

## Dependence, dates and context

The matched rows cite **8,573 distinct article identifiers**, and **1,417 articles occur in more than one target/concept combination**. Article-to-pair membership is retained for later exposure and clustering decisions; rows and cases must not be treated as independent because their evidence IDs differ. No content-based scientific deduplication was attempted.

Every row has publicationYear and a literature identifier. A PMC identifier is populated on 7,638 rows; publicationDate and evidenceDate are populated on 10,343, leaving 70 without those dates. Publication dates range from 1977-01-01 to 2025-07-11; **440 rows have a publicationYear different from the year in publicationDate**. Both values and original locators are retained in publication-date-disagreements.json. This is an unresolved metadata inconsistency (possibly differing date conventions); no date is repaired or promoted to historical eligibility. The source dates are descriptive metadata, not proof of earliest public availability or independent publication verification. Europe PMC file download observations range from 2026-10-11 to 2026-10-17; these establish contemporary upper bounds only. HGNC's snapshot label and download observation are also distinct. The projected studyId, ancestry, ancestryId, cellType and biosamplesFromSource fields are unpopulated for all selected rows. Missing structured context must remain unknown; unread source passages could report additional context.

Each raw source entry has an allowed agent-evidence/reference role and no recorded parents; fresh receipt and source checks therefore reveal no evaluator ancestor in this scoped inventory. This does not authorize future derived manifests or prove that upstream provider annotations never incorporated clinical knowledge. No evaluator artifacts were read. Exact original row-group/row locators were replayed for **14 metadata rows, one per target**, and matched without remapping.

OT catalog terms report CC0 1.0 with upstream and source-scope qualifications; HGNC redistribution/terms remain explicitly unverified. No new online terms check was performed. Article IDs or PMC access do not establish reuse permission for full text or passages. Actual passage rights and completeness must be recorded before sharing model-visible excerpts.

## Requirements before selection or execution

1. Merge this unranked frame with the independent exposure register, including Virtual Biotech and shared-article exposure. Do not use model performance to choose a target or indication.
2. Obtain HR3 domain-matched reviewer coverage and resolve the RA concept policy. Preserve both concepts in the audit even if one is later excluded.
3. Qualify a bounded, deterministic set of source passages and their rights, locators, context, publication precision and available bounds. Source presence is not sufficiency. Define uncertainty/low-information inclusion before outputs.
4. Assign action/modality/tissue only when the intended question and pinned sources justify them. Metadata here supports none of those assignments by itself.
5. Replay all selected passage locators, enforce complete payload budgets without silent truncation, verify no evaluation ancestors, group repeated targets/articles appropriately, and freeze exclusions/splits before generation.

All currently independent metadata work is complete. Freshness, source-content sufficiency, human coverage and exact case selection remain unresolved; no new active cases or model-input manifests were generated.

## Reproduction and retained evidence

Scratch evidence lives in `data/cache/recovery-step8-source-feasibility-20261026/`: file-checks, identifier-resolution, candidate-pair-metadata, matched-metadata JSONL, article membership, locator replay, catalog scope, partition inventory, progress and resource summary. Planning `source-feasibility-pins.json` hashes each artifact and the preparation scripts; scripts are copied here for review, not integrated into runtime.

The initial scratch probe stopped on the duplicate RA name and a Python filename collision (`inspect.py` shadowed the standard library); its failure.json is retained. The successful script was renamed `feasibility_scan.py` and deliberately preserved all five concepts. This was a preparation-script correction, not a changed source record or silent case substitution. Runtime, worker, sealed runs and existing review packets were untouched.
