# P05 source-only builder notes v1

Status: implemented and tested on fictional sources only. The neutral DRAFT is published. No actual source-value scan, registry collection, selected-case capture, model call, network call, or download has run. Root READY is deliberately absent from this change.

The paper scope is deterministic technical/source validation. The model branch remains closed after conformance failure. This builder creates stage 1 originals and their audit records; it creates no agent packet, evaluator reference, model output, causal/MR conclusion, action direction, or probability.

## Exact review artifacts

- Builder: `tools/science/prepare_source_validation_set.py`, SHA256 `ca51a824d76a2910ef607d3b0af26cfcad91df2bae6293479f1e1d7c6be4c02b`.
- Fictional tests: `planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_set.py`, SHA256 `20447a3e6ac5e23de4943604494cf63f4d80e3daa097e0f14900025e472adb1a`.
- Neutral DRAFT: `REGISTRY-PLAN-DRAFT-v1.json`, SHA256 `d2a16bbfa79794c6c19c4e8bed8ff7ae1a01fb5d04dc675b5685c7cf84da6174`.

The DRAFT pins the builder, all 66 current `src/asof/**/*.py` files, Windows, the absolute workspace `.venv` interpreter, Python 3.11.15, and PyArrow 21.0.0. No `src` file or P04/P04b artifact was edited.

## Before any actual values

Root must independently publish `REGISTRY-READY-v1.json` with `schema_version: 1`, `status: "READY"`, `scope: "p05_source_only_stage1"`, `frozen_by: "root"`, the exact DRAFT `plan_sha256`, and exact copies of its `code_sha256` and `environment`. READY also pins `row_guard_cutoff_utc`: an explicit UTC instant no earlier than the neutral frame's `2026-11-01T06:07:02.784027+00:00` default, and no later than execution admission. Tests can be pinned separately by root. READY is a prospective protocol freeze within already authorized work.

The builder holds guard files under stable locks, validates exact neutral metadata/catalog/code/environment bindings, and then reserves a new output directory exclusively through the public `RunJournal`. Only after reservation does it lock all 137 original payloads and all 137 receipts. It hashes every payload, verifies every exact receipt byte sequence and identity, privately archives content-addressed receipt bytes, and admits original SourceNode/catalog roles and contemporary availability against the frozen cutoff before reading source values. The verified manifest retains newly measured byte counts and hashes. HGNC remains `reference`; Open Targets originals retain permitted `agent_evidence` access. Raw selected-original captures are UNQUALIFIED/AUDIT_ONLY, `evaluation_only`, and `agent_visible: false`; these labels are enforced on every capture record as well as in per-artifact lineage. Stage 1 creates no agent packet.

The exact frame is 137 files / 2,866,248,239 compressed bytes: 100 GWAS evidence shards, all 25 credible-set shards, 10 target shards, one disease file and one HGNC TSV. Source reads are limited to the declared originals and receipts. The E: originals are opened read-only. Study data are absent and are never substituted.

## Registry, selection and originals

SQLite retains every physical GWAS row, its identity projection, eligibility/exclusions and unit hash, including duplicates and excluded rows. A normalized `source_files` table avoids repeating long physical paths and hashes; the `physical_rows` view exposes those fields together with zero-based row-group, row-in-group and physical-row locators. Native date guard values remain in `identity_json`; the frozen cutoff and replay rule are stored as registry metadata.

Small normalization reads include only target `id/approvedSymbol`, disease `id/name`, and HGNC `hgnc_id/symbol/ensembl_gene_id/status`, with explicit optional `gene_group/gene_group_id` presence. Exact, unique Approved HGNC/id/symbol mapping is required. No alias, case-fold, status repair, disease replacement or first-row resolution occurs. Known exposed symbols CD276, OSMR, ERBB2, PCSK9, IL6R, CFTR, GLP1R, SCN9A and CTLA4 are excluded; all other exposure is UNKNOWN. No freshness or independence claim is made.

The GWAS source partition and raw datasource must exactly equal `gwas_credible_sets`, and datatype must equal `genetic_association`. Registration projects identity fields plus the explicit eligibility-only fields `evidenceDate/publicationDate/publicationYear/releaseDate/releaseVersion`. Optional literature is converted only after selected-unit Arrow filtering. Native publicationDate and publicationYear describe the same event and use their intersected precision intervals; disjoint intervals exclude as a conflict. Evidence/release dates are separate. Entirely future intervals, straddling precision-unverified intervals and malformed explicit dates are excluded and retained in the registry. Missing dates remain unknown. releaseVersion is preserved upstream annotation metadata, with no assumption that it names the Open Targets release.

