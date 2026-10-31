# Frozen entry integration static review

HOLD for one concrete interface defect. No subject was imported or run, and all three frozen source pins remain unchanged.

`preflight_owner_ops_v1.py:132` invokes `self.sink.close_journal(ack, hard_end)`. The canonical `SinkFacade` in `preflight_entry_kernel_v1.py:146` exposes `append`, `close` and `publish`, without `close_journal` or a fallback. Owned finalization therefore encounters `AttributeError` before the backend close callback, after consuming the journal-close attempt. The retained close ACK stays false; receipt, seal and pure completion cannot follow.

The smallest successor should align that one facade/call spelling while preserving the same backend object, ACK facts, original-clock checks and once-only attempt. Root must choose the correction and first-evidence ordering; this review changes no frozen source or oracle.

The remaining finite source pass found matching Core/delegate methods, immutable non-owning views, captured table18 identity checks, role/capture and context restrictions, canonical raw/cache ownership, signed-BOOL close semantics, retained late ACK projections and guarded final snapshot issuance. These are static findings, not execution evidence. The reviewer authored the kernel and did not author Ops/FileView; Native's independent full-source/harness review is separate.

Real entry, native/FFI, physical I/O, full roster, new84 execution, RSS/resource fit and science remain unqualified.
