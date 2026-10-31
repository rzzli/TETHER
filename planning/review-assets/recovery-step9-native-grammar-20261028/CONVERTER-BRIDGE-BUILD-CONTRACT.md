# Actual converter bridge: build preparation only

The owner-installed C++ toolchain passes its own-source probe without a restart.
Prepare and compile a small author-written x64 bridge against the three exact
common headers now retained at commit
`848bbda9041decd87904f7eb5a2990863ecce03b`. Do not compile fetched implementation
files or load any llama DLL yet. Finish the separate 0.3.10 engineering gate
before a prospectively declared native converter experiment.

## Typed bridge and binary binding

- Use the actual `common_json` class declaration and ordinary C++ lifecycle.
  Native constructors/parse/dump/destructor live in the approved common DLL.
  Never reinterpret opaque storage, manually call a destructor through a guessed
  signature, or substitute a source-rebuilt converter for the actual DLL.
- Generate the needed import library from inspected approved DLL export names.
  Use `/MD`, release, `/EHsc`, C++17, UTF-8 and iterator debug level zero. Link
  `llama-common.dll` through `/DELAYLOAD`; record source/header/tool/import-library/
  executable hashes, complete argv, filtered scoped environment and diagnostics.
- Before first `common_json` use, the eventual program must restrict DLL search,
  add only the explicit approved native directory, load common via full-path
  `LoadLibraryExW`, and confirm actual module paths. Required AsOf approval/hash
  checks and ordinary stable-file leases belong to the eventual trusted parent.
  Compiler/toolchain usability does not establish DLL ABI compatibility.
- Expose only fixed round-trip and converter commands using local bounded files.
  No free-form process launcher, network, server, GGUF/vocabulary read, model
  loading, context, inference or generated biological answer. No global environment
  changes. Write build outputs only in a new ignored project cache directory.

## Future execution must be separately frozen

The first native stage is an isolated ABI round-trip smoke on fixed synthetic
JSON, then conversion of the one schema shared by the frozen 109-case corpus.
Use the converter's actual default `force_gbnf=false`, matching the intended
server path; never force a different backend to obtain a favorable result.
Record native diagnostics, returned grammar, exact input and module identities.
Reject empty grammar, unexpected backend markers, unsupported constructs and
incomplete-conversion warnings. A crash or warning is a failed/unsupported probe,
not proof that the original real run failed or that a source rebuild is equivalent.

If conversion fails or warns, close the converter gate negative and stop before
any later vocabulary stage. Retain the original 109 cases; do not repair answers,
weaken schema, retry a failed response or select a new case to hide a mismatch.
If it passes, a separate protocol must distinguish character EOF recognition from
actual vocabulary/EOG filtering. A non-null sampler alone is insufficient: an
empty grammar produces a no-op. Future filtering tests need anchored nonempty
grammar and positive/negative controls. Vocabulary-only metadata initialization,
if later needed, must be reported explicitly and source-qualified; it is not
weight inference and must not be described as no model-related initialization.

Build success alone completes none of these execution/conformance requirements.
No actual DLL operation is authorized by this build-only contract. Root will
freeze a finite execution protocol after the current framework gate passes.
