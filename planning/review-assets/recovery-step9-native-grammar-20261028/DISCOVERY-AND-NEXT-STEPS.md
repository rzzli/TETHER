# Pinned native grammar gate: preparation and converter qualification

28 October 2026 UTC. AsOf 0.3.9 adapter/controller engineering is accepted in the
[preceding closeout](../recovery-step9-native-integration-20261027/CLOSEOUT.md).
This workstream has not run a model, server or native grammar acceptance test.
Human submissions remain pending. No scientific gate is completed here.

## Verified local preparation

Static inspection rehashes three approved b11717 runtime DLLs and parses their PE
export tables without loading them. `llama-common.dll` has 3,454 named exports,
including two C++-mangled schema converter overloads. `llama.dll` has 282 named
exports, including three public grammar-sampler initializers. The server
implementation DLL has 880 named exports. No plain-text C conversion/validation
entry was identified by this bounded name inspection. Export presence is not a
behavioral qualification. See [discovery evidence](RUNTIME-DISCOVERY.json).

The local runtime file listing has no standalone grammar validator. No C++
compiler, CMake, Ninja or binary-inspection tool was on PATH. Standard Visual
Studio, LLVM, CMake and Windows SDK paths were absent; nonstandard installations
remain unknown from that path scan alone. The owner subsequently confirmed that
there is no existing C++ toolchain. No credentials were requested and no installer
was started by the agents. The owner then installed Build Tools; the
[own-source probe](INSTALLED-TOOLCHAIN-PROBE.md) now passes compile, link, SDK/STL
operations and execution without restarting or changing the global environment.
This proves toolchain usability, not compatibility with the pinned native DLL.
Earlier missing-toolchain JSON reports remain dated snapshots. Two scoped AI engineering feasibility reviews found no supported
route completing actual converter and grammar acceptance without a compatible
toolchain or prebuilt bridge/validator; see [alternatives](NO-COMPILER-FEASIBILITY-REVIEW.md)
and [owner-readable prerequisites](TOOLCHAIN-REQUIREMENTS-REVIEW.md).

The first static parser used a 2,048-byte export-name bound. An actual approved
C++ template export is 2,325 bytes, so the probe failed. The corrected helper uses
a file-bounded 64 KiB limit and succeeds on all three approved DLLs. The failed
log is retained. This was a discovery-helper defect, not an AsOf runtime defect.

The [frozen corpus](CORPUS-PREPARATION.json) reuses all 105 original oracle cases
without editing them and adds four explicit 1,800/1,801-character ASCII/astral
Unicode probes. All 109 current 0.3.9 post-validator results and independently
rerun PowerShell7.6.5/JsonSchema.NET results agree, except the already declared
cross-claim-text uniqueness rule enforced only after generation. The corpus is
prepared with an isolated installed dependency-free wheel. It is synthetic
engineering material, not human references. One fixed oracle child runs; no
tokenizer, native library, model or server runs. Original inputs remain unchanged.

## Primary-source inspection and unresolved compatibility

The pinned tag's [converter header](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/common/json-schema-to-grammar.h)
uses C++ input/output types; a guessed ctypes string signature is inappropriate.
Its [converter implementation](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/common/json-schema-to-grammar.cpp)
can emit incomplete-conversion warnings, and compile options can select a
different grammar path. The string-pattern branch precedes length handling;
therefore joint pattern/length behavior is a specific test target, not assumed
correct. These are source-inspection findings, not measured behavior of the
installed binary. The [server documentation](https://raw.githubusercontent.com/ggml-org/llama.cpp/b11717/tools/server/README.md)
supports schema-constrained sampling and refers to implementation tests for its
supported features. Documentation alone does not establish schema equivalence.

Some exact-tag header/test/API requests returned browser cache misses. They are
not evidence of 404s or absent upstream files. The restricted-shell Git lookup also
failed on DNS. A separately permitted, credentials-disabled public tag lookup
resolved b11717 to `848bbda9041decd87904f7eb5a2990863ecce03b`, matching the retained
runtime's `848bbda90` startup build prefix. The startup log reports Clang20.1.8
for Windows x86_64. See [identity evidence](SOURCE-TAG-IDENTITY-authorized.json).
Full source/build correspondence, headers and compiler settings still need
qualification; the commit-prefix match is not a reproducible-build proof. No
repository clone, source archive or runtime binary has been acquired.

Subsequent bounded reference acquisition retains eight text files at that exact
commit, including the license: 371,242 bytes, all HTTP200, no redirects, within
512 KiB/file and 2 MiB total. Hashes are independently rechecked in
[source verification](SOURCE-TEXT-VERIFICATION.json) and
[preparation verification](PREPARATION-VERIFICATION.json). None was built,
executed or imported. This is not the full build dependency closure.

The exact validator source initializes grammar without a vocabulary and checks
UTF-8 characters plus complete-input stacks. Invalid documents still exit zero,
so process success alone cannot be used as an acceptance verdict. Actual token
apply/accept uses a non-null vocabulary; character EOF is distinct from native
vocabulary/EOG behavior. The scoped [source review](NO-COMPILER-FEASIBILITY-REVIEW.md)
retains the precise paths and limitations. A documented `uniqueItems` limitation
also makes the frozen duplicate-reference negative important; no actual pinned
converter result is assumed from the documentation.

## Ordered resumption

1. **Toolchain usability complete:** the owner-installed x64 Build Tools/SDK
   compile/run probe passes. A bridge calling the actual DLL still needs MSVC-compatible C++ ABI,
   matching headers/runtime and declared build options; generic compiler presence
   alone is insufficient. Agents did not install software or acquire paid access.
   The owner handled installation.
2. Use the resolved exact source commit to identify minimum headers, hash them,
   and establish their relationship to the approved binary. Distinguish a source-equivalent
   rebuild from a probe of the actual installed converter. Do not mislabel either.
3. Implement a small fixed model-free bridge, with no model/server loading or
   network. Freeze executable/dependency hashes, commands, time/memory bounds and
   the 109-case corpus before running native conversion/acceptance. Test the
   converter and grammar document/EOS acceptance separately; retain warnings,
   failures and unsupported constructs. Do not guess C++ object layouts in ctypes.
4. Compare native results to schema and post-validation expectations. Keep the
   declared uniqueness exception explicit. Fail unsupported/mismatched schema
   behavior; no permissive object grammar, clipping, repair or corpus replacement.
5. Close the grammar result. Version any necessary runtime/interface correction
   separately and requalify it. Only then declare a finite actual-native
   experiment, with unchanged case budgets and no automatic retry or R07 restart.

**Current constraint:** corpus and static discovery are complete; native
conformance awaits a usable model-free bridge, ABI qualification and pinned headers/build
correspondence. This leaves R09 open. R10–R16 and independent human review retain their
separate scientific dependencies.
