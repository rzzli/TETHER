# Draft public-C recognition bridge

**Draft source only, 28 October 2026. No build, execution or new native permission.** `typed_public_c_recognizer.cpp` is an author-written x64 Windows consumer of exact public `llama.h` declarations and its reviewed seven-header include closure. It compiles no fetched implementation and binds public exports using `decltype(&::function)` plus `GetProcAddress`; it accesses no private sampler/grammar/vocabulary layout. This document does not accept the ABI, DLL/source correspondence, CPU initialization, resource limits or native conformance. The earlier header-closure/loader notes describe their review-time state; later follow-up closure/source decisions must be linked by the parent before a build or run.

The source has not been compiled or run. Static peer review and a separately authorized build remain required; compiler errors or source defects may remain. Only this draft and this design are changed by this task. No production module, frozen corpus, header, model, receipt or scientific label/outcome/human file is edited.

## Modes and authority

Exact argv (wide Windows command line parsed by `wmain`):

```text
bridge.exe --abi <exact-runtime-directory> <existing-new-output-directory>
bridge.exe --recognize <exact-runtime-directory> <existing-new-output-directory> <exact-pack-file> <exact-cpu-basename> <exact-shard-1> <exact-shard-2> <exact-shard-3>
```

`--abi` has two positional arguments after its mode (argc4 including executable). It securely loads only the pinned core DLLs, resolves typed public exports, records process modules/public layouts, and calls `llama_version` and `llama_model_default_params`. It calls no backend registry, backend initializer, model loader, tokenizer or grammar function. It observes the source-predicted defaults by typed return, rejects mismatches, and reports that independent ABI acceptance remains pending. The exact API version bytes are currently **unknown**; the earlier CLI build prefix is not this API result. A first ABI-only header may declare an empty expected-version string, and the child reports its bounded nonempty printable-ASCII observation without fabricating an expected value. A nonempty expected value, when supplied, must match exactly. Recognition requires a nonempty exact value pinned from a separately retained/reviewed ABI report in a new versioned header/build. This is sequential qualification, not a relabeling or repair of the first ABI observation. It does not prove all public structs/calling conventions safe from these two observations. Module loader/DllMain/dependency effects still belong to the parent ABI protocol.

`--recognize` is a different gated mode (argc9). It requires `R09_RECOGNITION_ENABLED=true` in a fresh, separately reviewed parent-generated pin header. That header must remain false/absent until CPU implementation, loader, ABI, corpus-pack and process-resource reviews close. The mode must run under the future parent's Job/process limits **before any target model call**, with hidden/no-window child creation and a hard external timeout/capture/memory boundary. The draft itself creates no process/window, network, server or child.

The only backend choice is the prospective fixed `ggml-cpu-x64.dll`. The CPU basename argument must match both that literal and the exact parent header. It is not a discovered best-backend choice. `ggml_backend_load` receives its full pinned path; no load-all, load-all-from-path, init-best, GPU, RPC, other CPU variants, context, encode/decode or model token-selection API is called or resolved. An ambient `GGML_BACKEND_PATH` is forbidden. Before `llama_backend_init`, the draft requires exactly one registry named by the parent (expectedCPU), exactly one device of CPU type with the exact parent device name, and matching loaded module path/pins. Registry construction and explicit CPU loading still execute delegated initialization; that source/build/import review is **pending**, not proved CPU isolation by these checks.

After initialization it rechecks the same registry/device pointers, exact singleton counts, CPU names and device type, uses one live non-null null-terminated empty device array, and calls `llama_model_load_from_splits` with **exactly three ordered pinned paths**. Overrides are `vocab_only=true`, `n_gpu_layers=0`, splitNONE, loadNONE, lazyOFF, main_gpu−1, `no_alloc=true`, `check_tensors=false`, `use_extra_bufts=false`, `no_host=false`, `load_mtp=false`, and null tensor/metadata/progress overrides. The typed native default object is the base; no layout is reconstructed. Null callback is intentional: the reviewed vocabulary-only path did not establish a useful progress callback/deadline. Settings express reviewed intent; runtime device/weight-I/O/resource behavior still needs observation.

## Required parent-generated pin header

The build must explicitly set `R09_PIN_HEADER` to an approved **data-only** header. The draft intentionally supplies no permissive placeholder and creates no pin header. It defines `ModulePin` and `FilePin` before including it. The header contract is:

