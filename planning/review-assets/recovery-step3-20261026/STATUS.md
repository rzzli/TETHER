# Archive restoration implementation status

Steps 1–3 are complete. Step 3 acceptance is retained in `acceptance.json`:
1,307 full tests, no failures/errors/skips, required probes and installed-wheel
checks pass with unchanged source pins. All seven guarded installed replays pass.

- New `asof.archive` package provides caller-approved logical/physical path maps,
  externally pinned materialization, a dependency-free verification CLI and
  versioned compatibility semantics. Archived Python is never imported/executed.
- Checkpoint and supplement preserve all 63 required historical source hashes.
  Earlier missing-byte reports are superseded by exact literal-patch recovery.
- 45 archive-focused regressions pass in the latest assembled suite scope
  (44 before the additional explicit semantic-dependency-drift regression).
- Seven real representative runs restore to fresh trees: v1 byte verification,
  core v2, recorded/native local selection, old bounded interpretation, recorded
  question interpretation and separate failed native-question inspection.
- Installed-wheel verification passes all seven under `-I`, an original-root
  read guard, repository-tools import prohibition, archived-code execution guard
  and network/child-dispatch prohibition. No forbidden attempts were observed.
- Guarded verification took 15.312 seconds and measured 57,524,224-byte peak
  working set. 961,051,145 bytes were copied during materialization.
- V1 semantics remain unavailable. Failed native interpretation is inspected as
  failure; successful native interpretation callbacks are unsupported and fail
  closed. No scientific validity or original-program execution is claimed.

The initial structural validation exposed nested archive ignore rules; dedicated
checkpoint/restore root exclusions now prevent archived files entering Git scope.
The initial installed check completed verification but failed to write its final
resource report because of a Windows handle-width error; the exact failed log is
retained. The corrected final guard run passes. Runtime code was not changed by
that resource-report repair.

Full validation through `run_validation.py` completed in 913.453 seconds, with
source pins checked before/after. Session 85875 is terminal, exit 0. Output is
`data/cache/recovery-step3-validation-20261026-full.log`; final reports are copied
here. The first installed resource-report attempt is retained separately from the
successful final check. Step 4 production edits may now proceed.

All core legacy modules remain byte-identical so far. Changes to package-data
configuration and data ignore rules are explicit. The source-dependent archive
compatibility guard must be reviewed/versioned when Step 4 edits live helpers;
never silently regenerate the dependency allowlist to hide semantic drift.
