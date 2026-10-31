# Detached own-worker qualification v1 — verified result

AI engineering verification of retained evidence, 2026-10-28 UTC. No worker, Windows API, model, compiler or verifier was rerun. This verifies the exact own compiled worker and selected detached policy on the observed host; it does not qualify target ABI, scientific behavior or universal containment.

**All four declared harmless cases pass their retained requirements.** The [verification record](DETACHED-NATIVE-QUALIFICATION-V1-RESULT-VERIFICATION.json), SHA-256 `7f184e9b4d04019c6fba3bc661dabe241b7ef6a2a0ee8c713711eeeae12eb961`, checks all 140 input pins, exactly 23 files, the 61-event journal chain, 20 independently decoded raw SDK snapshots and 284 lease records over 142 paths. All 142 initial owned leases close successfully; final recheck leases are already closed. Earlier receipt, cleanup record and required terminal seal match; no primary, late or after-seal failure marker is present.

| Case | Retained observation |
|---|---|
| Resources, PID 17792 | Natural exit 0/reaped, 0.719 seconds. The 64 KiB allocation control succeeds and is released; the 384 MiB allocation fails with error 1455; exactly one deliberate descendant attempt fails with quota error 1816. Peak job commit: 995,328 bytes. |
| Overflow, PID 31260 | Capture stops at 65,536 retained stdout bytes with at least 69,632 observed; explicit exit 125/reaped, 0.953 seconds. Further output remains unknown. |
| Sleep, PID 33828 | Declared work deadline triggers; exit 125/reaped, 6.000 seconds, retaining the existing two-second cleanup reserve within the eight-second case budget. |
| Suspended abort, PID 29636 | Exact Job membership is checked, then the assigned suspended worker is stopped without any resume attempt/return or worker-start marker; exit 125/reaped, 1.719 seconds. |

All four final raw samples show total 1, active 0, terminated 0 and an empty PID list. Assigned/running samples show only each exact owned PID; no extra current PID or active-2 sample is accepted. The resources final total 1 satisfies the **prospectively declared resources-only range `[1, 2]`** in the [policy contract](DETACHED-POLICY-CONTRACT-v1.json) and [exact root decision](DETACHED-NATIVE-QUALIFICATION-ROOT-DECISION-v1.json). This is not a generic total-2 allowance. Quota error 1816 does not uniquely identify the private rejection mechanism, and the reported null failed-child fields are not independent process-identity evidence.

Every creation reservation records `0x0008040C`. The [new SDK copy](detached_parent_launch_draft_v1.py) differs from frozen SDK v3 by exactly one constant expression: `CREATE_NO_WINDOW` is replaced by `DETACHED_PROCESS`. Reversing that literal produces byte-identical source and an identical AST. Both native execution flags remain literal false. The unchanged JOB_LIST/HANDLE_LIST path uses suspended creation, exact membership/identity checks and one resume for the first three cases; suspended abort has none. No Job-breakaway flag, host allowlist, IOCP driver or arbitrary flag route is introduced. The own EXE remains SHA `0100ee6004531a41a28156385ad66fd5c0bded43c4840091a846573efe6d8e49`.

Parent elapsed time is 10.094 seconds before the early receipt and 10.312 seconds before the terminal seal, within 60 seconds. No owned cleanup or finalization error is retained. The evidence still preserves the original parent report's review-pending status; this separate verification supplies the scoped result without rewriting it.

All 17 files of the earlier C++ qualification failure, all 12 files of the consumed IOCP diagnostic and all 17 files of the Python v4 failure remain hash-identical to their retained verification records. Neither those failures nor the IOCP unknown-return accounting gap is repaired or retroactively passed. This positive detached-policy experiment does not prove why the previous extra association occurred or that arbitrary target code cannot allocate a console later.

A new exact protocol and decision are still required for target ABI. Vocabulary/document/EOG, integrated resource feasibility, model quality, fresh-case readiness and independent human/scientific evaluation remain separate gates. No reported image file, GGUF, model or protected payload was read during this review.
