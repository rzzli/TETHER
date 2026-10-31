# Public header closure: one known prerequisite remains

**The public C API header closure is incomplete.** The five newly acquired
GGML/GGUF headers resolve all direct includes of the pinned `include/llama.h`,
but `ggml/include/ggml-backend.h:4` unconditionally includes **`ggml-alloc.h`**,
which is not retained. Its own includes remain unknown. Do not certify complete
closure, substitute a newer file or recreate its declarations by hand.

This static review traces all twelve quoted include directives in six retained
headers from commit `848bbda9041decd87904f7eb5a2990863ecce03b`. Exact paths,
hashes, include lines, searched locations and all seventeen GGML/GGUF types
referenced by `llama.h` are retained in
[HEADER-CLOSURE-REVIEW.json](HEADER-CLOSURE-REVIEW.json).

| Header | Quoted repository includes | Result |
|---|---|---|
| `include/llama.h` | `ggml.h`, `ggml-cpu.h`, `ggml-backend.h`, `ggml-opt.h`, `gguf.h` | All five retained. |
| `ggml/include/ggml.h` | None | Standard headers only. |
| `ggml/include/ggml-cpu.h` | `ggml.h`, `ggml-backend.h` | Retained. |
| `ggml/include/ggml-backend.h` | `ggml.h`, **`ggml-alloc.h`** | Second include unresolved. |
| `ggml/include/ggml-opt.h` | `ggml.h`, `ggml-backend.h` | Retained, indirectly reaches missing header. |
| `ggml/include/gguf.h` | `ggml.h` | Retained. |

The required candidate addition is exactly
`ggml/include/ggml-alloc.h` at the same pinned commit, under a separately bounded
approved acquisition step. Inspect any dependencies it exposes before declaring
closure complete. The four system leaves observed are `stdbool.h`, `stddef.h`,
`stdint.h` and `stdio.h`; this source review does not recursively qualify the
installed compiler/UCRT/SDK headers. No include was fetched or compiled here.

## Import/export and compiler obligations

The header macro branches are explicit:

- `LLAMA_SHARED` selects `LLAMA_API`; on Windows/MSVC, undefined `LLAMA_BUILD`
  selects `dllimport`, while defining it selects `dllexport` (llama.h 15–27).
- `GGML_SHARED` similarly controls `GGML_API` using `GGML_BUILD`
  (ggml.h 176–188).
- `GGML_BACKEND_SHARED` similarly controls `GGML_BACKEND_API` using
  `GGML_BACKEND_BUILD` (ggml-backend.h 6–18).

Without each shared macro, its declaration has no DLL-import attribute.
Freeze the consumer choice explicitly; a bridge consuming the DLLs must not
define upstream library-build macros. The public declarations use `extern "C"`
under C++, but that alone does not prove struct ABI or actual exported behavior.
Use the exact headers and `decltype(&API)` function-pointer types. A future
GetProcAddress-only bridge should make no accidental ordinary upstream calls;
review its final static imports for unintended implicit dependencies.

Preserve the qualified x64 compiler, normal calling convention/packing, CRT
and macro settings. No size/alignment measurement or compile acceptance has
occurred in this review. Exact matching source is not proof that an installed
DLL has a compatible effective build configuration.

## Type and lifetime obligations

GGML supplies opaque backend device/buffer handles, tensor/context/graph types,
enums and callback signatures; the optimizer header also supplies types needed
to parse the complete public header. These unconditional includes cannot be
pruned simply because the eventual bridge uses only seventeen APIs.

`llama_model_params` is returned and passed by value and contains backend-handle
pointers, enums, callbacks and booleans. The public candidate array contains
`size_t`, `int64_t` and `bool`; `selected` is an array index, and its data pointer
may change. Use the supplied declarations rather than copied layouts or guessed
widths. `llama_token` is explicitly `int32_t`. Borrowed vocabulary handles require
the model and modules to outlive all samplers and token operations, as detailed
in [the public API review](PUBLIC-C-API-REVIEW.md).

CPU device policy, vocabulary-only loader ordering, metadata reads, allocations,
EOG behavior and resource feasibility are separate gates. In particular, the
model-parameter comment says null devices means all devices, not CPU selection.
A complete header closure would permit preparation for a separately authorized
build; it would not authorize DLL, GGUF, vocabulary, tokenizer or model access.
