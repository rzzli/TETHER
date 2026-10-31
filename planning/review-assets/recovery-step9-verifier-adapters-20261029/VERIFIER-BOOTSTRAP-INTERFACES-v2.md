# Pure interface v2 correction

V2 fixes the two reproduced ordinary interface defects. `capture` now requires
the original source-bound port before changing hash-attempt state, reserving
events or dispatching reads. Snapshot primary/error/compile diagnostics return
detached copies of all nested ordinary containers, so callers cannot change
owner records through a returned report.

The two new regression methods first failed against the saved byte-identical v1
source. V2 passes all22 synthetic methods. The retained proof shows that the
entire module AST is unchanged apart from `capture`, `snapshot` and the new
diagnostic-copy helper. V1, its20-pass proof, independent fault evidence and HOLD
remain preserved.

This remains a source/pure prototype with injected ports and synthetic bytes.
Every snapshot reports verification completion and real profile qualification
as false. It provides no real first-clock entry, production-engine integration,
live platform adapter, real evidence checker or runtime permission. No original
payload, CPU/GGUF/pack, SDK, native or compiler operation occurred. Independent
re-review is required; the original negative experiment and timed-out external
verification remain unchanged.
