# Q03 source feasibility audit

The frozen question is feasible as scoped source-composition reporting and missingness-aware identity verification. It cannot establish independent genetic replication, effect agreement, target superiority, or a causal conclusion. The deterministic first eligible slice gives a real nontrivial example, but both requested evidence-versus-credible-set identity comparisons are unassessable because the evidence-side values are missing.

## Boundary and sequencing

Only original Open Targets 25.09 Parquet sources, their named acquisition metadata, neutral selected provider catalog metadata, and original target/disease label mappings were admitted. No prior candidate/reference answers, human/expert responses, outcome labels, memory, clinical archive contents, current API payloads, new downloads, paid calls, or backend study were used. Filename discovery did not open prior review artifacts. A preliminary broad catalog-ID filter also printed neutral metadata for a few uncollected GWAS provider entries; no payloads or research values were read, and none entered the admitted universe. The persisted inventory uses the explicit selected-product allowlist.

1. `SOURCE-SCHEMAS.json` and `SOURCE-INVENTORY.json` were produced using only file metadata and Parquet footers, with zero biological rows read.
2. Task semantics were frozen as SHA-256 `25e6d7e577cd0bad3fbb029f0f7b54a8497783f36f22b334ca18de86ade59847`.
3. Before biological rows, `SOURCE-SELECTION-POLICY.json` was frozen as SHA-256 `d57234aa5facafeeb4956ee9cf80febf00a9aa9ef2e73a186df9e083bdc1edeb`. It binds the inventory digest, the complete 100-shard local evidence universe, distinct ordered target IDs, and the lexicographically first eligible `(diseaseId, targetA, targetB)` tuple. Eligibility is at least one direct row for each target and at least two distinct nonempty union study-locus IDs. Selection does not use scores, effects, labels, or a desired overlap pattern.
4. Only after that freeze were source rows decoded. Retained projections are in ignored `data/cache/tether-q03/`, not a candidate/reference-answer pack.

## Availability and provenance

| Product | Actual local complete files | Scope and evidence |
|---|---:|---|
| `evidence/sourceId=gwas_credible_sets` | 100 | 1,753,850 rows from footers; exact path-set equality with the named core download queue partition; every row's `datasourceId` checked during the full scan |
| `credible_set` | 25 | 2,862,043 rows; two core files plus 23 isolated completion files; exact path-set equality with the selected 25.09 catalog record; 26 physical row groups |
| `study` | 0 | One explicitly queued path, absent on disk; no completed receipt in the named batch state |
| `target` / `disease` | 10 / 1 | Original label projections only; labels never used as selection or join keys |
| `l2g_prediction` | 16 | Footer/schema inventory only; actual completed receipts show the catalog's zero-completed snapshot is stale; not used in Q03 |
| `colocalisation_coloc` | 0 | Four `.partial` files excluded; not parsed or used |

All 125 admitted evidence/credible-set payloads were independently SHA-256 hashed against local acquisition receipts: 2,768,160,958 bytes, all matched, all release IDs `25.09`. This is local receipt reconciliation, not publisher-authenticated hashing. `SOURCE-FILE-MANIFEST.json` records each path, size, hash, receipt ID, release, and publisher URL. The evidence and credible-set coverage assertions are separate; neither is a claim about all possible GWAS studies or other releases.

`LABEL-SOURCE-MANIFEST.json` separately pins the two original files containing the three retained labels: 13,397,731 bytes independently SHA-256 checked against their acquisition receipts, with each label's physical row locator. `SOURCE-EXCERPT-MANIFEST.json` lists the actual decoded column projections, retained source-only file hashes, and all 11 locators.

The absent study file is explicitly named in `data/manifests/private/core-2026-10-10-queue.json` with receipt ID `ot25-2082bc61c0bd8a16e75c6a51`:

`raw/open_targets_platform/25.09/output/study/part-00000-1e42fdda-f476-428f-8a26-2c8b5c9a3b1e-c000.snappy.parquet`.

## Deterministically bound slice

The exact disease is `EFO_0000094` (B-cell acute lymphoblastic leukemia). The distinct ordered targets are `ENSG00000009413` (REV3L) and `ENSG00000026297` (RNASET2). The labels come from original mapping rows after binding. These identifiers are an algorithmically selected feasibility example, not a proposed scientific target comparison.

The complete admitted evidence slice contains four rows: one for target A and three for B. It references four distinct non-null study-locus IDs, all uniquely resolved in the separately scanned 25-file credible-set universe. There are no missing membership keys, duplicated evidence IDs, conflicting evidence IDs, unmatched locus IDs, multiply matched locus IDs, or conflicting required credible-set projections in this slice. Every selected credible-set `studyType` is `gwas`.

This metadata sample is the complete selected slice, not a statistical sample of all Open Targets evidence. Its missingness must not be extrapolated to the full release.

| Field family | Selected evidence (4 rows) | Selected credible sets (4 rows) | Consequence |
|---|---|---|---|
| `studyLocusId` | 4 present | 4 present | Exact source-object linkage is possible |
| `studyId` / `variantId` | All missing | All present | Both independent string-equality checks are `not_assessable` for all four links; missingness is not agreement |
| Cohort / ancestry | All inspected fields missing | No corresponding schema fields | Cannot assess shared participants, cohorts, population transfer, or ancestry-specific evidence |
| Sample size | All missing | All missing | Cannot audit sample-weighting or effective independent sample count |
| Beta, SE, effect frequency | Evidence beta/CI missing; no SE field | All missing | Effect consistency, harmonization, and effect-size synthesis unavailable |
| P-value mantissa/exponent | All missing | All present | Can report provider lead-variant p-values; cannot reconstruct or combine effects |
| Build and allele orientation | No explicit build/ref/alt fields | No explicit build/ref/alt fields | Variant strings are kept opaque; no historically verified build or allele orientation is inferred |

