# Trusted-platform bridge build result verification

VERIFIED: the exact compile/link batch succeeded. The generated executable was not run.

All257 input pins (76,775,545 bytes), fourteen output files, eight journal events and every receipt/seal hash match. Compiler PID19268 and linker PID8640 each recorded exit0 and reaping, with bounded untruncated captures and no timeout/cleanup error. Context-manager lease cleanup returned before the final seal at4.750s. Eleven early-receipted and thirteen terminal-receipted files plus the seal form the exact file universe; three compiler-created telemetry-named directories are empty.

Source and compiled copy match dbf76b19. The258560-byte EXE SHA256 is 2feffe29d916f9345067d9458714525eb73a2554824f3567383856562c2b2464. The unchanged data header keeps recognition false and expected version empty. The source/contract/protocol agree on trusted-System32 policy fingerprint807995f6. Policy ID/hash/rejection markers are present as static bytes; their presence proves no runtime formatter or policy behavior.

Independent PE parsing equals the build report: x64 PE32+, console subsystem, ASLR/NX/high entropy, no delay imports and no prohibited static target/network/process-launch imports. The ordinary DLL-name set matches the census build. Exact import deltas are retained in JSON.

No helper, compiler or generated executable was rerun by this verifier. Known fixed inputs were hashed; no unknown platform image or metadata-derived path was opened. Tool descendants/network, individual lease-handle closes and complete transitive toolchain closure remain unqualified. Actual policy/ABI observation requires independent parent/protocol review and a separate root decision. The JSON exposes exact source/header/copy/receipt/terminal/EXE pins and relative outputs[] for that future parent.
