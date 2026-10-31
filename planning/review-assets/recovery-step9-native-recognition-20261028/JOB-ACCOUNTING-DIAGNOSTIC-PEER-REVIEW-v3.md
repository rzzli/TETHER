# V3 accounting diagnostic: source-only peer clearance

**CLEAR for the exact bounded OS-only diagnostic source; separate root execution decision remains required.** This review did not import or execute helpers, rerun fixtures, call Windows APIs or launch a diagnostic child.

| Frozen input | SHA256 |
|---|---|
| probe_job_accounting_v3.py | d5f23f471adc9d4ee293d2bee27a3d85443b578a4a116e50ce53ccd235920e49 |
| JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL-v3.json | e47419db7763b21b36885691d1e589aaf171d94c3c992c0500922cae62005412 |
| check_job_accounting_v3.py | 9a6209d8820014c64ad37f783ef1caa8912ec042b4f92a2bd613ce05db7456b1 |
| JOB-ACCOUNTING-V3-FAULT-CHECKS.json | 212256d8ca505947b6865474341c40a1d8b440574e74f4fee99c63f4e0f07480 |
| JOB-ACCOUNTING-DIAGNOSTIC-PREPARATION-v3.md | 26364dd73531d4ae8374b52c66c51c8b152f15ec7b14d27607f4e14d366b586d |

The v2 failure remains authoritative and consumed: five files, empty worker directory, zero dispatches and no snapshots. V3 corrects its source-supported ctypes import-startup rejection by adding only exact parent literal `kernel32` to the existing None/exact-System32 choices (helper130-139). Preparation and worker still reject every ctypes load. Twenty retained pure guard/path cases report success, including rejected suffix/case aliases, unrelated libraries, wrong/relative paths, zero/truncated and inconsistent lengths. These fixtures directly call captured audit closures and mocked readers; they never exercise the real DLL loader or module API.

Before any Job call, api() obtains the actual cached `ctypes.windll.kernel32` object and queries its own handle with correctly typed, bounded GetModuleFileNameW (helper320-333). Its reported UTF16 length must be positive and less than32768 and match the complete string. Both paths must be absolute and resolve strictly to the same expected System32 kernel32 file. The later explicit-path handle must equal that verified cached handle (helper360-362). The first CreateJobObjectW call is helper443, after this proof returns. A failed or truncated query cannot proceed to Job setup.

Independent own Python read/hash/AST validation confirms all53 current protocol pins, all34 preserved v2 pins and all27 initial pins. The original16-file probe and consumed five-file v2 cache remain intact. All four SDK excerpts match exact physical LF line ranges, including the new module-path signature; local ctypes line473 and its source hash are bound. The fresh prospective v3 output remains absent. Six earlier marker/drain/SDK fixtures and all six retained artifact hashes/file universe also revalidate. The two new mock module files contain their fixed inert fixture text; their hashes are recorded in the JSON review.

Eleven existing functions, including drain_capture, publish_marker, worker, safe and environment, are AST-identical to v2. All five structure classes remain identical. execute() is identical after normalizing only the extra bootstrap proof return/report assignment. Thus the capped64KiB captures, overflow/error stop handling, fsynced atomic markers, owned cleanup and five-second sealing reserve are retained. Scope remains one hidden direct-base worker, five snapshots, at most16 job PIDs and16 unique PIDs, eight seconds for the whole child and45 seconds overall. Read-only process image/creation queries stay restricted to job-returned PIDs; the added module-path query inspects the parent's own cached system module. No retry, global/private enumeration, target DLL, GGUF/model, compiler, network or server action is added.

No material source blocker remains in this finite scope. Actual ctypes startup, module path retrieval, Job/PID accounting, threads/pipes and termination remain untested by these fixtures and by this review. Cooperative deadlines can overrun during blocked OS/I/O calls; observations remain non-atomic and incomplete sealing remains possible. The preserved earlier v2 static CLEAR missed startup and does not qualify actual accounting. This review grants no runtime permission, establishes no cause for the original active2 observation, and makes no native containment/model or scientific-completion claim.
