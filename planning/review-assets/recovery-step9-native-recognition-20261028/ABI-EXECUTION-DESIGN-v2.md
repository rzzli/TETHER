# Prospective ABI parent v2: creation-time Job assignment

28 October 2026 UTC. **Hard-disabled source preparation only.** No creator/Job WinAPI, native target, GGUF/model, network connection or compiler was invoked. Pure tests did use the accepted installed journal implementation and fresh project-cache files. This is AI engineering work, not independent scientific review or native execution authorization.

The separately named [v2 source](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/abi_parent_launch_draft_v2.py) has SHA-256 `b129c2a67c7b0bc44eb337ca63ad79a6c05067ad7a249986deb68b7591c6373c`. Its constructor and orchestration entry remain hard-disabled; there is no target execution command. The old `ec26…` source, old design,19-test record and [peer HOLD](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-LAUNCHER-DRAFT-PEER-REVIEW.json) remain unchanged. The v2 draft needs its own independent source review.

## Corrections from the held draft

| Retained finding | v2 behavior | Relevant pure evidence |
|---|---|---|
| `RunJournal(kind="native_abi")` is unsupported and failed before the old failure boundary. | Use actual installed `kind="build"` inside the protected path. Exclusively reserve an outer output root first, so a journal-constructor failure can retain its own marker without adopting an existing/racing directory. Journal and child artifacts live under `execution/`. | Accepted `RunJournal`/`read_chain` exercised in a fresh D: cache directory; the old kind is concretely rejected. Injected constructor failure retains an authoritative marker. Existing roots are not adopted. |
| Accounting/PID responses were discarded or asserted before persistence. | Capture full48/136-byte SDK buffers, both return lengths, API success/error codes, every accounting field, assigned/listed counts, capped PIDs and monotonic query bounds. Journal the bounded observation before checking any of those fields. | A real accepted hash-chained journal retains raw active2/PIDs20,99 before the fake anomaly raises; Resume is never called. Failed/truncated fake responses remain inspectable. |
| Lease validation followed by failed close could replace the primary error and lose ownership. | Register the returned handle before validation. Keep the validation error and independent close error in that record; a failed close leaves the handle tracked for final cleanup. | Combined fake hash-validation/Close failure raises the original validation error and retains the handle plus both errors. |

The actual installed journal text is pinned at `498362a56e2597f5381093592240e8dd350f8b74d8728beeef8b8e1e7adaeb11`. No accepted runtime module was changed to accommodate this helper.

## Creation-time assignment replaces the earlier gap

The local SDK defines `ProcThreadAttributeHandleList=2`, `ProcThreadAttributeJobList=13` and the input bit`0x20000`; their public attribute constants are therefore `0x20002` and `0x2000D`. The prospective launcher initializes an attribute list with **count2** and keeps both arrays alive through creation and list destruction:

- `HANDLE_LIST`: precisely three inheritable handles—NUL stdin, stdout writer and stderr writer.
- `JOB_LIST`: precisely the newly owned Job handle. `CreateJobObjectW` uses null security attributes; this handle is non-inheritable and excluded from the three stdio handles.

Microsoft documents `JOB_LIST` as assigning the listed Jobs during process creation on Windows10+/Server2016+. Its value storage must remain alive until attribute-list deletion. See [UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute). The exact local SDK text is pinned in [ABI-DRAFT-PREPARATION-v2.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-DRAFT-PREPARATION-v2.json).

`CREATE_SUSPENDED` remains mandatory. After successful creation the parent checks raw Job observations, exact membership, configured limits and the returned process/thread identity before the sole Resume call. There is **no manual `AssignProcessToJobObject` call or fallback**. A failed attribute update prevents `CreateProcessW`; failed creation/membership/accounting prevents Resume. This removes the successful-Create/post-return/manual-Assign interval from the design. It is not a universal guarantee for arbitrary parent death inside an unreturned OS call.

Creation state distinguishes setup, a durably reserved real API attempt, an observed return, returned success/failure and an unknown outcome. Interruption after the API reservation but before observed return leaves `unknown_CreateProcessW_outcome`; cleanup terminates the newly owned Job even if no process handle was observed. Resume state likewise preserves `unknown_may_have_run`. Neither case implies zero native activity or proven reaping of an unobserved process.

## Finite raw accounting policy

All raw samples are named and journaled before validity assertions: configured-empty, before-resume, immediately after Resume, periodic running samples and after wait. Running queries are scheduled every0.9s, with a maximum40 snapshots in the30s owned attempt. Every query is retained; unrelated CPU/time-field changes do not trigger extra sampling. Exhaustion stops before another query. The actual query start/end times remain in the record; this schedule is not a claim that the OS cannot stall.

The two public queries are sequential rather than atomic. Running samples may consistently show the one live owned PID **or** its normal completed state; an immediately completed child is not forced to appear active. Inconsistent/failed/truncated responses stop with their exact raw evidence. A timing-dependent mismatch alone is not labeled an established containment breach, and it does not trigger a retry.

The verified [OS v3 record](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/JOB-ACCOUNTING-V3-RESULT-VERIFICATION.json) observed0→1→1→1→0 active processes with only the owned PID29040. The [root disposition](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/JOB-ACCOUNTING-DISPOSITION.json) retains the original active2 result as unexplained and holds target execution. That one diagnostic did not exercise this new suspended/JOB_LIST launcher.

## Retained limits and next gate

The intended ABI experiment remains one attempt:60s whole parent,30s owned child including cleanup,256MiB process and Job commit, active-process limit1,64KiB per captured stream and4MiB child JSONL. It supplies only the fixed compiled executable, `--abi`, approved runtime directory and empty child output. Original path/hash leases, explicit minimal environment, exact loaded-module checks, raw version/default/layout observations, authority of failure markers and no model/CPU-backend/registry/tokenizer/grammar API policy remain as described in the [earlier design](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-EXECUTION-DESIGN.md), subject to the corrections above.

The raw output tree is now an exclusive outer root containing `parent-reservation.json`, effective config, captures, parent report/receipt and `execution/` with its accepted build journal and child directory. Original read leases remain held through final input rechecks and sealing. A later cleanup/deadline failure marker invalidates an earlier receipt. Retained lease records describe ownership at sealing time; close failures remain independently authoritative.

**Thirty pure tests pass**, zero errors/failures/skips, in0.091s. [The report](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/ABI-PARENT-V2-PURE-CHECKS.json) hashes the exact source/checker. Fake tests exercise the concrete typed creator method, including two live attribute arrays and failed updates, but they do not call real WinAPI. Full orchestration and real inherited handles, Job resource enforcement, memory peaks and timeout cleanup are still unqualified.

After exact-hash peer review, the next authorized preparation is a finite **harmless-worker** qualification of this same SDK path. The root-authored resource/overflow/sleep/suspended-abort worker can exercise resource/capture/deadline/never-resume behavior only under a separately reviewed protocol and decision. Native target execution stays disabled until those results are independently verified and a new enabled helper/protocol is frozen. No whole-project, grammar, inference-quality or scientific completion follows from this draft.
