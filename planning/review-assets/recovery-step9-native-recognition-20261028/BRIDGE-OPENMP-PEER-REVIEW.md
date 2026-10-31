# Narrow static peer review: required OpenMP dependency

28 October 2026. **The v1→v2 OpenMP source correction is clear for root's separate build-preparation review. No build, ABI experiment or runtime execution is approved by this note.** No material blocker was found in this narrowly scoped delta.

Scope honesty: this reviewer authored the original v1 bridge and the later v3 pack/layer correction. Another agent authored the v2 OpenMP change. This is an independent review of that agent's **OpenMP delta only**, not an independent whole-bridge review or clearance of this reviewer's v3 work. The existing v1 whole-source peer review and separate prospective v3 review retain their own scopes. The known version1-pack raw-NUL eligibility hold is not closed by OpenMP handling.

Local file hashes were rechecked. Source references below are one-based lines in `typed_public_c_recognizer_v2.cpp`:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Original `typed_public_c_recognizer.cpp` |47,485| `3f7e13ec7695bd5257e3e58d627ae71c1a2cdcaea7dbec8aad869424a0f5188b` |
| OpenMP `typed_public_c_recognizer_v2.cpp` |48,060| `29a863cb3a7a04d877953f895e4e831a43ce992352f07dc210a51c83c744737c` |
| Original `BRIDGE-DRAFT-DESIGN.md` |19,551| `2bb222d6830a52513fab88c1db29b0d5b7cc093d5357ff224f3d3a42b2f8431b` |
| OpenMP `BRIDGE-DRAFT-DESIGN-v2.md` |20,904| `746b726a3841ee50cd8c34c8961e473fab95110af644ce6cfc7db3a2b80e38d8` |

All paths are in `D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028`. The review compared exact source/design bytes using a no-index text diff and read the unchanged lease/load helpers. Git's difference exit status1 denotes a nonempty diff here, not a failed compiler or runtime test.

The reported prerequisite is that the pinned `ggml-base.dll` imports `libomp.dll`. The producer/root performed that static PE work. This review **did not reparse DLL bytes**; it verifies correct conditional handling in source. The parent must bind `R09_LIBOMP_REQUIRED` to the reviewed exact PE closure and bind the actual OpenMP bytes in its generated pin header. The source flag alone is not evidence of an import or permission to widen the dependency set.

The source delta has the intended restrictions:

- **Conditional allowlist:** line165 permits exact case-insensitive `libomp.dll` in either mode only when `R09_LIBOMP_REQUIRED` is true. It does not add other DLL names or CPU variants. `ggml-cpu-x64.dll` still requires `recognition=true`; `Runtime` begins with that flag false (168).
- **Required pin:** line175 rejects a true requirement flag without the exact OpenMP pin. Existing pin syntax/size/name/duplicate validation remains in172–174. With a false requirement flag, an extra OpenMP pin does not silently enlarge the valid list because172 calls the restricted allowlist.
- **Hash/read lease before load:** `load_core` at179 now permits only a core name or the conditionally required exact OpenMP basename. It rejects an already loaded basename, calls `lease` first, and then loads the full runtime-root path. `lease` at178 obtains the exact header pin and verifies size/SHA; the unchanged `Lease` at125–135 rejects reparse paths, opens `GENERIC_READ` with `FILE_SHARE_READ`, and streams SHA-256 under that live handle. The handle remains owned in the runtime lease vector. No new null/size/hash bypass was introduced.
- **Secure explicit order:** line366 conditionally preloads OpenMP **before** line367 loads `ggml-base.dll`, `ggml.dll` and `llama.dll`. The reused load path uses `LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32`, checks the resolved module path and process-pins the exact handle (179). It does not use a basename search, discovery, a fallback OpenMP path or load-all API.
- **Module inventory remains restrictive:**185–190 require the exact runtime directory/pin and mode allowlist for OpenMP, while `core_name` remains the same three DLLs (164). Thus the required dependency does not turn the three-core count into four or excuse a CPU DLL in ABI mode. Unknown non-runtime modules still require the exact parent System32-name/path list.
- **ABI caller path remains narrow:**363–375 add only the dependency preload. The ABI branch still records observations from `llama_version` and typed defaults, and does not call the bridge's backend registry/device/init/model/tokenizer/grammar paths. `recognize` remains reachable only from the other mode (375). Function-pointer resolution is not a registry call.

The design correction accurately distinguishes explicit bridge calls from dependency initialization. `LoadLibraryExW` can execute OpenMP/core `DllMain` or other dependency initialization even in ABI mode. Neither this code nor this review proves zero native-package initialization, no threads/devices, safe OpenMP behavior, complete DLL-source correspondence, or general OS module-injection prevention. Root still owns exact runtime/header/compiler/pin identities, static imports/System32 prediction, ABI authorization, Job/time/memory/capture/reaping, loaded-module checks and all runtime-result qualification.

No file under review was edited. This reviewer performed only text reads/diffs and local source/design SHA-256 hashing for this task; no helper/oracle import or execution, compilation, DLL loading/PE-byte parse, GGUF/model/tokenizer/server call, network request, biological outcome/label read or human-file read occurred. The companion JSON records this exact conditional clearance and scope limits.
