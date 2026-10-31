# Verifier recovery v2: source and pure correction

The root-approved successor preserves v1 and its HOLD. The saved v1 witness
has three unsafe-close failures for a null return, a foreign object and a typed
null handle; the late valid-owned return control passes. V2's 23 synthetic
methods pass, including those ownership boundaries and the factory records.

| Observed return | Cleanup ownership | Disposition |
| --- | --- | --- |
| Exact `OpenReturn`, `owned is True`, non-null handle | Registered immediately before clock or metadata checks | Close once, including a late return or later metadata failure |
| Exact `OpenFailure` | No handle transferred | Known original I/O failure; incomplete |
| Null, foreign object, typed null or invalid ownership flag | No guessed handle | Observed malformed ownership; unknown and incomplete |

The future live port must validate platform-specific handles and normalize them
before minting the typed ownership acknowledgment. The platform-neutral engine
does not interpret raw native handle values. A malformed return may conceal an
untransferred resource; its unknown state is retained rather than claiming
cleanup or attempting a guessed close.

Authority, file-port and checker factories now use the existing stage machinery
after exclusive output reservation. Each has a durable attempt reservation;
its returned state is recorded before a throwable clock check. These six added
events fit the unchanged fixed allowance of 64. The joint 256-file/2,048-event
budget remains 1,728 reserved slots, including failure headroom.

The changed owner methods are initialization, open/hash bookkeeping, result
reporting and the added known-I/O status in finalization. The retained proof
records equality of every other owner method. The fixed gates, 300/295/5 clock,
immutable context, once-only cleanup and terminal veto behavior are preserved.

This remains orchestration tested with synthetic bytes, clocks, ports and
checkers. It provides no live adapter, real first-clock bootstrap, CLI or actual
archive/core qualification. No old original, CPU/GGUF/pack, SDK, target or compiler
operation occurred. The previous real verification timeout remains incomplete.
Independent review is required; the author does not self-approve the component.
