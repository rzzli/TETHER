# Public-C bridge v4: exact dynamic symbol owners

Source preparation only, 28 October 2026. The consumed first fixed ABI attempt failed before its two intended queries. Its original source, executable, protocol, outputs and independent reviews remain unchanged. The [retained diagnosis](DETACHED-ABI-EXPORT-FAILURE-DIAGNOSIS-v1.md) identifies five incorrect DLL-owner assumptions. This document authorizes no compilation or execution.

The new author-owned [v4 source](typed_public_c_recognizer_v4.cpp) has SHA-256 `2f34035545c6d7bd742b8932a95449aeb76ebc48084e8dc170cbea6b740794ae`. Its only source changes are the dynamic-symbol resolver/API block and passing the already securely loaded base handle into that API constructor:

| Exact owner | Required typed names |
|---|---|
| `llama.dll` | The original15 `LLAMA_APIS`, unchanged. |
| `ggml.dll` | `ggml_backend_load`, `ggml_backend_reg_count`, `ggml_backend_reg_get`, `ggml_backend_dev_count`, `ggml_backend_dev_get`. |
| `ggml-base.dll` | `ggml_backend_reg_name`, `ggml_backend_reg_dev_count`, `ggml_backend_reg_dev_get`, `ggml_backend_dev_name`, `ggml_backend_dev_type`. |

`symbol` still performs one `GetProcAddress` against its supplied exact module handle and converts the result using the declaration's `decltype(&::function)`. Failure now reports `required_export_missing:<owner>:<name>` using only frozen owner/name literals. It performs no alternate-module search. The base handle is obtained through the existing pinned full-path loader; no new DLL, OS API, search directory or upstream implementation is added.

The ABI branch still intends only `llama_version()` and `llama_model_default_params()` calls after all25 addresses resolve. Wider address resolution is disclosed, not claimed as invocation. Recognition remains governed by the unchanged separately generated false pin-header gate; this source does not enable it. The model/CPU/grammar branches, constants, candidate handling, original document bytes, outputs and cleanup are byte-identical outside the explicitly reviewed API and constructor-call changes. The old consumed EXE has not been rebuilt or rerun.

The [seven static regression tests](check_bridge_symbol_owners_v4.py) read the exact four approved DLLs as PE data using the retained bounded PE reader class, with no module loading. They derive the25 owner/name requirements from the actual new macros and loader declarations, require every name to exist as a direct export of its declared owner, reproduce the original five wrong-owner failures, reject each wrong-owner mutation and missing/duplicate/unlisted owner controls, and verify unaffected source bytes plus original source/EXE/disabled-header hashes. The [retained proof](BRIDGE-SYMBOL-OWNERS-PURE-PROOF-v4.json) records the exact inputs. This closes static owner availability, not calling-convention or ABI safety.

Before any compiler dispatch, root and an independent peer must review this exact source/diff, proof and a **new bounded build protocol**. That protocol must preserve the consumed failed attempt, pin the new source/copy/header, retain `/MD` and the reviewed public header closure, statically inventory the resulting PE, and seal cleanup/failures. No prior build or execution authorization automatically applies. A later ABI execution also needs a separately reviewed parent/protocol with the negative-exit observation correction described in the [parent-v2 design](DETACHED-ABI-PARENT-FAILURE-OBSERVATION-DESIGN-v2.md). CPU, model, vocabulary, document/EOG and resource gates remain pending.
