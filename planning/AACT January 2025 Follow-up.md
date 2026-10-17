---
title: AACT January 2025 follow-up restoration and comparison
date: 2026-10-16
status: restored-paired-comparison-complete-program-labels-unadjudicated
tags: [asof, aact, clinical, feasibility]
---

# January 2025 follow-up

**The January 2025 snapshot is restored and all 24 frozen trials have been compared.** Technical checks passed; the temporary database server is cleanly stopped. Program-level clinical outcomes and censoring remain unadjudicated.

The user supplied the requested follow-up archive at `E:/projects_data/drug_target_agents_data/raw/aact_snapshots/jan2025zip/d3q4ma1gbexj9z8dnia2w8m7t5a4.zip`. It is retained separately from the January 2023 archive. This continuation preserves the frozen 24-trial selection and earlier mapping exclusions from [[Clinical and Genetics Feasibility Pilot]]. Open the [paired review](../data/benchmark/cohorts/aact-followup-20250101-20261017T051834Z/Review.html) for all 24 dated records and their original qualifications.

## Archive identity and compatibility

The 2,105,000,060-byte ZIP has SHA-256 `53bb8d15d3bc902659f2f64985af4636679d1208eac1f143d96aa42d7f2ef297`. All five members passed complete read/CRC checks. The database dump is 2,109,959,523 bytes, SHA-256 `e14fd827d451ed585036e321c604c4cc7cabb5cb3d6cf1d165c8b8699ad93468`. Its header reports creation on **January 1, 2025 at 05:22:15**, timezone unspecified, from PostgreSQL 14.3 using pg_dump 16.4. Exact public availability and publisher checksum remain unverified.