```cpp
// ModulePin = { const wchar_t* name; const char* sha256; uint64_t bytes; }
// FilePin   = { const wchar_t* path; const char* sha256; uint64_t bytes; }
inline constexpr ModulePin APPROVED_RUNTIME_DLLS[] = { /* exact records */ };
inline constexpr wchar_t R09_RUNTIME_DIRECTORY[] = L"<exact approved mirror>";
inline constexpr wchar_t R09_CPU_BASENAME[] = L"ggml-cpu-x64.dll";
inline constexpr bool R09_LIBOMP_REQUIRED = false; // true only if exact PE closure requires it
inline constexpr char R09_CPU_REGISTRY_NAME[] = "<source/build-qualified exact name>";
inline constexpr char R09_CPU_DEVICE_NAME[] = "<source/build-qualified exact name>";
inline constexpr char R09_EXPECTED_LLAMA_VERSION[] = ""; // unknown allowed ONLY for first ABI-only build
inline constexpr const wchar_t* R09_SYSTEM_DLL_NAMES[] = { /* exact known System32 dependency names */ };
inline constexpr FilePin R09_PACK = { L"<exact pack path>", "<sha256>", /* bytes */ };
inline constexpr FilePin R09_SHARDS[3] = { /* exact ordered source-bound metadata paths/hashes/sizes */ };
inline constexpr bool R09_RECOGNITION_ENABLED = false;
```

The runtime allowlist is limited to `llama.dll`, `ggml.dll`, `ggml-base.dll`, `ggml-cpu-x64.dll`, and `libomp.dll` only when explicitly required. Core three and CPU pin records are mandatory; the draft rejects other pin basenames and duplicate names even if the parent accidentally includes the old broad converter inventory. CPU/libomp are not allowed loaded modules in ABI mode. Every non-executable loaded module must either be an exact allowed runtime module inside the exact mirror or an exact parent-listed System32 dependency. The bridge executable identity is owned by the parent's hash/lease. No arbitrary directories, relative paths, UNC/network paths, ADS or reparse paths are accepted. DLL search uses approved directory/system flags, and loaded native DLLs remain process-pinned so native exception/destructor code cannot be unloaded during C++ unwind. The parent must reject unexpected imports/modules and dependency loading; this is not complete OS injection prevention.

For the first disabled-recognition ABI build only, the not-yet-frozen pack descriptor may be an explicitly unused empty descriptor in the parent header; it is never read in ABI mode. Recognition requires a later nonempty exact pack binding, reviewed expected version and enabled header/build. There is no default permissive header in the source.

The parent must derive model identities from existing `MODEL-ARCHITECTURE-EVIDENCE.json` metadata, then hash/lease them under the separately authorized runtime protocol. This draft reads no GGUF now. At future runtime, the child independently opens read leases denying write/delete, verifies exact sizes and streams BCrypt SHA-256 over all three shard files before loading. This deliberate fresh hashing **reads weight-file bytes** and consumes the same120-second cooperative budget; it is separate from tensor allocation/inference. It may prove impractical and must not be silently omitted or have its budget enlarged after a failure. Parent protocol review can prospectively choose a separately justified identity/lease scheme; that would be a new draft revision and new pins.

## Finite binary input pack: version1

All integers are unsigned32 little-endian. No C struct or native pointer is serialized. Every length-prefix is byte length. `blob(cap)` is `u32 length` followed by that many exact bytes, rejecting lengths above cap before copying. `id` is `blob(256)`, nonempty printable ASCII; parent assigns stable opaque IDs and separately binds every ID to the original authoritative locator. Hash fields are exactly32 raw SHA-256 digest bytes, not64 ASCII hex. The whole pack is pinned by path/bytes/SHA in the header and at most20MiB. Trailing bytes, duplicate IDs within their record category and out-of-range indices fail before backend/model initialization.

