# Bounded feasibility utilities

Registry-scale evaluator sizing is implemented under the frozen v0.4 protocol.
See `planning/Registry-scale Cohort and Label Audit v0.4.md`; these are development
events, with null training labels and no scientific validation claim.

```powershell
.venv/Scripts/python.exe -m tools.feasibility.registry_extract --protocol planning/protocols/registry-sizing-v0.4.json --output data/benchmark/cohorts/NEW-EXTRACTION
.venv/Scripts/python.exe -m tools.feasibility.registry_cohort --protocol planning/protocols/registry-sizing-v0.4.json --frames data/benchmark/cohorts/NEW-EXTRACTION/frames.json --output data/benchmark/cohorts/NEW-COHORT
.venv/Scripts/python.exe -m tools.feasibility.registry_audit --protocol planning/protocols/registry-sizing-v0.4.json --frames data/benchmark/cohorts/NEW-EXTRACTION/frames.json --cohort data/benchmark/cohorts/NEW-COHORT --output data/benchmark/cohorts/NEW-AUDIT
```

Use fresh directories; these commands are examples, not instructions to repeat
completed extraction. `registry_extract` owns and stops only initially stopped
restores, uses read-only transactions and verifies completed frames before explicit
reuse with `--resume-completed-from`. Do not restart on a polling timeout.
`registry_cohort` streams records into a local SQLite index using the optional
ingestion dependency; mapping fields are explicitly projected and evaluator-only.
`registry_audit` verifies original JSONL bytes and source fields, retains qualified
AI-authored review separately, and never infers negative labels or scientific accuracy.
The sealed SQLite index is checkpointed. Inspect it with SQLite URI
`file:PATH?mode=ro&immutable=1`, or make a separate working copy; ordinary WAL readers
can update shared-memory sidecars even in read-only mode. The recovery test verifies
the seal again after its immutable index integrity check.

`advancement_rules.py` implements the evaluator-only v0.3 program relations,
experimental-regimen dosing endpoint and shared-event accounting.
`apply_advancement_policy.py` applies explicit source-bound development judgments
to the frozen set; `verify_advancement_policy.py` checks the policy hash, parent
chains and replay. See `planning/Program Advancement Rules v0.3.md`. Unknowns do
not become negative labels, and synthetic tests do not enter the real cohort.

The linked Phase 3 follow-up is in `planning/Phase 3 Linkage Follow-up.md`.
`extract_phase3_followup.py` briefly starts a stopped existing restore, reads a bounded
explicit NCT list twice under read-only transactions, and stops its own server.
It refuses an already-running server or reused output and never performs an import.
`assess_phase3_link.py` distinguishes enrollment from conditional dosing bounds;
`verify_phase3_linkage.py` replays the sealed assessment without a database.

The current program/outcome review is documented in `planning/Program and Outcome Feasibility.md`.
`program_outcomes.py` contains evaluator-only date, phase and reference checks;
`build_program_feasibility.py` reproduces the explicitly authored 24-case review into a fresh
protocol directory; `verify_program_feasibility.py` checks sealed bytes, parent evidence,
the journal and source-inclusive replay. These utilities do not assign training labels.
Use the public manifest anchor and the current pointer in `data/derived/active-program-feasibility.json`.

These scripts produce evaluator-only development artifacts, not AsOf agent inputs or scientific gold. Use fresh output locations. Clinical extraction requires the existing isolated AACT restore and reads its locally protected credential internally; never pass or print a password. The database must already be running and should be stopped after use.

- `audit_clinical_origin.py`: read-only origin extraction and deterministic selection from a prewritten `protocol.json`.
- `render_clinical_audit.py`: render retained origin records, explicitly authored review annotations and separate current-record receipts. Does not derive outcome labels.
- `fetch_genetics_region.py`: retrieve all indexed records in a frozen interval using isolated pysam. Retains partial failures, headers, hashes and counters; refuses an existing regional output directory.
- `qc_genetics_region.py`: gene-specific deduplication, allele alignment, explicit QC exclusions and ALT-dosage external-reference LD. Requires isolated NumPy; no MR or colocalization.
- `verify_pilots.py`: read-only checks for this fixed 24-case / IL6R pilot, including independent correlation recomputation. The two provider exceptions are recorded; this is not a generic validated ingestion pipeline.
- `compare_clinical_snapshots.py`: query the same frozen NCT IDs from a separate follow-up restore; retain registry changes, arm context and date types without clinical labels. Refuses an existing output directory and retains execution failures.
- `verify_clinical_followup.py`: verify the original sealed selection, restored table/constraint/index/date audits and deterministic comparison. Checks source and code hashes; reports source identifier exceptions separately from scientific validity.
- `restore_intermediate_aact.py`: sequentially restore an explicit plan of user-supplied ZIPs into new, isolated local databases; record full archive CRC/hashes, stage events, technical audits and the frozen cohort. Stops each server after extraction. Never retries an existing output directory.
- `verify_intermediate_aact.py`: verify completed restore journals, sealed artifacts, dump dates, technical summaries and exact cohort membership without restarting a database. `--rehash-originals` also rehashes the ZIPs and extracted members. Local consistency does not attest publisher authenticity.
- `harvest_trial_publications.py`: retain bounded exact-NCT Europe PMC discovery responses; matching an identifier does not establish trial-arm relevance.
- `retain_public_sources.py`: retain explicitly listed public HTTPS sources and failed retrieval receipts. Challenge pages are not usable article content. No account credentials or bulk collection.
- `render_outcome_review.py`: render authored, source-qualified development notes for the frozen cases. No clinical label assignment or independent adjudication claim.
- `build_clinical_timeline.py`: build evaluator-only observed state sequences from a manifest of sealed extracts. Reject later posting dates, changed source proofs and duplicate trials; preserve missing observations and nonmonotone states. No event-date or censoring inference.

From the repository root, repeat retained-artifact verification with a **new** output file:

```powershell
.venv/Scripts/python.exe -m tools.feasibility.verify_pilots --clinical data/benchmark/cohorts/aact-origin-audit-20261017T021043Z --genetics E:/projects_data/drug_target_agents_data/derived/regional_genetics/il6r-ra-20261017T021530Z --numpy-path E:/projects_data/drug_target_agents_data/cache/numpy-2.3.4-win-cp311 --output data/derived/feasibility-recheck.json
.venv/Scripts/python.exe -m unittest tests.test_feasibility
```

Frozen protocols, raw regional subsets, source receipts and exact executed extraction code are retained in their respective artifact directories. Do not rerun acquisition or rendering into those directories. Local content hashes do not attest a publisher's historical availability. See `planning/Clinical and Genetics Feasibility Pilot.md` for limitations and the unresolved provider metadata checksum.

The January 2025 continuation uses portable PostgreSQL 17.11 on local port 55433, separately from the 2023 restore. Its source directory and retained setup/import recipes are in `planning/AACT January 2025 Follow-up.md`. Do not rerun an import against a completed database. Comparison is evaluator-only; registry completion, termination and administrative observation cutoff are not substituted for program success, failure or censoring.

The intermediate batch uses separate ports 55434–55436 and preserves each actual dump date, including July 2 for the supplied July 2023 archive. Read `planning/Clinical Long Session Progress.md` and the batch's `result.json` before resuming. A live import must not be restarted; a failed stage requires inspection and a separately recorded recovery decision. The optional January 2026 archive is outside the frozen endpoint.
