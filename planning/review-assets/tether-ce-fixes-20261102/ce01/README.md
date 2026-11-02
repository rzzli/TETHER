# CE01: preserve transport inputs during report publication

The new regression was run against the original verifier before the correction.
It failed because `OutputPath` equal to the input receipt returned success and a
complete report. `Test-DownloadBatch-before.ps1`, its hash, and the failing test
output retain that baseline. The earlier independent audit also retained the
before/after receipt-byte witness.

The corrected verifier preflights the requested output against queue, original
and receipt paths, including missing originals/receipts. It rejects existing
destinations, alternative data streams, and reparse points in the report path.
Ordinary path normalization and case-insensitive comparisons cover equivalent
Windows paths; rejecting every existing destination also protects hard-link
aliases. It writes the complete JSON to a new sibling file, flushes it, and uses
the non-replacing file-move operation to publish. A concurrent report creator
cannot be overwritten. Temporary files are cleaned up on publication failure.
Results for ordinary source-validation failures still publish with `complete:
false` and process exit 2. Publication failure exits without reporting success.

All **12 tests pass**, zero skips, using tiny fictional inputs. They cover exact,
equivalent/case, queue, raw, missing-input, hard-link and junction aliases;
existing-report retention; valid and invalid input reports; a non-directory
parent; stdout-only use; and two concurrent publishers with exactly one winner.
The PowerShell parser and diff whitespace checks also pass. See
[VALIDATION.json](VALIDATION.json) and [after-tests-02.txt](after-tests-02.txt).

Two environment failures remain in the evidence: default sandbox TEMP access
failed before the first assertion, then workspace-TEMP execution reached the
intended pre-fix assertion. The first full fixed-suite run passed ten tests but
could not create hard-link/junction fixtures in the sandbox. The same suite
passed with reviewed permission for those temporary Windows filesystem fixtures.
No production dataset/receipt, downloader worker, stopped monitor, runtime
package or historical result was changed by this correction.

This qualifies a Windows/PowerShell 7 transport utility. It does not establish
scientific or temporal validity, or protection against a malicious filesystem
owner replacing directories concurrently. The publication operation never
intentionally replaces an existing destination.
