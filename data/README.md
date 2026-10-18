---
title: AsOf Data Workspace
date: 2026-10-09
updated: 2026-10-18
tags:
  - asof
  - data
  - provenance
status: acquisition-started
---

# AsOf data workspace

October 18 science-prerequisite work adds a separate ten-case contemporary source
reference pilot: 10,512 observations, fifty original-row audits, two blinded AI
source reviews and third-agent adjudication. Its answers stay evaluator-only under
`data/benchmark/gold_evidence/science-prerequisites-20261018/`; they are not independent
biological truth or agent-visible evidence.

Four historical Open Targets 24.09 mapping products are now collected and parsed:
800 publisher-matched Parquet partitions / 115,821 projected rows, plus five
release/integrity metadata originals (121,968,718 total bytes). These products retain
historical identifiers, names and mechanism annotations with explicit clinical-field
exclusions. They do not supply association/genetics features or the full Virtual
Biotech evidence bundle. See `data/manifests/public/2026-10-18-historical-mappings.json`.
The original downloader and transport receipts remain unchanged.

The January 2025 origin candidate universe is sealed as reconstructed exploratory
information, with historical mapping candidates and all clinical-ready/locked flags
false. January 2026 endpoint restoration is technical-only; April 2026 ascertainment
data are still missing. Current scientific status is in
`planning/Scientific Prerequisites Execution 2026-10-18.md` and TODO.md.

October 17 WP0 correction: the catalog now records the five AACT technical restores
in its verification/blocker fields. ChEMBL and colocalisation are incomplete/idle at
the retained process/filesystem observation. Dated acquisition snapshots remain
unchanged; no partial file is promoted or worker restarted. See
`data/manifests/public/2026-10-17-catalog-status-correction.json` and
`planning/review-assets/wp0-20261017/README.md`. The evaluator-only registry sizing
protocol is frozen at `planning/protocols/registry-sizing-v0.4.json`; counts are pending.

This folder contains the complete data requirements and acquisition inventory for AsOf. The documentation scaffold and authorized public transport are implemented. Originals live under `E:\projects_data\drug_target_agents_data`. [[docs/FRAMEWORK|The v0.2 framework]] now includes a pinned local Open Targets/HGNC adapter, source lineage, bounded offline extraction and semantic verification. MR calculations and a trained/validated clinical scoring pipeline remain later work. See [[Project Audit and v0.2 Completion]] for the current completion evidence and full requirements status.

Read [[data/STORAGE_AND_DOWNLOAD_REPORT|the capacity and download report]] first for the storage verdict, measured source sizes, current scope and monitoring/resume commands. The collection uses E: for originals and D: mainly for derived data and scratch; the placeholder `raw/` folders shown below are not where the active bulk worker writes.

Start with [[data/DATA_PLAN|the detailed data plan]]. The machine-readable inventory is [[data/catalog/sources.json|catalog/sources.json]]: **83 providers and 178 dataset/product records**, including all 38 components required by the pinned Virtual Biotech release and `asof_normalized_packets`. Counts describe acquisition units and generated products, not independent studies or datasets ready to analyze.

Related project notes: [[AsOf Feasibility Analysis and Peer Survey]], [[Beyond the Virtual Biotech Tooling Gaps and Project Plan]], [[Agentic Target-Evaluation Frameworks Critical Review]].

Normalization recipe 2.2 retains four additional source-context fields while preserving
the pinned Open Targets 25.09/HGNC selection. It is a new derived release, not a new
acquisition or a correction to provider originals. The before/after comparison remains
evaluator-only; it must not enter agent-visible manifests. See [[Context Revision Completion]].

October 16 addition: one January 1, 2023 AACT archive is collected and technically restored on E: (55 tables; 437,548 unique studies). Nine stored-record rows have unmatched study IDs and are preserved as exceptions. See [[AACT Historical Restoration]] and `data/manifests/public/2026-10-16-aact-restoration.json`. This does not provide an AsOf AACT adapter, clinical cohort, scientific validation or exact first-public availability; subsequent origin and regional technical pilots are documented below.

## Layout

The completed October 17 continuation is documented in [[Clinical Long Session Progress]].
Five selected AACT archives are restored; all three new servers are stopped. The new
2,206-file contemporary manifest has no missing selected inputs, and ten dossiers passed
source-inclusive verification. CFTR uses two bounded packets without losing records.
Previous missing-input records and failed builds stay frozen. The full-window IL6R
technical revision preserves the original pilot. These products do not establish
independent clinical labels, causal effects or scientific validity.

