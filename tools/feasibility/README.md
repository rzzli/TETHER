# Bounded feasibility utilities

These scripts produce evaluator-only development artifacts, not AsOf agent inputs or scientific gold. Use fresh output locations. Clinical extraction requires the existing isolated AACT restore and reads its locally protected credential internally; never pass or print a password. The database must already be running and should be stopped after use.

- `audit_clinical_origin.py`: read-only origin extraction and deterministic selection from a prewritten `protocol.json`.
- `render_clinical_audit.py`: render retained origin records, explicitly authored review annotations and separate current-record receipts. Does not derive outcome labels.
- `fetch_genetics_region.py`: retrieve all indexed records in a frozen interval using isolated pysam. Retains partial failures, headers, hashes and counters; refuses an existing regional output directory.
- `qc_genetics_region.py`: gene-specific deduplication, allele alignment, explicit QC exclusions and ALT-dosage external-reference LD. Requires isolated NumPy; no MR or colocalization.
- `verify_pilots.py`: read-only checks for this fixed 24-case / IL6R pilot, including independent correlation recomputation. The two provider exceptions are recorded; this is not a generic validated ingestion pipeline.

From the repository root, repeat retained-artifact verification with a **new** output file:

```powershell
.venv/Scripts/python.exe -m tools.feasibility.verify_pilots --clinical data/benchmark/cohorts/aact-origin-audit-20261017T021043Z --genetics E:/projects_data/drug_target_agents_data/derived/regional_genetics/il6r-ra-20261017T021530Z --numpy-path E:/projects_data/drug_target_agents_data/cache/numpy-2.3.4-win-cp311 --output data/derived/feasibility-recheck.json
.venv/Scripts/python.exe -m unittest tests.test_feasibility
```

Frozen protocols, raw regional subsets, source receipts and exact executed extraction code are retained in their respective artifact directories. Do not rerun acquisition or rendering into those directories. Local content hashes do not attest a publisher's historical availability. See `planning/Clinical and Genetics Feasibility Pilot.md` for limitations and the unresolved provider metadata checksum.
