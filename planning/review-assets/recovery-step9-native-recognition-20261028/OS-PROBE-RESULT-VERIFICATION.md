# OS-only result: narrow checks verified, accounting remains unresolved

All sixteen retained artifacts match the inspected source and decision.
The three worker identities agree with their assigned PIDs and owner PPID;
captures are empty, and all owned process handles are recorded reaped and closed.
Configured flags are `0x2108`, process commit cap **64 MiB** and active-process
limit **one**. The resource fixture reports MemoryError for its 96 MiB allocation
and quota error **1816** for descendant creation. Explicit termination returns
**87**; last-handle closure promptly reaps its ready sleeping worker with exit
**0**, which the prospective fixture permitted.

**Two raw accounting observations need explanation.** Both `timeout` and `close`
record `active_processes=2`, `total_processes=2` before termination, despite
`active_limit=1` and no intended descendant attempt in those modes. Initial
assignment was checked as one; post-reap queries return zero where retained.
The peer has not established whether this reflects OS semantics, measurement
or parsing behavior, or additional processes. It must not be silently normalized
or treated as proof the active count never exceeded one.

[The verification record](OS-PROBE-RESULT-VERIFICATION.json) preserves all raw
hashes, queried values, identities and the unresolved observations. Source report
SHA256 is `2b35761da99681ffb84995590c8199f58d45289167665905557df01ba1ce0f38`.
Retain the narrow configuration/rejection/owned-handle results, while holding
unqualified future-native containment claims pending explanation of the counters.

Per-attempt reported times are 0.093, 0.094 and 0.078 seconds; root's full tool
measurement is 0.829 seconds. No timing was rerun. The cap concerns per-process
commit, not working set or a universal job-memory bound. This is not native DLL,
model, GGUF or general process-tree qualification. The peer performed no probe,
Windows API, network or target-native call.
