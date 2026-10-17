---
title: One historical AACT restoration
date: 2026-10-16
status: awaiting-authorized-archive-access
tags: [asof, aact, historical-data, feasibility]
---

# One historical AACT restoration

The current authorized task is to restore **one historical AACT snapshot** and retain technical evidence of its contents. The user explicitly deferred the 20–30-program clinical audit and regional QTL/GWAS/LD example. No archive has been downloaded or database restored yet.

## Verified access and local environment

The live [AACT snapshot page](https://aact.ctti-clinicaltrials.org/snapshots) returns HTTP 302 to `/session/new`. The [official landing page](https://aact.ctti-clinicaltrials.org/landing) describes account access for snapshots. The legacy `downloads/snapshots?type=pgdump&year=2022` and `downloads/postgres_instructions` routes returned 404. Search-indexed archive listings are not working-download evidence.

The Docker client is installed, but its engine was not reachable through the Docker Desktop Linux named pipe. `psql`, `pg_restore` and `postgres` were not found on PATH. This is not proof that no PostgreSQL installation exists elsewhere. No Docker service was started and no software or dataset was installed. The [official AACT container instructions](https://github.com/ctti-clinicaltrials/aact-docker-db) describe PostgreSQL restoration; their sample current/default download must not replace the selected historical artifact.

Fresh disk observations are recorded in [[data/manifests/public/2026-10-16-aact-restoration-access.json|the access report]]. Both authorized drives have over 1.6 TiB free. Actual archive size, expanded size, index/WAL requirements and temporary footprint remain unmeasured until an archive is selected.

Required external input: an authorized snapshot download link or the local path to an archive downloaded after signing in. No password or token is needed in chat. Browser automation is not available in this session, so an existing signed-in browser session could not be checked.

## Selection fixed before inspecting outcomes

Use the existing plan's **January 1, 2023 candidate origin** only as the restoration-selection bound; it is not a locked benchmark protocol. Prefer a snapshot dated exactly at that origin if available, otherwise verify an earlier official snapshot and explicitly record its gap to the candidate origin. The selected date is currently null. Do not silently substitute a January 2 or current snapshot for January 1 eligibility. Do not assume a filename proves release date or first-public availability.

A single snapshot establishes restoration feasibility only. It cannot establish phase-transition events, first-public outcome dates, longitudinal mapping quality or censoring; those remain subsequent work.

## Restore and acceptance procedure once access is available

1. Record the official listing entry, snapshot date, format, original filename, download time and source. Confirm the selected artifact is within the date bound. Preserve access restrictions and avoid recording credentials or signed-query secrets in public manifests.
2. Download into a fresh versioned directory under `E:/projects_data/drug_target_agents_data/raw/aact_snapshots/`. Retain original bytes, byte count, SHA-256 and available provider checksum. Validate archive integrity and members before extraction. A local hash identifies the acquired bytes; without a publisher checksum it is not independent publisher attestation.
3. Inspect the dump table of contents and producer PostgreSQL version before restoration. Use a compatible isolated local PostgreSQL instance and a new database/data directory under `E:/projects_data/drug_target_agents_data/derived/aact_restore/`. Bind locally, disable unsolicited startup/network exposure, retain errors and logs, and leave existing services/databases unchanged. If only flat files are supplied, report that format explicitly and validate its complete import rather than claiming a native dump restore.
4. Retain schema, table and column inventories, table row counts, constraint/index status, and technical NCT-ID uniqueness/join checks. Inspect the availability and types of registration/update/result-posting dates, phase/status, interventions, conditions and sponsor fields. Record actual date ranges and violations without treating planned trial dates as publication dates.
5. Confirm zero unreviewed restore errors, record database/storage footprint and tool versions, and retain reproducible commands and SQL. Record snapshot/publication/annotation/retrieval dates separately. Keep null or unverified historical provenance explicit.
6. Publish a technical restore report. Raw AACT contains clinical outcomes; it remains quarantined from agent-visible manifests until a separate field/time/role projection is reviewed. Do not alter T6 inputs, start a clinical-program audit, infer predictive power or launch genetics work.

## Next-to-do list

| Order | Work | Status |
| --- | --- | --- |
| 1 | Restore one historical AACT snapshot and verify its schema/content | Active; awaiting authorized archive access |
| 2 | Audit 20–30 clinical programs, target/drug/indication mappings, event dates and censoring | Deferred by user; not started |
| 3 | Assemble and QC one complete regional QTL/GWAS/LD example | Deferred by user; not started |

The existing download worker and stopped periodic monitor remain untouched. No data collection, parsing, historical eligibility or scientific validation status is promoted by this access check. See [[Feasibility Gate Decision]] and [[project-goals]].
