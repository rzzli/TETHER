# P05 source-only builder v3: strict legacy receipt separator compatibility

Status: 40 fictional tests pass. The v3 DRAFT is published; root must separately freeze READY v3 before actual source execution. This agent performed no actual payload/source-value scan, network/model call, or download.

## Exact artifacts

- Builder `tools/science/prepare_source_validation_set.py`: SHA256 `6b698be8da73b3272017e43afe4b7dc373b48e334b38df0ca596e3473783fd75`.
- Tests `planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_set.py`: SHA256 `8afb8a093a09d4b91e75534d280edc773be75c7bf866c258881725194bd60481`.
- New `REGISTRY-PLAN-DRAFT-v3.json`: SHA256 `bf4558d695b1de255575e62a2877aa944f060d51b02e12d4cdbdae10955e483b`.

Frozen files remain byte-identical:

- v1 DRAFT: `d2a16bbfa79794c6c19c4e8bed8ff7ae1a01fb5d04dc675b5685c7cf84da6174`.
- v1 READY: `f9673029667f4c119a3bd958e172239a27ddac884d4833d3db30353a3ba5f15f`.
- v2 DRAFT: `2f68e901ba11b381e19543bc848f06af2944e8936f8293bb654f87082d187f05`.
- v2 READY: `cb7e2d7d60d2b46e305aba849dfce0ba9f5187bfac2b46c2c6d51b460cab336c`.

## Narrow correction

Root reports that the v2 attempt passed the 137-payload hash loop and failed during receipt identity verification before any source values. Its failed directory and failure seal remain preserved. Legacy receipt JSON used Windows backslash separators in `relative_path`; neutral descriptors use canonical forward slashes. Root's metadata-only probe found this as the sole mismatch in 114 older receipts, with 23 newer receipts already using forward slashes.

The public pure helper `check_receipt_identity(document, record, source_id=...)` now compares `document["relative_path"].replace("\\", "/")` exactly with the trusted canonical descriptor path. It performs no filesystem access, path collapse, case folding, alias resolution, traversal acceptance, whitespace trimming or URL normalization. Changed components, dot/dotdot components, repeated separators, absolute/drive/UNC forms and changed case remain mismatches. All other required receipt identities remain exact: completed status, dataset, release, SHA256, byte count and URL; malformed JSON field types are rejected.

The helper is suitable for a metadata-only preflight using normalized records from `inventory_from_metadata(frame, acquisition)`, without opening any payload. Callers remain responsible for verifying receipt bytes/hash before trusting the parsed receipt. Its result names the neutral source ID and reports whether separator normalization was needed. Errors name only the mismatched field names and source ID; observed field values are not printed. The production verifier supplies its existing `original-###` lineage ID.

Verification still hashes and checks the original receipt bytes before parsing and archives those exact bytes afterward. The helper never modifies the document, checksum, receipt path, archive contents or source originals. A legacy receipt archive retains its original backslash spelling and hash.

The implementation now uses only `REGISTRY-PLAN-DRAFT-v3.json` and `REGISTRY-READY-v3.json`. Root READY v3 must bind the exact v3 DRAFT, code pins, environment and explicit UTC cutoff. v1/v2 READY cannot authorize the revised implementation. The v2/v3 neutral plan comparison differs only in `artifact_id` and `code_sha256`; selection, projections, eligibility, frame and budgets are unchanged. All restrictions and path/reservation guards described in `BUILDER-NOTES-v1.md` and `BUILDER-NOTES-v2.md` continue to apply. No src/P04/P04b artifact changed.

## Validation

```powershell
& 'D:\Projects\drug_target_agents\.venv\Scripts\python.exe' -B planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_set.py -q
```

40 fictional tests pass with workspace cwd and TEMP/TMP. The prior 36 checks remain. Four new checks cover POSIX/Windows/mixed separator positives, strict unsafe/changed-path negatives, unchanged exact identities and field-only diagnostics, and integration that verifies and archives a legacy-format receipt as byte-identical original data.

The independent reviewer also reports a metadata-only preflight of all 137 registered receipt JSON files under stable locks with fresh receipt byte/hash checks: 137 pass, including 114 separator-normalized and 23 already POSIX. That reviewer opened zero payloads and inspected zero source values.

Only the metadata-only `--draft` action was executed for v3, reporting 137 files and `source_values_read: 0`. Actual v3 execution remains for root after final consistency review and a fresh READY v3 freeze.
