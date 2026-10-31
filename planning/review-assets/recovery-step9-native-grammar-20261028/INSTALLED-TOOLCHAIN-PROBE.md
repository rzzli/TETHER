# Installed Windows x64 toolchain works without restarting

28 October 2026 UTC. The owner reported installing Build Tools and authorized a
local compiler/SDK probe. A fresh author-written C++ program compiled, linked and
ran successfully. No restart was needed for this probe. Earlier missing-toolchain
reports remain preserved as observations made before installation.

Authoritative result: [TOOLCHAIN-LOCAL-PROBE-v2.json](TOOLCHAIN-LOCAL-PROBE-v2.json).
The installer reports Build Tools 2026 version `18.11.12324.101`, complete and
launchable, with `isRebootRequired: false`. The x64/x86 tools component query passes.

| Item | Observed |
|---|---|
| Installation | `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools` |
| Environment initialization | `Common7\Tools\VsDevCmd.bat -no_logo -arch=x64 -host_arch=x64` |
| Tool directory | `VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64` |
| Compiler / linker | `cl.exe` 19.51.36260.0 / `link.exe` 14.51.36260.0 |
| Windows SDK | 10.0.26100.0 |
| `_MSC_VER` / `_MSC_FULL_VER` | 1951 / 195136260 |
| `_MSVC_STL_UPDATE` / `_MSVC_STL_VERSION` | 202604 / 145 |
| `_ITERATOR_DEBUG_LEVEL` | 0 |
| `sizeof(std::string)` / `sizeof(std::vector<int>)` / pointer | 32 / 24 / 8 bytes |
| Windows API and STL operations | Passed |
| llama modules loaded in probe process | None |

The scoped environment and outputs are under
`data/cache/r09-installed-toolchain-probe-20261028T025723Z/`. Only approved build
environment keys were exported: PATH, INCLUDE, LIB, LIBPATH and relevant VS/SDK
variables. No complete environment or secrets were dumped. The parent process
environment is unchanged; no `setx`, installation or system configuration command
was used. Twenty selected compiler/linker/component/header/import-library hashes
were checked before and after. Exact initialization/compile/link/run arguments,
stdout/stderr, C++ source, object and executable hashes are retained in the report.

The first attempt also compiled and linked successfully, but its harness treated
`link.exe /?` returning 1100 as failure. That invocation printed complete normal
help and no stderr. The first report/cache are preserved. The corrected v2
harness explicitly recognizes that informational exit only after checking its
contents, then compiles and runs a fresh copy of the same author-written probe.
The successful executable returned zero.

No AsOf runtime/test/resource file was changed. No foreign/fetched source,
llama DLL, model or server was executed; no data/outcome payload was opened.
Parent Python guards report no denied/unapproved operations; this is not an
OS-wide process/network attestation of vendor environment initialization.

**Next:** use these absolute paths or the retained filtered environment for the
separately declared grammar bridge. Compiler usability and common STL sizes do
not establish the existing llama DLL's complete ABI/configuration, source/build
equivalence or grammar conformance. Those checks and human scientific review
remain separate.
