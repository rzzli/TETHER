# Explicit CPU registration: bounded source assessment

AI engineering review, 2026-10-28 UTC. This reviews local source text at revision `848bbda9041decd87904f7eb5a2990863ecce03b`. The two newly retained files are `ggml-backend-dl.h` (791 bytes, SHA256 `225bd83a197c4e8b5f985717176824d1144e2b74a79f04838f51b84115c14dc5`) and `ggml-cpu.cpp` (25,005 bytes, SHA256 `ccf382d3fbf126b5ddb5850a0a970656fb24e00587da4003419439277c91cd01`). Their [result verification](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/BACKEND-RESULT-VERIFICATION.json) and [structured assessment](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/EXPLICIT-CPU-REVIEW.json) retain exact provenance.

## Conclusion and scope

The inspected source supports a finite experiment using one exact CPU library, a strict sole-CPU registry check, and then `llama_backend_init` without entering its automatic discovery branch. This conclusion is conditional on the registry actually remaining nonempty and on the pinned release implementing the reviewed interfaces. It does not establish source-to-binary build identity, zero GPU API activity, complete side-effect auditing, general DLL search safety, dependency unload, ABI conformance, or grammar correctness.

No known unsafe action requiring a change to the proposed scope was identified. The known side effects and delegated internals below must be accepted explicitly in a separate runtime protocol. **Source acquisition stops here.** No further include crawl, private-source compilation, source download, backend invocation, or experiment was performed or authorized by this review.

## What explicit loading does

The retained [registry implementation](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/ggml/src/ggml-backend-reg.cpp:220) shows `ggml_backend_load(path)` calling `get_reg().load_backend(path, false)` (393–394). `load_backend` passes that exact path to `dl_load_library`, optionally invokes `ggml_backend_score`, resolves the exported `ggml_backend_init`, invokes it, checks the backend API version, then registers the result and retains the library handle (220–263).

That explicit path does not call the `load_best` directory-scanning routine or `load_all` in the reviewed source. However, it still executes library loading and provider code before a registry-name check can run. The first `get_reg()` also constructs its conditionally compiled registry (119–174, 292–294). Compiled providers, release build flags, PE imports, DLL initialization, and actual loaded module paths therefore remain relevant. A post-load CPU check can detect a mismatch and stop later work; it cannot prove that no earlier unapproved side effect occurred.

The new [dynamic-loader header](D:/Projects/drug_target_agents/data/cache/r09-native-backend-source-20261028T165636Z/sources/ggml/src/ggml-backend-dl.h:19) defines a unique-pointer handle whose Windows deleter calls `FreeLibrary` (19–26). It only **declares** `dl_load_library`, `dl_get_sym` and `dl_error` (42–44). Their bodies, search flags, error details, and transitive dependency behavior remain uninspected. The CPU file invokes `GGML_BACKEND_DL_IMPL(ggml_backend_cpu_reg)` at 719; the export macro's definition is also outside the retained subset. Neither is silently treated as inspected.

## CPU provider behavior visible here

The provider's registry name is exactly `CPU`, and its reported device count is one ([ggml-cpu.cpp:514](D:/Projects/drug_target_agents/data/cache/r09-native-backend-source-20261028T165636Z/sources/ggml/src/ggml-cpu/ggml-cpu.cpp:514), 514–536). Its device name is also `CPU`; its device type callback returns `GGML_BACKEND_DEVICE_TYPE_CPU` (353–388). `ggml_backend_cpu_reg` calls `ggml_cpu_init()` before returning a static registry (706–716). That feature-initialization body is not in this file. No claim is made that it is free of allocation, CPU instructions, synchronization, threading, or other effects.

Registering this provider enumerates its one device in the existing registry code (backend-reg.cpp 201–204). The device constructor has a known Windows side effect: it opens the read-only CPU-description registry key, queries `ProcessorNameString`, stores a description, and closes the key (CPU file 289–350). This is a hardware-description read, not network or model I/O.

