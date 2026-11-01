# P05 source-only builder v2: prospective output path correction

Status: corrected entry guard; 36 fictional tests pass. The v2 DRAFT is published, and root must separately freeze READY v2 before any actual source execution. This change performs no actual source-value scan, network/model call, or download.

## Exact artifacts

- Builder `tools/science/prepare_source_validation_set.py`: SHA256 `cb0bffdc02fc5813f3d2b545fc1e54364d93ea225378b9f7ccd55471bceb835f`.
- Tests `planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_set.py`: SHA256 `a762a5894350bec351b513fbf8ea81a6a60375205d6bf532083739b97535a177`.
- New `REGISTRY-PLAN-DRAFT-v2.json`: SHA256 `2f68e901ba11b381e19543bc848f06af2944e8936f8293bb654f87082d187f05`.
- Frozen v1 DRAFT remains byte-identical: `d2a16bbfa79794c6c19c4e8bed8ff7ae1a01fb5d04dc675b5685c7cf84da6174`.
- Frozen v1 READY remains byte-identical: `f9673029667f4c119a3bd958e172239a27ddac884d4833d3db30353a3ba5f15f`.

The v1 code/checkpoint and frozen artifacts describe the unsuccessful initial entry attempt. That attempt called the public `checked_path` on the prospective output leaf, whose `_no_links` check requires the path to exist. It raised FileNotFoundError before output reservation or original/source reads. Root records that attempt separately.

## Narrow correction

The allowed output remains a fresh `data/derived/preprint-p05-source-validation-<UTC>` directory. Entry first enforces its exact approved parent and strict basename, validates the existing parent with the unchanged public `checked_path`, and uses `lstat` to reject any existing leaf, including an existing link. The leaf is allowed to be absent at this stage.

After the exact v2 plan/READY/code/environment guard succeeds, the unchanged public `RunJournal` reserves the output directory exclusively. The builder then validates the now-created leaf with the full public `checked_path` inside the failure-protected `output_reservation_validation` stage. Any rejection produces a terminal failed journal/failure seal and occurs before original source access. Existing symlink/reparse checks are retained. An unapproved output path, existing leaf, or reparse parent is rejected.

The implementation now uses only `REGISTRY-PLAN-DRAFT-v2.json` and `REGISTRY-READY-v2.json`; it cannot authorize this changed code through the frozen v1 READY. Root READY v2 must bind the exact v2 DRAFT hash, complete code pins, environment and explicit UTC cutoff using the same schema as v1. The builder does not write READY.

Selection, projections, eligibility/date rules, source-frame hashes, scientific scope and resource bounds are unchanged from `BUILDER-NOTES-v1.md`: select an actual 1..12 eligible units under the cap, retain/fail at zero, never replace a selected missing/conflicting case, keep every copied selected original UNQUALIFIED/AUDIT_ONLY and hidden from agents, and require future agent-packet/reference builders to reread eligible originals plus the neutral plan. The full original/receipt stable verification and source-role admission still precede all values. No src/P04/P04b artifact changed.

## Validation

```powershell
& 'D:\Projects\drug_target_agents\.venv\Scripts\python.exe' -B planning/review-assets/preprint-p05-20261031/test_prepare_source_validation_set.py -q
```

36 fictional tests pass with workspace cwd and TEMP/TMP. The prior 33 checks remain. Three entry regressions cover a fresh absent leaf reaching `load_guard`, real exclusive reservation plus protected created-leaf validation before source access, and existing/unapproved/reparse-parent rejection. The entry tests and the complete fictional pipeline now exercise the actual public `checked_path`, `stable_files` and `RunJournal` implementations instead of replacing the path check with a lambda. Targeted failure injection verifies that a created-leaf validation error is journaled/sealed before source access. Reparse-parent testing emulates only the OS reparse attribute returned by lstat while keeping the public rejection logic real; it creates no live junction.

Only the metadata-only `--draft` action was executed for v2, reporting 137 files and `source_values_read: 0`. Actual v2 execution remains for root after peer consistency review and a fresh READY v2 freeze.