```text
data/
  README.md
  DATA_PLAN.md
  .gitignore
  catalog/sources.json
  manifests/
    public/                       # reviewed, sanitized metadata only
  raw/{dataset_id}/{release_id}/   # future immutable originals
  reference/                      # future pinned reference/crosswalk products
  derived/{snapshot_id}/{product_id}/
  benchmark/
    cohorts/
    labels/
    splits/
    gold_evidence/
  cache/                          # disposable and never authoritative
```

Use an immutable version or checksum-backed release identifier. A `latest`/`stable` alias, study ID, year or download timestamp is not sufficient to identify an exact dataset. The source catalog records release families and candidates; it does not select final benchmark origins or certify exact files.

## Planned, checked and collected are separate

| State | Meaning here |
| --- | --- |
| `collection_status: planned` | The source/product is needed or is an optional candidate. Nothing in this scaffold constitutes its acquisition. |
| `queued` / `downloading` / `partial` | An authorized transport wave is queued or has begun; complete product acquisition is not claimed. |
| `collected` | All expected files for the selected acquisition unit have receipts. This does not imply historical eligibility, parsed schema or scientific validity. |
| `verification.level: documentation_checked` | Primary documentation was inspected. File access, content and temporal eligibility may still be unknown. |
| `directory_checked` | A listing responded and named entries were observed. No payload schema or completeness is certified. |
| `sample_inspected` | A small response or previously audited file was inspected. Read its evidence/limitations; this does not certify a full collection. |
| `parse_status: parsed` | A retained, explicitly scoped product was parsed; this does not certify whole-provider completeness. |
| `validation_status: not_run` | Independent scientific validation has not occurred, even when technical checks pass. |
| `temporal.classification: unverified` | No selected artifact's historical eligibility has been established. |

Products have a mixture of planned, queued, partial and collected states. Selected-source normalization is recorded separately from full product acquisition, and scientific validation remains `not_run`. The catalog is a point-in-time acquisition record; retained receipts and scoped build reports support any status updates. This milestone does not refresh transport queues or restart monitoring. Successful metadata requests alone never change collection status.

Null values mean **unknown or unselected**, never zero storage, absent biological evidence or permission granted. Required field lists are normalized acquisition/output requirements; they are not claims about a provider's exact raw schema.

## Catalog interface

`sources.json` is the machine-readable requirements interface introduced by the original documentation scaffold. It has `schema_version: 1`, a review date/timezone, profile/status definitions, `providers[]` and `datasets[]`. The later framework implementation adds separate runtime case/snapshot/evidence/scorer contracts; it does not turn this catalog into a raw-data adapter or download queue.

- Providers have stable IDs, official documentation/access/terms pointers and caveats.
- Dataset IDs are unique and reference a provider. They describe purpose, priority/stage, tasks/hypotheses/ablations, role, minimum fields, scope, formats, release policy, temporal status, access/terms, dependency/overlap groups, storage basis, verification and blockers.
- `dependencies` are unconditional inputs. `conditional_input_groups` describe alternatives or optional inputs without requiring every candidate provider. `overlap.dataset_ids` identifies shared evidence or duplicated acquisition.
- Dependencies describe normalization/interpretation/validation inputs; they do not grant access or require restoring every dependency before reading a source's metadata. `conditional_fields` apply only when their scientific condition holds, such as case/control counts for a binary phenotype.
- `bundle_id` groups related products such as Open Targets and ChEMBL releases. Do not sum a quoted bundle size once per component.
- `default_public_route_candidate: true` means a candidate for the research route, not cleared access or redistribution. Restricted/controlled optional products are false and excluded from default profiles.
- `verified_historical`, `reconstructed`, `contemporary_only` and `unverified` classify temporal claims independently from collection and content QC.

The catalog is a requirements inventory, not an executable download configuration. Authorized, resolved files use separate private transport queues. Download-entry pointers for remaining products may be null, point to documentation or designate a candidate family that still needs exact file resolution.

The October 10 completion audit attached missing documentation evidence to 15 records and corrected trait-specific genetics and LD contracts. The catalog preserves its original review date and records `last_updated` separately. See [[data/manifests/public/2026-10-10-completion-audit.json|the completion audit]].

## Tracking and provenance

