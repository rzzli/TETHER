# Native harmless worker: source preparation v3

This is author-written source and a prospective design. No compiler, linker, worker, target DLL or model was run for it. The Python harmless v4 qualification is still failed at unexplained overflow Job accounting; that evidence and the generic ABI total-1 predicate remain unchanged. This source does not establish a cause or clear the ABI gate.

The [standalone C++ worker](harmless_launch_worker_native_v3.cpp) removes Python startup, imports, `.pth` execution and Python's process-launch wrapper from a possible future controlled fixture. It retains a Windows console executable and OS/CRT initialization. Consequently it cannot by itself exclude console-host behavior, third-party instrumentation or other OS effects. Any actual qualification must independently retain identity and raw accounting observations; its success would qualify only this exact launcher/worker architecture on this host. Versions 1 and 2 source/design remain preserved. Version 2 added only failure evidence for an unexpected successful descendant: nullable returned PID/thread ID and wait, termination, reaping and handle-close outcomes. The expected rejected-association path and its acceptance predicate are unchanged; no new API family is used.

The consumed version-2 build failed at compilation with C4244 under the retained `/W4 /WX` policy: constructing `std::string` from `wstring` iterators implicitly narrows each character. No link or worker execution occurred. Version 3 changes exactly that one source line to the existing `utf8(expected_w)` function, after validation has restricted the value to exactly 64 lowercase ASCII hex characters. This preserves the expected SHA bytes and warning policy; it introduces no API or behavior change for eligible inputs. The failed build remains evidence, and this new source requires a separately reviewed fresh build.

## Source contract

The normal CLI is exactly `[OWN_EXE, MODE, CHILD_OUTPUT, EFFECTIVE_PROTOCOL, PROTOCOL_SHA256]`. Modes are `resources`, `overflow`, `sleep` and `suspended_abort`. The own module and `argv[0]` must agree and all paths must be existing canonical descendants of the fixed project `data/cache` root, with no reparse ancestor. Protocol filename is `effective-protocol.json`; the child output must equal its parent plus `execution/MODE/child`.

The worker reads at most 1 MiB of protocol bytes, using a read handle that denies write/delete sharing, and verifies SHA256 through Windows BCrypt. It neither parses general JSON nor claims independent validation of the protocol role. The separately reviewed parent remains authoritative for exact role, executable/source hashes, file leases, limits and argv. The worker echoes the matching hash, own executable, mode and PID in a bounded marker. An additional exact two-argument `--rejected-child` entry immediately returns 0, without recursion, marker or I/O.

| Mode | Prospective behavior |
|---|---|
| `resources` | Allocate, touch and release a 64 KiB successful control; attempt a 384 MiB committed `VirtualAlloc`, recording rejection and its error. Make exactly one `CreateProcessW` attempt of the same own executable with `--rejected-child`, no shell/search/inherited handles, and record the expected failure 1816. An unexpected success receives at most two seconds of owned-handle wait/termination cleanup and still fails the fixture. Publish the result before enforcing memory rejection, one spawn attempt, and quota rejection. |
| `overflow` | Countedly write exactly 73,728 `x` bytes to inherited stdout, then sleep 120 seconds. This path has no descendant attempt. Parent capture overflow must stop it first. |
| `sleep` | Sleep 120 seconds; parent timeout must stop it first. |
| `suspended_abort` | Reaching the worker body publishes a started marker and returns failure. The parent must stop the assigned worker before resume, so no marker should exist in the qualified case. |

Started/result markers are bounded to 4 KiB, written completely to exclusive pending files, flushed and closed, then published by a same-directory non-overwriting rename. Errors leave partial evidence and return nonzero with bounded, counted stderr. The worker performs no directory creation or cleanup of previous output. It cannot replace an existing marker. Its own write failure is not converted into a successful observation.

## Separate gates before use

The intended build uses the same x64 `/MD` CRT selection as the existing ABI bridge, with `/EHsc /std:c++17 /utf-8 /D_ITERATOR_DEBUG_LEVEL=0`, the Windows SDK and `bcrypt.lib`. This is not a static-CRT comparison. The eventual exact compiler/link argv, source copies, tool/header hashes and actual PE imports require a new reviewed build protocol. No worker execution is part of that build. Reuse the frozen build helper's bounded tool invocation, guard, environment and PE inspection functions rather than adding a second build framework.

Any later real qualification needs a separately reviewed parent/protocol and root decision, the compiled EXE plus CRT/system dependency pins, exclusive outputs, original Job controls, capped captures, finite cleanup and authoritative failure seals. The resources-only planned descendant accounting policy cannot justify extra associations in overflow/sleep or in the ABI child. No native fixture result, ABI version observation, tokenizer/EOG test, grammar conformance or scientific validation is claimed here.
