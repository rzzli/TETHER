# Static peer review of ABI-only build preparation

28 October 2026. **No material blocker found for root's separate exact-hash build decision. This review grants no build or runtime authorization.** The helper, protocol, generated data header and copied public-header/source inputs were reviewed read-only. The helper was not imported or executed; no compiler/linker, generated bridge, target DLL, GGUF, model, tokenizer, server or network operation was invoked.

The reviewer authored the underlying bridge's v1/v3 work and the scoped OpenMP-delta review. This review independently assesses the **other agent's build helper/protocol/preparation**, not the reviewer's own C++ implementation or an independent whole-bridge/scientific acceptance. The three source reviews retain their stated scopes.

| Exact artifact | SHA-256 |
|---|---|
| `build_public_c_bridge.py` | `733a47bb8c047e129560c0c68dd63d97cf09c95c23b3cabd105df7791927c09c` |
| `BUILD-PROTOCOL.json` | `5c6086e48ca9fb3b3f1f61a2eea780e64f1392bbdc819216e37b09935acc345e` |
| `BUILD-PREPARATION.json` | `b879cbef8e783fc240fa1cc37c514c7536af61856f5def7a32a30740720bb366` |
| Producer `BUILD-PREPARATION-CHECK.json` | `f6f07110ea14769756298e34aa1273e9cb6cc108f88751388b0f86eb827f8529` |
| Generated `recognizer_runtime_pins.hpp` | `dee857596074375218a3c3f8d11130f4066fbfb07b7ae08e454f1f12306a1784` |

The first four files are in `D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028`. The generated data header is in `data/cache/r09-public-c-bridge-preparation-20261028T175036Z` under the project root. Helper line references below refer to the exact source hash above.

## Inputs and prepared bytes

Independently rehashed **193 distinct input files**, totaling the producer-recorded76,233,600 bytes; every current length/SHA matched the frozen protocol. This included static reads of compiler/runtime/System32 bytes where listed; it did not execute them. No input descriptor targeted E:, a `.gguf` file or protected benchmark data. Independently checked276 unique ancestor/path components; none was a reparse point. The output directory `data/cache/r09-public-c-bridge-build-20261028T175036Z` remained absent.

The prepared directory contains exactly nine files: seven copied public headers (`llama.h`, `ggml.h`, `ggml-cpu.h`, `ggml-backend.h`, `ggml-opt.h`, `gguf.h`, `ggml-alloc.h`), the copied own bridge and the generated data-only pin header. Every header source/copy hash matched. The copied source is exact bridge v3 SHA `0d6d7c8bf7495d35811fda56df805dba4e0cf7aa5470776df0903cd5215ad9f4`. The helper prepares these copies with exclusive creation and validates them (375–391); it does not compile fetched implementation files.

The build command compiles **only the copied author-written `.cpp`**, using `/c`, C++17, `/MD`, release iterator settings, `/EHsc`, `/Zp8`, `/Gd`, `/W4 /WX`, `/utf-8`, and exact prepared include directories (347–357). Upstream shared/import macros are in the reviewed consumer source; library-build macros are not introduced by the commands. Link is a separate fixed x64 command over the own object, BCrypt and Kernel32 import libraries; CRT defaults are governed by the pinned toolchain environment. Direct SDK/STL leaves/tools/libraries are pinned; the helper/protocol explicitly do **not** claim a complete transitive compiler/SDK closure.

The producer's preparation check records correction of the direct BCrypt header pin from nonexistent `um` to actual SDK `shared/bcrypt.h` during pre-build metadata preparation. No failed compilation is asserted for that correction. The current protocol pin/command inputs use the actual shared header.

## ABI-only data header and static dependency scope

The generated header is literal data only: five exact runtime module pins, one exact runtime directory, CPU basename/names,16 finite System32 candidate names, three recorded shard **descriptors**, an empty unused pack descriptor, empty expected API version and `R09_RECOGNITION_ENABLED=false`. It has no behavior or permissive loader code. No shard file was opened to generate or review these metadata descriptors (314–344). The current source can report unknown version in ABI-only mode; later recognition requires a separately reviewed nonempty version and enabled header/build.

