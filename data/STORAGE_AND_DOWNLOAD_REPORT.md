---
title: Storage Capacity and Initial Download Report
date: 2026-10-10
tags:
  - TETHER
  - storage
  - acquisition
status: downloads-started
---

# Storage capacity and initial downloads

**The available drives are enough for the core benchmark and selective genetics/single-cell acquisition. They are not enough to mirror every full source in the inventory.** Bulk originals are being stored in `E:\projects_data\drug_target_agents_data`; D: is reserved mainly for project files, derived data and scratch work.

This report reflects October 10 measurements and the initial acquisition wave. Download status changes while the worker runs; use the live status command below for current completion/failure counts. Source collection does not establish historical eligibility, parsed schemas, causal evidence or benchmark validity.

## Actual capacity

The volumes are separate disks, both NTFS. D: is on NVMe; E: is USB-attached. The E: filesystem supports the queued multi-gigabyte files.

| Drive | Free space at assessment | After reserving 20% of total disk capacity | Planned use |
| --- | ---: | ---: | --- |
| D: | Approximately 1,664 GiB / 1.63 TiB | Approximately 1,292 GiB / 1.26 TiB | Derived/restored tables, indices and scratch |
| E: | Approximately 1,760 GiB / 1.72 TiB | Approximately 1,387 GiB / 1.35 TiB | Original data and transfer/cache work |
| Combined | Approximately 3.34 TiB free | Approximately **2.62 TiB usable** | Selective research collection with working-space reserve |

These figures distinguish binary GiB/TiB from decimal GB/TB. Free space changes as files arrive. The reserve is based on total disk capacity, not simply 20% of current free space. Machine-readable measurements are in [[data/manifests/public/2026-10-10-storage-assessment.json|the storage assessment]].

## What was measured remotely

I recursively inventoried native public Open Targets output directories. Apache listing sizes are rounded, so the totals below are **estimates**, with a conservative bound derived from displayed precision. Deployment/search/error derivatives were excluded to avoid counting redundant representations. All inspected payload sizes were present and no directory request failed.

| Open Targets release | Payload files | Estimated compressed/native bytes | Conservative planning bound |
| --- | ---: | ---: | ---: |
| 19.11 | 6 | 4.45 GiB | 4.55 GiB |
| 21.11 | 8,155 | 3.89 GiB | 4.13 GiB |
| 23.12 | 11,492 | 158.59 GiB | 160.39 GiB |
| 25.09 | 3,508 | 28.99 GiB | 29.39 GiB |
| Combined | 23,161 | **195.92 GiB** | **198.47 GiB** |

The 23.12 `literature` component accounts for about 147.36 GiB of that release. Its schema, licensing scope, encoder/text versions and temporal suitability remain to be inspected before analysis; its size should not be treated as independent evidence volume. The 21.11/23.12 layouts differ from 25.09 and still require explicit compatibility work.

ChEMBL 35 SQLite is **4,986,486,022 bytes**, about **4.64 GiB compressed**, verified by HTTP Content-Length. Its archive SHA-256 is published in the release checksums. Expanded database, indices and restore space are not yet measured. One SQLite archive is selected rather than downloading duplicate SQLite/PostgreSQL/MySQL representations. [Publisher release and checksums](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_35/).

Detailed file metadata is in [[data/manifests/public/2026-10-10-download-size-inventory.json|the archive-size inventory]]. A source directory listing is not a completed download.

## What fits and what needs selection

The four measured Open Targets releases plus one ChEMBL 35 archive are approximately **201 GiB** compressed/native payloads, with a planning bound near **203 GiB**. This leaves substantial room within the approximately 2,680 GiB usable budget for mappings, selected trial snapshots, derived data and targeted genetics.

The following larger sources prevent a promise that the *entire* inventory fits:

- The cited UKB-PPP downloader estimates a whole regional collection around **9 TB**. That alone exceeds these drives. Use complete cis regions/per-protein subsets under verified access, not a whole collection or significant-hits-only substitute. [Downloader estimate](https://github.com/nglm/ukbppp_dl).
- GTEx lists complete v8 cis-eQTL associations around **462 GB** and cis-sQTL around **939 GB**, in requester-pays storage. These are provider-reported directory estimates; selected tissue/region footprints and expanded/working costs are unknown. [GTEx downloads](https://www.gtexportal.org/home/downloads/adult-gtex/overview).
- Whole Census, spatial imaging, raw proteomics, genome references and all GWAS releases are not globally sized. Collect specific studies/regions and processed slices first.
- AACT restore/index size, the number of historical trial snapshots and independent backup needs remain unmeasured. Two working drives do not automatically supply an independent backup.

A practical planning allocation is E: 800 GiB for originals plus 250 GiB transfer/cache work, and D: 500 GiB derived/restored data plus 500 GiB scratch/indices. This totals 2,050 GiB and leaves roughly 630 GiB additional usable margin *after* the disk reserves. These are allowances, not measured data footprints or a commitment to download all sources.

## Downloads actually started

The starter batch completed all three files, **33,422,927 bytes / 33.4 MB**:

| Product | Stored location relative to E data root | Checks completed |
| --- | --- | --- |
| Virtual Biotech trial-label CSV | `benchmark/labels/vbt_labels/71f9da6/clinical_trial_labels_reconciled.csv` | Exact known size, expected header, prior-audit SHA-256 match |
| Virtual Biotech trial linkage | `reference/vbt_linkage/71f9da6/chembl_clinical_nct_data.parquet` | Exact size, Parquet header/footer, captured SHA-256 |
| HGNC current snapshot | `reference/hgnc_symbols/snapshot_2026-10-10/hgnc_complete_set.txt` | HTTP byte count, TSV header, captured SHA-256 |

The HGNC file is a contemporary checksum-backed retrieval snapshot, not an earlier-origin annotation release. The Virtual Biotech labels/linkage are curation inputs, not validated dated outcomes.

The core batch contains **3,513 files**: all **3,508 Open Targets 25.09 Parquet payloads**, the ChEMBL 35 SQLite archive, and four ChEMBL documentation/attribution/checksum files. Its conservative bound is **34.04 GiB**. Queue ordering prioritizes useful reference tables and attribution metadata. ChEMBL payload completion is not claimed merely because its metadata has arrived.

An initial connection reset interrupted the core attempt after 121 files completed. Completed files and partials were preserved. The worker was fixed to isolate native transfer errors, retry connection failures and resume without overwriting verified originals, then the same batch was restarted. The initial 121 completed receipts remain valid; the current-attempt counter may temporarily differ while cached files are rechecked.

The official GCS mirror returned `UserProjectMissing`, identifying requester-pays access. No billing project or paid transfer was attempted. The free EBI HTTPS source remains in use; throughput may limit completion time even though storage fits.

## Monitoring, resume and status refresh

The worker runs in a tool-managed shell session. Keep the E: disk connected. The status file and per-file receipts live under the E data root's `manifests/`. The catalog/public acquisition summary are point-in-time snapshots; the live state is authoritative for the current run.

```powershell
# Read compact live progress and errors.
& 'D:\Projects\drug_target_agents\tools\data\Get-DownloadStatus.ps1'

# Refresh the catalog/public metadata snapshot from receipts.
& 'D:\Projects\drug_target_agents\tools\data\Sync-DownloadCatalog.ps1'

# Resume only after the prior worker is no longer running.
& 'D:\Projects\drug_target_agents\tools\data\Start-DownloadBatch.ps1' `
  -QueuePath 'D:\Projects\drug_target_agents\data\manifests\private\core-2026-10-10-queue.json' `
  -DataRoot 'E:\projects_data\drug_target_agents_data' `
  -Concurrency 4 -MinimumFreeGiB 373 -MaximumBatchGiB 300
```

The worker rejects a second live copy of the same batch, duplicate/out-of-root paths, unsupported source hosts and oversized declared batches. It reserves at least 373 GiB on E:, limits transfers, preserves partial files, checks signatures/size and captures hashes. Existing files require a source receipt or expected hash. A captured local hash, a match against a prior audit, and a publisher checksum are separately identified.

Parquet header/footer or gzip magic checks are transport checks; they do not validate all rows, schemas or scientific assumptions. No ingestion, MR or model execution has occurred. Offline checks confirmed rejection of corrupt Parquet signatures and a checksum mismatch; starter reruns revalidated cached files. An isolated missing-URL test also confirmed that a failed transfer is recorded while its successful peer completes, instead of interrupting the whole batch.

## Access and deferred collections

AACT historical archive access/restoration, FinnGen form-mediated access and UKB-PPP object permissions still need resolution. No credentials are requested or recorded in public metadata. PROTAC/MedDRA and other restricted products remain outside the default public route. Full GTEx/requester-pays transfers and large raw biological collections are deferred until their selections and budgets are established.

The initial download scope is a valid start to the user-authorized acquisition phase. It does not mean all 177 inventory products have been acquired. Exact origin/model/horizon and target/indication selections still govern later historical feature construction.