All four linked records say `PICS` and describe top-hit-based fine mapping. All carry source quality-control flags for study-level QC, lack of in-sample LD reference, and curated top hits. Their missing effect/sample fields and source flags make the limitation substantive rather than merely missing paperwork.

Four source objects map to three reported study IDs and three reported lead-variant IDs. A study ID is reused across the two target groups, and a lead-variant ID is reused across two source objects. These are traceable identifier-reuse facts, not independent replications, shared-participant determinations, or colocalisation results. More independent grouping is impossible without appropriate original-study/cohort/participant and variant/LD metadata. A study table would help traceability but alone would not prove independence.

## Missing inputs and excluded claims

Required additional inputs for stronger scientific questions include release-matched study metadata, original sample/cohort identity and overlap, ancestry, study design and phenotype definitions, consistently oriented effect estimates and uncertainties, a verified historical build/allele contract, and suitable LD/full credible-set or colocalisation evidence. The exact requirement depends on the scientific estimand; simply counting distinct provider labels cannot substitute for it.

No inference from distinct strings to independent biology is permitted. The current slice cannot support MR, effect-direction agreement, replication counting, quantitative meta-analysis, causal-gene attribution, drug efficacy, or clinical calibration. Full locus/LD membership arrays and partially downloaded colocalisation files were not read. No current documentation was treated as proof of a historical schema/build invariant.

## Bounded execution and verification

PyArrow 21.0.0, batch size 8,192. One successful audit pass took 16.14 seconds, including 2.17 seconds of hashing. Peak Windows process working set was 524,574,720 bytes. Decoded Arrow logical bytes were 570,220,997; this counts repeated projection passes and excludes Python object overhead.

These are not physical disk-I/O measurements. Bytes presented to SHA-256 may come from filesystem caches; Arrow `nbytes` measures decoded projected buffers, not compressed Parquet reads, cache misses, or total storage traffic. Physical I/O was not instrumented.

| Phase | Rows decoded/scanned | Rows retained |
|---|---:|---:|
| Full evidence identifier selection | 1,753,850 | Eligibility aggregates only |
| Full evidence identifier slice | 1,753,850 | 4 |
| Scientific evidence columns in selected row groups | 70,001 | 4 |
| Full credible-set ID traversal | 2,862,043 | 4 locators |
| Scientific credible-set columns in selected row groups | 126,062 | 4 |
| Target/disease label projections | 118,256 | 3 |

There were two full audit attempts. The first reached terminal resource reporting after source extraction, then failed because Windows process-handle width was not declared in the memory-telemetry call. The pointer binding was corrected and the same frozen policy rerun. Resource measurements above are for the successful pass only; they are not total-turn costs. No semantic or selection change accompanied the telemetry correction.

`SOURCE-AUDIT-ATTEMPTS.json` records both attempts, their exit codes, the actual first failure, successful-pass counts/resources, and the absence of reliable first-pass timing/peak-memory measurements.

**Retention limitation:** attempt 2 overwrote attempt 1's three fixed-path source projection files, `SOURCE-FILE-MANIFEST.json`, and `SOURCE-INPUT-BINDING.json`. No separate first-attempt bytes or hashes were retained; the first binding timestamp is also unavailable. Equality of the two attempts' projection bytes cannot be established, and deterministic selection is not a substitute for retained evidence. The current source excerpts, hashes, binding, and feasibility JSON describe the successful second attempt. Attempt 1 failed before writing a feasibility JSON.

**Code-pin limitation:** no contemporaneous executed-script hash or separate file snapshot was captured for either measured attempt. The previously recorded script hash `a68448e1f6595edc3a54f06b2f9228ac0a2bda5bd87cb1c1679650f03ae938d4` identifies a later file that already contained the inventory-hash precondition, not either measured revision. Those exact post-run bytes are now preserved as `revisions/post-run-inventory-guard.py`, with this honest basis. Neither measured revision is claimed to have a recoverable independent byte-level pin; no synthetic reconstruction is represented as an executed artifact.

`verify_source_locators.py` independently reread seven original row groups and reconstructed all 11 retained records (four evidence, four credible-set, three labels) exactly at their zero-based physical row-group/row offsets. It decoded 243,440 projected rows and 60,271,349 Arrow logical bytes. It also rechecked the frozen task and inventory hashes. Results are in `SOURCE-LOCATOR-VERIFICATION.json`. An explicit frozen-inventory hash guard was added to the main audit after the successful run; the independent verification exercised that exact hash check without repeating the full scan.

The reusable audit now requires a fresh `--run-id`, places reports and projections in separate per-run directories, refuses existing directories/files, and records the main/helper code hashes at future run start. `SOURCE-NO-CLOBBER-VERIFICATION.json` documents a small collision fixture: existing run IDs, cache-only collisions, attempted JSON replacement, and unsafe run IDs were rejected; sentinel bytes were unchanged. These utility edits were not present in the measured run. They were tested without reading raw sources, and no full audit was rerun for the documentation or precondition changes.

This is a source feasibility audit. It runs no model, candidate system, reference-answer evaluation, new backend study, or paid service.
