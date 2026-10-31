# Static loader and backend qualification

AI engineering source review, 2026-10-28 UTC. This is neither a scientist review nor execution authorization. The exact upstream revision is `848bbda9041decd87904f7eb5a2990863ecce03b`. Files were read as text; no compiler, DLL, GGUF parser, tokenizer, model, backend, or server was run. The source acquisition receipt is `cf2a70a3488d4dd96320d893a22e1b7706d6f913e8f5f238c9e68d4de1405f90`. Individual source hashes and structured findings are retained in [LOADER-BACKEND-REVIEW.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/LOADER-BACKEND-REVIEW.json).

## Decision

The inspected caller path skips `load_tensors` when `vocab_only=true`. This establishes ordering in these source files, not an end-to-end zero-weight-read, bounded-memory, CPU-only, or binary-conformance guarantee. Device preparation runs before the vocabulary-only return. The default initialization helper can discover and load multiple backend families. The GGUF parser, file helpers, resource-owning aliases, and architecture-specific constructors delegate behavior to files outside this reviewed subset.

Minimum conservative **prospective** parameters are identified below. Initialization and delegated file-I/O behavior remain prerequisites; this review does not approve a native invocation.

## Loader path and ordering

1. `llama_model_load_from_file` creates an empty split list; the explicit-splits API copies the supplied ordered paths. Both call the same implementation. Exactly one of metadata, filename, or `FILE*` must be supplied. The no-backend rejection is conditional on `!vocab_only`; it is skipped for vocabulary-only loading. See [llama.cpp:380](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/src/llama.cpp:380), lines 380–444 and 466–496.
2. `llama_model_load` constructs `llama_model_loader` first, assigns its lazy mode, prints metadata, creates the architecture-specific model, and prepares devices. Only then does it set `hparams.vocab_only`, load hyperparameters, load vocabulary, copy statistics, print model information, and return before `load_tensors`. See [llama.cpp:315](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/src/llama.cpp:315), lines 315–376. Model creation delegates to the architecture factory at model.cpp 371–390; its selected derived constructor is not established by this subset.
3. The loader constructor receives no `vocab_only` argument. It calls `gguf_init_from_file` with `no_alloc=true` and a non-null context pointer, opens a `llama_file`, walks tensor descriptors, and constructs a weights index. If metadata declares multiple shards, it opens and parses every additional shard before returning. Missing/duplicate tensor names, wrong shard numbering/count, or total tensor-count mismatch fail. See [llama-model-loader.cpp:533](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/src/llama-model-loader.cpp:533), lines 533–675. Thus vocabulary-only does not mean “open only the first shard.” Use the complete pinned ordered shard list; reject unexpected inputs rather than permit filename inference.
4. Generic hyperparameter loading copies scalar metadata, processes optional Hadamard metadata, and loads the general name before its own vocabulary-only return (model.cpp 1357–1379). Vocabulary loading delegates to `vocab.load`; statistics merely copy counts (1352–1354, 1572–1575). Vocabulary construction and its memory cost belong to the separate vocabulary review. The Hadamard path reads/validates metadata arrays; it is not omitted solely by `vocab_only`.
5. The skipped tensor path contains buffer selection, CPU-device requirements, tensor construction, mapping initialization, backend buffer allocation, and tensor-data loading. Mapping initialization is model.cpp 1890; data loading is 2026–2029. The loader's explicit file seek/read and mapping access are at 1531–1543 and 1699–1806. These caller sites are unreachable after the vocabulary-only return. The body of `gguf_init_from_file`, `llama_file`, and the weights-index constructor is not retained here, so absolute zero weight-range reads remains unverified.

`no_alloc=true` alone is not equivalent to this early return: the later no-allocation branch returns at model.cpp 2014–2016, after mapping initialization and dummy backend buffers. `load_mode=NONE` and `lazy_mode=OFF` remove two mapping routes if the tensor path were entered, but do not replace the required `vocab_only` gate. Lazy OFF means eager tensor reading when tensors are loaded; it is not a standalone “never read weights” switch. See [llama-model.cpp:1578](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/src/llama-model.cpp:1578), lines 1578–1631 and 1866–2039, and loader.cpp 1411–1440.

## Devices, initialization, and discovery

The actual default struct has `devices=nullptr`, `n_gpu_layers=-1`, layer splitting, AUTO load/lazy modes, `main_gpu=0`, `vocab_only=false`, extra buffer types enabled, and `no_alloc=false` (model.cpp 3347–3368). Negative GPU layers mean all layers in the public header. Changing only the vocabulary flag retains default device-selection behavior.

A **non-null pointer to a one-element null device array**, with split mode NONE, takes the explicit-device branch and iterates zero devices. A null `devices` pointer instead enumerates registered devices before any later main-GPU filtering. `n_gpu_layers=0` by itself does not skip enumeration. See [llama.cpp:158](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/src/llama.cpp:158), lines 158–184 and 185–310. The borrowed array must remain alive through model destruction.