Registration is distinct from creating a compute backend. The separate `ggml_backend_cpu_init` function allocates a CPU backend/context and initializes threadpool/work fields (217–244). The device's `init_backend` callback calls that function (404–405), but registration itself does not invoke that callback in the reviewed path. The proposed vocabulary recognizer must not request compute-backend construction, a threadpool, context, graph or decode. Avoid feature-procedure enumeration as an unnecessary extra path; its feature function calls CPU initialization again (541–543).

## Why the public initializer can avoid discovery

The public header directs callers to initialize once. The exact [initializer body](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/src/llama.cpp:122) initializes timing, creates/frees a tiny GGML context, and calls `ggml_backend_load_all()` only when `ggml_backend_reg_count()` is zero (122–134). After a successful explicit CPU registration, require:

1. The returned registry is non-null and is the sole registry entry.
2. Its name is exactly `CPU`, its device count is one, and that device has CPU type.
3. No other registry modification is performed by bridge code between these checks and initialization.
4. After the single initializer call, the same registry pointer, count, name and device identity remain unchanged.

Under the inspected control flow and that nonempty-registry condition, initialization skips `load_all`. `load_all`, `load_all_from_path` and `init_best` must remain forbidden, with no fallback when explicit loading fails. The general discovery routine otherwise scans multiple backend families and considers `GGML_BACKEND_PATH`; restricting only its directory would not make it CPU-only. The proposed child environment should remove that and other unapproved backend environment settings even though this explicit-load route does not use them.

The reviewed vocabulary-only settings remain essential: native default struct, `vocab_only=true`, non-null empty device array, split NONE, GPU layers zero, main GPU minus one, load mode NONE, lazy OFF, no-allocation, no tensor validation, and no optional overrides. The no-allocation parser still allocates potentially large metadata; its source limits are not an experiment memory cap. The source-level initialization conclusion does not change the earlier resource-fit or scientific gates.

## Finite runtime qualification boundary

The root may separately qualify a bounded experiment against trusted, exact pinned release DLLs while explicitly accepting the uninspected implementation bodies. Before any such call, the protocol must bind the own-code bridge, public headers, exact CPU/base/core module hashes, model shard hashes, case corpus and result schema. Build-source identity must remain separate from the binary identity observation.

The root's proposed containment is an OS job/memory limit in effect before the first target load, a single owned process with an enforced deadline, fixed system DLL search policy, absolute pinned module loading through bridge-owned `LoadLibraryEx`, and before/after module inventories. The exact implementation of those controls still requires review and harmless fault checks. `SetDefaultDllDirectories`/absolute paths and pinned preload ordering are experiment controls, not a proof of every delegated loader path. Module initialization executes before post-load inspection; disallowed loaded modules or registry changes must fail and preserve evidence immediately. No automatic alternative backend, repaired corpus, budget increase, retry, or inference is introduced.

The source acquisition helper's successful PID transport and capture caps are useful evidence, but they do not themselves implement native-process memory isolation. The native protocol needs its own effective memory, process, time and output limits, including startup/CPU initialization, and must retain failures. No zero-weight OS I/O claim should be made: future whole-shard hashing and CRT/OS read-ahead are distinct from skipped explicit tensor-blob reads.

## Lifetime and remaining guarantees

The CPU registry/device are static objects. The accepted dynamic handle is held by the global registry. The registry destructor deliberately releases retained handles without unloading, because backend threads may still use them (backend-reg.cpp 176–183). Although its explicit unload routine removes devices and erases an entry (266–288), this review does not recommend using it as proof of safe dependency teardown. `llama_backend_free` only calls quantization cleanup in this revision. Free grammar samplers before model-owned vocabulary, free the model, perform the paired backend cleanup, and end the bounded process; do not report complete library unload.

The next possible gate is preparation and review of a typed public-C bridge and its finite execution protocol. It remains separate from actual native execution, ABI round-trip, grammar/EOG recognition, practical resource fit, model quality, clinical evaluation, human review, and freshness. Those statuses remain unchanged.
