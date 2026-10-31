# Accounting diagnostic v3 — bootstrap correction, preparation only

V3 is prepared and frozen for separate root/peer review. **No diagnostic worker,
ctypes load or Windows Job API was executed during preparation.** V1 remains
unexecuted and held; the consumed v2 failure is preserved with its diagnosis and
independent failure review.

| Frozen artifact | SHA256 |
|---|---|
| `probe_job_accounting_v3.py` | `d5f23f471adc9d4ee293d2bee27a3d85443b578a4a116e50ce53ccd235920e49` |
| `JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL-v3.json` | `e47419db7763b21b36885691d1e589aaf171d94c3c992c0500922cae62005412` |

The v2 [failure diagnosis](JOB-ACCOUNTING-V2-FAILURE-DIAGNOSIS.md) and
[independent review](JOB-ACCOUNTING-V2-FAILURE-PEER.md) establish a pre-dispatch
bootstrap rejection, not a Job-limit result. Pinned ctypes source accesses
`windll.kernel32.GetLastError` during import. V2 rejected that exact basename
before Job setup, recording zero dispatches and zero snapshots. Its five files,
receipt and two-event journal remain unchanged.

V3 makes a narrow parent-only correction:

- Allow exact literal **`kernel32`**, in addition to the already allowed current
  process and exact full System32 path. Preparation and worker roles still
  reject all ctypes loads. Other basenames, suffix/case aliases and unrelated
  full paths remain rejected.
- After ctypes import, query **the actual cached `ctypes.windll.kernel32`
  handle** with bounded `GetModuleFileNameW`. Reject empty, truncated,
  inconsistent-length or nonmatching paths. Require its resolved path to equal
  the expected System32 kernel32 file before any Job call, and require the
  separately opened explicit-path handle to match that verified cached handle.

The protocol binds **53 files**, preserving all 34 v2 pins and the original
27 pins, all sixteen original OS-probe artifacts, the five-file v2 failure,
source/peer/decision records, and exact ctypes bootstrap source
`608671c6b49e5e027e3348fcf492718c33f69f919d99f4ff170522c40bd4c550`.
The public module-path API signature is pinned from the installed SDK; no
source or SDK body was downloaded.

[Twenty pure checks](JOB-ACCOUNTING-V3-FAULT-CHECKS.json) passed using captured
audit-hook closures and mocked path readers, without invoking ctypes or a real
module-path API. They cover the three permitted parent cases, rejected aliases
and other libraries, all preparation/worker rejections, correct mocked path,
wrong module, zero/truncated/inconsistent lengths and relative path. The earlier
six marker/capture tests are preserved; those helpers, worker logic, limits and
stages are AST-identical to v2. No fixture worker was dispatched.

Scope remains one hidden direct-base sleep worker, five snapshots, at most
sixteen job-returned PIDs, eight seconds for the whole child and 45 seconds
overall with five seconds reserved for sealing. Atomic markers, capped pipe
capture, abort-aware checkpoints, owned cleanup and raw counter preservation
are unchanged. The only added metadata query concerns this parent's own cached
system module. There is no global process enumeration, private process API,
target DLL, GGUF/tokenizer/model/context access, inference, network or server.

The fresh output remains absent at
`data/cache/r09-job-accounting-diagnostic-v3-20261028T185655Z`.
After separate exact-hash root authorization, the proposed command is:

```powershell
& 'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe' -I -B 'D:\Projects\drug_target_agents\planning\review-assets\recovery-step9-native-recognition-20261028\probe_job_accounting_v3.py' --execute e47419db7763b21b36885691d1e589aaf171d94c3c992c0500922cae62005412
```

That command has not run. The original active-process accounting anomaly remains
unresolved; this readiness document grants no containment or native-model pass.
