# Rejected quota additions and Job lifetime accounting

28 October 2026 UTC. **A rejected limit association can increment `TotalProcesses`; exact finaltotal2 is a defensible prospective expectation for the one intentional harmless quota attempt. Keep the ABI and generic no-descendant gates at total1.** This is AI primary-document/source analysis, not a new experiment or independent verification of the actual run. No helper, Windows API, worker/model or protected payload was executed/read, and no source/protocol was changed.

## Primary documentation and inference

Microsoft's [basic Job accounting documentation](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information) explicitly includes failed limit associations in lifetime `TotalProcesses`; its short relevant statement is “this value is incremented.” It also says `ActiveProcesses` may temporarily increase for such a failure until the terminated process exits and references are released. Therefore, total2 alone does not establish that a second child ran user code. A final zero active count/empty PID list describes the sampled drained state; it is not a complete historical execution census.

[ActiveProcessLimit](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) documents termination and failed association when an addition exceeds the active limit. [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject) gives the same rejection behavior. Normal CreateProcess descendants inherit the Job without the relevant breakaway permissions. See [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

Error1816 is [ERROR_NOT_ENOUGH_QUOTA](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1700-3999-). It does not uniquely identify the active-process limit. This fixture also exercises a memory quota, so the error code should be interpreted together with its exact protocol, read-back Job limits, attempt count, worker result and raw accounting.

## Connection to the retained harmless worker

The frozen [worker](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/harmless_launch_worker.py:89), SHA-256 `dc388b9a83d11d76ed30403658ee31f8cbf91276ffeafca1b6f91f9b49eb9811`, requests384MiB and then attempts exactly one descendant through `Popen` (lines97–116). It requires `MemoryError`, rejected creation and WinError1816. It has no retry. Its descendant command exits immediately; there is no original descendant first-entry marker, so such a marker cannot be retroactively inferred absent/present.

The root reports initial/running total1, active1 and only the owned worker PID; the worker reports the one rejected attempt; final raw values are total2, active0, terminated0 and no PID. A separate peer verifies those actual artifacts. The documented failed-association lifetime increment is consistent with this transition. The record does not prove the precise internal kernel execution ordering or independently exclude every possible live interval.

`TotalTerminatedProcesses=0` remains the observed value. Do not convert it into proof that no limit rejection happened or invent a universal rule that rejected additions must have that value. The documentation defines this separately from the lifetime association count. The earlier unplanned active2 result remains unexplained; the planned quota attempt supplies no cause for that older observation.

## Prospective role-specific correction

For **resources / harmless_after_wait only**, require all of the following before accepting the final counter tuple:

1. The exact frozen resource worker/protocol/mode and returned owned identity match; configured active limit is1 with no breakaway.
2. Pre-attempt observations show total1, active1 and the owned worker only.
3. The complete matching worker result records exactly one intended descendant attempt, rejectedtrue and WinError1816.
4. The owned worker is waited/reaped, and both raw SDK responses have valid lengths/decodes.
5. The selected role's final tuple is **total2, active0, terminated0, empty PID list**, with every raw field preserved.

Use exacttotal2 for this selected finite qualification, rather than a generic total1-or2 allowance. Total1, total3, malformed/missing evidence or another role fails that declared expectation. The terminated0 value is a deliberately selected observed-platform qualification value, not a claim of universal API semantics. Other roles and the ABI launcher retain strict total1.

Preserve the original failed qualification and its reason. A new policy/protocol needs explicit prospective root review; this document does not relabel an old failure as a passed attempt or authorize another execution.

## Bounded distinction if further diagnosis is needed

A separately authorized diagnostic could use one owned main worker, active limit1, no breakaway and exactly one planned descendant attempt. Retain an atomic before-attempt marker and raw parent baseline, then the exact creation outcome/error and whether a PID/handle was returned. Take named bounded raw snapshots after that result and after cleanup. No second attempt or wider process quota is needed.

A separately versioned harmless descendant can write a first-entry nonce marker as its first action. A marker or successful returned spawn supplies positive evidence of user-code entry/creation and fails the intended rejection test; terminate/reap through the owned Job. Marker absence and endpoint counters alone cannot prove universal nonexecution. Retain transient counters without treating a documented failed-association transition as a demonstrated running child. Any additional sampling/handshake must fit the existing finite timeout and capture bounds and receive its own exact decision.

The source/protocol references, root-reported versus documentary facts, unchanged ABI rule and proposed scope are pinned in [JOB-QUOTA-ACCOUNTING-SOURCE-ANALYSIS.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/JOB-QUOTA-ACCOUNTING-SOURCE-ANALYSIS.json).
