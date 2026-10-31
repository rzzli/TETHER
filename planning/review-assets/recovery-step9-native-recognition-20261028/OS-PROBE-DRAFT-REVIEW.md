# Windows Job probe: pre-execution draft review

Reviewed draft `81a2a83424035245d355f8f0aa3d6550c8a29cbc61b6227bdc3f254000c2e994`
by reading source only. **Hold execution for the cleanup and path corrections
below.** No probe was imported or run; no network or target-native call occurred.

The pinned local `ctypes.wintypes` provides every imported name, including
`LARGE_INTEGER` at line 32. Static Windows x64 field layout is consistent with
BasicLimit 64, ExtendedLimit 144 and Accounting 48 bytes. The kernel32 signatures
have compatible pointer/scalar widths for the actual null/value arguments.
`IoCounters` uses signed 64-bit fields where the API uses unsigned counters;
layout is compatible for this probe, which does not interpret those counters.
These checks are not runtime execution evidence.

Required corrections:

- Make job-handle closure unconditional even if termination or wait fails.
  Currently an exception in the cleanup wait skips `CloseHandle`. If assignment
  fails, the newly launched worker is outside the job; terminating the empty job
  cannot clean it up. Use bounded kill/wait fallback on that exact owned process
  handle, retain cleanup errors, and close the job in an unconditional outer
  finally. No PID enumeration or unrelated-process termination is needed.
- Validate the reserved output and child leaf directories with resolved-root
  containment and fresh `lstat`/Windows reparse checks before writes. Current
  parent `mkdir` and arbitrary `--child` paths lack those checks.

Qualification checks should also assert the queried flags, active limit one and
64 MiB commit cap. Retain the descendant spawn's precise error; an arbitrary
`OSError` alone does not establish its cause. The last-handle-close fixture
should require a nonzero worker exit and empty diagnostics, in addition to
prompt reap after the ready marker.

The intended bounds are otherwise finite: the child waits for assignment before
the memory/process fixtures, uses a directly launched pinned interpreter, and
parent operations address only its created job or owned process handle. The
ready marker precedes a thirty-second sleep, permitting distinct explicit-job
termination and last-handle-close checks. The third fixture is meaningful only
after cleanup/path corrections and a newly frozen exact-source review.
