# Requirements for native document and EOG checks

Read-only engineering assessment, 28 October 2026 UTC. No acquisition, build,
DLL call, vocabulary initialization, model or server execution occurred. Five
retained key source hashes were rechecked. The closed converter-negative result
is preserved; it grants no permission to run these later stages.

**Smallest identified actual-DLL route:** use the pinned public C grammar sampler
API with one explicitly vocabulary-only handle. This requires model-related
metadata initialization, although it need not create an inference context or
evaluate weights. No supported complete-document recognizer without vocabulary
was identified in the inspected actual exports.

## Character EOF and vocabulary EOG are different tests

| Route | What it could establish | Important limit |
|---|---|---|
| Exact-source internal character recognizer | Consume UTF-8 codepoints and require an empty accepting grammar stack at complete input | Source-equivalent rebuild, not automatically the installed DLL; does not test actual token/EOG classification |
| Actual `llama_sampler_init_grammar(nullptr, ...)` | Potential parseability check for nonempty character-only GBNF | No public string-consumption/stack API; a non-null sampler does not establish document acceptance |
| Actual grammar sampler with real vocabulary | Actual token-piece rejection and vocabulary-specific EOG admission | Needs an explicitly qualified vocabulary-only load, typed headers and resource protocol |

The retained core-DLL export inventory contains three public grammar initializers,
but no `llama_grammar_*` character/stack functions. The inspected common/server
exports do not supply those internal functions either. Do not recover them through
RVA/ordinal guesses or cast opaque sampler state. Unqualified PEG-related C++
exports are not evidence of the same complete GBNF recognizer.

The upstream string-validator test uses internal null-vocabulary initialization,
codepoint acceptance and empty-stack EOF recognition. It returns zero for both
valid and invalid documents: process exit zero is not its validity result.
Conversely, real sampler apply/accept asserts a non-null vocabulary; EOG handling
consults that vocabulary. Empty grammar can create a non-null no-op sampler.
These conclusions come from the [retained exact-source record](../recovery-step9-native-grammar-20261028/SOURCE-TEXT-ACQUISITION.json),
especially `tests/test-gbnf-validator.cpp`, `src/llama-grammar.cpp` and
`src/llama-sampler.cpp` at commit `848bbda9041decd87904f7eb5a2990863ecce03b`.

## Missing prerequisites before a typed build/load

1. Close the exact public-header include graph. Retained `include/llama.h`
   directly needs missing `ggml/include/{ggml.h,ggml-cpu.h,ggml-backend.h,ggml-opt.h,gguf.h}`;
   their transitive requirements remain unverified. Consume exact declarations,
   with the appropriate DLL-import macro; do not copy struct layouts or assume
   older `use_mmap`/`use_mlock` fields. This revision uses `load_mode`/`lazy_mode`.
2. Inspect the exact loader implementations before asserting weights are omitted
   or GPU devices untouched. Relevant unretained references include `src/llama.cpp`,
   `src/llama-model.cpp`, `src/llama-model-loader.cpp` and tokenizer-tool loading.
   Verify the vocabulary-only early return, split-GGUF behavior, default parameter
   object, device selection, allocation and required backend initialization.
3. A null-vocabulary source-built recognizer additionally needs its private
   grammar/Unicode/dependency closure and an explicit structured validity result.
   The retained references alone are not a complete build closure. Label this
   evidence separately from actual-DLL token filtering.

For the actual-vocabulary route, start with the DLL's typed default model params.
Candidate overrides are `vocab_only=true`, `n_gpu_layers=0`, a live null-terminated
**empty** device list, `check_tensors=false`, `use_extra_bufts=false` and no MTP
loading. A null device pointer means all available devices, not CPU-only. Keep
overrides/device arrays alive through loading. Select load/lazy modes only after
loader inspection; `no_alloc` is not a substitute for vocabulary-only loading.
Avoid backend load-all/device discovery unless its necessity and behavior are
qualified. These specify CPU intent, not verified GPU isolation.

## Later finite test contract

After a separately versioned grammar is ready, freeze its bytes/hash, intended
generation language, corpus, post-validation-only exceptions and controls. Do not
reconvert or repair the closed schema. Then:

1. Create one qualified vocabulary-only handle, obtain its vocabulary and create
   a fresh non-lazy grammar sampler per document. Reject empty grammar. Create no
   inference context and call no encode/decode or token-selection API.
2. Tokenize with automatic specials and special-string interpretation disabled.
   Bound sizing calls, tokens and buffers. Require concatenated token pieces to
   equal the original UTF-8 bytes; no silent prefix removal or normalization.
3. Apply grammar filtering to the next actual token candidate with a finite
   initial logit. Accept it only if allowed. Record the first rejection. Never
   feed rejected tokens onward; accepting EOG at incomplete state can abort.
4. Enumerate all vocabulary EOG IDs using `llama_vocab_is_eog`; do not assume only
   EOS. Probe admission after complete input and at incomplete-prefix controls,
   without accepting rejected EOG tokens. This tests EOG filtering, not generation.
5. Include valid complete, truncated, wrong-literal/reference, duplicate-reference,
   extra-property, oversize/Unicode and trailing-content controls. Return structured
   outcomes; a non-null sampler or exit zero cannot substitute. Free samplers
   before freeing the vocabulary-owning handle.

Vocabulary-only still creates a `llama_model*` handle and reads GGUF metadata.
Fresh hashing of roughly 9 GB of split GGUF files also reads weight-file bytes;
distinguish that I/O from allocating weight tensors or inference. Bound and measure
time, working set, mappings and device behavior; the 1.297-second converter result
does not size this stage. Original-path leases, once-only attempts, capped captures,
owned-handle cleanup and explicit negative dispositions remain required.

No native document/EOG test is authorized or completed by this requirements note.
It cannot qualify model quality, source sufficiency or independent human review.