Up to twelve unique eligible `(targetId, diseaseId, studyLocusId)` units are selected by lowest SHA256 of `preprint-p05-deterministic-v1|release|targetId|diseaseId|studyLocusId`, with lexical ties. Twelve is an upper bound, with no promised data readiness: actual counts 1..12 are accepted and reported explicitly; zero fails with the full registry retained. Scientific measurements, numerical availability and model performance are unavailable to selection. A selected case is never replaced because its later join or measurement is missing or conflicting.

All selected GWAS physical rows, including excluded duplicates of a selected unit, are captured for audit only. An explicitly future-dated duplicate remains excluded and quarantined; capture never admits it as agent evidence. Every credible-set shard is scanned at batch size 8,192 using only the approved projection; exact selected studyLocusId Arrow filtering precedes Python conversion. All matching physical rows and conflicting projections are retained. Native studyId/variantId agreements, disagreements and missing context are reported without semantic variant inference. Selected-originals JSONL files preserve native beta/SE/p-value/sample-size observations as study/variant data; allele, scale, ancestry and genome build remain unknown unless the authorized source projection supplies them. NaN and both infinities are explicit typed invalid context, never replacement numbers. These unqualified audit captures are not gold references.

## Outputs and failure interpretation

Actual output, when root runs it, must be a fresh ignored `D:/Projects/drug_target_agents/data/derived/preprint-p05-source-validation-<UTC>` directory. It contains the SQLite registry, selected-case plan, bounded per-case audit-only selected-original JSONL, mapping provenance/schema absence, coverage/counters, resource report, complete original/neutral-metadata lineage, private exact receipts, hash-chained stage journal and final artifact seal. Lineage includes every original, the neutral frame/acquisition/current catalog, DRAFT and READY, with explicit per-artifact roles. Neutral registry/case-plan data parents are exactly the original source IDs plus neutral-plan; other protocol/catalog metadata are explicit bindings. Audit capture/product-value nodes are never parents of the neutral registry or case plan. Both agent-packet builders and reference builders belong to a later fresh phase and must reread eligible originals plus the neutral case plan, recheck row dates, and derive their results with no evaluator-only ancestor. They must not consume audit capture values as parents.

Limits are 4 GiB compressed input, 256 files, 2 GiB SQLite registry, 3 GiB total output, 64 MiB per case product and 1,200 seconds. SQLite uses a page cap. Deadline and total-output checks are cooperative, including Arrow batch boundaries; there is no hard OS watchdog or hard process-memory cap. The existing public `asof.ingest.peak_memory_bytes()` reports Win32 PeakWorkingSetSize for the overall Python process lifetime, with null plus a reason if the OS query is unavailable or fails. This counter is separate from optional psutil sampled RSS. No dependency is installed. Arrow bytes are measured, and physical I/O bytes are null/not measured.

Source/guard lock exits, SQLite/product handles and journal close must succeed before publishing a success seal. Success requires a matching terminal `build_completed`, `seal.json`, and absence of `failure-seal.json`. A failure retains a stage/error-class record and explicit partial-artifact manifest; hashes that cannot be measured before deadline are marked unavailable. Partial products are unusable. Journal failure append and failure-seal publication are attempted independently; a journal-close fault can leave an earlier `build_completed` event, but it cannot publish a qualified success seal. Any replacement uses a new directory.

## Validation

Executed with workspace cwd and workspace TEMP/TMP:

```powershell
& 'D:\Projects\drug_target_agents\.venv\Scripts\python.exe' -B planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_set.py -q
```

33 fictional tests passed. The original 31 checks remain, with amended case-count expectations. Coverage includes duplicate/conflicting/missing mappings, exact source values, exposed symbols, date precision/intersection/conflicts, full physical registration, deterministic unique-unit ranking, accepted counts below the cap and retained zero-case failure, projection boundaries, multiple row groups and 8,192-row batches, all-match multi-shard capture, explicitly future duplicates quarantined with per-record/per-artifact roles, neutral lineage without capture parents, missing-case retention, typed invalid numbers, receipts/hash ordering and exact archives, role/availability denial, bounds, READY/code/environment/cutoff gates, transitive dependency changes, positive/unavailable/failed peak-memory plumbing, concurrent output reservation, and injected journal-close/lock-exit/failure-append faults. The fictional end-to-end path uses a trusted Python test seam for small local originals; serialized production inputs cannot choose alternate locking or inventory.

The only executed builder CLI action was `--draft`, which read pinned neutral metadata and reported `source_values_read: 0`. Root's final amendments regenerated that still-unfrozen neutral DRAFT before any READY existed, using the same metadata-only plan function. Actual execution remains for root after final review and READY publication.
