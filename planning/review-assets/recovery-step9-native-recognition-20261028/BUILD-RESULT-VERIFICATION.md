# Independent verification of the public-C bridge build

28 October 2026 UTC. **PASS within build-only scope. The bridge has not been executed or ABI-qualified.** This is AI engineering verification of retained artifacts, not a scientific review. No build, helper import, DLL/EXE execution, GGUF read or network request occurred during this review.

The separately authorized compile/link result is retained at [the build directory](D:/Projects/drug_target_agents/data/cache/r09-public-c-bridge-build-20261028T175036Z). Its receipt SHA-256 is `ebae856c74554b200b8d486cc5ce958fa530dc75499035bf82a9133114ae7c72`; root build decision SHA-256 is `b101dd005624c09a6df48d940b07cc5c73ea4aafcc2a8f40a67166e7dae067c3`. Detailed independent checks are in [BUILD-RESULT-VERIFICATION.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/BUILD-RESULT-VERIFICATION.json), SHA-256 `5a05e7310a42caebd9fdd6991487424d5cc860fe21bb5a806f5991c4c920f6bc`.

## Retained evidence checked

- All **193** unique protocol input files rehash to their frozen sizes and hashes; input paths/ancestors checked had no symlink/reparse attributes. The effective protocol is byte-identical to reviewed protocol `5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e`.
- The directory contains exactly **11 receipted outputs plus the receipt**, with every output size/hash correct and no authoritative failure marker.
- All **eight journal events** rehash with correct sequence/previous links. The receipt matches the final journal tip. Each compile/link terminal record equals the corresponding attempt file and build-report entry, with the exact approved argv and PID.
- Both owned launched handles exited0 and were reaped, with no timeout, cleanup error, truncated capture or guard denial. Compile elapsed **2.016s/45s** and link **0.062s/10s**, including reported cleanup. Captures retain31/1,156 bytes for compiler stdout/stderr and0/0 for linker; compiler stderr contains the `/Bv` toolchain pass-version inventory, with no warning/error text observed.
- An independent stdlib PE/COFF reader confirms **x64 machine0x8664**, PE32+ executable and x64 COFF object. Its complete ordinary imports reproduce the retained report; delay imports are empty. Static imports contain no upstream llama/GGML DLL, network DLL or listed process/network-spawning import. This is a static-import result, not a dynamic behavior attestation.
- The seven copied public headers and copied v3 own-source are byte-identical to their pinned sources. Pin header hash remains `dee857596074375218a3c3f8d11130f4066fbfb07b7ae08e454f1f12306a1784`: recognitionfalse, empty observed-version expectation, unused empty pack descriptor. Recorded model descriptors were read as metadata only; no model file was opened.

## Produced artifacts and claim boundary

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `typed_public_c_recognizer_abi.exe` |188,416| `9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696` |
| `bridge.obj` |1,277,145| `c9f7f0de3cd24c69fb3061404de6e3060e756bbe056ce96a120e7c2fbdb0dac9` |

The retained status literal `ABI_disabled_public_C_bridge_built_not_executed` is a **build label**. The compiled program has an ABI-only route, whose execution is still unperformed; the recognition route is disabled by its bound header. No ABI compatibility, actual loaded-module inventory, tokenizer piece identity, native membership, EOG result or model-quality conclusion follows from compilation. The report's pre-finalization elapsed value is3.484s; this review does not invent a retained full finalization duration.

Compiler ownership covers the launched handles. Descendants, process-tree containment and system-wide writes were not independently attested. Representative toolchain/SDK/STL/library leaves are pinned, without a complete transitive compiler dependency closure. Only own bridge code and seven public headers were compiled; fetched upstream implementation files were not compiled. OS containment, actual native execution protocols, resource gates, fresh-source and human scientific gates remain separate.