`llama_backend_init` initializes GGML timing/tables, asks the registry count, and calls `ggml_backend_load_all` if the count is zero (llama.cpp 122–134). Registry access constructs a static registry, whose constructor conditionally registers compiled backend families (backend-reg.cpp 119–174, 292–317). This is not proven CPU-only by the selected model-device array.

Discovery scans executable/current directories and a possible compiled backend directory, loads candidate libraries to score them, then initializes/registers a selected backend. `load_all_from_path` attempts BLAS, accelerator, RPC, and CPU families and honors `GGML_BACKEND_PATH`. Even a supplied directory still tries every listed family, so it is not a CPU-only selector. See [ggml-backend-reg.cpp:480](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/ggml/src/ggml-backend-reg.cpp:480), lines 480–597, and 220–261.

The public header instructs initialization once at program start. Silently omitting it would need a separate source-supported decision. Preloading one exact CPU library before initialization is a possible design, but is **not yet qualified**: `ggml_backend_load` itself touches the registry, conditionally compiled registrations and library initialization remain relevant, and dynamic-loader/CPU internals are unreviewed. Do not use `load_all`, `load_all_from_path`, `init_best`, ambient backend paths, or the example tokenizer as shortcuts.

## Conservative candidate settings and lifetime

Start with the typed native `llama_model_default_params()` result; do not recreate its ABI layout manually. Override:

| Field | Prospective value | Reason |
|---|---|---|
| `vocab_only` | `true` | Required pre-tensor return. |
| `devices` | non-null `{nullptr}` array | Suppresses default model-device enumeration. |
| `split_mode` | `LLAMA_SPLIT_MODE_NONE` | Avoids tensor-parallel meta-device creation. |
| `n_gpu_layers`, `main_gpu` | `0`, `-1` | Explicit no-offload intent; not independent enumeration guards. |
| `load_mode`, `lazy_mode` | `LLAMA_LOAD_MODE_NONE`, `LLAMA_LAZY_MODE_OFF` | Avoids implicit AUTO/mapping policy. |
| `no_alloc`, `check_tensors` | `true`, `false` | Defense against tensor-data allocation/validation; not a proof by themselves. |
| `use_extra_bufts`, `no_host`, `load_mtp` | `false`, `false`, `false` | Avoids optional tensor paths. |
| overrides and tensor split | null | No added metadata/buffer-policy authority. |

Use exact pinned existing shard paths, not the `FILE*` API (its loader branch queries CPU buffer alignment at loader.cpp 690). No context, KV cache, graph, decode, sampling model, or server is needed for vocabulary/grammar recognition. The example tokenizer creates a context after vocabulary loading at [tokenize.cpp:142](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-source-20261028T161554Z/sources/tools/tokenize/tokenize.cpp:142), lines 142–156, so its executable is outside the intended scope. A progress callback cannot supply a proven deadline here: the observed vocabulary-only path contains no invocation of it.

`llama_model_free` deletes the model; its destructor is virtual, and the base destructor deletes LoRAs (model.h 859–860; model.cpp 1346–1349, 3379–3380). Local `unique_ptr` ownership in the loader handles visible failure paths, but exact file/context deleters depend on missing headers. Keep grammar samplers and borrowed vocabulary references inside the model lifetime; free samplers before the model. `llama_backend_free` only calls `ggml_quantize_free` in this revision. The registry destructor deliberately releases dynamic handles without unloading because backend threads may still exist (backend-reg.cpp 176–183). Do not claim full backend unload from either free call. A bounded owned worker with measured resource/module evidence remains necessary.

## Unresolved source prerequisites

No automatic acquisition is requested or authorized. At the same exact commit, a separately bounded proposal should consider:

- `ggml/src/gguf.cpp`: prove what `no_alloc=true` reads/allocates and how temporary GGUF contexts close.
- `src/llama-model-loader.h`: inspect weights-index construction, member ownership, and resource aliases/destruction.
- `src/llama-mmap.h` and `src/llama-mmap.cpp`: inspect `llama_file` open/size/read/close behavior and mapping helpers.
- `ggml/src/ggml.c`: resolve GGML initialization/table setup and metadata-context allocation when deciding whether global backend initialization is necessary.
- Conditional on explicit CPU backend loading: `ggml/src/ggml-backend-dl.h` and the exact CPU registration implementation, plus runtime build/import provenance. Its implementation file location and full dependency closure are not established by this review.
- The selected architecture's constructor declaration/definition, if its factory path cannot be established as side-effect-free from retained metadata and headers. No GGUF was inspected here to select that architecture.

These are delegated-behavior gaps, not discovered runtime failures. Even favorable source follow-up would not establish native ABI, finite grammar/EOG conformance, practical memory/time fit, clinical validity, or the human/fresh-source gates. Those retain separate acceptance conditions.
