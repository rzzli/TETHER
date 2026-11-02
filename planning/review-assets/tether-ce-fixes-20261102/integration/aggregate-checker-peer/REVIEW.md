# BG01 aggregate checker peer review

This review found and corrected **two acceptance-checker defects**. The fresh checker-only validation passes **39 component controls**. It does not establish a full-gate pass or BG01 completion. No runtime, test, tool, retained log, original receipt, model or dataset was changed.

## Findings and corrections

1. **P2 — an earlier unittest `OK` could validate an unfinished or skipped later run.** The original parser selected the last `Ran` count but accepted any earlier standalone `OK`. Three fictional logs demonstrated acceptance of an interrupted second summary, a skipped second summary, or newly started execution after a prior complete summary. `RESULTS.json` and `fictional-logs/` retain all three red witnesses. The corrected parser requires exactly one complete `Ran`/`OK` block. Ordinary logs must end at that successful summary. The full driver has a separate, explicit `driver_report` argument: its final JSON must equal the supplied report, and intervening output cannot contain another unittest execution, summary or interruption marker. Actual logs were preserved.

2. **P2 — the preservation checklist had no completeness requirement.** The original predicate accepted both an empty checklist and a single unrelated passing row. `preservation-red.json` retains these extracted-expression controls; they are not aggregate PASS records. The corrected checker pins the original preservation and readback bytes, verified against both commits `5cd633b` and `4aa3328`, and requires the complete 196-check inventory. This includes 110 installed payload checks, 66 old engine source checks and 12 retained artifact hashes. Existing fresh artifact rehashes and the exact, reviewed archive-profile exception remain in place.

The final checker SHA-256 is `1188ac0dd9edbf85ce605d4a8254fe9c31a70f3a02c47bab17f83de56f5e08b3`. The immutable preservation and readback pins are respectively `9c6f2a3168b1cd083dbc973a7d15141b5d9ff3e7e3ac6551a4f23010b63f493c` and `945faf8789de924d916f2d8ad52355014c73fa92bd2eb0130a3b4b0122e6edfd`.

## Evidence reviewed

- **Exact full gate:** the original 2020-test/zero-failure/zero-error/zero-skip expression accepts its exact fictional control and rejects fewer/more tests, errors, skips and a missing skip field. The current source inventory equals full-gate04's launch inventory. An actual invocation of the aggregate checker with an explicitly missing terminal bracket returned `FAILED`; no missing evidence was promoted to PASS.
- **Archive compatibility:** both chained profile migrations and their 52-test qualification evidence pass the component checker. Supplying the first profile's validation as the current profile rejects. Current source pins remain consistent.
- **Installed qualification:** current attempt02 passes fresh package/source/wheel/context and log consistency checks. Attempt01 rejects because its captured source bytes predate the serde/profile changes. Missing qualification rejects. The actual attempt02 command records use isolated installed interpreters; package inventories resolve beneath the isolated environment.
- **Windows replacement:** actual bounded retry, compatibility and no-clobber evidence pass. The peer evidence retains its first failed stress expectation and its revised safety criterion. It recorded 1/16 terminal writer failures with native delete-sharing readers and 2/16 with normal Python readers, plus one reader I/O failure for the latter. Those are availability limitations. Complete observed payloads and explicit bounded terminal outcomes support the safety claim; they do not establish universal successful writes, compare-and-swap, monotonic ordering, or the cause of earlier WinError5 failures.
- **Old artifacts:** the two committed preservation documents are byte-identical to the working copies. All 12 listed retained hashes were freshly checked; only the original archive profile uses its already reviewed two-step replacement exception. Protected old evidence was not rewritten.

## Validation and scope

`run_peer.py` produced 24 initial controls: 21 matched their expected acceptance/rejection and three exposed the unittest defect. Its missing-bracket aggregate run is retained as failure evidence. `validate_fixes.py` then produced **39/39 passing controls** in `GREEN-VALIDATION.json`, including all retained red logs, LF/CRLF variants, full-driver JSON equality, interruption/skip rejection, actual component evidence and weakened preservation records. Both runs checked that the runtime/test/tool inventory stayed unchanged. Overlapping project test totals are not added together.

The peer work executed no full test gate, build, model, download, biological analysis or paid call. At completion of this review the parent still owns the full-gate04 completion decision. The checker is an evidence-consistency check, not an attestation against a malicious filesystem owner. Source bracketing does not eliminate arbitrary mid-run edits that are restored before the final hash capture. Installed verification stdout establishes what the qualifier checked at capture; this review did not rerun all installed CLI commands.

Changed existing file: `../check_stage.py`. All other new files from this review are confined to this directory. Existing red results, source evidence and logs remain unchanged.
