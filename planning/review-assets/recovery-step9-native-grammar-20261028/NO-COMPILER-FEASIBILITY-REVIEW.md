# No-compiler feasibility review

**Later update:** the owner has now installed Build Tools and the toolchain probe
passed. The absence findings below are historical. The current route is the
[typed actual-runtime design](TYPED-ACTUAL-RUNTIME-BRIDGE-DESIGN.md); native DLL
interop and grammar behavior remain unqualified until its separate execution gate.

AI engineering review by `/root/grammar_no_compiler_feasibility`, 28 October
2026 UTC. Read-only inspection and primary-source research; no runtime DLL,
model, server, compiler or validator was executed, no binary acquired, and no
AsOf runtime/test/data-evidence file changed. A later authorized bounded acquisition
retains eight exact-source text references under an ignored workspace cache.

No supported route was identified that completes both actual pinned-DLL schema
conversion and native document acceptance under the present no-toolchain,
no-model/server constraints. This is a scoped finding, not proof that every
possible implementation is impossible.

The [local export report](RUNTIME-DISCOVERY.json) identifies C++ converter
overloads. The official [b11717 header](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/common/json-schema-to-grammar.h)
uses C++ JSON/document and string objects. Calling it as a plain C string
function through ctypes would guess an undocumented ABI and object layout.
The public grammar-sampler exports accept an existing grammar; they do not
replace JSON-schema conversion.

| Candidate route | Useful evidence | Remaining limitation |
|---|---|---|
| Official Python/JavaScript converter | A separate schema conversion result | Does not execute the pinned DLL converter or establish identical compile options/semantics |
| Existing server/CLI schema option | Application-path conversion during supported operation | No documented model-free command found that also validates arbitrary documents; starting a model/server is outside this probe |
| Source-built `test-gbnf-validator` | Native string/complete-input recognition from the selected source revision | Needs a built executable/toolchain; a rebuild is not automatically evidence about the installed DLL |
| Existing C grammar sampler API | Potential grammar parsing/token-admission tests with appropriate vocabulary inputs | Does not convert JSON; character end-of-input and vocabulary-specific EOG acceptance must be reported separately |

The [b11717 GBNF guide](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/grammars/README.md)
links the model-free string validator at `tests/test-gbnf-validator.cpp`; an older
example-path link remains elsewhere in the guide. It also documents unsupported
schema features. In this project, `quote_refs` uses `uniqueItems`, which the guide
lists as unsupported. The frozen `duplicate_reference` case therefore matters.
The root schema uses alternatives of complete object schemas, so the guide's
separate warning about mixing object properties and alternatives in one type
does not directly describe the root. These are compatibility risks, not measured
outcomes of the approved binary.

The practical artifact needed is an MSVC-ABI-compatible Windows x86_64 bridge
that calls the approved converter DLL, with source/build instructions, exact
commit/header hashes, compiler/standard-library/runtime identity and DLL hashes.
For model-free string recognition, also supply a matching built validator or
compile the exact grammar recognizer. Verify that it accepts complete input,
rather than merely parsing a grammar definition. Do not describe that as tested
model-vocabulary EOG handling unless that path is actually exercised.

A matching prebuilt bridge/validator could avoid a local compiler installation;
none is identified in the current local runtime inventory. A generic compiler
or arbitrary prebuilt validator is insufficient. The confirmed absence of a
local toolchain is therefore a real dependency for the current bridge route.

Minimum decisive source inspection before building: exact-commit `include/llama.h`,
`src/llama-sampler.cpp`, `src/llama-grammar.cpp`, `src/llama-grammar.h`,
`tests/test-grammar-integration.cpp`, `tests/test-gbnf-validator.cpp` and
`grammars/README.md`. Add the converter/JSON headers when designing the bridge.
Browser cache misses for several exact-commit URLs were not treated as 404s.
No permissive grammar, unsafe ABI workaround, interface repair or substitute
scientific validation is recommended by this review.

## Exact-source addendum

The parent authorized eight fixed raw-GitHub text URLs at commit
`848bbda9041decd87904f7eb5a2990863ecce03b`. The
[frozen v2 protocol](SOURCE-TEXT-PROTOCOL-v2.json),
[acquisition](SOURCE-TEXT-ACQUISITION.json) and
[verification](SOURCE-TEXT-VERIFICATION.json) retain all eight HTTP200 files,
371,242 bytes, SHA256 values and elapsed times. Each is below 512 KiB/15 seconds,
with no redirects, credentials or unknown bytes. The original unexecuted protocol
and helper remain retained: before any fetch, the bounded reader was tightened
to avoid a cap-plus-one read, and unknown timeout accounting was made terminal
for remaining URLs. None of the fetched material was imported, built or executed.

Exact source now establishes:

- `tests/test-gbnf-validator.cpp:79` creates a grammar with null vocabulary.
  Its codepoint loop and empty-stack test at line29 implement complete-string
  recognition without loading a model. **Line108 returns zero after both valid
  and invalid inputs**. A harness cannot use exit0 as a validity label; use an
  explicit structured result or a carefully specified wrapper around this source.
- `tests/test-grammar-integration.cpp:19` uses the same null-vocabulary setup;
  line94 accepts synthetic token IDs/pieces. This remains distinct from exercising
  an actual model vocabulary's special-token/EOG behavior.
- `src/llama-grammar.cpp:1360` and `:1403` require a non-null vocabulary in the
  real token sampler's apply/accept paths. The EOG branch at line1384 uses the
  vocabulary's token classification. Directly calling that path with null
  vocabulary is not an acceptable workaround.
- `src/llama-sampler.cpp:2831` exposes a public C grammar initializer. With null
  vocabulary it may support a **grammar parseability-only** diagnostic for
  character-only grammars, but it does not accept arbitrary input strings or
  convert JSON schemas. It cannot complete the requested conformance gate.

The supported model-free source route is therefore concrete: build a fixed
converter/string-recognizer harness using the exact implementation and an
explicit validity result. Actual-DLL conversion still needs a compatible C++
bridge; native character/EOF recognition may require building the upstream test
target/dependency closure. That closure is not established by these eight
reference files alone. A full source-equivalent rebuild must be labeled as such,
separately from testing the already approved DLL. No toolchain-free completion
route was established.
