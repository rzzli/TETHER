# V2 failure: guarded standard-library bootstrap, no dispatch

The consumed v2 attempt remains failed with an authoritative marker. Its exact
five-file universe, three receipted output hashes and two-event journal verify.
It recorded **zero dispatches, zero snapshots and no worker identity**. No Job
setup or target/model operation was reached.

Pinned local `Lib/ctypes/__init__.py:473` assigns
`GetLastError = windll.kernel32.GetLastError`. Importing ctypes therefore
requests the exact library name `kernel32`. V2 had installed its guard before
the import and allowed only `None` or the full expected System32 path. That
standard bootstrap request triggered `Only current-process and exact system
kernel32 loads` before the diagnostic could collect evidence.

The empty `guards.denied` array does not mean no request was rejected: the
ctypes branch raises directly without appending that array. This diagnosis
uses the retained failure and pinned source ordering, not a rerun.

[The diagnosis record](JOB-ACCOUNTING-V2-FAILURE-DIAGNOSIS.json) binds all hashes,
including ctypes source
`608671c6b49e5e027e3348fcf492718c33f69f919d99f4ff170522c40bd4c550`.
The correction is a narrow parent-only allowance for exact literal `kernel32`,
followed by verification of its actual cached module path before any Job call.
No general DLL-basename allowance is justified.

The original active-process counter anomaly remains unresolved. This failed
attempt established neither a new Job-limit result nor a native target failure.
No worker, network request, Windows Job API reprobe, target DLL/GGUF or model
call was performed for this diagnosis.
