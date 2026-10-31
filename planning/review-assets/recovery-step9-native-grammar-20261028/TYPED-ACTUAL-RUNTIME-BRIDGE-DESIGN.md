# Typed actual-runtime bridge design

AI engineering design by `/root/grammar_no_compiler_feasibility`, 28 October 2026
UTC. Source/static-export inspection only; no compilation, DLL execution,
vocabulary loading, model context, inference or server was performed. Thirteen
small source/license references were acquired under two separate fixed protocols.
The owner has now supplied Build Tools. This supersedes toolchain absence as the
immediate constraint in the earlier no-compiler review, not its ABI cautions.

The actual-runtime route is viable in principle, with staged gates. First call
the approved converter DLL through exact typed headers. Any captured conversion
failure, incomplete-conversion warning or unsupported grammar mode closes the
declared qualification negative **before vocabulary initialization**. Only a
clean converter result can justify a separately frozen vocabulary-only sampler
stage. No source-rebuilt recognizer needs to substitute for the actual runtime.

## Converter first

The existing `llama-common.dll` exports the `common_json` constructors/destructor,
static `parse(const std::string&)`, `dump(int)` and both converter overloads.
Therefore header-only nlohmann construction must not be assumed. Use the exact
`common_json` declaration and typed parse/converter signatures, with normal C++
object lifetime and the DLL's implementation where required. Do not cast a C++
member destructor to an invented C function signature.

The five converter references are now retained and verified: 78,445 bytes, all
HTTP200, no redirects/unknown bytes and all caps met. See the
[acquisition](CONVERTER-SOURCE-TEXT-ACQUISITION.json) and
[verified header closure](CONVERTER-HEADER-CLOSURE.json). The converter-only
consumer's complete non-STL closure is exactly `common/json-schema-to-grammar.h`,
`common/json-schema.h`, `common/json.h`. The last two require only STL headers.
No vendor nlohmann or GGML header is needed to consume these declarations.
Do not compile external `json.cpp` or the converter implementation: they are
reference-only. Native `json.cpp` constructs the backing JSON value inside the
opaque aligned storage defined by the header and implements parse/destruction.

Resolve the actual converter overload by its verified decorated export and the
header's signature. If ordinary `common_json` construction/destruction needs
imports, generate a narrow import library from verified exports and consider
`/DELAYLOAD`: explicitly load the full approved DLL path before first use. Keep
all foreign objects local to that loaded module's lifetime. Pin x64 release build,
`/MD`, exception mode, iterator-debug level and the installed standard library;
the producer's Clang20.1.8 identity alone does not prove MSVC14.51 interoperation.
Return/destruct a tiny controlled object/string under an isolated finite process
before interpreting corpus results. Record crashes as failures, without retry.

A minimal typed design uses `decltype(&common_json::parse)` for the static parse
function and `std::string (*)(const common_json &, bool)` for the selected converter
overload. Parse/convert may be obtained with `GetProcAddress`; the automatically
destroyed `common_json` still requires its native destructor to link normally.
A narrow verified-export import library can satisfy that call. C++17 prvalue
initialization avoids an unnecessary caller-side move; if the linker reports
additional methods, resolve them explicitly rather than leaking/skipping cleanup.
Build only the author-written bridge with the three exact headers, release `/MD`,
`/EHsc`, iterator debug0, the narrow import library and `delayimp.lib`/
`/DELAYLOAD:llama-common.dll`. No additional source fetch is needed for this
converter-only declaration closure. Actual execution waits for root's full
0.3.10 gate and a separate fixed execution protocol.

The [static import inspection](ACTUAL-DLL-IMPORT-DISCOVERY.json) confirms the
approved common/core DLLs depend on MSVCP140, VCRUNTIME140/VCRUNTIME140_1 and UCRT.
That supports the dynamic release-CRT choice; it does not establish full ABI
compatibility. Use secure full-path DLL loading, approved dependency leases,
loaded-module path/hash checks and complete stderr capture.

The 109 frozen documents share one schema hash. Convert that schema once with
the same default mode used by the production schema path. Never silently force
an alternate GBNF mode if the result selects another backend. Capture stdout,
stderr, returned grammar bytes/hash, exception and loaded-DLL identities. Known
uniqueness and pattern/length risks are negatives to preserve, not repair here.

One specific early negative is source-grounded: current `_text` emits an
unanchored non-whitespace pattern. Exact converter line407 requires `^...$`;
lines394–398 record an unsupported-pattern warning and substitute its broad
string primitive, then line980 emits the incomplete-conversion warning. Capture
the actual DLL result before asserting that behavior. If observed, close the
declared qualification negative and stop before any vocabulary load. Reject
empty grammar and unexpected backend markers too: an empty grammar can create
a non-null no-op sampler, so non-null initialization is not enforcement proof.

## Conditional vocabulary-only stage

Exact `include/llama.h` exposes `vocab_only`, and documents that it omits weights.
It also uses `load_mode`/`lazy_mode`, not old `use_mmap`/`use_mlock` fields. Begin
with the actual DLL's default parameter object, then set typed fields. Set
`vocab_only=true`, `n_gpu_layers=0`, disable tensor checks/repacking, and establish
an explicitly empty device list: a null device pointer means all available
devices, not CPU-only. Keep the list alive through loading.

The exact loader implementation was not fetched, so verify its vocabulary-only
early return and device/tensor behavior before relying on those flags. Candidate
reference files are `src/llama.cpp`, `src/llama-model.cpp`,
`src/llama-model-loader.cpp` and the tokenizer tool source. No loader behavior was
measured here. The public header also directly needs missing
`ggml/include/{ggml.h,ggml-cpu.h,ggml-backend.h,ggml-opt.h,gguf.h}`; inspect their
transitive includes before compiling rather than copying structure layouts.

All seventeen required public API exports were found statically in the approved
`llama.dll`: defaults/backend init/free; model load/free/get-vocab; vocabulary
count/is-eog/eos/eot; tokenize/token-to-piece; grammar init/apply/accept/free; version.
Create no inference context and call no encode/decode/sample API. A vocabulary-only
load still creates a `llama_model*` handle and reads GGUF metadata. Report it as
one vocabulary load, not as no model-related load. Hashing approved GGUF files
also reads weight-file bytes; distinguish that from allocating/loading weight
tensors for inference. Retain original asset leases, measured memory and time.

## Finite token and EOG test

For each document, use a fresh grammar sampler and ordinary tokenization with no
automatic BOS/EOS and no special-token interpretation. Require reconstructed token
pieces to equal the original UTF-8 bytes; otherwise report an applicability failure.
Check each actual token as one candidate with finite initial logit. Apply only the
grammar sampler; accept the token only if still allowed. Never accept a rejected
token: native EOG acceptance can abort on incomplete grammar state.

Enumerate vocabulary EOG IDs once with `is_eog`; do not assume EOS is the only one.
After all document tokens pass, probe those candidates through grammar apply.
Their admission tests actual vocabulary-specific completion without generating
tokens or evaluating a model. Keep this distinct from the earlier character/EOF
recognizer. Fresh sampler/free per document prevents cross-case state reuse.

Freeze the existing 109 cases and separately named safety controls before running:
valid complete document, truncated closing delimiter, wrong literal/reference,
duplicate reference, extra property, oversize text, trailing non-whitespace and
EOG at an incomplete prefix. The existing post-validation-only claim-text
uniqueness exception stays explicit. Return structured booleans/rejection kinds,
token/grammar/document hashes and EOG IDs; exit0 alone is not acceptance. Stop at
the declared failure boundary with no corpus replacement, normalization, repair,
stochastic sampling, HTTP request or automatic retry.
