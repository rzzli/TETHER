---
name: research-log-2026-10-16
description: Versioned context corrections, ten rebuilt dossiers and original-row comparison
metadata:
  type: project
date: 2026-10-16
timezone: America/Los_Angeles
---

# Context revision completion

## Historical AACT restoration completed

The user supplied a 3,194,237,475-byte ZIP and confirmed the January 1, 2023 versioned download. The dump creation timestamp matches. CRC/SHA-256 checks, isolated portable PostgreSQL 15.19 restoration and all technical queries completed. Retained results: 55 tables, 437,548 unique studies, 40,240,578 total rows, 72 validated constraints and 227 valid application indexes (322 including TOAST). Nine `study_records` rows for four missing study IDs are a documented unresolved source-relationship exception. Missing phase/study-type/download-date fields and planned date extremes remain explicit. No records were repaired or removed.

Database logical size is 17.85 GB; archive plus restore directory/software cache about 25.84 GB. Import took 1,978.25 seconds; technical audit 117.47 seconds. Peak memory was not measured. Server was shut down cleanly. The existing catalog writer records acquisition of one archive; no framework adapter or agent admission. See [[AACT Historical Restoration]] and `data/manifests/public/2026-10-16-aact-restoration.json` for the sealed evidence anchor. Public availability time and strict historical eligibility remain unverified. Clinical-program and genetics tasks remain deferred; download worker/monitor untouched.

## Archived pre-download access work

Follow-up: the user has no archive/link. Public Zenodo records 10058991 (four tables, original date unspecified) and 13984069 (partial September 2024 export) do not establish an eligible full snapshot. HEAD on the 2020 ZIP explicitly documented by the official AACT Docker repository returned 404. Registration is available; no account was created or bulk files downloaded. Retained findings and account-access instructions are in [[AACT Historical Restoration]]; steps 2 and 3 remain deferred.

The user selected restoration of one historical AACT snapshot first, explicitly keeping the 20–30-program audit and regional genetics pilot deferred. Live HTTP probes show `/snapshots` redirects to sign-in; old archive/instruction paths return 404. Docker CLI is present but its engine is stopped/unreachable; PostgreSQL tools are not on PATH. No dataset or software was downloaded and no restore was attempted without an archive. The pending external input is an authorized historical archive link or local file path, not credentials. [[AACT Historical Restoration]] records the selection bound, restoration acceptance checks and next-to-do list; sanitized access evidence is retained in `data/manifests/public/2026-10-16-aact-restoration-access.json`.

The user authorized implementation of the next step after [[AI Assisted Review Completion]]. Recipe 2.2 preserves source passages, sections/offsets, PMC IDs, study overviews and clinical significance. Four initial regressions reproduced the omissions and presentation/duplicate issue before correction; two further tests cover comparison tampering and oversized packets. Full validation passed 120 tests, required probes and installed-wheel execution. The final comparator checks also passed six targeted tests.

All ten contemporary dossiers were rebuilt offline, verified against sources and compared with the preserved baseline. The fresh source audit checks 20 distinct rows; the comparison separately rechecks the original 20 review rows, with overlap allowed. All original statements, scientific fields, records, hypothesis keys and physical source locators are unchanged. Exact additional-context counts and resource measurements are retained in [[Context Revision Completion]]. The 65 missing inputs remain missing. No independent scientific validation, probability or support-weight claim is made.

The first enriched build was technically valid but failed strict comparison because the prepared manifest normalized path separators used by the existing source-ID recipe. The manifest was corrected to retain original spellings and a fresh build/run completed. Both attempts remain retained; the registry explicitly selects the corrected one. This is an identity-portability limitation, not raw-data corruption. Original proposals, baseline artifacts and AI reviews remain intact.

Catalog publication used the existing validated maintenance entry point and changed only the generated normalized product. Detailed comparison content remains evaluator-only. No downloads, live provider calls, paid queries, historical backfill or monitor restart occurred. Next gates remain versioned qualified hypotheses if narrowed cases are desired, historical AACT restoration, a complete regional genetics pilot and empirical power/independent evaluation.
