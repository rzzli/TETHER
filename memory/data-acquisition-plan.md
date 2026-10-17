---
name: data-acquisition-plan
description: Implemented AsOf data inventory, historical compatibility and staged acquisition requirements
metadata:
  type: project
updated: 2026-10-17
---

# AsOf data acquisition plan

## October 17 completed continuation

[[Clinical Long Session Progress]] supersedes the older collection counts below: five
selected AACT archives restored; all 24 frozen trials extracted at five dates; a complete
2,206-file Open Targets 25.09/HGNC selection with zero missing inputs; ten new verified
dossiers and a fresh 20-row audit. The selected evidence acquisition unit is 2,194 files.
The source-defined full-cis IL6R revision retains 2,979 QC variants. Historical archive
checks remain scoped and evaluator-only. No independent clinical labels, historical
agent admission, MR or scientific validation were established. The optional January
2026 ZIP passed archive checks only and remains outside the endpoint. Source failures,
the retained packet-size failure and its explicit bounded-packet recovery are documented.

## January 2025 follow-up restored and compared

The supplied January 1, 2025 AACT archive is restored separately with PostgreSQL 17.11: 50 tables, 48,706,419 rows and 520,688 unique studies; 114 validated constraints and 267 valid indexes including TOAST. Checked identifier relationships have no exceptions. All 24 frozen trial IDs were found and replay-verified; the original 2023 evidence is unchanged. Both servers are stopped. See [[AACT January 2025 Follow-up]] and `data/manifests/public/2026-10-16-aact-followup.json`.

The file-access blocker is resolved. The 24 records show four completed, one terminated, ten active-not-recruiting, six recruiting and three unknown states at follow-up. The sole newly posted registry result belongs to the already-separated CFTR safety extension; none of the twelve provisional candidates has registry results posted by endpoint. External publications may still exist. Clinical outcome/event/censoring labels remain null pending program/arm rules and dated evidence adjudication; this is not absence of therapeutic evidence or a power estimate. Later 2026 statuses remain separate. All 130 tests and required probes passed; four targeted tests were rerun after phase-format correction. No live models, probabilities, MR or monitoring/downloader changes; $0 provider spending. Earlier dated entries below preserve prior missing-input states.

## Current addition — October 16

One user-downloaded January 1, 2023 AACT snapshot is collected and technically restored on E:. See [[AACT Historical Restoration]] for 55-table/437,548-study validation, nine unmatched stored-record rows, hashes and resource evidence. The catalog acquisition scope is one archive, not the historical series. This is a direct PostgreSQL restore, not an AsOf parser/agent packet; scientific validation and strict first-public availability remain unverified. No new clinical audit or genetics work; downloader and monitor untouched.

## Archived state — October 11

The catalog contains **83 providers / 178 products**. The v0.2 adapter reads a frozen selected manifest of **2,141 files / 3,752,440,123 bytes**, using Open Targets 25.09 and HGNC `snapshot_2026-10-10`. Its 65 missing inputs remain explicit. Generated normalized packets carry parent hashes, exact archived receipt bytes, original row locators, unresolved scientific context and selected-subset coverage. Parsing status changes only for retained scoped products; independent scientific validation remains `not_run`.

See [[Project Audit and v0.2 Completion]] and [[research-log-2026-10-11]] for fresh-build evidence, ten dossier status, source audit and resources. E: holds originals and receipt archives; D: holds ignored derived packets and run artifacts. The user requested stopped periodic monitoring; this milestone leaves the downloader and monitor untouched. No new downloads, paid requests, registrations or historical backfill are included.

## Earlier scaffold and acquisition history

The following paragraphs describe the original 177-product scaffold and October 10 acquisition authorization; they are not a claim that the current implementation remains documentation-only.

The user explicitly authorized the revalidated documentation-only scaffold. It is implemented in [[data/README|the data entry point]], [[data/DATA_PLAN|the detailed requirements/roadmap]] and [[data/catalog/sources.json|the provider/product catalog]]. Related context: [[project-goals]], [[asof-feasibility-findings]], [[research-log-2026-10-09]].

The inventory contains 83 providers and 177 dataset/product records, including 38 pinned Open Targets components. All products are planned, with parsing and scientific validation not run. Metadata/directory checks and prior sample inspection are recorded independently from collection status. No biomedical datasets were acquired into this scaffold and no downloader, ingestion service or runtime adapter was added.

Four stages: Foundation identifiers/history/program labels; primary causal genetics/literature/direction/perturbation; broader expression/proteomics/structure/modality/component evaluation; later spatial/signature/safety/patent/prospective/H6 extensions.

Key implementation facts:

- Historical Open Targets names/layouts differ. Actual directory metadata was inspected for 19.11, 21.11, 23.12 and 25.09; candidate aliases do not prove schema equivalence. Legacy Genetics has a separate archive.
- The catalogue records eQTL Catalogue's post-2019 launch and release/hash needs, including persistent IDs with changed sample content. Original GTEx and catalogue-reprocessed GTEx are distinct products.
- GTEx requester-pays bulk size, UKB-PPP access, PROTAC/MedDRA restrictions, SIDER denial and unresolved benchmark terms remain explicit.
- Conditional genetics inputs are alternatives, not a requirement to acquire every exposure/outcome provider. Evaluator labels/gold and restricted assets are excluded from default agent profiles.
- A public metadata manifest records sanitized source observations; heavy datasets/generated outputs and benchmark payloads are ignored. Future isolation must use approved mounts/egress, not gitignore alone.

Open research/acquisition gates: model/origin/horizon and cohort definition; AACT restoration; old schemas and availability; exact QTL/LD files and terms; assay/protein/build compatibility; mature independent labels and empirical power; storage/transfer budgets; original H6 inputs.

## Public acquisition subsequently authorized

On October 10 the user explicitly requested downloads and capacity checks using the external E: storage root. Initial public transport is implemented, with source-size inventories, bounded queues, resumable partials, format signatures and hash receipts. The catalog's raw collection status can now change; scientific parsing/validation remains not run.

Starter files total 33,422,927 bytes. The core queue is 3,513 files, bounded at 34.04 GiB, covering all 3,508 Open Targets 25.09 Parquet files and ChEMBL 35 SQLite plus metadata. The first connection-reset interruption preserved 121 completed files; worker error isolation was corrected and the same batch resumed. Use live status rather than assuming completion.

Both drives are NTFS; after reserving 20% of capacity they offer approximately 2.62 TiB usable. The measured core/historical Open Targets payloads fit; unrestricted multi-TB pQTL/GWAS/raw imaging mirrors do not. The GCS Open Targets mirror requires a billing project; no paid transfer was attempted. Details and commands: [[data/STORAGE_AND_DOWNLOAD_REPORT]].

October 10 completion: attached primary documentation evidence for 15 previously checked-but-unreferenced records. Thirteen contracts now distinguish molecular QTLs, phenotype-specific outcome GWAS, API responses, raw phased genotype panels and derived LD provenance. Conditional counts/variance fields preserve explicit unknowns. Provider/product counts and collection status are unchanged; see [[data/manifests/public/2026-10-10-completion-audit.json|the public metadata audit]] and [[research-log-2026-10-10]].

## October 16 feasibility continuation

See [[Clinical and Genetics Feasibility Pilot]]: 24 origin trial representatives screened; all event/censoring labels remain null pending January 2025 follow-up. Indexed BLUEPRINT QTD000021, GCST90132223 and IGSR regional slices are collected/QC-processed only for the specified IL6R interval. Source metadata checksum/count exceptions remain explicit. Whole-provider catalog statuses are unchanged; the scoped public manifest is authoritative for this pilot.