Required OpenMP is true in this header. Retained `BUILD-STATIC-PE.json` shows direct `ggml-base.dll` and CPU imports of `libomp.dll`, and libomp's PSAPI dependency. The v2/v3 source's conditional exact pin/read-lease/preload handling is covered by the separate OpenMP review; preparation does not load those DLLs. The16 System32 names are explicitly a **prospective fixed import/CRT/startup/BCrypt prediction**, not an observed complete inventory. Static delay-import names remain listed as unresolved candidates; the preparation does not quietly expand the allowlist or promise runtime success. The older converter retained native-package modules only, so it is not evidence of all loaded System32 modules (271–312,392–399,419–425).

## Finite compiler/linker dispatch

`--build` requires the caller's explicit reviewed protocol hash and rechecks the helper/limits/disabled-recognition/empty-version/no-result-execution invariants (532–538). It regenerates and compares exact compiler/linker argv and filtered environment before dispatch (561–563). The parent audit hook permits only the active exact command, exact cwd/environment and at most two owned `Popen` dispatches; network/shell and unapproved parent writes are rejected (244–268). No response file, shell command or generated-executable dispatch is introduced.

The compile cap is45 seconds, link10, within a60-second global cooperative interval with five seconds reserved for finalization. Each tool's effective end is the smaller stage deadline/global-minus-reserve (440–443). Retained stdout and stderr are each capped at256KiB **per tool stage**; overflow/capture errors request owned-process termination, are recorded, and veto success. Two stages can therefore retain at most1MiB across four stream files. Child stdin is closed, shell use is false, handles are closed on launch and `CREATE_NO_WINDOW` is requested (451–483).

The helper polls/kills/waits the **Popen-owned compiler/linker process handle** and joins drain threads with bounded waits. It retains interrupted/failed attempts and disallows automatic retries (484–527). A success requires spawn/reap/zero exit, no capture truncation/error, no cleanup error and whole-stage interval within its declared effective interval. A failed compile prevents link dispatch.

This is **not** an OS Job or complete process-tree/memory/write isolation mechanism. Compiler-spawned descendants are not independently attested or broadly killed; inherited pipes can leave unresolved capture threads, which veto success. Cooperative deadline checks cannot interrupt every file/API operation, and cleanup minimum waits can overrun the nominal interval before failure is reported. The helper and protocol disclose the owned-handle/descendant and toolchain-closure limits rather than claiming a hard60-second process-tree bound. Root's decision must remain within that stated trusted-tool build scope; actual bridge/native execution still needs its separate Job/resource protocol.

## Leases, outputs and no-result-execution boundary

The helper pins the accepted installed0.3.11 wheel/environment, exact own source/design/source-qualification and three scoped review identities before dispatch. `stable_files` leases cover the193 inputs plus the exact protocol while their hashes are rechecked; they are checked again after linking (565–568,582–583). Generated object/executable are separately read-leased during bounded static checks (571–578). The parent audit guard rejects GGUF/E:/benchmark input reads; the bridge model paths in the data header remain unused descriptors.

The prospective output directory must not already exist; journal creation reserves the attempt (539–545). Tool capture/attempt files and build reports use exclusive creation. Failure records are retained and `failure.json` is authoritative over a built-status report or receipt; late finalization/lease/deadline errors attempt that marker too (551–559,590–622). Partial artifacts are not repaired or overwritten. A hard kill/I/O failure can still prevent complete finalization, so external owner review remains necessary.

After linking, the helper **reads PE bytes only**, rejects delay imports and forbidden upstream/network library/API imports, rehashes inputs and publishes a build-only report/receipt (573–589,592–611). It never invokes the generated EXE, neither `--abi` nor `--recognize`. Its only subprocess sites are the exact compiler/linker calls. The protocol has `execute_result=false`, `recognition_enabled=false`, `build_authorized_by_preparation=false`; preparation reports zero child/compiler/linker/target/model activity. A prospective successful compile would establish an artifact/static-import observation only, not a passing ABI or recognizer.

## Disposition

No source/protocol/preparation was changed and no material blocker was found within the declared build-preparation scope. The exact source and protocol hashes above are ready for **root's final decision**, with all original scopes and failure evidence preserved. This review itself does not authorize compilation, accept any timing/resource guarantee, or enable ABI/model/native execution. Root approval, actual build results/static import review, separately qualified runtime limits and all native/scientific/human gates remain pending.
