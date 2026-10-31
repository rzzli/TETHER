# Source-fetch v1 peer precheck — rejected before execution

The exact unexecuted helper `49d1208f858ec0fa56b64e4fd946a4cb736b68ce12d226e8e442865ca426dcfd`
and protocol `5ce8d0cc2314f640d80b16c5d6e2f1309c6d36eefb8fb63306b0db35332a4ae4`
have a blocking parent-interruption gap. `run_child` can retain a parent
`error_class`/`interrupted` flag while the child exits successfully; `collect`
does not inspect these fields and could qualify that source and continue.
A separately frozen revision must reject both conditions and retain a synthetic
otherwise-successful interrupted-attempt check. The author independently found
this issue before any fetch; root has kept v1 unexecuted.

All **111 input pins** rehashed successfully. The retained no-network
interrupted-read fixture and its two-event journal also verified: an unreliable
zero-byte report becomes unknown receipt with its 1 MiB reservation retained;
the remaining eleven requests are stopped. This fixture does not exercise the
separate parent-interruption defect.

No additional material defect was found in the fixed twelve-path identity,
redirect/proxy exclusion, retained-body reservation, exclusive output,
`lstat`/reparse ancestry checks, isolated fixed child dispatch, capture caps,
owned kill/reap, full-process deadline check, partial receipts or terminal
failure veto. Source/receipt byte bounds describe retained bodies, not measured
network transfer. Aggregate timing relies on cooperative checkpoints around
local filesystem operations; this is not an OS sandbox.

[The companion JSON](SOURCE-FETCH-PEER-PRECHECK-v1.json) records exact anchors and
scope. This review imported/executed no helper and made zero requests, fetch
children, native calls or GGUF reads. It does **not** clear v1 for execution.
