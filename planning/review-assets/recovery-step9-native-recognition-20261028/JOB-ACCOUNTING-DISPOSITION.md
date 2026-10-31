# Scoped accounting result and next launch gate

28 October 2026 UTC. The separately declared v3 OS-only diagnostic completed once
and its [independent verification](JOB-ACCOUNTING-V3-RESULT-VERIFICATION.md) passes.
All 53 inputs, fourteen output files, thirteen receipt entries, eight journal
events and five raw accounting/PID snapshots agree. The only listed live process
was the owned canonical Python worker, PID29040, with strict parent8256 and stable
creation time. Active counts were **0,1,1,1,0**; total process counts were
**0,1,1,1,1**. The worker exited87 after owned-job termination; process, metadata
and Job handles closed. Captures were empty, with no cleanup errors. Whole-child
time was1.140 seconds; helper completion1.203 seconds is the root's measurement.

The cached ctypes bootstrap module resolves to the actual System32 kernel32 and
matches the explicit full-path handle. The prior v2 diagnostic remains failed
before worker dispatch. Its [independent failure review](JOB-ACCOUNTING-V2-FAILURE-PEER.md)
supports the narrow startup-guard explanation without inventing an observed
traceback or rejected audit argument. Original held v1 and failed v2 records are
not replaced by the successful v3 result.

**The original active2 observation was not reproduced; its cause remains
unresolved.** V3 validates this declared worker/measurement path. It does not
prove that the old probe was correct, explain every host process behavior,
establish universal process-tree isolation or qualify target-library execution.
The original anomalous snapshots remain available. Future checks must retain
contradictory raw observations before asserting consistency.

This result permits continued **preparation** of a new public-SDK launcher and
its separate harmless-worker qualification. It does not permit running the
compiled ABI bridge. The next protocol must require Job membership, exact PID/
accounting and read-back limits before the only resume, plus bounded capture,
memory/time, independent handle cleanup and retained unknown-creation/resumption
states. The same launch path must be exercised with owned harmless code before
any target DLL call. Unexpected accounting stops that attempt and preserves its
raw record; no automatic fallback or favorable rerun is allowed.

The current SDK-launcher draft is hard-disabled and has a
[source HOLD](ABI-LAUNCHER-DRAFT-PEER-REVIEW.md): unsupported journal kind,
accounting evidence discarded before assertions and lease cleanup that can
replace the primary failure. Those findings require a separately preserved
revision and meaningful regressions. The prospective design also moves Job
assignment into documented process-creation attributes, with restricted stdio
inheritance and suspended execution. This addresses the post-return assignment
gap; no universal guarantee about caller death inside an OS API is claimed.

No new target DLL, GGUF, tokenizer, model inference, server, dataset download or
paid provider call occurred. Accepted runtime remains0.3.11; whole R09 and all
scientific/human gates remain open. The [native-build project assessment](../../Project%20Progress%20Reassessment%202026-10-28%20-%20Native%20Build.md)
is a preserved earlier snapshot; this disposition records the later OS evidence.
