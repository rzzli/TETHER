# Prospective ABI parent v3: retained late cleanup and terminal seal

28 October 2026 UTC. **Hard-disabled draft; no real Windows creator/Job API, native target, compiler, model/GGUF or network execution.** This is AI engineering preparation. Full-orchestration tests below inject fake SDK behavior and synthetic output bytes, using the real accepted journal and local files only.

The [v3 source](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/abi_parent_launch_draft_v3.py) is SHA-256 `c111ac5f42209eb61fc49522d4cd6db544987b1c4230577404022e1add6eb2f4`. It remains `NATIVE_EXECUTION_ENABLED=False` with no target execution command. The old `ec26…` and `b129…` drafts, old designs/tests and both peer HOLD records remain unchanged.

## Narrow change and reason

The [v2 peer review](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-LAUNCHER-DRAFT-PEER-REVIEW-v2.json) cleared the original three defects within source/fake scope but retained one material finding: the parent report and receipt were written before original input leases closed. If an earlier failure already had `failure.json`, a later Close error was only kept in memory. The existing marker suppressed a second retained record.

V3 adds one helper, `seal_post_lease_cleanup`, and replaces only that final close block with its invocation. The existing `prepare_config` identity label advances to v3. AST comparison confirms that every existing class and all other top-level functions are identical to v2. This does not change JOB_LIST, SDK launch layouts/calls, caps, ownership, raw snapshot policy, source/model data or accepted runtime code.

## Required artifact order

1. Retain the original pre-cleanup report/receipt with their existing hashes. They are never rewritten.
2. Attempt every tracked live-lease close. Preserve each path/handle, prior validation error, earlier close errors, whether this close was attempted/returned, its error and the final observed closed state. Previously closed leases are recorded explicitly. A close exception leaves that handle's closure unconfirmed; no success is inferred.
3. Exclusively write **`post-lease-cleanup.json`** with every outcome, the original primary-failure identity/marker hash, the earlier receipt hash and elapsed/deadline status. This record is required even when there were no close failures or there was already an earlier failure.
4. On a late close/deadline error, always write a separate authoritative **`late-failure.json`**. It binds the cleanup record and preserves the original primary failure. An existing `failure.json` does not suppress this supplement.
5. Exclusively write required **`terminal-seal.json`**, binding the earlier receipt, cleanup artifact, primary/late markers and a complete hash inventory of all earlier output files. The seal itself is the sole file outside that inventory in an ordinary completed attempt. A missing seal means **incomplete**, even when the early receipt exists.
6. A parent deadline crossed during the final seal adds authoritative `after-seal-failure.json`, which invalidates the earlier seal. Every known failure marker overrides all status claims. An absent earlier receipt cannot produce a successful terminal status.

Lease closes occur before potentially failing post-cleanup artifact hashes. If writing/sealing fails, the helper attempts a separate late supplement containing the close outcomes and preserves the exception; it does not overwrite or repair an earlier artifact. Unavailable storage or abrupt parent death can still prevent durable records. No missing record is interpreted as success, and no incomplete attempt is automatically repeated.

The earlier report remains an explicitly pre-cleanup snapshot. The required terminal seal and any authoritative supplement determine the overall engineering status after cleanup. Even a successful terminal status is only `ABI_observations_retained_independent_qualification_pending`, never scientific or general ABI acceptance.

## Validation and retained synthetic cases

[Thirty-three pure checks](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-PARENT-V3-PURE-CHECKS.json) pass with zero failures/errors/skips in0.296s. Their report hash is `50638171ed0f866f70ecb0bee7cab4fd35b39c3880c53dd752d6f56e1e27d0fb`; the checker hash is `96f614e23d81758284e364d42654c5dffa832cd84c936b0ff9016ab7427bfc11`.

The three new cases verify:

- An existing synthetic primary marker and receipt remain byte-identical after a late Close error. Both original and late errors remain in their separate artifacts, and the terminal seal binds both.
- Full parent orchestration, real installed `RunJournal`/`read_chain`, raw capture files, raw snapshots, child-artifact parsing, final input recheck, lease closes and output inventory can finalize a **fake-only success**.
- The same complete path retains an earlier fake observation-validation failure plus a later fake original-lease Close failure, with an authoritative late supplement and failed terminal status.

The full-path fixtures temporarily inject a fake API factory before enabling the function's test flag, then restore the hard-disabled global. The real `Kernel32` constructor is never reached. Their artificial child rows use `FAKE_PURE_FIXTURE_NOT_NATIVE`, and the effective configuration marks `pure_fixture=true`. No OS child is created; these are control-flow and file-integrity tests, not an actual ABI run.

[ABI-DRAFT-PREPARATION-v3.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-DRAFT-PREPARATION-v3.json) pins the exact sources, prior HOLD,30-test evidence, SDK/build/OS references and all files of the three synthetic terminal fixtures. Each fixture's complete terminal output inventory was independently rehashed when that preparation record was written.

## Next bounded gate

All bounds and JOB_LIST/SUSPENDED decisions remain those in the [v2 design](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-EXECUTION-DESIGN-v2.md):60s parent,30s owned attempt,256MiB process/Job commit, active1,64KiB streams, max40 named raw Job observations and no target model/tokenizer/grammar work. Original active2 remains unexplained; the separate OS v3 diagnostic is a finite observation, not universal containment proof.

This exact source/schema still requires independent peer review. The next actual execution, if authorized separately, is the finite harmless-worker qualification of the same SDK suspended/JOB_LIST/stdio/resource/capture/cleanup path. Native ABI stays disabled until those results, a new enabled helper and exact protocol/root decision are reviewed. No grammar, EOG, inference-quality, fresh-source, human-scientific or full-project gate is completed by these pure checks.
