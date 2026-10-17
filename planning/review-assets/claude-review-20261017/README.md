# Claude review, October 17, 2026 — verification scripts and results

Evidence for [[Claude Review and Plan_claude10172026]]. Every script is read-only with respect to the project (nothing
under `data/`, `runs/`, `src/` or `E:\` is modified); each prints JSON (or text) to stdout and the saved output is in
`results/`. Scripts use absolute paths for this machine, like the other review assets. Run them with the project
interpreter and isolated mode unless noted: `.venv\Scripts\python.exe -I scripts\<name>.py`.

| Script | What it checks | Output in `results/` | Time |
| --- | --- | --- | --- |
| `verify_seals.py` | Re-hashes every file listed in the seven cohort evidence manifests; size, unsealed files, parent chain | `seals.json` | <1 s |
| `verify_public_anchors.py` | Re-hashes every `path` + `sha256` pair in `data/manifests/public/*.json` | `public-anchors.json` | <1 s |
| `verify_registry_runs.py` | `asof verify --receipt-sha256` for the ten canonical dossiers; report hashes of all registry entries | `registry-verify.json` | about 5 min |
| `rehash_inputs.py` | SHA-256 and size of all 2,206 frozen raw inputs | `rehash-inputs.json` | about 25 s |
| `verify_aact_archives.py` | SHA-256 and size of the six AACT archives | `aact-archives.json` | about 5 min |
| `verify_publisher_sha1.py` | Downloads Open Targets' `release_data_integrity` (checks it against its `.sha1`) and compares the 2,205 selected files | `publisher-sha1.json` | seconds |
| `check_publisher_coverage.py` | Compares the 2,206-file manifest with the publisher's file list (evidence, target, disease parts; ChEMBL excluded by design) | `publisher-coverage.json` | seconds |
| `check_publisher_timestamps.py` | Publisher `Last-Modified` header for the selected files (HEAD requests only) | `publisher-timestamps-all.json`, `-sample200.json` | about 2 min |
| `independent_source_audit.py` | Scans all 2,194 evidence files for the eight (target, disease) pairs; traces 213 random observations to raw rows | `source-audit.json` | about 1 min |
| `verify_vb_counts.py` | Virtual Biotech label and linkage counts | `vb-counts.json` | seconds |
| `verify_ld_matrix.py` | Recomputes the full-cis LD matrix from stored dosages (needs NumPy, see the script header) | `ld-matrix.json` | seconds |
| `check_bounded_packets.py` | Property test of `asof.ingest._packet_groups` with a small artificial limit | `bounded-packets-property.txt` | seconds |
| `crude_pair_sizing.py` | Order-of-magnitude pair-level transition counts from the Virtual Biotech linkage (planning aid, not labels) | `crude-pair-sizing.json` | seconds |
| `selfcheck_review_numbers.py` | Recomputes the numbers quoted in the review from the repository and the saved results | (stdout) | seconds |

Also saved: `validate-full-powershell-7.6.7.json` (full-mode `tools/validate.py` report with a portable PowerShell 7.6.7,
SHA-256 `d2f952ebdbf24386cb8923553aa58e41a846db35a6155ea04c58142a4b16dbb7`, not installed system-wide),
`validate-core-no-powershell7.json` (core mode on this machine) and `unittest-verbose.txt` (173 tests).

Notes on the saved outputs:

- `publisher-timestamps-all.json` reports one transient failure (`sourceId=gene2phenotype/part-00132-…`); a manual HEAD
  retry returned `Last-Modified: Tue, 19 Aug 2025 21:02:07 GMT`, the same day as the other 2,204 files.
- `public-anchors.json` contains one expected mismatch: the registry hash in `2026-10-16-context-revision.json` equals
  the registry as committed at 670778d, baf0ed1 and 0ca0b19; the living registry changed afterwards.
- `crude-pair-sizing.json` inherits the linkage's known limits: contemporary ChEMBL-curated mapping that lags
  registration, comparator arms linked as program drugs, start dates without date type.
- `*.err` files carry progress messages only.
