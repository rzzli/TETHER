# Q01 implementation and qualification — TETHER 0.4.2

The TETHER command boundary now supervises its owned engine child with an absolute elapsed-time deadline and one aggregate stdout/stderr byte cap. The implementation replaces the old unlimited `communicate()` call without changing the frozen AsOf 0.3.11 engine or its workflow budgets. Qualification is local Windows execution, not cross-platform certification or a scientific result.

## Contract

- Immutable `ProcessLimits` defaults to **3,600 seconds** and **16,777,216 output bytes**. Time must be positive and finite; byte limits must be integers from 1 through 67,108,864. Boolean aliases are rejected. Defaults are conservative operational choices, not measurements establishing feasibility for an arbitrary scientific workload.
- CLI `--process-timeout-seconds` and `--process-output-bytes` configure child-backed subcommands. Full option spelling is required. In-process verification rejects these arguments; outer inspection rejects explicitly supplied limits. The engine's default 300-second workflow budget is unchanged.
- The original accepted CLI argument list retains its existing invocation hash semantics. Wrapper flags are removed only from the engine dispatch arguments. Effective limits are separately bound in the prepared/dispatch events, manifest and supervision report.
- The deadline starts immediately before process creation, spans child execution and pipe EOF, and is checked again after the last read/poll before success. OS process creation itself cannot be preempted; elapsed time is checked after it returns.
- The qualified Windows CLI uses `PeekNamedPipe` to poll unbuffered pipes, with one reader and no shared handles. Each pipe gets at most 16 KiB per polling round. There are no pipe-reader threads. The POSIX `select` branch is present but was **not executed here**. Windows synchronous handles are not universally nonblocking in arbitrary embedded multithreaded applications; that use is unqualified.
- Both streams share one retained-byte budget. Exact-cap output succeeds only after EOF; one additional byte proves overflow and is counted but not retained. Observed counts on incomplete captures are lower bounds, not total child output. The cap bounds captured bytes, not the Python interpreter's total memory; converting buffers into immutable result bytes can temporarily duplicate bounded captured content.
- Failure cleanup attempts termination, bounded draining, kill when necessary and reaping, with a separate **five-second cleanup wait budget**. It targets only the owned child. Descendants are not contained or terminated. An inherited pipe handle cannot keep the polling loop alive beyond its deadline. Native OS operations themselves are not a hard realtime guarantee.
- Original timeout/overflow/interruption/read errors remain primary. Cleanup errors, EOF state, retained/observed byte counts, process-started/reaped state and measured elapsed intervals are recorded. No recovery path redispatches.

For outer `run` and `demo`, directories/journals are reserved before dispatch; failure retains capped stream files and `tether-failure.json`, without a success receipt. Existing inner journals retain pending-call reservations and measured/estimated usage. Successful manifests and journals bind the limits and supervision declaration; verification checks stream sizes, finite timing, exact field types, EOF/reaping and the deadline/cap constraints. These are consistency checks, not independent measurements of billing or OS execution authenticity.

Other delegated commands have no implicit outer directory. Their failures emit the bounded supervision diagnostic to stderr, including cleanup/reaping uncertainty. They do not implicitly create captured-byte artifacts. Existing engine output paths, if present, remain available. In-process outer verification and publication after the child returns are outside the child deadline.

## Validation

| Check | Outcome | Evidence |
|---|---|---|
| Existing package suite after implementation | 73 passed | `PACKAGE-TESTS-FIRST.txt` |
| Added real-child and CLI regression module | 13 passed | `PROCESS-TESTS-FIRST.txt` |
| Combined package suite | **86 passed in 31.649 seconds** | `PACKAGE-TESTS-FINAL.txt` |
| Independent supervisor/failure probes | 87 assertions passed, including exact cap, overflow, block/trickle, per-stream/dual floods, inherited descendant pipe, terminate failure, invalid limits and pending/measured accounting | `../peer/` reports |
| Independent CLI/proof probes | 18 assertions passed, including genuine source-inclusive completion, invalid flags and five resealed supervision inconsistencies | `../peer/` reports |
| Independent interruption/delegation checks | 10 assertions passed | `../peer/` reports |
| Offline final wheel | CRC/RECORD closure and 16 runtime source files checked; 22 wheel members; installed with original frozen core wheel; isolated imports without PyArrow | `WHEEL-QUALIFICATION-FINAL.json` |
| Installed final wheel behavior | Genuine demo, externally anchored verification, wrong-anchor rejection, actual CLI timeout/overflow, capped retained streams, one dispatch, child reaping and inspection without retry all passed | Same qualification report |

The final test run was followed only by a docstring/README clarification of the Windows embedding limitation. The final installed wheel includes that clarification and was requalified. Earlier build evidence remains retained rather than overwritten. One initial metadata-sync invocation used an unsupported `uv sync --build-constraints` argument; it failed before synchronization, and the supported offline locked sync then passed. The wheel build itself used the retained setuptools 84.0.0 constraints. Setuptools emitted the existing license-table deprecation warning; no unrelated packaging rewrite was made.

Final wheel: `data/cache/tether-042-qualified-build-v2/wheels/tether_target_agents-0.4.2-py3-none-any.whl`, **32,642 bytes**; SHA-256 **`090c49f8613101d31dd5a7859033ffcf830223ab99b3ffaa9b2f53abfda0dc06`**. Local Windows-only qualification does not claim hosted CI, POSIX behavior, native-model transport qualification, or a rebuilt paper package. Previous 0.4.0/0.4.1 outer artifacts continue to require their pinned launcher implementations.

## Changed surface and residual work

Current package changes are the new `_process.py`, integration in `_presentation.py` and `_cli.py`, finite-module registration, version/lock updates to 0.4.2, updated front-door regressions, 13 new process tests and package README. Tests preserve failure causes under interruption, pipe failure, cleanup failure, unavailable metadata writes and concurrent output reservation.

The old urllib transport timeout semantics and old packet admission read implementation in `src/asof` remain unchanged. This change provides an outer process envelope when those engine commands are launched through this CLI; it does not rewrite the old transport contracts or strengthen direct legacy Python calls. No model execution, provider download, protected outcome inspection, new scientific computation or provider spending was introduced.
