# Pinned public C API review

28 October 2026 UTC. **Source review only; native recognition is unqualified.**
No network request, compilation, DLL call, tokenizer call or GGUF read was made
for this review. The seventeen candidates below were observed in the retained
static export inventory; their presence does not establish ABI compatibility or
runtime behavior. Exact declarations, source hashes and evidence ranges are in
[the companion record](PUBLIC-C-API-REVIEW.json).

The review uses commit `848bbda9041decd87904f7eb5a2990863ecce03b` (`b11717`):
[public header](../../../data/cache/r09-native-grammar-source-20261028T020623Z/sources/include/llama.h),
[sampler implementation](../../../data/cache/r09-native-grammar-source-20261028T020623Z/sources/src/llama-sampler.cpp)
and [grammar implementation](../../../data/cache/r09-native-grammar-source-20261028T020623Z/sources/src/llama-grammar.cpp).
The preserved [inventory](LOCAL-SOURCE-INVENTORY.md) proposed eleven additional
references. The separate [scope addendum](SOURCE-SCOPE-ADDENDUM.md) adds exactly
`src/llama-vocab.cpp`, because the header alone cannot qualify token-piece sizing.
The resulting twelve-file batch remains a source-acquisition proposal, not
permission to load a vocabulary or model.

## Exact candidate surface

Line numbers refer to the retained public header. Full multiline parameter lists
are copied verbatim into the companion JSON, rather than redeclared here.

| API | Header lines | Contract and material boundary |
|---|---:|---|
| `llama_version` | 478 | `const char *`; bounded copy while DLL lives; ownership/nullability are undocumented. |
| `llama_model_default_params` | 482 | Exact `llama_model_params` returned by value; actual defaults await implementation review. |
| `llama_backend_init` | 489 | Header requests once at startup; device discovery/effects remain unknown. |
| `llama_backend_free` | 492 | Once at shutdown under the qualified initialization lifecycle. |
| `llama_model_load_from_file` | 525–527 | Path plus parameters by value; split-file access, failures and early returns need loader review. |
| `llama_model_free` | 550 | Public release after all vocabulary users; do not assume null-tolerance. |
| `llama_model_get_vocab` | 596 | Returns `const llama_vocab *`; conservatively borrow from the live model. |
| `llama_vocab_n_tokens` | 621 | `int32_t` count; validate bounds before allocation or iteration. |
| `llama_vocab_is_eog` | 1211 | Test every vocabulary ID for the full EOG set. |
| `llama_vocab_eos` | 1218 | EOS hint; not an exhaustive EOG list. |
| `llama_vocab_eot` | 1219 | EOT hint; absent/out-of-range semantics need implementation review. |
| `llama_tokenize` | 1278–1285 | Explicit byte length, token buffer/capacity, two special-token flags; signed sizing result. |
| `llama_token_to_piece` | 1292–1298 | Byte buffer/capacity, `lstrip`, `special`; no null terminator. |
| `llama_sampler_init_grammar` | 1530–1533 | Vocabulary, grammar string and root; public route is non-lazy. |
| `llama_sampler_apply` | 1443 | Filters candidates without advancing grammar state. |
| `llama_sampler_accept` | 1442 | Advances state; rejected tokens/EOG must never be accepted. |
| `llama_sampler_free` | 1448 | Free each standalone sampler once; chain ownership forbids double-free. |

## Types, loading and ownership

Use the complete exact public header closure and typed
`decltype(&llama_tokenize)`-style `GetProcAddress` bindings. Do not copy private
layouts, invent GGML typedefs, cast private sampler contexts or guess RVAs.
`llama_token` is declared `int32_t` (header 65–70). The candidate structures
(231–244) are public: `selected` is an array index, not a token ID, and samplers
may change `data`; do not assume sorting or stable pointers generically.

The five GGML headers required by `llama.h` remain unreviewed. Its model parameter
declaration (320–356) says `vocab_only` means vocabulary without weights, but this
comment does not prove loader ordering, allocation, split access or CPU-only
behavior. In particular, `devices == nullptr` means **all available devices**,
not CPU selection. This revision uses `load_mode` and `lazy_mode`; do not import
older `use_mmap`/`use_mlock` assumptions. Actual defaults, backend registration
and metadata/resource costs require the pending exact implementation review.

Keep the model and DLL alive for all borrowed vocabulary operations. The grammar
sampler retains its vocabulary pointer and copies its grammar/root strings
(sampler 2666–2673, 2773–2835). Conservative cleanup is: free all document
samplers; free the model after the final vocabulary use; free the backend if its
qualified lifecycle required initialization; unload modules last. No independent
vocabulary destructor or ownership transfer is assumed.

## Token bytes and sizing

For unchanged-document tests, specify `add_special=false` and
`parse_special=false`; measure exact byte roundtrip rather than presume it.
The tokenize contract (1269–1285) returns a nonnegative count on success, a
negative required count on insufficient capacity, and `INT32_MIN` on overflow.
Check the overflow sentinel before negation, use checked wide arithmetic and
bound byte lengths, capacities and allocations prospectively. The header does
not establish that a null token pointer with zero capacity is safe.

Token-to-piece has a separate contract. It writes no terminator, allows leading
space removal and special-token rendering, but the header does **not** specify
negative sizing/overflow semantics. Adjacent `llama_detokenize` documentation
cannot fill that gap. No null-buffer sizing call is qualified before inspection
of the newly requested implementation. Use `lstrip=0` for roundtrip; specify
special rendering explicitly rather than changing it to repair failures.
Treat returned pieces as bounded byte spans: individual tokens may contain
partial UTF-8. Concatenate exact bytes before whole-document comparison and
decoding; do not trim, normalize or decode each piece independently.

## Grammar membership and completion

Public grammar construction delegates with `lazy=false` (sampler 2831–2835).
Use a fresh sampler for each document with nonempty grammar and explicit root
`root`; reject null initialization. Empty grammar produces a no-op sampler, and
the generic apply/accept wrappers tolerate null samplers, so neither a non-null
handle nor normal process exit proves recognition.

Grammar apply (grammar 1359–1400) examines candidates with finite initial logits,
sets rejected logits to negative infinity and preserves state. Ordinary accept
then advances it. EOG is allowed when an accepting stack exists. Accepting EOG
prematurely reaches `GGML_ABORT` (1402–1459): filter first and never accept a
rejected candidate. Enumerate `is_eog` for every valid vocabulary ID; EOS/EOT
helpers alone are insufficient. Partial-UTF-8 state crosses token boundaries.
Singleton membership checks do not qualify a full-vocabulary production mask or
its resource cost. Actual document/EOG conformance, header/ABI qualification and
bounded CPU metadata/resource profiling remain future gates under a separately
reviewed finite protocol. Scientific validation is not attempted here.
