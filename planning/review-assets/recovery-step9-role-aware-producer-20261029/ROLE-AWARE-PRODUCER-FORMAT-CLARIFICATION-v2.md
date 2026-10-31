# Role-aware format schema v2: finite clarification

The separately named v2 machine contract closes exactly the five groups in the preserved schema HOLD. It adds no encoder, producer, golden corpus or runtime authority.

Byte pools use descriptor record_size=1 and count=byte length in every profile, including empty and fragment query pools. Fixed tables keep their exact widths/counts. An absent fragment expected_size is None with a false presence bit and zero bits; known empty size0 is present. Input-handle atoms permit HANDLE or UNOBSERVED only, refusing NULL rather than conflating it with HANDLE0. Returned scalar NULL remains supported and distinct.

Error definition is an independent three-state atom: UNOBSERVED, observed False or observed True. It is not inferred from raw error-code presence or nonzero value. The full fourteen-API table permits True only in the declared HANDLE INVALID, DWORD0 or BOOL0 error-probe branch; defined code0 remains a known code. An applicable definition can precede a missing error return, and an undefined raw error may already be observed. These are format rules for existing declared transport, not a new error-probe export or physical call.

DecodedLedger.to_dict returns the exact canonical encode-value shape, with bytes pools/digests, list tables, tuple module_edges, typed atoms and optional None values. Getters remain detached and cache-only. FormatError exposes a string enum-name code, nonbool byte offset or None, and an internal tuple path. Optional call.error_id uses None/0xffffffff. The new BOOL atom maps to source BOOL32 without changing its signed value or normalizing nonzero results.

Packets require schema_version2 and scope role_aware_producer_format_v1. Reports require schema_version2 and format_id ROLE_AWARE_LEDGER_1 without a new scope key. Both use only OBSERVED_COMPLETE, OBSERVED_NEGATIVE or INCOMPLETE as structural data statuses, with all qualification flags false. Legacy scope/status inheritance is forbidden.

The 13,823,488 and combined 127,809,034 figures are logical reference/value-bit allowances only. They exclude ALL CPython boxed numeric payload and integer digits, object/container storage, allocator and original exception/module graphs. They establish no physical live-memory or RSS bound. Accepted F1 byte-store ownership and the vocabulary-only 256 MiB harness ceiling are unchanged; inference RAM/VRAM/KV fit remains separate and unknown.

V1 d5f28f0b, its freeze dfc9be92 and HOLD 44eee606 remain unchanged. Independent review and a literal corpus freeze still precede any encoder/producer source scope; actual source/owner/FFI/physical/full-roster/new84/resource/science gates remain open.
