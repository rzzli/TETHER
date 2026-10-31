# Fixed ABI failure: static export-owner diagnosis

The consumed first ABI attempt failed while resolving functions from the wrong DLL. **All15 required `llama_*` names exist in the pinned `llama.dll`; five of10 `ggml_*` names were searched in `ggml.dll` but are exported by the already-approved `ggml-base.dll`.** This review loaded no DLL, invoked no target API, compiled no code and read no GGUF. Original attempt bytes are unchanged.

| Required name | Frozen requested owner | Actual direct export owner |
|---|---|---|
| `ggml_backend_reg_name` | `ggml.dll` | `ggml-base.dll` |
| `ggml_backend_reg_dev_count` | `ggml.dll` | `ggml-base.dll` |
| `ggml_backend_reg_dev_get` | `ggml.dll` | `ggml-base.dll` |
| `ggml_backend_dev_name` | `ggml.dll` | `ggml-base.dll` |
| `ggml_backend_dev_type` | `ggml.dll` | `ggml-base.dll` |

All five actual exports are direct functions rather than export forwarders. The other five GGML requirements are present in `ggml.dll`. The retained machine report gives all25 names, exact export ordinals/RVAs, module hashes, counts and import tables. The unchanged source eagerly resolves the15 llama names, then the10 GGML names. Its first wrong-owner lookup is `ggml_backend_reg_name` (source lines195–207). Therefore the code path stops before either `llama_version()` or `llama_model_default_params()` is invoked. Their observed results remain unavailable. DLL/CRT initialization may already have run; source ordering is not an intercepted-call or complete module-side-effect audit.

The local acquisition metadata identifies runtime tag `b11717`; the source inventory records tag `b11717`, full commit `848bbda9041decd87904f7eb5a2990863ecce03b` and previously observed runtime short commit `848bbda90`. These agree at the recorded tag/commit level. The reviewed headers and exact own-source copy were used by the successful MSVC x64 `/MD` build. This does not establish reproducible compiler/dependency equivalence for the vendor DLLs. The exact approved PE exports, rather than the header filename or a function-name prefix, establish the module-owner correction.

The build and static checks missed a real preflight requirement. `decltype(&::function)` verifies available header declarations and function types, while `GetProcAddress` resolves string names at runtime. The linker sees no ordinary upstream function import and cannot reject the incorrect owner. Existing static PE checks verified the bridge's imports and allowlist; they did not match every dynamically requested name to its specific pinned DLL. Synthetic strict-parser/lifecycle tests also did not establish export availability. This is a local integration error, not evidence that the public functions are unavailable from the release.

The smallest prospective correction is a **new versioned source/build** with explicit DLL-owner tables:15 llama names in `llama.dll`, five registry enumeration/load names in `ggml.dll`, and five registry/device inspection names in `ggml-base.dll`. Pass the already securely loaded base handle into the typed API object. Missing-symbol diagnostics should identify both exact owner and name, with no module-search fallback. Retain the two intended ABI calls, disabled recognition and original25 typed requirements. Before compiling, statically regression-check the complete new mapping against the exact PE exports, including a wrong-owner negative. A separate two-function ABI object with deferred recognition binding is possible but changes more behavior than needed.

The consumed negative-exit parent currently stops normal validation before the final Job/peak/capture-EOF observations. Those values are unavailable for this attempt; later parent correction must preserve this fact, retain the primary failure and add bounded error-path observations before closing handles. It must not alter the qualified SDK or relabel the failed attempt.

Evidence: [machine diagnosis](DETACHED-ABI-EXPORT-FAILURE-DIAGNOSIS-v1.json), SHA-256 `639266a36340fbc4124b254d2fcff03d8a2564c28dbb64eccdd8b17f87ced388`; [independent static crosscheck](ABI-EXPORT-STATIC-CROSSCHECK-v1.json). Actual full result integrity is reviewed separately. No rerun, new build or later native/document/EOG gate is authorized here.
