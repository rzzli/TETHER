# Toolchain requirements for the model-free grammar check

Read-only AI engineering assessment, 28 October 2026 UTC. No installer, compiler,
DLL, model or server was executed; no files or binaries were downloaded. This
assessment does not replace independent scientific review.

**Recommendation:** use a complete Windows x64 C++ development toolchain, rather
than a compiler executable alone. The predictable documented route is Microsoft's
standalone Build Tools with **Desktop development with C++**. The Visual Studio
IDE is unnecessary. Installation is an owner/administrator action, not something
performed by this review. [Microsoft command-line Build Tools instructions](https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line?view=msvc-170),
[installation permissions](https://learn.microsoft.com/en-us/visualstudio/install/install-visual-studio?view=visualstudio).

## What must be available

| Input | Practical requirement and reason |
|---|---|
| Compiler and linker | Windows x64, Microsoft-compatible C++ ABI. `cl.exe`/`link.exe` are a practical baseline. `clang-cl` is another candidate; the retained runtime reports Clang 20.1.8, but matching that version alone does not prove compatibility. |
| C++ and C development files | MSVC Standard Library headers, VC runtime development headers/import libraries, UCRT development headers/libraries and Windows SDK. Existing runtime redistributable DLLs do not provide a complete development environment. |
| Source/header identity | Pin the source tree at `848bbda9041decd87904f7eb5a2990863ecce03b`, including the converter, `common_json`/schema types and their transitive headers. Do not treat just the converter declaration as a sufficient header bundle. The exact include closure still needs inspection. |
| Build configuration | Record target architecture, compiler/linker/STL/SDK versions, runtime-library selection, iterator/debug settings and relevant JSON/schema configuration macros. Establish these before exchanging C++ objects with the existing DLL. |
| Approved runtime | Use the existing hash-verified DLLs through fixed paths. Identify their actual CRT dependencies and source/build settings; do not replace them with newly compiled equivalents and claim the installed binary was tested. |
| Build driver | A small single-purpose bridge can be built directly from a native-tools environment; CMake/Ninja are useful for building upstream tests, but are not inherently required for every one-file bridge. |

LLVM documents separate Windows SDK, UCRT and Visual C++ runtime development
inputs for `clang-cl`; its Microsoft ABI support also has limitations. A portable
LLVM archive by itself therefore does not establish a complete usable route.
[LLVM Windows header/library lookup](https://clang.llvm.org/docs/UsersManual.html#windows-system-headers-and-library-lookup),
[LLVM MSVC compatibility](https://clang.llvm.org/docs/MSVCCompatibility.html).

Microsoft publishes component IDs for the x64/x86 tools and Windows SDK. A stable
toolset and SDK should be selected and recorded; the newest installation must not
be assumed to reproduce the existing binary's settings. Optional MFC, ATL,
C++/CLI, ARM targets and the full IDE are not requirements of this bridge design.
[Build Tools component directory](https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=visualstudio).

## Is a supported workspace-only, no-admin route available?

**Not established by the official documentation reviewed.** Microsoft's documented
installer and `winget` acquisition paths use an administrator command prompt.
Even an offline layout is an installation package, not evidence that unpacking it
produces a supported portable toolchain. No installer or layout should be run
without the owner's approval. [MSVC acquisition](https://learn.microsoft.com/en-us/cpp/overview/acquire-msvc?view=msvc-170),
[offline installation documentation](https://learn.microsoft.com/en-us/visualstudio/install/create-an-offline-installation-of-visual-studio?view=visualstudio).

This does not prove a no-admin arrangement is technically impossible. An owner/IT
team could supply an authorized complete development environment at a nonstandard
path, or a matching prebuilt model-free validator. Its provenance, required files,
license/redistribution authorization and compatibility would still need checking.
Neither arbitrary third-party portable MSVC bundles nor a MinGW/GCC replacement
should be assumed equivalent to this DLL's C++ interfaces.

## Acceptance after the files are available

1. Inventory/hash the toolchain, exact source headers, runtime dependencies and
   effective build flags. Build a small bounded C++ bridge with a plain-text or
   explicit C boundary for Python; do not guess `std::string`/JSON layouts in ctypes.
2. Call the existing DLL converter only after its typed ABI/configuration is
   qualified. Test conversion warnings/failures and document/EOS grammar acceptance
   separately against the frozen 109 cases. Model loading and inference are not
   prerequisites of the intended check, but the actual bridge must demonstrate that.
3. A validator rebuilt from the same source can provide useful source-level
   evidence. Label it separately from a call into the installed DLL. Matching a
   source commit is not proof of identical build output or behavior.

Microsoft's binary-compatibility policy has linker/runtime restrictions and does
not establish compatibility of arbitrary third-party C++ types or build macros.
Treat successful linking as a preliminary check, followed by behavioral tests.
[Microsoft C++ binary compatibility](https://learn.microsoft.com/en-us/cpp/porting/binary-compat-2015-2017?view=msvc-170).

**Owner handoff:** if this route is chosen, provide a complete installed/supplied
Windows x64 C++ toolchain and its location, or a pinned matching model-free
validator. Agents can then qualify and use it. No toolchain installation, ABI
compatibility or native grammar conformance is claimed complete here.
