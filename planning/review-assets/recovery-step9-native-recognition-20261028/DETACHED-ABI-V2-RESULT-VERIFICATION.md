# Corrected fixed ABI attempt: retained negative verified

28 October 2026 UTC / 28 October Los Angeles. AI read-only engineering evidence verification; not human scientific review. **The once-only corrected ABI attempt failed closed on `unapproved_non_native_module`. Its failure, terminal observations and ownership records are internally consistent. No ABI/version/default or native-recognition qualification passes.**

The [verification JSON](DETACHED-ABI-V2-RESULT-VERIFICATION.json), SHA `4b2a3cd7b09c14a8dc3d444ea6e815c8fefeeb9952cfa9724615af77769e9c24`, was produced by the retained [read-only verifier](verify_detached_abi_v2_retained.py). It independently rehashes the exact 202 approved inputs, checks the output universe and receipts, reconstructs the journal hash chain, decodes SDK raw buffers and reconciles lease closure. This review launches no child, calls no SDK/target API, loads no native library and reads no GGUF. Approved input binaries are read for hashes; the unknown module is neither guessed nor opened.

| Evidence | Verified result |
|---|---|
| Protocol / root decision | `58154061a1a2dff9e3369a01662cb2b8be601012ba16c2b694f98255067adf6d` / `077108c22c3642271f282e527ac02957b74117ad3b161a5d8e6c5fd52e788978` |
| Exact output universe | 13 files, two subdirectories; 10 early-receipt outputs and 12 terminal-seal outputs agree |
| Journal | 17 events; chain tip `7b734048a5654cb159c6d52b3f95324ddfa0e7e31d0b0a50b63f9670f12ec325` |
| Owned process | PID 37796, one suspended creation/one resume, flags `0x0008040C`, exit 2, reaped, 0.234 seconds |
| Raw Job samples | Empty; suspended sole PID; first-running sole PID; final total 1 / active 0 / terminated 0 / empty PID list |
| Capture | Stdout 62 observed/retained bytes, stderr zero; both physical EOFs observed, neither truncated |
| Memory | Process and Job commit limits 268,435,456 bytes each; both measured peaks 2,166,784 bytes |
| Terminal observation | Complete bounded observation after observed owned exit and before cleanup; three call reservations, one capture poll, no observation errors |
| Original-path leases | 408 records over 204 unique paths; 204 final rechecks completed; all 408 final close outcomes retained without error |
| Finalization | Primary failure unchanged, no cleanup/finalization error, no late failure marker; required failed seal at 0.891 seconds |

The child retains `attempt.json`, `failure.json` and a two-row `result.partial.jsonl`: an OpenMP initialization warning marker followed by the module-policy failure. It does not retain `result.jsonl`, a module inventory, layouts, a version value or typed default values. `terminal_observation.complete=true` means its independent bounded EOF/Job/memory observations completed; it does **not** override the primary error or the failed receipt/seal.

Source SHA `2f34035545c6d7bd742b8932a95449aeb76ebc48084e8dc170cbea6b740794ae`, [line 188](typed_public_c_recognizer_v4.cpp#L188), names the module-policy rejection. At [line 377](typed_public_c_recognizer_v4.cpp#L377), successful `Api` construction precedes the rejected inventory expression; the first explicit version query follows at line 378 and the default query at line 382. This supports **source-derived** completion of the corrected export-resolution constructor and zero subsequent explicit version/default calls in this failure path. Actual call counters are not instrumented, and the committed inventory row is absent. It does not provide an observed complete module census or establish typed ABI compatibility.

The rejected module's name, path, hash and origin remain unavailable. DLL/CRT/OpenMP initialization may have effects; those effects were not instrumented. The next prospective diagnostic must retain bounded module identity before rejecting it, under a separately reviewed source/build/protocol. The failed attempt stays unchanged; no guessed whitelist entry, arbitrary module search, automatic repeat, CPU backend, model or vocabulary work follows from this result.
