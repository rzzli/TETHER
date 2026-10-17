---
title: One historical AACT restoration
date: 2026-10-16
status: restored-with-documented-data-exceptions
tags: [asof, aact, historical-data, feasibility]
---

# One historical AACT restoration

**One January 1, 2023 AACT snapshot has been restored and technically checked.** The user confirmed the versioned download date, matching the dump's internal creation timestamp. The 20–30-program clinical audit and regional QTL/GWAS/LD example remain deferred. Restoration is complete with documented data exceptions; scientific validation and strict historical benchmark admission remain open.

## Completed restoration — October 16, 2026 local date

| Check | Retained result |
| --- | --- |
| Original archive | `E:/projects_data/drug_target_agents_data/raw/aact_snapshots/t28miw7docut6vcrht1ff6ci630i.zip`; 3,194,237,475 bytes; original unchanged |
| SHA-256 | `0e7c54e6e7214ac7bd31da20960e1a9ce8590b18b87a9661b414f5b1c76cf1d1` |
| Archive integrity | All three ZIP members fully read, CRC checked and separately hashed |
| Dump identity | CUSTOM format 1.14; database 14.3, exporter 15.1; creation `2023-01-01 06:11:12`, timezone unspecified |
| Local restore | Portable PostgreSQL 15.19; new `aact_snapshot` database; exit code 0, no restore warning/error lines |
| Complete table inventory | All 55 table names match dump TOC; 40,240,578 total rows; 20 views and 55 sequences |
| Studies | 437,548 rows and distinct NCT IDs; no null or malformed NCT IDs across 48 tables checked |
| Constraints/indexes | 72 declared constraints validated; 227 application indexes plus 95 TOAST indexes valid and ready |
| Join exception | Nine `study_records` rows refer to four NCT IDs absent from `studies`; other 46 child tables checked have no orphan NCT IDs |
| Runtime state | Cleanly stopped; local-only `127.0.0.1:55432`, SCRAM authentication, no Windows service installed |

The restore root is `E:/projects_data/drug_target_agents_data/derived/aact_restore/restore-20261017T011039Z/`. UTC artifact names use October 17; the work occurred October 16 in America/Los_Angeles. The original dump, schema, TOC, reproducible setup/restore/audit scripts, SQL queries, execution logs and per-table audit are retained there. `sealed-evidence/evidence-manifest.json` binds 419 evidence files by SHA-256; local credentials and database files are excluded from that manifest. Credentials are stored only in a Windows-user-restricted local directory. No passwords, signed download URLs or outcome records enter public metadata.

The sanitized [restoration report](../data/manifests/public/2026-10-16-aact-restoration.json) records hashes, dates, counts, exceptions, resources and the sealed evidence manifest hash. The [acquisition publication](../data/manifests/public/2026-10-16-aact-acquisition.json) updates only `aact_snapshots` through the existing validated catalog writer. Its collection scope is exactly one archive. Catalog parser/scientific-validation flags remain `not_run`: this milestone adds no AsOf AACT adapter or agent-visible packets. Earlier catalog verification text is dated pre-acquisition evidence; the new acquisition snapshot and restoration report describe current local holdings.

## Data exceptions and temporal limits

The nine unmatched stored-record rows comprise protocol, document or derived sections for four study IDs. Their identifiers/types/timestamps are retained in `followup-audit.json`; cause remains unresolved. No record was deleted, repaired from a newer release or assigned an invented match. A clean restore does not make every source relationship valid.

In `studies`, phase is null for 99,586 rows and study type for 829; these are recorded missing values, not automatically corruption. `nlm_download_date_description` is null for all 437,548 rows. Latest first-posted and last-update-posted dates are December 30, 2022; latest results-first-posted date is December 26, 2022. No submission/posting date inspected exceeds January 1, 2023. Start/completion fields include dates through 2100 and old extremes; future planned dates are not evidence that later information leaked into this snapshot. Later cohort rules must handle date types and missingness explicitly.