Catalog mutation now has one validated entry point; preparation and transport
inspection are read-only. See [[docs/MAINTENANCE]] for explicit paths, immutable
reports, locking and prior-hash checks. The normalized ten-case product is collected
and parsed, with scientific validation `not_run`; its evidence is recorded in
[[data/manifests/public/2026-10-12-v02-normalization.json]]. The canonical local
build and dossiers are selected by [[planning/run-registry.json]], including retained
superseded/incomplete attempts. Bulk artifacts remain intentionally absent from Git.

Documentation/catalog files and reviewed metadata under `manifests/public/` are versionable. Raw/reference/derived data, benchmark records and caches are ignored, while placeholders preserve the folder structure.

Only put sanitized metadata in public manifests: source/dataset/release IDs, public unsigned URLs, hashes, sizes, software versions, access observations, limitations and protocol identifiers. Exclude credentials, signed URLs, tokens, private host/cache paths, patient identifiers, benchmark answers, outcome labels and licensed content.

The initial public revalidation manifest contains directory names, access results and factual limitations. It contains no biological payload or benchmark outcome.

## Collection profiles

1. **Historical benchmark:** approved origin-eligible source and annotation versions; field-level dates and coverage; no current-data backfill.
2. **Contemporary assessment:** pinned current sources, labeled as contemporary.
3. **Virtual Biotech reproduction:** commit `71f9da68c95c5ee0ef4c1d9b8f45f10693de022d` with the 25.09 component inventory; separate from proof of historical compatibility.
4. **Evaluation only:** labels, gold answers, split assignments, future outcomes and comparator keys remain outside agent-visible manifests.

Folder separation and `.gitignore` do **not** enforce confidentiality or historical access. Future execution must mount approved slices rather than the whole data root, remove label/credential access and control network egress.

The contemporary pilot uses a frozen explicit manifest with 65 missing inputs; the builder cannot silently use newly downloaded replacements. Exact historical-origin and clinical-protocol decisions, AACT restoration, regional genetics/LD access and independent scientific validation remain outstanding. No accounts or paid transfers were created by this milestone. The user's stopped periodic monitoring remains stopped; inspect transport progress only on request.

October18 qualification update: four OT24.09 mapping products are qualified and an
origin-only reconstructed exploratory universe is sealed; strict historical completeness
and clinical program equivalence remain unqualified. January2026 AACT technical
restoration passed independent terminal checks (52 tables,563,840 studies,
55,380,326 rows), with an empty cohort result and stopped owned server. The scoped
manifest is `data/manifests/public/2026-10-18-aact-endpoint-technical.json`.
April1,2026 ascertainment data remain missing, so Science3 is blocked and Items4–7
have not started. No clinical labels or agent-visible future data were admitted.

## Contemporary normalization and retained provenance

`inspect-source` checks selected originals, transport receipts, schemas, roles and approved paths. `build-snapshot` reserves a new directory, repeats inspection, archives exact receipt bytes at `E:\projects_data\drug_target_agents_data\manifests\receipt-archive\<sha256>.json`, and creates packets with raw-parent references and physical row locators. The copied receipts keep runs stable if a later transport retry rewrites its own receipt. Build journals retain stages, counters and terminal failures; `inspect-run` describes them without restarting work.

The ten development hypotheses use Open Targets 25.09 and HGNC `snapshot_2026-10-10`. Clinical status/outcomes and ChEMBL/known-drug evidence are excluded. Provider metrics and unresolved biological context are descriptive; numerical prediction features remain empty and clinical probabilities null. Source review compares statements and context with distinct original rows. It is technical validation, not independent biological adjudication or expert gold.

Normalized products remain under ignored `data/derived/`; finalized dossiers and their private lineage live under ignored `runs/`. Sanitized completion metadata belongs under `manifests/public/`. The original incomplete build directory is retained for diagnosis, with no invented explanation for its termination.

New bounded feasibility artifacts: [[Clinical and Genetics Feasibility Pilot]] links the 24-trial clinical review and IL6R/RA regional QC. The public scoped manifest is `data/manifests/public/2026-10-16-feasibility-pilots.json`. Regional data are on E:, clinical records remain evaluator-only, and full-provider catalog status is unchanged. Follow-up labels and scientific inference remain unvalidated.

January 2025 continuation: [[AACT January 2025 Follow-up]] records the second restored AACT archive (50 tables; 520,688 studies), all 24 frozen trial IDs matched, and clean shutdown. The scoped catalog acquisition is now two archives, backed by `data/manifests/public/2026-10-16-aact-paired-acquisition.json`. No AsOf parser/agent admission or clinical labels were added; dated program-event/censoring adjudication remains the next gate. This supersedes the missing-follow-up statements in earlier entries.
