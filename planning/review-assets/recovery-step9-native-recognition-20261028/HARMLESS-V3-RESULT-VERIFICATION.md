# Actual harmless v3: independent failed-result verification

**The v3 attempt is authoritatively failed, with complete retained evidence.** Only resources ran; overflow, sleep and suspended_abort remain unattempted. No helper/API/child rerun, native target or global process scan was performed by this reviewer.

All143 input pins and the byte-identical effective protocol validate. The exact13-file universe,12 terminal inventory hashes,10 early-receipt output hashes, required failed terminal seal, primary failure marker and16-event journal chain agree. There are no pending, late-failure or after-seal failure files. All290 lease records are observed closed afterward:145 were already closed recheck leases and145 original leases closed during final cleanup, with no close errors.

| Raw stage | TotalProcesses | ActiveProcesses | Terminated | Listed PIDs |
|---|---:|---:|---:|---|
| configured_empty | 0 | 0 | 0 | none |
| before_resume | 1 | 1 | 0 | 7276 |
| harmless_running_first | 1 | 1 | 0 | 7276 |
| harmless_after_wait | 2 | 0 | 0 | none |

All four48-byte accounting and136-byte PID buffers independently decode to the recorded fields and valid returned lengths. The shared finished predicate expected(1,0,0,[]); observed(2,0,0,[]) differs **only in cumulative TotalProcesses**. This is not a new ActiveProcesses2 sample. The final response was journaled before assertion and before ordinary owner handle cleanup. Final peaks/result-validation code was not reached after that assertion; no final memory-peak qualification is available.

Recorded creation uses canonical base Python PID7276/thread25012, creation-time Job membership and previous resume count1. Worker markers bind the same PID/protocol and report384MiB allocation rejection plus exactly one descendant attempt rejected with OSError1816. Natural exit is0; the200-byte stdout JSON matches the result marker, stderr is empty, captures are untruncated and the owner records reaped=True with no cleanup errors. These are valid raw observations, not a full qualification pass. Whole case is0.734s; parent pre-receipt1.218s, post-lease1.281s and pre-terminal1.312s, within8s/60s. Root separately reported invocation exit1.

Microsoft documents that lifetime TotalProcesses includes limit-rejected associations, and ActiveProcesses can rise temporarily until the terminated process and references are released. [Accounting structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information). The active-process-limit documentation also describes failed over-limit association and delayed decrement while process references remain. [Limit structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information).

A narrow harness-policy defect is therefore supported as an inference: this resources fixture intentionally makes one rejected descendant attempt, while its reused finished predicate assumes cumulative total stays1. The documented behavior is consistent with final total2/active0/empty list plus the independent one-attempt1816/exit0 marker. It does not identify a second PID, uniquely prove the cause of the second cumulative entry, explain Terminated0, or establish the original older active2 cause.

A future separately reviewed resources-only final policy(2,0,0,[]) with exact one-attempt/1816/exit0 evidence is supported for prospective preparation. Pre-resume/all other stages/ABI stay strict; no ActiveProcesses2 or generic allowance follows. Preserve this consumed failed cache unchanged. It cannot be retroactively passed, and the three unattempted negative modes remain unqualified. This review grants no rerun, v4 execution, native/model or scientific permission.