```text
8 bytes magic = 52 30 39 4e 43 30 31 00 ("R09NC01\0")
u32 version = 1
u32 grammar_count in [1,20]
u32 case_count in [1,200]
u32 prefix_count in [0,6]

repeat grammar_count:
    id
    32 bytes grammar SHA256
    blob(65536) exact nonempty UTF8/no-NUL GBNF bytes (root fixed to "root")

repeat case_count:
    id
    u32 source_group: 0=primary frozen wire, 1=new serialization of retained
                      authored abstention, 2=independent harness byte guard
    u32 grammar_index
    u32 expected_kind: 0=native nonmember, 1=native member,
                       2=independent UTF8 rejection, 3=independent raw-NUL rejection
    32 bytes document SHA256
    blob(65536) exact original document/guard bytes

repeat prefix_count:
    id
    u32 base_case_index (must have expected_kind1)
    u32 kind: 0=exact immutable byte-prefix, 1=first natural BMP UTF8 split,
              2=first natural astral UTF8 split
    u32 cut: exact byte count for kind0; zero for kind1/2
    32 bytes prefix SHA256: exact hash for kind0; all-zero reserved for kind1/2
```

The parent must freeze exact case count and provenance; **do not use166**. The working proposed inventory is167 retained documents plus18 separately frozen authored serializations plus four byte guards =189, within200. The retained18 `response-fixture.json` wrappers contain parsed response dictionaries, **not historical raw answer wire**. The parent may prospectively construct18 new canonical compact/sorted UTF8 serializations of those unchanged authored abstention dictionaries under a declared policy, retain wrappers/receipts unchanged, hash the new bytes and test pure membership before dispatch. This group is `new_serialization_of_retained_authored_abstention`; it is neither model-generated nor recovered historical raw wire. Each uses its own pinned preparation grammar. No such serialization/repair is applied to any original167 case. The earlier proposal's167-document denominator remains separately reported; group counts are emitted separately. Preparation/installed counts (18,12synthetic+6IL6R;36states/74interface rejections) must not be presented as189 native passes or biological entailment. The parent's finite pack must preserve original167 exact bytes, variant grammar bindings and labels/provenance, including two post-only duplicate-claim-text members, seven serialization-domain exclusions and five schema parser-edge controls. Source_group2 must use expected_kind2/3, and groups0/1 must use expected_kind0/1; declared guard bytes are checked before backend initialization.

The B=65,536 diagnostic document cap is intentionally above the retained corpus maximum34,381B; it permits oversize/negative/post-only diagnostic fixtures. It changes no production wire/prompt/case budget. K=65,536 token slots, P=65,536 piece bytes, grammar65,536B, vocabulary262,144 IDs, EOG64 IDs, total token budget1,000,000 (charging every tokenization, including independently tokenized byte-prefixes, and every reused natural-prefix token consumption), six prefix slots and20MiB pack are hard draft caps. Native internal allocations/work are not bounded by output-buffer caps; external Job limits remain required. No whole-vocabulary token-piece/NUL scan occurs; only pieces actually used by cases/prefixes are inspected.

Byte-prefix controls use a new tokenization/fresh sampler, require whole-prefix valid UTF8/no-NUL and exact roundtrip. Kind1/2 natural prefixes reuse the already roundtrip-verified complete positive document's actual token sequence, selecting the first token boundary inside a2/3-byte or4-byte scalar respectively. There is no retokenization or artificial token ID. If no suitable boundary exists, the slot records coverage_unavailable and final qualification fails; no substitute text/vocabulary is selected. Slot counts/rules are frozen before outcomes. Exact byte-prefix cuts/hashes must be frozen offline before target execution. Natural-prefix hash/cut is determined by the fixed selection rule after tokenization and recorded. Do not count an intermediate partial prefix as a whole-input UTF8 harness failure.

## Recognition and outcome layers

The pack is fully parsed and hashes checked before backend or model work. Each input receives independent strict byte UTF8 and raw-NUL checks; only these permit `expected_kind2/3` match. These are harness rejections, never native rejection. ASCII JSON lone-surrogate escape strings and duplicate keys must not be pre-parsed away. No JSON parser, normalization, trim, prefix removal or document repair exists in the draft.

The child enumerates `is_eog` for every valid ID, requires a positive/capped vocabulary count and nonempty/capped EOG set, and emits the complete EOG IDs plus hash of their compact JSON list. It does not assume EOS/EOT exhaust termination. Document tokens use `add_special=false`, `parse_special=false`; a non-null one-slot buffer is tried once, `INT32_MIN` is checked before wide negation, and one exact bounded resize/retry is allowed. Piece calls similarly use a real one-byte buffer, `lstrip=0`, `special=true`, at most one resize/retry and exact count agreement. All ID/range/EOG checks precede piece use/grammar acceptance. The actual piece spans must concatenate exactly to the original bytes; mismatches and EOG-in-document are harness-ineligible, not native false. Only used pieces are inspected for raw NUL; the original no-NUL/full roundtrip condition prevents an invisible suffix being scored as a document pass.

