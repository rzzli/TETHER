# Corrected typed ABI bridge v4 — build result verification

AI engineering read-only verification, 2026-10-28 UTC. **The corrected x64 bridge compiled and linked; it has not been executed.** This is not ABI, recognition or scientific acceptance.

[Verification JSON](TYPED-ABI-BUILD-V4-RESULT-VERIFICATION.json), SHA `48535ac53123db5246c95b7d7ed9211695531e687346e9854ca98d5c51d17473`, verifies all 194 input pins, exactly 14 files and the eight-event journal chain. All 11 early-receipt outputs and 13 terminal-inventory outputs match. Post-lease context cleanup returned without error, the complete terminal seal agrees, and no authoritative failure marker is present.

Compiler PID 10576 exited 0/reaped after 1.907 seconds; linker PID 36744 exited 0/reaped after 0.047 seconds. Both match the declared commands/captures and finite tool ceilings. Elapsed time before the terminal seal is 4.125 seconds. No compiler or linker was rerun for this review.

The 191,488-byte executable is SHA `c5df7b62ce1de641407d973e5994aa91ea244331e5de2d243d3f1e717997e398`. Independent static parsing confirms x64 PE32+, console subsystem, ASLR/NX/high-entropy flags, exact reported ordinary imports and no delay imports. No target DLL is statically linked. The own source copy matches source `2f340355…0794ae`; all seven public headers and the unchanged pin header match their approved bytes. Recognition remains false and expected API version remains empty. The retained 25-symbol owner proof binds this corrected source; export presence does not establish callable ABI compatibility.

The cleanup record covers the context-manager outcome, not individually instrumented handle closes. Tool ownership covers the launched compiler/linker handles, not all descendants or a complete transitive toolchain. The old failed ABI, old executable and old build artifacts remain untouched. The generated executable and permitted DLL inputs were read for hashes/static inspection; none was executed or loaded. No CPU backend, model, GGUF or protected payload was read. A separately qualified parent/protocol and root decision are still required before one new ABI observation.
