# BG01 implementation review

Status: implementation and focused checks pass; full-gate and installed-release qualification are still required. This is not the BG01 completion record. Baseline for the fixes is `114fecf`; the activated execution plan was committed as `749f296`.

## Reviewed changes

CE01 preflights a fresh report destination, protects queue/original/receipt paths including missing inputs, refuses existing files, reparse paths and alternate data streams, and publishes a complete same-directory temporary file using non-replacing move. Twelve fictional tests cover ordinary success/failure, equivalent paths, hard links, junctions and concurrent publishers. Root inspected the patch and tests. This does not promise protection from a malicious filesystem owner swapping parents during execution; it prevents the reproduced overwrite and static aliases under the stated local filesystem trust boundary.

CE02 carries fully validated response usage through a `BackendFailure` that remains a `ContractError` for existing direct callers. The workflow's existing measured-failure path then accounts usage and stops dispatch on the reservation violation. The archive checker reconciles response hashes, attempts, reservations, accounting and violation records. Malformed/unqualified responses retain unknown/conservative accounting; adapter-reported counts are not authenticated physical consumption. Root inspected the implementation; separate peer controls exercise sealed-run verification and unchanged valid older failed archives. The workflow implementation itself is unchanged.

CE03 extracts the existing used-ancestor receipt/availability relationship into a pure shared helper and invokes it for every policy inventory input during prepare and verify. It preserves non-download availability bases and does not add another raw hash pass. Root inspected both call sites and the helper; a separate reviewer exercised used/unused timestamps, references, URLs, alternate bases and equal hash-call counts. Valid older policy seals still verify at this boundary; the formerly accepted unused-node contradiction is now rejected. Matching old launchers remain necessary for old outer code proofs.

## Qualification boundaries

The source/metadata-aligned development environment is `data/cache/tether-051-dev`: engine 0.3.12, TETHER 0.5.1, PyArrow 21.0.0. Two environment setup failures (sandbox uv cache write, then conflicting editable/noneditable source overrides) are retained. Explicit offline local editable requirements resolved them without changing older qualified environments.

Focused suites overlap and are not summed. The complete facade suite passes 138 tests. The first full core gate is retained in `integration/full-gate-01.log`: it was interrupted after 14 failures/errors from the stale 0.3.11 executing dependency profile. The process is confirmed terminal; no ordinary final JSON was produced. Its driver lacked a whole-source launch manifest, and root's initial progress filter missed live failure entries; the correction and exact log hash are retained in the interruption record. This run is not a pass.

The 0.3.12 archive profile preserves the previous resource byte-for-byte, retains the same policy and module inventory, and updates exactly the three reviewed module pins. Archive Python code remains unchanged. After migration, 52 archive tests pass and three relocated 0.3.11 controls verify valid normal/unknown-usage runs while rejecting the old invalid overquote. The fresh full gate will bracket the complete runtime/resource/test/tool inventory; installed qualification independently compares wheel and installed bytes. No hostile-worktree attestation is claimed.

The old 0.5.0/0.3.11 environment and releases are preserved and separately checked under `legacy-preservation/`. Old benchmark results, paper/PDF/release artifacts, original receipts, downloader and stopped monitor are not modified. No new biomedical benchmark, model call or provider spending has occurred in BG01.

The final `VALIDATION.json` must verify the completed full gate, installed qualification, retained source pins and preservation evidence before TODO marks BG01/CE01–CE03 complete. The goal then proceeds to BG02; this review does not substitute for that independent comparison.
