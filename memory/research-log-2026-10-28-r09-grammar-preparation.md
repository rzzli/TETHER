---
name: research-log-2026-10-28-r09-grammar-preparation
description: Frozen 109-case corpus and pinned DLL/source commit discovery; native conformance awaits toolchain/bridge and build qualification
metadata:
  type: project
updated: 2026-10-28
---

# Grammar gate preparation

This follows accepted [[research-log-2026-10-28-r09-native-integration]]. No TETHER
runtime/resource/test file changed after its 1,724-test/324-pin acceptance.
Static inspection rehashes approved b11717 common/core/server DLLs and finds C++
converter overloads and public grammar sampler entry points. No DLL was loaded.
A static helper's initial 2,048-byte name bound failed on a 2,325-byte template
export; a bounded correction passes, with the initial failure retained.

All 105 earlier synthetic oracle cases remain unchanged; four explicit ASCII/
astral 1,800/1,801-character probes make a frozen 109-case corpus. Current isolated
installed 0.3.9 Python and PowerShell7.6.5/JsonSchema.NET checks agree except the
known post-validation-only cross-claim uniqueness rule. This is not native grammar
acceptance or source/biological validation. No model/server/tokenizer was run.

Pinned-tag primary converter inspection identifies incomplete-conversion warnings,
compile-dependent paths and joint string-pattern/length handling as native test
targets. Browser cache misses are not file-absence evidence. A restricted-shell
Git lookup failed; a separately permitted credentials-disabled public lookup
resolved b11717 to 848bbda9041decd87904f7eb5a2990863ecce03b, matching the retained
runtime's 848bbda90 build prefix. That old startup log reports Clang20.1.8 for
Windows x86_64. Source/binary build equivalence, headers and flags remain
unqualified. No repository clone, source archive/runtime binary or paid data was acquired.

No C++ compiler/CMake/Ninja was found on PATH or standard VS/LLVM/SDK paths. The
owner confirmed no existing C++ toolchain. The current model-free
bridge route needs MSVC-compatible ABI and pinned headers/build identity; no unsafe
C++-layout guessing, system installation or real inference was attempted. Human
reviews remain pending. Resume from the
[retained plan](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-grammar-20261028/DISCOVERY-AND-NEXT-STEPS.md);
native conformance/R09–R16 remain open.

The owner subsequently installed Build Tools. Its scoped own-source probe now
passes compile/link/run plus Windows SDK/STL operations without restarting.
Compiler 19.51.36260.0, linker 14.51.36260.0 and SDK 10.0.26100.0 are recorded;
no llama DLL/model/server was loaded. A first optional linker-help exit-code
assumption failed after successful compilation; the corrected v2 harness preserves
that failure and accepts only the successful compiled probe. This removes the
toolchain-availability constraint, not ABI/build/grammar qualification. A typed
actual-DLL converter bridge is being designed with exact source headers. Native
execution is gated on completion of the separate duration-correction validation.
