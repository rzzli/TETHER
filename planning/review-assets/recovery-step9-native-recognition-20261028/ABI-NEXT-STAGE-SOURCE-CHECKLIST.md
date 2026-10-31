# Next ABI stage: source-only checklist

This is a preparation checklist, not an execution protocol or an ABI result. The harmless v4 launcher qualification is prepared and awaiting independently verified execution. The consumed harmless v3 failure remains retained. No ABI parent may be enabled or dispatched until the v4 gate passes and a separately pinned ABI-only role receives exact-source review and a root decision. The original [SDK draft](abi_parent_launch_draft_v3.py) remains hard-disabled; its flag must not be toggled.

## 1. Bind the existing compiled input

Use the existing build, without recompilation or a fallback executable:

| Input | SHA256 |
|---|---|
| `data/cache/r09-public-c-bridge-build-20261028T175036Z/typed_public_c_recognizer_abi.exe` | `9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696` |
| Build receipt | `ebae856c74554b200b8d486cc5ce958fa530dc75499035bf82a9133114ae7c72` |
| [BUILD-PROTOCOL.json](BUILD-PROTOCOL.json) | `5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e` |

The exact ABI argv is `[EXE, "--abi", approved_runtime_directory, new_empty_child_output_directory]`. It supplies no model, corpus, tokenizer, grammar or GGUF argument. Bind the copied source, generated pin header, build inputs and complete approved runtime provenance retained by the build; do not silently trim its broader provenance set to the four DLLs used by ABI mode.

## 2. Preserve the narrow native call path

The [author-written bridge](typed_public_c_recognizer_v3.cpp:363) loads the following four files from `data/cache/approved-native-mirror-20261028T004531Z/runtime`, by full path, with restricted DLL search and per-file leases/hashes:

| Actual ABI dependency | SHA256 |
|---|---|
| `libomp.dll` | `a12116ba72d1d6820407cf30be23da04ce79d6bb8a71a5ee71759c5a1faa6f1c` |
| `ggml-base.dll` | `84e3057e6fe2c581a9d194d27e5510b1a71723074e01dfb9b34926e4d5af52f3` |
| `ggml.dll` | `2a49a0f2d3c58b182bfa5267950cef2e4f3378a12e9ebbc6b36554bf5ca016ba` |
| `llama.dll` | `166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d` |

Typed exports are resolved through exact public declarations. The ABI branch calls only `llama_version()` and `llama_model_default_params()`. Backend registration/init, CPU backend loading, model/vocabulary loading, tokenization, grammar sampling and inference remain later stages. Merely resolving their export addresses does not execute those APIs. Loading these four DLLs can execute their native/CRT/OpenMP initializers; the branch's call flags are source-level observations, not independent instrumentation of all native behavior.

## 3. Review a new finite parent role

The prospective parent should reuse the unchanged SDK launch/capture/cleanup logic through a separately reviewed ABI-only constructor and role. Preserve `JOB_LIST` membership at creation, suspended validation before resume, three inherited standard-I/O handles, and raw Job observations. ABI accounting remains exact total 1; the harmless resources final-total-2 exception must not propagate.

Retain the declared parent 60 s / child 30 s limits, cleanup reserve, 256 MiB process/Job commit caps, active-process limit 1 and 64 KiB stream caps. Bind the independently verified actual harmless result, exact environment/helper/build/runtime pins and decision before reserving one new output. Use durable attempt/dispatch records, no retries, owned-process cleanup, post-lease sealing and an authoritative failure veto. This changes no scientific case budget.

## 4. Independently qualify the returned artifacts

Require natural exit 0, complete reaping and cleanup, no failure/partial artifact, and the exact child files `attempt.json` and `result.jsonl`. Enforce the existing 4 KiB attempt, 4 MiB JSONL and 64 KiB row limits, strict JSON, and the five ordered events: OpenMP dependency load reservation; exact core modules/exports; typed version/defaults; ABI observations; normal completion. Compare actual module paths/hashes, layout sizes/offsets and every default field with the compiled pin/source obligations.

The version is presently unknown: the build's expected-version string is empty. Require a nonempty printable-ASCII observation of at most 256 characters and retain the exact value; do not infer it from a release tag. The child must report all backend/registry/model call flags false and parent qualification required. Any new recognition build must separately bind a reviewed version observation. A successful ABI observation is not tokenizer/EOG/grammar conformance, resource qualification of vocabulary loading, or scientific validation.
