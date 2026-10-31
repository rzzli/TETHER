# One-worker accounting diagnostic — preparation only

The new diagnostic is prepared and **has not run**. Preparation dispatched no
worker and called no Windows Job/process API. Root must review the exact helper
and protocol and issue a separate decision before `--execute`.

| Frozen artifact | SHA256 |
|---|---|
| `probe_job_accounting.py` | `ca36c94c8cffb3d0ec0b93990bb934b17994fa75101cd5f1b80696f8870608d1` |
| `JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL.json` | `b600804f82347476afd4cf1d0c866f3de53067d45e4d816f7c681c1ae505053f` |

The protocol binds **27 files**, including the canonical base executable, exact
local Windows SDK 10.0.26100.0 headers/excerpts, local ctypes field definitions,
the prior source/decision/review and all sixteen original probe artifacts.
The original report remains
`2b35761da99681ffb84995590c8199f58d45289167665905557df01ba1ce0f38`.
No original artifact is changed or reclassified.

Use **one** directly launched hidden, pinned Python worker that writes a strict
PID/PPID/base/prefix marker, waits for assignment authorization, then writes
ready and sleeps for thirty seconds. It creates no descendant. Parent policy
remains flags `0x2108`, active limit one and 64 MiB process commit cap. Five
fixed observations compare accounting with the actual PID list:

1. Configured empty job.
2. Assigned worker, before its authorization marker.
3. Worker ready and sleeping.
4. After one second of steady sleeping.
5. After owned-job termination, worker wait and process-handle closure.

Each snapshot retains `JobObjectBasicAccountingInformation` (class 1), all 48
raw bytes, field offsets and returned length; `JobObjectBasicProcessIdList`
(class 3), bounded 136-byte buffer and raw bytes; and separate query timestamps.
The SDK fields and enum constants are pinned. Runtime checks require 64/144/48
byte limit/extended/accounting structures and 136-byte sixteen-PID buffer, with
accounting counter offsets 32/36/40/44 and PID entries starting at offset eight.

At most **sixteen job-returned PIDs total** receive read-only
`OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` metadata queries. Only image
path, opened PID and creation time are read; access failures remain explicit.
Own-worker PPID comes from its strict marker. Other PPIDs remain null because
no documented narrow getter is used. There is no Toolhelp/global process
snapshot, NtQuery/reserved-field inference, remote-memory read, elevation or
termination by an observed PID. Query results are non-atomic; unknown identities
and differing counters remain raw observations rather than a causal conclusion.

Bounds are **eight seconds for the whole child and 45 seconds overall**, with
five seconds reserved for finalization. Metadata/query checkpoints consume the
same deadline; no buffer expansion, second child or automatic retry is allowed.
The parent terminates only its created job, with bounded fallback on its owned
worker handle. Read-only metadata handles, worker handle and job handle have
explicit cleanup. Partial snapshots, a fsynced hash-chained journal and failure
marker remain readable on failure; a failure marker vetoes a previously written
report/receipt. Input hashes and the original artifact universe are checked
before and after the diagnostic. This is a finite local diagnostic, not an OS
sandbox or hard scheduling guarantee.

The proposed new output is
`data/cache/r09-job-accounting-diagnostic-20261028T172641Z` and remains absent.
If root authorizes this exact protocol, the command is:

```powershell
& 'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe' -I -B 'D:\Projects\drug_target_agents\planning\review-assets\recovery-step9-native-recognition-20261028\probe_job_accounting.py' --execute b600804f82347476afd4cf1d0c866f3de53067d45e4d816f7c681c1ae505053f
```

This preparation made no diagnostic execution, source request, compilation,
target DLL/GGUF/tokenizer/model access, inference or server start. Accounting
qualification remains held until the new observations are independently reviewed.
