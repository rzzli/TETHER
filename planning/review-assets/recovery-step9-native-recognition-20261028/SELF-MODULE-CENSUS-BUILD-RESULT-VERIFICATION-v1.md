# Census bridge build result verification

VERIFIED: the exact compile/link batch succeeded; the resulting census-capable bridge was not executed.

All 234 input pins (76,213,854 bytes) still match. The fourteen-file output universe is exact: eleven early-receipted files, thirteen terminal-receipted files and the terminal seal itself. All receipt/seal hashes and the eight-event journal chain match. Compiler PID9916 and linker PID23384 each recorded exit0 and reaping, with no capture truncation, timeout or cleanup error. Total time before the terminal seal was4.656s. Three empty compiler-created telemetry-named directories contain no payload files.

Source and compiled copy match child v8 SHA256 28a515c2e7d8301f7648152014e481c9a98de1559ea76d3d23ca533e1cfb8a18; the unchanged header remains recognition-disabled. EXE SHA256 is 559e4e9a654c9487679c551eebf73d6a279416d0990f491d0918d99cdb6f6183 (249344 bytes). Independent PE parsing matches the recorded imports: x64 PE32+, console subsystem, ASLR/NX/high entropy, no delay imports, unchanged ordinary DLL-name set and no prohibited static target/network/process-launch import. Added C++ exception-pointer imports are consistent with reviewed <exception> use; this is static evidence only.

Read-lease context-manager cleanup returned before final sealing. The retained observation does not attest individual-handle closes, tool descendants/network or complete transitive toolchain closure. The legacy v5 journal terminal-event name was deliberately retained. No generated result, target API, census or recognition operation was run by this verification. The JSON provides exact source/header/compiled-copy/EXE/receipt/terminal pins and relative outputs[] for a separately reviewed future parent.
