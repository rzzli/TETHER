# Local source inventory for the public-C recognition gate

28 October 2026 UTC. Local inspection only: no network, fetch, compilation, DLL load, GGUF read, tokenizer, model or server call. The [machine-readable inventory](LOCAL-SOURCE-INVENTORY.json) records hashes, include observations and scope.

Pinned source: `848bbda9041decd87904f7eb5a2990863ecce03b` (tag `b11717`, retained runtime prefix `848bbda90`). This identity match does not prove compiler/build equivalence. No candidate URL below was requested in this pass.

## Already retained

All **13** prior source/license references rehash successfully: eight original references (**371,242 B**) and five converter references (**78,445 B**). The original set is `include/llama.h`, sampler/grammar implementation, private grammar header, two grammar tests, grammar README and LICENSE. The converter set is its three consumer headers and two implementation references. Their [acquisition](../recovery-step9-native-grammar-20261028/SOURCE-TEXT-ACQUISITION.json) and [converter acquisition](../recovery-step9-native-grammar-20261028/CONVERTER-SOURCE-TEXT-ACQUISITION.json) remain unchanged. Converter consumer closure does not close the public-C llama header graph.

Retained `llama.h:4–8` directly includes the five missing GGML headers below. Their contents and transitive dependencies are unknown. Do not claim these five alone are a complete compile closure.

## Minimum proposed bounded reference batch: 11 files

All files are **not retained at this exact commit**. Upstream availability, sizes and hashes remain unverified/null until separately authorized acquisition. Implementation filenames are inspection candidates; their precise function contents are not asserted before reading them.

| Exact-commit URL/path | Purpose before a bridge/load | Local basis or uncertainty |
|---|---|---|
| [ggml/include/ggml.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/ggml/include/ggml.h) | Core GGML types, enums and API/import definitions required to consume llama.h. | Observed direct include at llama.h:4; its own includes/macros are uninspected. |
| [ggml/include/ggml-cpu.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/ggml/include/ggml-cpu.h) | CPU/threadpool declarations used by the public llama API. | Observed direct include at llama.h:5; transitive closure uninspected. |
| [ggml/include/ggml-backend.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/ggml/include/ggml-backend.h) | Backend/device/buffer types including ggml_backend_dev_t and any public device APIs. | Observed direct include at llama.h:6; transitive allocator/backend dependencies unknown. |
| [ggml/include/ggml-opt.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/ggml/include/ggml-opt.h) | Optimizer-related public types referenced by the complete llama.h declaration surface. | Observed direct include at llama.h:7; do not trim the public header to avoid it. |
| [ggml/include/gguf.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/ggml/include/gguf.h) | GGUF metadata declarations needed by llama.h and to interpret metadata-only loading. | Observed direct include at llama.h:8; transitive closure uninspected. |
| [src/llama.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/src/llama.cpp) | Locate public model-load/default-parameter/backend entry points and follow their delegation. | Candidate implementation location identified by prior local requirements; contents/location of each function not yet verified. |
| [src/llama-model.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/src/llama-model.cpp) | Check vocab_only ordering against device selection, vocabulary parsing, tensor creation/allocation and cleanup. | Public model params expose vocab_only; the exact loader early return is not retained or proved. |
| [src/llama-model-loader.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/src/llama-model-loader.cpp) | Trace GGUF/split-file opening, metadata reads, load/lazy modes, mappings and tensor-data access. | llama.h documents split naming and new load_mode/lazy_mode fields; exact implementation remains uninspected. |
| [src/llama-model.h](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/src/llama-model.h) | Interpret private model loading state/signatures while reviewing the loader, without copying opaque layouts into the bridge. | Requested bounded supporting reference for model implementation; not a public-C consumer header. |
| [tools/tokenize/tokenize.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/tools/tokenize/tokenize.cpp) | Compare the pinned tokenizer tool initialization/flags and vocabulary-only path; avoid assuming its backend setup is safe to reuse. | Candidate upstream tool path; remote existence and exact behavior unverified in this local-only pass. |
| [ggml/src/ggml-backend-reg.cpp](https://raw.githubusercontent.com/ggml-org/llama.cpp/848bbda9041decd87904f7eb5a2990863ecce03b/ggml/src/ggml-backend-reg.cpp) | Trace backend registration/discovery/dynamic loading and determine what initialization can touch before CPU-only vocab work. | Public devices=null means all available devices; registry implementation is needed before claiming GPU/device isolation. |

## Static public API and remaining gates

A fresh static PE-table read of the approved `llama.dll` (SHA-256 `166e8de1bd07573dc0f51ab1f429ab5df0d08492e7302bbe41a39014248f5e6d`) confirms **282** named exports and all **17** candidate C APIs: version/default params; backend init/free; model load/free/get-vocab; vocabulary count/is-EOG/EOS/EOT; tokenize/token-to-piece; grammar init/apply/accept/free. The explicit split-list loader also exists. No `llama_grammar_*` prefix export is present. These are symbol observations, not behavior or ABI qualification.

After acquisition, close every quoted-header edge and inspect GGML macros; additional repository includes require a bounded follow-up, not automatic downloads. On Windows, retained `llama.h` selects `dllimport` with `LLAMA_SHARED` and without `LLAMA_BUILD`. Consume actual declarations; do not copy opaque layouts or obsolete model-param fields.

Loader/backend review must establish default parameters, split-GGUF access, the `vocab_only` return point relative to tensor allocation/weight reads/device selection, and necessary backend initialization. A null device list means all available devices according to the header; CPU intent needs an explicit qualified policy. `no_alloc` is not a demonstrated substitute for vocabulary-only loading.

Only then can a new finite typed-build/ABI and vocabulary-only execution protocol be frozen. A vocabulary-owning model handle still reads model metadata; it is not zero model-related work. No inference context or encode/decode/generation/server is authorized by this inventory. Public sampler export presence does not prove document recognition or EOG handling. The closed converter-negative result and accepted pure v3 preparation remain distinct evidence; scientific, fresh-source, human-review and full-case resource gates remain open.