The bundled `schema.png` is empty. The protocol/results definition HTML files have identical bytes; they are retained but not treated as distinct authoritative definitions. The actual SQL schema is extracted from the dump. PostgreSQL 15 rejected dump format 1.15 before any import. Portable PostgreSQL 17.11 was obtained through the [official PostgreSQL Windows download route](https://www.postgresql.org/download/windows/) and [EDB binary listing](https://www.enterprisedb.com/download-postgresql-binaries); it reads the dump successfully. Tool-source URL, byte count and local SHA-256 are retained. No Windows service or global software installation was added.

The new instance uses `127.0.0.1:55433`, SCRAM authentication and locally protected credentials. The January 2023 restore remains unchanged on its separate port/data directory. Restoration omits source ownership/ACLs while preserving database data; original ZIP and dump bytes are unchanged.

## Schema and comparison scope

The TOC contains 50 tables compared with 55 in 2023. Removed tables are `active_storage_attachments`, `active_storage_blobs`, `file_records`, `study_records` and `verifiers`; no new tables appear. The disappearance of `study_records` does not demonstrate repair of its previously documented orphan rows. In the six tables used by the comparison, no columns were removed; `studies.patient_registry` was added.

The comparison reads the same 24 NCT IDs and preserves the 12 candidate, five exclusion and seven complex-review decisions. It retains source statuses, phases, interventions, arms, planned endpoints, completion date types, stop reasons and first-results/public-update dates. Status/phase formatting differences are normalized for comparison, without inferring development transitions.

Clinical success/failure, program-event dates, publication-event dates and individual censoring dates remain null pending program-level adjudication. The fixed January 1, 2025 administrative observation endpoint is not silently assigned as each program's censoring date. Current October 2026 registry records remain separate and do not enter this dated comparison. Already-posted origin results and prior mapping exclusions remain in force.

## Execution evidence

Restore artifacts: `E:/projects_data/drug_target_agents_data/derived/aact_restore/followup-20250101-20261017T051834Z/`.

Comparison output: `D:/Projects/drug_target_agents/data/benchmark/cohorts/aact-followup-20250101-20261017T051834Z/`.

The retained recipe performs restoration, analysis, table/identifier/constraint/index/date audits, frozen-case comparison, then server shutdown. Every stage retains logs and failure state. This is a one-time foreground task; the download worker and stopped recurring monitor are untouched. Provider spending remains $0.

| Technical check | Result |
| --- | --- |
| Restore | Exit 0; no restore error/warning lines; clean shutdown |
| Tables and rows | All 50 TOC tables present; 48,706,419 total rows |
| Studies | 520,688 unique NCT IDs |
| Identifier relationships | No null/malformed NCT IDs or orphan NCT relationships found in checked tables |
| Constraints | All 114 declared constraints validated |
| Indexes | All 177 application indexes valid/ready; 267 including TOAST |
| Posting dates | Latest first-study, last-update and first-results posting dates each December 27, 2024; none after January 1, 2025 |
| Comparison | All 24 IDs found; deterministic replay identical; original sealed evidence unchanged |
| Tests | 130 tests passed, no skips; ten required probes passed; four targeted tests rerun after phase-format correction |

Public provenance is `data/manifests/public/2026-10-16-aact-followup.json`. It anchors 395 restoration evidence files and 12 comparison files, excluding private credentials and database pages. Archive/dump hashes bind the large originals separately. The paired acquisition publication updates only the scoped `aact_snapshots` acquisition through the existing catalog writer: two archives, 5,299,237,535 bytes. Catalog parsing/scientific-validation flags remain `not_run` because no AsOf adapter or validated clinical labels were added.

## What the paired records show

| January 2025 registry status | All 24 trial representatives | Twelve provisional candidates |
| --- | ---: | ---: |
| Active, not recruiting | 10 | 4 |
| Recruiting | 6 | 2 |
| Completed | 4 | 3 |
| Unknown | 3 | 3 |
| Terminated | 1 | 0 |

These are descriptive counts from a purposive sample, not independent program/event counts or success rates. Fifteen normalized status fields changed; two phase fields and two verbatim condition lists changed. Phase changes are field changes, not established development transitions. Three UNKNOWN states have old last-update dates; the last sponsor update cannot be assumed to be the first public date of every derived registry status.

Only two of the 24 records have a registry first-results posting date. One predates origin (P14, enoblituzumab); the only new posting within follow-up is P06, the CFTR safety extension already marked for separate review. **None of the twelve provisional candidates has registry results posted by this endpoint.** This does not establish absence of published external results; it shows why registry snapshots alone do not supply the intended outcome labels.

Five focused original-row checks are retained in `review-checks.json`:

- **P06 / NCT04043806:** actual completion December 14, 2022; first results posted July 6, 2023. The active origin state therefore needs reporting-lag adjudication.
- **P08 / NCT03729596:** terminated, with the recorded reason “Business decision.” No biological failure is inferred.
- **P19 / NCT05551117:** active, not recruiting and Phase 2 in the 2025 snapshot. Its separate current record reports termination and February 2026 results; those later observations cannot replace the endpoint state.
- **P21 / NCT05144529:** recruiting in the 2025 snapshot. The separate 2026 record retrospectively reports September 2024 completion and a slow-enrollment stop. Occurrence, reporting and observation dates require separate treatment.
- **P23 / NCT05649137:** completed December 13, 2024, with no registry result-posting date at the endpoint. Completion alone does not establish therapeutic success.

The original four anchor exclusions, one already-known-outcome exclusion and seven split/separate-review cases remain unchanged. The checks are AI-assisted source-fidelity review, not independent scientific adjudication.

## Measured resources and next step

Import took 1,661.28 seconds (27.69 minutes); the technical audit took 96.09 seconds. Import through audit, comparison and shutdown took 1,770.53 seconds (29.51 minutes). Database size at audit start was 17,832,359,603 bytes; the stopped data directory occupies 18,931,181,033 bytes including WAL. Extracted files occupy 2,110,154,568 bytes; the new portable-tool cache occupies 522,317,400 bytes. Together with the original ZIP this is approximately 23.67 GB, excluding small reports/evidence copies. Peak memory was not measured. These measurements do not size the full project inventory.

The missing-follow-up-file blocker is resolved. The next gate is a versioned **program/arm-level outcome and censoring protocol**, followed by dated primary-publication/sponsor evidence review for the retained candidates. Two snapshots show states but generally do not identify first-public transition dates. Resolve the seven complex mappings, pre-origin events, stale records and publication lag before counting eligible events or estimating power. Do not add replacement cases based on observed favorable outcomes; any expanded selection needs rules fixed from origin information first. Clinical probabilities, scorer training and live model comparison remain deferred.
