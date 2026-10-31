# Typed actual-DLL converter bridge: build only

Author-owned preparation under [the build contract](CONVERTER-BRIDGE-BUILD-CONTRACT.md),
28 October 2026 UTC. The final v3 C++ bridge compiles and links. **It has not been
executed, and no llama DLL has been loaded by this work.** All compiler/library
tool processes have terminated. Root must freeze a separate finite execution
protocol after the 0.3.10 engineering gate before running it.

Authoritative [v3 build report](TYPED-CONVERTER-BRIDGE-BUILD-v3.json) and
[preservation manifest](BRIDGE-BUILD-PRESERVATION.json) retain commands, diagnostics,
exact source, three header copies, tool/library inputs and output hashes.

| Item | Observed build evidence |
|---|---|
| Final cache | `data/cache/r09-typed-converter-bridge-build-20261028T033334Z/` |
| Author source SHA256 | `3e00990253fe29b5a76d177c4d5998642eded5c73e7eef04274e247e133147d0` |
| Executable | 89,600 bytes; SHA256 `ea5064b8e2b68aa193efb0e129ef1da6087809d1a6fb21facccefaad70c362ca` |
| Narrow import library | 3,786 bytes; SHA256 `a21e9405e30ba6782066108a14d2394877d0bf424a57580f2aa68a2e62aed3ed` |
| Compiler flags | x64, C++17, `/MD`, `/O2`, `/DNDEBUG`, `/EHsc`, iterator debug0, UTF-8, `/W4 /WX` |
| Source compiled | Author-written `.cpp` plus the three exact consumer headers; no fetched implementation `.cpp` |
| Native interface | Exactly four verified decorated methods: parse, dump, normal destructor and `json_schema_to_grammar(common_json const&, bool)` |
| Static imports | `llama-common.dll` only in the delay-import table; no ordinary llama/ggml imports |
| Forbidden direct APIs | No model/vocabulary/context/sampler/inference/process/network API imports identified |
| Native program executions | 0 |

The fixed future interface is:

```text
typed_converter_bridge.exe roundtrip <approved-runtime-directory> <input.json> <new-report.json>
typed_converter_bridge.exe convert   <approved-runtime-directory> <input.json> <new-report.json>
```

These are an interface description, not commands authorized for execution now.
The code requires absolute local fixed-drive paths and new report/attempt/output
paths. It bounds JSON input at 2 MiB, returned text at 4 MiB and each native DLL
read at 128 MiB. Root's actual execution protocol must choose tighter applicable
inputs, time/resource caps and stable-file leases; these constants are only build
limits, not approval to consume maximum resources.

Before any `common_json` operation, the eventual code restricts DLL search to
System32/explicit approved directories, loads common via its full path, checks its
hash/path, and pins that exact module for the finite process lifetime. Pinning
keeps native exception vtables/destructors available through outer error handling;
it is released by process termination. Loaded native module paths/hashes are
checked before and after typed operations against thirty approved DLL proofs.
There is no opaque-storage manipulation or guessed member-function signature.

The converter uses `force_gbnf=false`. Original return bytes are retained in an
output file with SHA256; empty output, invalid text and unexpected backend markers
fail. Structured status says only that the native call returned, never that ABI or
grammar conformance passed. Native stderr remains unchanged; **any native
diagnostic must fail the future external qualification**. No fallback grammar,
schema anchoring, corpus edits or later vocabulary stage is permitted to hide a
warning/negative. The module pin follows the documented
[Windows process-lifetime flag](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandleexw).

The first link failure came from literal quotation marks preserved in generated
`.def` export names. C++ compilation succeeded; the import library did not match
the four typed symbols. That helper defect was corrected with validated unquoted
decorated names. V2 then linked successfully. V3 added the explicit process-lifetime
pin and early new-output checks. Each cache retains its exact author source,
helper, headers and build records; older authored-source pointers are historical,
not invitations to run archived helpers. No native execution or response retry
occurred in any attempt.

Build success proves neither actual DLL ABI compatibility nor schema/grammar
enforcement. Fixed ABI round-trip and actual conversion remain future experimental
gates. R07, human scientific review, source sufficiency and model quality are
unchanged.