A fresh nonempty non-lazy public grammar sampler is created per complete document/prefix. Ordinary candidates start at finite0.0f; apply must leave a singleton candidate with the same ID/shape and either unchanged0.0f or negative infinity. Only admitted non-EOG tokens are accepted, exactly once. The first rejection stops document consumption. If all tokens are admitted, every enumerated EOG is apply-probed, never accepted. A member requires all tokens and all EOGs admitted. A nonmember can reject an ordinary token or all terminal EOGs. A mixture of EOG decisions is a protocol/native discrepancy. An EOG result at a first-rejected-token state is not called after-complete-input; the draft records completion_EOG=null in that case.

The first expectation mismatch stops the batch after preserving its case row; remaining cases are unexecuted, not passes. Prefix controls require ordinary-prefix admission and all-EOG rejection. Missing natural split coverage is retained and prevents final success. Samplers free before model release; model free and backend free must return before final result publication. Native modules remain pinned until process exit; backend free is not called proof of backend-thread/module unloading.

## Outputs, accounting and failures

The caller supplies an existing empty directory with absent fixed basenames. An exclusive `attempt.json` claim is published before DLL loading. Every JSONL event is append-written and flushed to a CREATE_NEW `result.partial.jsonl`; total8MiB, row64KiB. On normal completion, close and rename to absent `result.jsonl` with no replace flag and write-through. No existing result is overwritten. A caught exception independently attempts a bounded JSONL failure row and exclusive `failure.json`; a full/broken JSONL stream cannot suppress the marker attempt. Partial bytes are retained. Native abort/access violation, hard timeout or process termination may bypass C++ catch/destructors; the parent must retain partial artifacts and publish its authoritative failure. Missing final output is not success.

Events include before-native case IDs/hashes, source-predicted defaults, sizeof/alignof/offsetof measurements, module paths, complete EOG enumeration, case status/match, first rejected token index/byte span, terminal EOG vector, prefix cut/hash/token count, used-piece NUL index/offset, and final tokenization/piece/apply/accept counters. Own `BridgeError` tags are emitted verbatim; unrelated/native C++ exception messages are replaced with fixed tags, because the grammar implementation can include piece text in an exception. No original document/piece contents or biological conclusions are deliberately copied to bridge JSONL/stdout. Native library stderr/stdout may contain its own diagnostics; capture/content disposition belongs to the parent protocol. Exit0 means only the child reached ordinary result publication; parent receipts and independent outcome/resource review are still mandatory.

The cooperative120-second checks bracket potentially long target calls and file chunks; **they cannot interrupt a blocked native call, allocation, destructor or OS operation**. Model loading, registry enumeration and tokenizer internals can overrun between checks. No kill or memory-bound claim is made. The parent must create the hard limit/job and own/reap the worker before recognition is permitted. The deadline includes child fresh hashing and all cases; it does not reuse the earlier1.297-second converter timing or establish production mask/full-case feasibility.

## Required review before building/running

- Verify all exact public-header macros/closure, expected layout assertions and compiler flags; inspect final static imports for unintended upstream imports despite decltype-only usage.
- Bind the fresh parent pin header/bridge/compiler/header identities, exact version string, System32 dependency allowlist, optional libomp necessity and CPU registry/device names from retained build/source/PE evidence.
- Close explicit CPU registration/initialization and loader delegated-source review. The code's exact CPU checks cannot retroactively qualify DLL initialization side effects.
- Freeze all case records,18 prospective new authored serializations and their unchanged wrapper/dictionary bindings, grammar bindings, expected layers/memberships, prefix byte cuts and originals-versus-extensions accounting. Metadata alone did not establish raw prefix offsets or token boundaries. Do not claim retained historical raw wire for the18 wrappers.
- Review cooperative timing, model-hash cost, Job timeout/memory/capture/reaping, original-path leases, exclusive output publication and terminal failure disposition. Conduct only separately authorized synthetic own-code tests/builds before any target call.

No gate above is marked complete by this draft. Native conformance, full-vocabulary production masking, actual case-time fit, fresh-source sufficiency, clinical/scientific validity and independent human review remain distinct.