The version date is supported by the user's download-page confirmation and internal dump/ZIP timestamps. Exact first-public availability, creation timezone and publisher checksum remain unverified. Therefore this completes a technical historical restore, not strict as-of eligibility certification. Raw clinical data remain outside all agent-visible manifests. No new cohort, outcome labels, censoring adjudication or biological conclusions were generated.

## Measured resources and operation

| Resource | Measurement |
| --- | --- |
| Database logical footprint after follow-up | 17,853,472,103 bytes (about 16.63 GiB) |
| PostgreSQL data directory after shutdown | 18,950,483,482 bytes, including 1,073,741,824 bytes of retained WAL |
| Extracted archive members | 3,200,288,842 bytes |
| Restore directory before evidence copy | 22,151,495,733 bytes |
| Portable PostgreSQL archive/tools cache | 492,905,865 bytes |
| Import / import-plus-audit-and-shutdown | 1,978.25 seconds / 2,192.28 seconds |
| Technical audit | 117.47 seconds |
| Free storage after work | D: 1,781,535,436,800 bytes; E: 1,848,187,891,712 bytes |

The original ZIP, restore directory and software cache together use about 25.84 GB before the small sealed evidence copy. There is ample capacity for this single restoration; this does not size the entire project inventory. Peak process memory was not instrumented and remains unknown. No paid access/provider spending occurred. Portable binaries were obtained from the EDB download linked by the [official PostgreSQL Windows page](https://www.postgresql.org/download/windows/); their source URL/hash is retained in the local cache receipt. Original owners/ACLs were intentionally omitted during restoration into the isolated database; source tables and rows were preserved.

To reopen the retained database, use the portable `pg_ctl.exe` under `E:/projects_data/drug_target_agents_data/cache/postgresql-15.19-5-portable/pgsql/bin/` with this restore root's `pgdata` directory and server log. Connect locally with the protected credentials, and stop it after work. Do not rerun `setup.py` or `restore.py` against the completed database; those are the retained creation/import recipes. Any repeat restoration requires a fresh directory/database.

## Archived pre-download access and local environment

The live [AACT snapshot page](https://aact.ctti-clinicaltrials.org/snapshots) returns HTTP 302 to `/session/new`. The [official landing page](https://aact.ctti-clinicaltrials.org/landing) describes account access for snapshots. The legacy `downloads/snapshots?type=pgdump&year=2022` and `downloads/postgres_instructions` routes returned 404. Search-indexed archive listings are not working-download evidence.

The Docker client is installed, but its engine was not reachable through the Docker Desktop Linux named pipe. `psql`, `pg_restore` and `postgres` were not found on PATH. This is not proof that no PostgreSQL installation exists elsewhere. No Docker service was started and no software or dataset was installed. The [official AACT container instructions](https://github.com/ctti-clinicaltrials/aact-docker-db) describe PostgreSQL restoration; their sample current/default download must not replace the selected historical artifact.

Fresh disk observations are recorded in [[data/manifests/public/2026-10-16-aact-restoration-access.json|the access report]]. Both authorized drives have over 1.6 TiB free. Actual archive size, expanded size, index/WAL requirements and temporary footprint remain unmeasured until an archive is selected.

Required external input: an authorized snapshot download link or the local path to an archive downloaded after signing in. No password or token is needed in chat. Browser automation is not available in this session, so an existing signed-in browser session could not be checked.

## Archived follow-up after no archive was available

The user confirmed they have no archive or authorized download link. A targeted public-source check found no suitable replacement among these candidates:

| Candidate | Verified listing/access | Decision |
| --- | --- | --- |
| [Zenodo 10058991](https://zenodo.org/records/10058991) | Deposited October 31, 2023; four text tables (748.9 MB listed); original snapshot date unspecified | Incomplete and historical eligibility unverified; not downloaded |
| [Zenodo 13984069](https://zenodo.org/records/13984069) | September 27, 2024 export; ten listed text files (1.5 GB), without a studies table | Partial and later than the candidate origin; not downloaded |
| January 27, 2020 ZIP linked in the [official Docker README](https://github.com/ctti-clinicaltrials/aact-docker-db) | Public documented URL returned HTTP 404 to HEAD | Unavailable at that URL; not downloaded |

This is a targeted access check, not proof that no eligible public mirror exists. The [official registration page](https://aact.ctti-clinicaltrials.org/sign_up) is available and requests name, email and password. The practical next step is for the user to register/sign in, open the historical snapshot listing and download a PostgreSQL snapshot at or before January 1, 2023, preferably the closest eligible date. Keep the original archive filename and listing date. Save under `E:/projects_data/drug_target_agents_data/raw/aact_snapshots/` and provide only its local path. If no eligible snapshot is listed, report that rather than selecting a newer one. No credentials should be shared in chat.

No account was created, archive acquired or database restored. Follow-up evidence is retained in `data/manifests/public/2026-10-16-aact-public-alternatives.json`.

## Selection fixed before inspecting outcomes

Use the existing plan's **January 1, 2023 candidate origin** only as the restoration-selection bound; it is not a locked benchmark protocol. Prefer a snapshot dated exactly at that origin if available, otherwise verify an earlier official snapshot and explicitly record its gap to the candidate origin. The selected version date is January 1, 2023, supported by user confirmation and internal timestamps; exact first-public availability remains unverified. Do not silently substitute a January 2 or current snapshot for January 1 eligibility. Do not assume a filename proves release date or first-public availability.

A single snapshot establishes restoration feasibility only. It cannot establish phase-transition events, first-public outcome dates, longitudinal mapping quality or censoring; those remain subsequent work.

## Retained restore and acceptance procedure

1. Record the official listing entry, snapshot date, format, original filename, download time and source. Confirm the selected artifact is within the date bound. Preserve access restrictions and avoid recording credentials or signed-query secrets in public manifests.
2. Download into a fresh versioned directory under `E:/projects_data/drug_target_agents_data/raw/aact_snapshots/`. Retain original bytes, byte count, SHA-256 and available provider checksum. Validate archive integrity and members before extraction. A local hash identifies the acquired bytes; without a publisher checksum it is not independent publisher attestation.
3. Inspect the dump table of contents and producer PostgreSQL version before restoration. Use a compatible isolated local PostgreSQL instance and a new database/data directory under `E:/projects_data/drug_target_agents_data/derived/aact_restore/`. Bind locally, disable unsolicited startup/network exposure, retain errors and logs, and leave existing services/databases unchanged. If only flat files are supplied, report that format explicitly and validate its complete import rather than claiming a native dump restore.
4. Retain schema, table and column inventories, table row counts, constraint/index status, and technical NCT-ID uniqueness/join checks. Inspect the availability and types of registration/update/result-posting dates, phase/status, interventions, conditions and sponsor fields. Record actual date ranges and violations without treating planned trial dates as publication dates.
5. Confirm zero unreviewed restore errors, record database/storage footprint and tool versions, and retain reproducible commands and SQL. Record snapshot/publication/annotation/retrieval dates separately. Keep null or unverified historical provenance explicit.
6. Publish a technical restore report. Raw AACT contains clinical outcomes; it remains quarantined from agent-visible manifests until a separate field/time/role projection is reviewed. Do not alter T6 inputs, start a clinical-program audit, infer predictive power or launch genetics work.

## Next-to-do list

| Order | Work | Status |
| --- | --- | --- |
| 1 | Restore one historical AACT snapshot and verify its schema/content | Complete with documented data exceptions; January 1, 2023 snapshot |
| 2 | Audit 20–30 clinical programs, target/drug/indication mappings, event dates and censoring | Deferred by user; not started |
| 3 | Assemble and QC one complete regional QTL/GWAS/LD example | Deferred by user; not started |

The existing download worker and stopped periodic monitor remain untouched. Collection is recorded for this one archive; historical benchmark admission and scientific validation are not promoted by the restoration. See [[Feasibility Gate Decision]] and [[project-goals]].
