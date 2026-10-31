# Current-run rejected-module diagnostic: retained negative verified

29 October 2026 UTC / 28 October Los Angeles. AI read-only engineering verification; not independent human scientific review. **The once-only diagnostic remains failed on the unchanged module policy. It reports `apphelp.dll` at the lexical path `C:\Windows\SYSTEM32\apphelp.dll` in this new run. This review opens no file at that reported path and establishes no image authenticity, full module inventory or historical identity.**

The [verification JSON](DETACHED-ABI-V3-RESULT-VERIFICATION.json), SHA `a92b92376c090401a70fd5ab0e699d0bd02b478b1d3490b9a64817d30cc34221`, is produced by a new [retained-data-only verifier](verify_detached_abi_v3_retained.py). The previous verifier and actual attempts remain unchanged. Approved input files are read for hashes; before hashing, this reader rejects a reported `apphelp.dll` image path from its input universe. It launches no experiment child, calls no SDK/target API, loads no library and reads no GGUF or protected answer payload.

| Evidence | Verified result |
|---|---|
| Protocol / root decision | `88672320d5969c5dbd32e265155353f31b187b51aeaad39396f40788fdda1fb8` / `40978ab1f166c29a7e52c835fb921c2543bf9eead5138fd97d6881fde204ac69` |
| Inputs / output universe | 243 unchanged approved input pins; exactly 13 files in two subdirectories |
| Journal | 17 events, one creation/one resume; tip `6513f62e2d72e6fb964fed75a671378aad5a20207cb26acca644a7b306dd84dd` |
| Owned attempt | PID 21828, flags `0x0008040C`, exit 2/reaped after 0.234 seconds |
| Raw Job | Empty, sole suspended PID, sole running PID, then final total 1 / active 0 / terminated 0 / empty PIDs |
| Captures | Stdout 939 bytes, stderr zero; both EOFs observed, neither truncated |
| Memory | Process/Job commit limits 268,435,456 bytes; measured peaks both 2,166,784 bytes |
| Leases | 490 close outcomes over 245 unique paths; all 245 final rechecks completed without error |
| Terminal observation / seal | Complete bounded EOF/Job/memory observations; no secondary errors; required seal remains failed at 0.953 seconds |

The child has three retained partial rows: the OpenMP initialization marker, `module_policy_rejection`, and the failure. No final `result.jsonl`, complete inventory, layouts, version or defaults observation exists.

The context has enumeration index 5, strict Boolean `system_directory_matches=true` and `system_basename_listed=false`. The name has 11 UTF-16 units and the path 31. Both prefixes are complete, with neither truncation nor surrogate-boundary adjustment. The verifier decodes each four-digit hexadecimal group as a **numeric UTF-16 code unit**, reconstructs the sequence and checks exact equality with the optional UTF-8 strings. This is not decoding a little-endian buffer hex dump, and no normalization is applied.

The diagnostic event records publication `attempt_reserved`; the retained failure marker and stdout record `returned`. Their remaining contexts match exactly, and the complete diagnostic row exists in the hashed partial stream. The strict rejection predicate is consistent with the unlisted basename. These observations describe reported current-process metadata and its publication, not file/signature identity or a complete census.

Pinned source places `Api` construction and the module enumeration before the explicit version/default queries. Zero subsequent explicit queries is a **source/control-flow inference**; counters are not instrumented and dependency initialization may have effects. A complete observed module row is still unavailable. The initial two failed experiments remain distinct: all 13 outputs of the preceding v2 failure were rehashed unchanged, and **its offender remains unknown**. The new reported name cannot be backfilled into that earlier run.

The next step is bounded policy-evidence review of this new observation. No allowlist entry, image-file read, alternate binary or additional execution is authorized by this verification.
